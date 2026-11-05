"""Shared monitoring behavior; every external boundary is replaced offline."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import monitor_oss as oss
import monitor_scope as scope
import pr_status
import github_read

spec = importlib.util.spec_from_file_location("notification_monitor", ROOT / "repo-monitor/monitor.py")
notification = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notification)


class MonitorStructureTests(unittest.TestCase):
    def test_pr_entry_points_share_ledger_identity_and_open_formats(self):
        ledger = (
            "| [#1](https://github.com/Owner/Repo/pull/1) | OPEN | active |\n"
            "- **[#2](https://github.com/owner/repo/pull/2)** OPEN(today)\n"
            "| [#3](https://github.com/owner/repo/pull/3) | CLOSED | 原 OPEN(yesterday) |\n"
        )
        with patch.object(Path, "read_text", return_value=ledger):
            self.assertEqual(set(scope.load_state_keys()), {"owner/repo#1", "owner/repo#2"})
            self.assertEqual(scope.load_state_keys(), oss.load_keys())

    def test_both_entry_points_ignore_transient_mergeability_differences(self):
        for module in (scope, oss):
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                current = dict(state="OPEN", reviewDecision="-", mergeable="MERGEABLE",
                               ci="no-checks", title="Example")
                (root / "pr_state.json").write_text(json.dumps({"owner/repo#1":
                    dict(current, mergeable="UNKNOWN")}), encoding="utf-8")
                output = io.StringIO()
                with patch.object(module, "CANONICAL", root / "pr_state.json"), \
                     patch.object(module, "REPORT", root / "PR_STATUS.md"), \
                     patch.object(module, "STATE", str(root / "STATE.md")), \
                     patch.object(module, "LEGACY_PATHS", ()), \
                     patch.object(module, "load_state_keys" if module is scope else "load_keys",
                                  return_value={"owner/repo#1": {}}), \
                     patch.object(module, "fetch", return_value=current), \
                     patch.object(oss, "audit_scope"), contextlib.redirect_stdout(output):
                    self.assertEqual(module.main(), 0)
                self.assertNotIn("UNKNOWN->MERGEABLE", output.getvalue())
                self.assertNotIn("UNKNOWN -> MERGEABLE", output.getvalue())

    def test_pr_readers_resolve_cli_on_path_and_use_utf8(self):
        response = SimpleNamespace(returncode=0, stdout="{}", stderr="")
        for invoke in (lambda: scope.gh(["api", "endpoint"]),
                       lambda: oss.gh(["api", "endpoint"]),
                       lambda: pr_status.api("endpoint")):
            with self.subTest(invoke=invoke), patch("shutil.which", return_value="/portable/gh"), \
                 patch("subprocess.run", return_value=response) as run:
                invoke()
                self.assertEqual(run.call_args.args[0][0], "/portable/gh")
                self.assertEqual(run.call_args.kwargs.get("encoding"), "utf-8")
                self.assertIsNotNone(run.call_args.kwargs.get("timeout"))

    def test_digest_does_not_publish_active_upstream_references(self):
        event = {"key": "owner/repo#1", "url": "https://github.com/owner/repo/issues/1",
                 "title": "Ask @other-person about other/repo#2"}
        calls = []
        def http(method, url, payload=None, token=None, headers=None):
            calls.append((method, payload))
            return [] if method == "GET" else {"number": 1}
        with patch.dict("os.environ", GITHUB_REPOSITORY="own/repo"), \
             patch.object(notification, "http", side_effect=http), \
             contextlib.redirect_stdout(io.StringIO()):
            notification.gh_update_digest_issue("fake", [event])
        body = next(payload["body"] for method, payload in calls if method == "POST")
        self.assertIn("`owner/repo#1`", body)
        self.assertIn("`Ask @other-person about other/repo#2`", body)
        self.assertNotIn(event["url"], body)

    def test_scope_audit_uses_all_pages_and_rejects_incomplete_search(self):
        rows = [{"repository_url": "https://api.github.com/repos/owner/repo", "number": n}
                for n in range(1, 102)]
        pages = [{"items": rows[:100], "total_count": 101, "incomplete_results": False},
                 {"items": rows[100:], "total_count": 101, "incomplete_results": False}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "STATE.md"
            path.write_text("", encoding="utf-8")
            output = io.StringIO()
            response = SimpleNamespace(returncode=0, stdout=json.dumps(pages), stderr="")
            with patch.object(oss, "STATE", str(path)), patch("subprocess.run", return_value=response) as run, \
                 contextlib.redirect_stdout(output):
                oss.audit_scope()
            self.assertIn("BLIND: owner/repo#101", output.getvalue())
            self.assertIn("--paginate", run.call_args.args[0])
            self.assertIn("--slurp", run.call_args.args[0])
            for invalid in (pages[:1], [dict(pages[0], incomplete_results=True)],
                            [dict(pages[0], total_count=1001)],
                            [{"items": [], "total_count": 0}]):
                output = io.StringIO()
                response.stdout = json.dumps(invalid)
                with self.subTest(invalid=invalid), patch.object(oss, "STATE", str(path)), \
                     patch("subprocess.run", return_value=response), contextlib.redirect_stdout(output):
                    oss.audit_scope()
                self.assertIn("UNKNOWN", output.getvalue())
                self.assertNotIn("BLIND:", output.getvalue())

    def test_later_page_failure_discards_successful_partial_stdout(self):
        partial = SimpleNamespace(returncode=1, stdout='[[{"id":1}]]', stderr="page 2 failed")
        with patch("subprocess.run", return_value=partial), self.assertRaises(github_read.GitHubReadError):
            github_read.api("repos/a/b/issues", paginate=True)

    def test_transport_errors_use_one_exception_and_missing_cli_is_not_retried(self):
        for failure in (OSError("unavailable"), subprocess.TimeoutExpired("gh", 60)):
            with self.subTest(failure=failure), patch("subprocess.run", side_effect=failure), \
                 self.assertRaises(github_read.GitHubReadError) as result:
                github_read.output(["api", "endpoint"])
            self.assertIs(result.exception.__cause__, failure)
        for module in (scope, oss):
            with self.subTest(module=module.__name__), \
                 patch("subprocess.run", side_effect=FileNotFoundError("gh missing")) as run, \
                 patch("time.sleep") as sleep:
                self.assertEqual(module.fetch("owner/repo#1")["state"], "QUERY_ERROR")
                run.assert_called_once()
                sleep.assert_not_called()

    def test_both_pr_readers_share_query_fields_and_common_observations(self):
        response = json.dumps({"state": "CLOSED", "mergedAt": "2026-10-25T00:00:00Z",
                               "statusCheckRollup": [], "url": "https://github.com/a/b/pull/1"})
        with patch.object(scope, "gh", return_value=response) as scope_query, \
             patch.object(oss, "gh", return_value=response) as oss_query:
            base, extended = scope.fetch("a/b#1"), oss.fetch("a/b#1")
        self.assertEqual(base["state"], "MERGED")
        for field in ("state", "mergedAt", "mergeable", "reviewDecision", "url", "headRefOid"):
            self.assertEqual(base[field], extended[field])
        self.assertLessEqual(set(scope_query.call_args.args[0][-1].split(",")),
                             set(oss_query.call_args.args[0][-1].split(",")))


if __name__ == "__main__":
    unittest.main()
