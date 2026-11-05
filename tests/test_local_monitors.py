"""Offline regression tests: no GitHub calls or real pipeline state changes."""
import contextlib
import importlib.util
import io
import json
import runpy
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def load_monitor(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
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
    def test_legacy_status_fingerprint_uses_gh_started_at_without_target_url(self):
        check = {"__typename": "StatusContext", "context": "CodeRabbit",
                 "startedAt": "2026-10-22T19:16:14Z", "state": "SUCCESS", "targetUrl": ""}
        fingerprint = oss.ci_fingerprint([check])
        self.assertIsNotNone(fingerprint)
        self.assertNotEqual(fingerprint, oss.ci_fingerprint([
            dict(check, startedAt="2026-10-22T19:16:15Z")]))

    def run_round(self, module, path, keys, values):
        loader = "load_state_keys" if module is scope else "load_keys"
        output = io.StringIO()
        with patch.object(module, "CANONICAL", str(path)), \
                patch.object(module, "STATE", str(path.parent / "STATE.md")), \
                patch.object(module, "LEGACY_PATHS", ()), \
                patch.object(module, "REPORT", str(path.parent / "PR_STATUS.md")), \
                patch.object(module, loader, return_value=dict.fromkeys(keys)), \
                patch.object(module, "fetch", side_effect=lambda k: values[k]), \
                patch.object(oss, "audit_scope"), \
                contextlib.redirect_stdout(output):
            status = module.main()
        return output.getvalue(), status

    def test_exit_status_and_partial_success(self):
        for module in (scope, oss):
            for states in ((), ("QUERY_ERROR",), ("OPEN", "QUERY_ERROR"), ("OPEN",)):
                with self.subTest(module=module.__name__, states=states), tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "pr_state.json"
                    values = {f"owner/repo#{i}": snapshot(state) for i, state in enumerate(states, 1)}
                    _, status = self.run_round(module, path, values, values)
                    self.assertEqual(status, 1 if not states or "QUERY_ERROR" in states else 0)
                    if "OPEN" in states:
                        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["owner/repo#1"]["state"], "OPEN")
                    else:
                        self.assertFalse(path.exists())

    def test_cli_exits_nonzero_for_incomplete_rounds(self):
        original_read = Path.read_text
        for name in ("monitor_scope", "monitor_oss"):
            for states in ((), ("QUERY_ERROR",), ("OPEN", "QUERY_ERROR"), ("OPEN",)):
                with self.subTest(module=name, states=states), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    ledger = "\n".join(f"| [#{i}](https://github.com/owner/repo/pull/{i}) | OPEN(today) |"
                                       for i in range(1, len(states) + 1))
                    def read_text(path, *args, **kwargs):
                        return ledger if path == ROOT / "STATE.md" else original_read(path, *args, **kwargs)
                    def query(command, **kwargs):
                        failed = states[int(command[3]) - 1] == "QUERY_ERROR"
                        response = dict(state="OPEN", statusCheckRollup=[], headRefOid="a" * 40)
                        return SimpleNamespace(returncode=int(failed), stdout=json.dumps(response), stderr="offline")
                    with patch("pr_state.PR_STATE_PATH", root / "pr_state.json"), \
                            patch("pr_state.PR_STATUS_PATH", root / "PR_STATUS.md"), \
                            patch("pr_state.LEGACY_PATHS", ()), \
                            patch.object(Path, "read_text", read_text), \
                            patch("subprocess.run", side_effect=query), patch("time.sleep"), \
                            contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as result:
                        runpy.run_path(str(ROOT / "tools" / f"{name}.py"), run_name="__main__")
                    self.assertEqual(result.exception.code, 1 if not states or "QUERY_ERROR" in states else 0)

    def test_round_helper_uses_temporary_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pr_state.json"
            with patch.object(oss, "reconcile_state_ledger", return_value=[]) as reconcile:
                self.run_round(oss, path, ["owner/repo#1"], {"owner/repo#1": snapshot("MERGED")})
            self.assertEqual(reconcile.call_args.kwargs.get("state_path"), str(path.parent / "STATE.md"))

    def test_error_preserves_open_baseline_and_later_merge_reports(self):
        for module in (scope, oss):
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "baseline.json"
                key = "owner/repo#1"
                baseline = {key: snapshot()}
                path.write_text(json.dumps(baseline), encoding="utf-8")
                output, _ = self.run_round(module, path, [key], {key: snapshot("QUERY_ERROR")})
                self.assertNotIn("离场", output)
                saved = json.loads(path.read_text(encoding="utf-8"))[key]
                for field, value in baseline[key].items():
                    self.assertEqual(saved[field], value)
                self.assertIn("query_error", saved)
                self.assertIn("query_error_at", saved)
                output, _ = self.run_round(module, path, [key], {key: snapshot("MERGED")})
                self.assertIn("OPEN -> MERGED", output)
                self.assertEqual(json.loads(path.read_text(encoding="utf-8"))[key]["state"], "MERGED")

    def test_new_tracked_pr_reports_after_successful_query(self):
        for module in (scope, oss):
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "baseline.json"
                old, new = "owner/repo#1", "owner/repo#2"
                path.write_text(json.dumps({old: snapshot()}), encoding="utf-8")
                output, _ = self.run_round(module, path, [old, new],
                                        {old: snapshot(), new: snapshot("QUERY_ERROR")})
                self.assertNotIn("新增在飞", output)
                self.assertNotIn("state", json.loads(path.read_text(encoding="utf-8"))[new])
                output, _ = self.run_round(module, path, [old, new],
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
                patch.object(fresh, "ALWAYS_SLICES", 1), \
                patch.object(fresh, "fetch_newest", side_effect=fetch), \
                patch("work_queue.refresh", return_value=[]) as refresh, \
                patch.object(sys, "argv", argv or ["monitor_fresh.py"]), \
                contextlib.redirect_stdout(output):
            fresh.main()
            refresh.assert_called_once_with()
        return output.getvalue(), json.loads(path.read_text(encoding="utf-8"))

    def test_round_helper_does_not_refresh_real_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            with patch("work_queue.refresh", side_effect=AssertionError("test leaked into real queue")) as refresh:
                self.run_round(path, (["owner/repo"], []), lambda repo, since: [])
            refresh.assert_not_called()

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


LEDGER = """# STATE.md — 跟踪范围 + 指针

## OSS 贡献在飞（3）

| PR | 仓库 | 状态 | 摘要 |
| --- | --- | --- | --- |
| [#1](https://github.com/owner/repo/pull/1) | owner/repo | OPEN(2026-10-01) | stays |
| [#2](https://github.com/owner/repo/pull/2) | owner/repo | OPEN(2026-10-02) | merged away |
| [#3](https://github.com/owner/other/pull/3) | owner/other | OPEN(2026-10-03) | closed away |

## 个人 fork 在飞（2）

| PR | 仓库 | 状态 | 摘要 |
| --- | --- | --- | --- |
| [#7](https://github.com/me/mine/pull/7) | me/mine | OPEN(2026-10-04) | stays |
| [#8](https://github.com/me/mine/pull/8) | me/mine | OPEN(2026-10-05) | merged away |
"""


class LedgerReconcileTests(unittest.TestCase):
    def cur(self, *states):
        names = ["owner/repo#1", "owner/repo#2", "owner/other#3",
                 "me/mine#7", "me/mine#8"]
        return {k: {"state": s} for k, s in zip(names, states)}

    def test_reconcile_requires_ledger_lock_before_reading(self):
        from pipeline_state import file_lock
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "STATE.md"
            original = LEDGER.encode("utf-8")
            path.write_bytes(original)
            with file_lock(path), self.assertRaises(RuntimeError):
                oss.reconcile_state_ledger(self.cur("OPEN", "MERGED"), state_path=str(path))
            self.assertEqual(path.read_bytes(), original)

    def test_failed_atomic_replace_preserves_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "STATE.md"
            original = LEDGER.replace("\n", "\r\n").encode("utf-8")
            path.write_bytes(original)
            with patch("pipeline_state.os.replace", side_effect=OSError("disk failure")), self.assertRaises(OSError):
                oss.reconcile_state_ledger(self.cur("OPEN", "MERGED"), state_path=str(path))
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(path.parent.glob("*.tmp")), [])

    def test_merged_and_closed_rows_are_removed_and_counts_fixed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "STATE.md"
            path.write_text(LEDGER, encoding="utf-8")
            removed = oss.reconcile_state_ledger(
                self.cur("OPEN", "MERGED", "CLOSED", "OPEN", "MERGED"), state_path=str(path))
            self.assertEqual(len(removed), 3)
            text = path.read_text(encoding="utf-8")
            self.assertIn("| [#1]", text)
            self.assertIn("| [#7]", text)
            self.assertNotIn("#2", text)
            self.assertNotIn("owner/other", text)
            self.assertNotIn("#8", text)
            self.assertIn("## OSS 贡献在飞（1）", text)
            self.assertIn("## 个人 fork 在飞（1）", text)

    def test_query_errors_and_open_rows_never_touch_the_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "STATE.md"
            path.write_text(LEDGER, encoding="utf-8")
            self.assertEqual(oss.reconcile_state_ledger(
                self.cur("QUERY_ERROR", "QUERY_ERROR", "OPEN", "OPEN", "QUERY_ERROR"),
                state_path=str(path)), [])
            self.assertEqual(path.read_text(encoding="utf-8"), LEDGER)

    def test_line_endings_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "STATE.md"
            path.write_bytes(LEDGER.replace("\n", "\r\n").encode("utf-8"))
            oss.reconcile_state_ledger(
                self.cur("OPEN", "MERGED", "OPEN", "OPEN", "OPEN"), state_path=str(path))
            raw = path.read_bytes()
            self.assertIn(b"\r\n", raw)
            self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))

    def test_ledger_removed_before_read_is_a_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "STATE.md"
            path.write_bytes(LEDGER.encode("utf-8"))
            with patch.object(Path, "read_bytes", side_effect=FileNotFoundError):
                self.assertEqual(oss.reconcile_state_ledger(self.cur("MERGED"), state_path=str(path)), [])

    def test_missing_state_file_is_a_noop(self):
        self.assertEqual(oss.reconcile_state_ledger(
            self.cur("MERGED"), state_path="Z:/definitely/missing/STATE.md"), [])
