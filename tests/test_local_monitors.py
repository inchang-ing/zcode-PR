"""Offline regression tests: no GitHub calls or real pipeline state changes."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_monitor(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / ".trash" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scope = load_monitor("monitor_scope")
oss = load_monitor("monitor_oss")
fresh = load_monitor("monitor_fresh")


def snapshot(state="OPEN"):
    return {"state": state, "reviewDecision": "-", "mergeable": "MERGEABLE",
            "updatedAt": "2026-10-15T10:00:00Z", "url": "https://example.invalid/pr",
            "ci": "no-checks", "title": "Example PR"}


def issue(number, created):
    return {"number": number, "created_at": created.isoformat(),
            "title": f"issue {number}", "labels": [], "user": {"login": "reporter"}}


class PRMonitorTests(unittest.TestCase):
    def run_round(self, module, path, keys, values):
        loader = "load_state_keys" if module is scope else "load_keys"
        output = io.StringIO()
        with patch.object(module, "CANONICAL", str(path)), \
                patch.object(module, "LEGACY_PATHS", ()), \
                patch.object(module, "REPORT", str(path.parent / "PR_STATUS.md")), \
                patch.object(module, loader, return_value=dict.fromkeys(keys)), \
                patch.object(module, "fetch", side_effect=lambda k: values[k]), \
                contextlib.redirect_stdout(output):
            module.main()
        return output.getvalue()

    def test_error_preserves_open_baseline_and_later_merge_reports(self):
        for module in (scope, oss):
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "baseline.json"
                key = "owner/repo#1"
                baseline = {key: snapshot()}
                path.write_text(json.dumps(baseline), encoding="utf-8")
                output = self.run_round(module, path, [key], {key: snapshot("QUERY_ERROR")})
                self.assertNotIn("离场", output)
                saved = json.loads(path.read_text(encoding="utf-8"))[key]
                for field, value in baseline[key].items():
                    self.assertEqual(saved[field], value)
                self.assertIn("query_error", saved)
                self.assertIn("query_error_at", saved)
                output = self.run_round(module, path, [key], {key: snapshot("MERGED")})
                self.assertIn("OPEN -> MERGED", output)
                self.assertEqual(json.loads(path.read_text(encoding="utf-8"))[key]["state"], "MERGED")

    def test_new_tracked_pr_reports_after_successful_query(self):
        for module in (scope, oss):
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "baseline.json"
                old, new = "owner/repo#1", "owner/repo#2"
                path.write_text(json.dumps({old: snapshot()}), encoding="utf-8")
                output = self.run_round(module, path, [old, new],
                                        {old: snapshot(), new: snapshot("QUERY_ERROR")})
                self.assertNotIn("新增在飞", output)
                self.assertNotIn("state", json.loads(path.read_text(encoding="utf-8"))[new])
                output = self.run_round(module, path, [old, new],
                                        {old: snapshot(), new: snapshot()})
                self.assertIn(f"[新增在飞] {new}", output)

    def test_empty_ledger_and_invalid_json_do_not_erase_baseline(self):
        for module in (scope, oss):
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "baseline.json"
                original = '{"owner/repo#1": "keep"}'
                path.write_text(original, encoding="utf-8")
                self.run_round(module, path, [], {})
                self.assertEqual(path.read_text(encoding="utf-8"), original)
                path.write_text("{broken", encoding="utf-8")
                with self.assertRaises(json.JSONDecodeError):
                    self.run_round(module, path, ["owner/repo#1"], {"owner/repo#1": snapshot()})
                self.assertEqual(path.read_text(encoding="utf-8"), "{broken")

    def test_invalid_api_state_is_query_error_not_closed(self):
        for module in (scope, oss):
            with self.subTest(module=module.__name__), \
                    patch.object(module, "gh", return_value='{"message": "failed"}'), \
                    patch("time.sleep"):
                self.assertEqual(module.fetch("owner/repo#1")["state"], "QUERY_ERROR")

    def test_alternating_entry_points_preserve_other_fields_and_checked_at(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pr_state.json"
            key = "owner/repo#1"
            oss_value = snapshot()
            oss_value.update(ci="1✓/0✗/0…/0ERR", title="Keep this title", checked_at="2026-10-15T01:00:00+00:00")
            self.run_round(oss, path, [key], {key: oss_value})
            scope_value = {k: v for k, v in snapshot().items() if k not in {"ci", "title"}}
            scope_value.update(reviewDecision="APPROVED", checked_at="2026-10-15T02:00:00+00:00")
            self.run_round(scope, path, [key], {key: scope_value})
            current = json.loads(path.read_text(encoding="utf-8"))[key]
            self.assertEqual(current["ci"], oss_value["ci"])
            self.assertEqual(current["title"], "Keep this title")
            self.assertEqual(current["reviewDecision"], "APPROVED")
            self.assertEqual(current["checked_at"], scope_value["checked_at"])
            self.run_round(oss, path, [key], {key: {"state": "QUERY_ERROR", "_err": "rate limit",
                "ci": "-", "title": "", "mergeable": "-", "reviewDecision": "-",
                "checked_at": "2026-10-15T03:00:00+00:00"}})
            current = json.loads(path.read_text(encoding="utf-8"))[key]
            self.assertEqual(current["checked_at"], scope_value["checked_at"])
            self.assertEqual(current["query_error_at"], "2026-10-15T03:00:00+00:00")
            self.assertEqual(current["ci"], oss_value["ci"])
            report = (path.parent / "PR_STATUS.md").read_text(encoding="utf-8")
            self.assertIn("生成时间", report)
            self.assertIn("最后成功核验", report)
            self.assertIn("rate limit", report)
            self.assertIn("Keep this title", report)


class FreshMonitorTests(unittest.TestCase):
    def run_round(self, path, tiers, fetch, argv=None):
        output = io.StringIO()
        with patch.object(fresh, "STATE_PATH", str(path)), \
                patch.object(fresh, "build_tiers", return_value=tiers), \
                patch.object(fresh, "fetch_newest", side_effect=fetch), \
                patch.object(sys, "argv", argv or ["monitor_fresh.py"]), \
                contextlib.redirect_stdout(output):
            fresh.main()
        return output.getvalue(), json.loads(path.read_text(encoding="utf-8"))

    def test_paginates_until_watermark_including_boundary_and_filters_prs(self):
        since = datetime(2026, 10, 15, 10, tzinfo=timezone.utc)
        pr = issue(3, since + timedelta(minutes=3))
        pr["pull_request"] = {}
        pages = [json.dumps([issue(4, since + timedelta(minutes=4)), pr]),
                 json.dumps([issue(2, since + timedelta(minutes=2)), issue(1, since)]),
                 json.dumps([issue(0, since - timedelta(seconds=1))])]
        with patch.object(fresh, "PER_PAGE", 2), patch.object(fresh, "gh_api", side_effect=pages) as api:
            result = fresh.fetch_newest("owner/repo", since)
        self.assertEqual([it["num"] for it in result], [4, 2, 1])
        self.assertEqual(api.call_count, 3)
        self.assertIn("page=3", api.call_args.args[0])
        self.assertIn("state=all", api.call_args.args[0])

    def test_later_page_failure_discards_partial_result(self):
        since = datetime(2026, 10, 15, 10, tzinfo=timezone.utc)
        for failed in ("", "{}", "not-json", '[{"number": 1}]'):
            with self.subTest(failed=failed), patch.object(fresh, "PER_PAGE", 1), \
                    patch.object(fresh, "gh_api", side_effect=[json.dumps([issue(2, since)]), failed]):
                self.assertIsNone(fresh.fetch_newest("owner/repo", since))

    def test_failed_repo_does_not_advance_while_successful_repo_does(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            previous = "2026-10-01T00:00:00+00:00"
            path.write_text(json.dumps({"default_since": previous,
                "repo_last_success": {"a/ok": previous, "b/fail": previous}}), encoding="utf-8")
            output, state = self.run_round(path, (["a/ok", "b/fail"], []),
                                          lambda repo, since: [] if repo == "a/ok" else None)
            self.assertEqual(state["repo_last_success"]["b/fail"], previous)
            self.assertGreater(state["repo_last_success"]["a/ok"], previous)
            self.assertIn("b/fail query incomplete", output)

    def test_legacy_migration_replays_and_unscanned_repo_keeps_fixed_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            previous = datetime.now(timezone.utc) - timedelta(minutes=5)
            path.write_text(json.dumps({"last_check": previous.isoformat(),
                "seen": {"a/first#1": previous.isoformat()}, "rot_index": 0}), encoding="utf-8")
            starts = {}

            def fetch(repo, since):
                starts[repo] = since
                return [{"repo": repo, "num": 1, "age_h": 0, "title": "known", "labels": "", "author": "u"}]

            output, state = self.run_round(path, ([], ["a/first", "b/second", "c/third"]), fetch)
            expected = previous - timedelta(days=fresh.PRUNE_DAYS)
            self.assertEqual(starts["a/first"], expected)
            self.assertNotIn("NEW: a/first#1", output)
            self.assertNotIn("b/second", state["repo_last_success"])
            _, state = self.run_round(path, ([], ["a/first", "b/second", "c/third"]), fetch)
            self.assertEqual(starts["b/second"], expected)
            self.assertEqual(state["default_since"], expected.isoformat())

    def test_rotating_repo_uses_its_own_previous_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            previous = "2026-10-10T00:00:00+00:00"
            path.write_text(json.dumps({"default_since": "2026-10-01T00:00:00+00:00",
                "last_check": "2026-10-14T00:00:00+00:00",
                "repo_last_success": {"a/rotating": previous}, "rot_index": 0}), encoding="utf-8")
            starts = []
            self.run_round(path, ([], ["a/rotating"]), lambda repo, since: starts.append(since) or [])
            self.assertEqual(starts, [datetime.fromisoformat(previous)])

    def test_init_keeps_failed_repo_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            _, state = self.run_round(path, (["a/ok", "b/fail"], []),
                lambda repo, since: [] if repo == "a/ok" else None,
                ["monitor_fresh.py", "--init"])
            self.assertIn("a/ok", state["repo_last_success"])
            self.assertNotIn("b/fail", state["repo_last_success"])
            self.assertIn("default_since", state)


class RoundLockTests(unittest.TestCase):
    def test_all_monitors_lock_before_reading_or_scanning(self):
        from pipeline_state import file_lock
        for module, state_name, loader in ((scope, "CANONICAL", "load_state_keys"),
                (oss, "CANONICAL", "load_keys"), (fresh, "STATE_PATH", "load_state")):
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "state.json"
                with patch.object(module, state_name, str(path)), patch.object(module, loader) as read:
                    with file_lock(path), self.assertRaises(RuntimeError):
                        module.main()
                    read.assert_not_called()


if __name__ == "__main__":
    unittest.main()
