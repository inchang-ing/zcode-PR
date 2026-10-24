"""The operational scanner must apply the same policy as the main pipeline."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/scan_candidates.py"
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("operational_scan", SCRIPT)
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)


class OperationalScanTests(unittest.TestCase):
    def scan_repo(self, repo, changes=None, missing=(), blocked=False, collision=False,
                  responses=None):
        issue = {"number": 1, "title": "Bug: crash", "body": "A reproducible error",
                 "created_at": "9999-01-01T00:00:00Z", "comments": 0,
                 "html_url": f"https://github.com/{repo}/issues/1",
                 "labels": [{"name": "bug"}], "assignees": [], "state": "open"}
        issue.update(changes or {})
        for field in missing:
            issue.pop(field)

        def gh(endpoint, *options):
            for fragment, response in (responses or {}).items():
                if fragment in endpoint:
                    return response
            if "/issues?" in endpoint:
                return [issue]
            if "/pulls?" in endpoint and collision:
                items = [{"title": "Fix #1", "body": ""}]
            else:
                items = []
            return [items] if "--slurp" in options else items

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool, ledger, out = root / "pool.json", root / "ledger.json", root / "out.json"
            pool.write_text(json.dumps({"watch": [{"repo": repo}],
                "blocked": {"repos": [repo] if blocked else []}}), encoding="utf-8")
            ledger.write_text('{"external": []}', encoding="utf-8")
            with patch.multiple(scan, POOL=str(pool), LEDGER=str(ledger), OUT=str(out)), \
                    patch.object(sys, "argv", ["scan_candidates.py"]), \
                    patch.object(scan, "gh", side_effect=gh) as api, \
                    patch.object(scan.time, "sleep"), contextlib.redirect_stdout(io.StringIO()):
                scan.main()
            return json.loads(out.read_text(encoding="utf-8")), [c.args[0] for c in api.call_args_list]

    def test_shared_repository_and_assignment_gates(self):
        for repo in ("ansible/ansible", "Python-Markdown/markdown", "langchain-ai/langchain"):
            with self.subTest(repo=repo):
                report, calls = self.scan_repo(repo)
                self.assertEqual(report["candidates"], [])
                self.assertTrue(report["skipped"])
                self.assertEqual(len(calls), 1)

    def test_allowed_repo_and_self_assignment_pass(self):
        for repo, changes in (("example/repo", {}), ("langchain-ai/langchain",
                {"assignees": [{"login": "inchang-ing"}]})):
            with self.subTest(repo=repo):
                report, calls = self.scan_repo(repo, changes)
                self.assertEqual([c["number"] for c in report["candidates"]], [1])
                self.assertTrue(any("/timeline?" in call for call in calls))
                self.assertTrue(any("/comments" in call for call in calls))

    def test_missing_or_malformed_policy_fields_never_pass(self):
        cases = [({}, (field,)) for field in ("labels", "assignees")]
        for field, values in (("labels", [None, {}, ["bug"], [{}], [{"name": ""}], [{"name": " "}], [{"name": 3}]]),
                              ("assignees", [None, {}, ["inchang-ing"], [{}], [{"login": ""}], [{"login": " "}], [{"login": 3}]])):
            cases += [({field: value}, ()) for value in values]
        for changes, missing in cases:
            with self.subTest(changes=changes, missing=missing):
                report, calls = self.scan_repo("example/repo", changes, missing)
                self.assertEqual(report["candidates"], [])
                self.assertIn("recheck required", report["skipped"][0][1])
                self.assertEqual(len(calls), 1)

    def test_other_assignee_and_required_label_are_preserved(self):
        for repo, changes in (("example/repo", {"assignees": [{"login": "someone-else"}]}),
                              ("mlflow/mlflow", {})):
            with self.subTest(repo=repo):
                report, _ = self.scan_repo(repo, changes)
                self.assertEqual(report["candidates"], [])

    def test_local_block_and_collision_checks_still_apply(self):
        report, calls = self.scan_repo("example/repo", blocked=True)
        self.assertEqual(report["candidates"], [])
        self.assertEqual(calls, [])
        report, calls = self.scan_repo("example/repo", collision=True)
        self.assertEqual(report["candidates"], [])
        self.assertFalse(any("/timeline?" in call for call in calls))

    def test_failed_collision_or_claim_check_is_unknown(self):
        for endpoint in ("/pulls?", "/timeline?", "/comments"):
            for response in ({"__error__": "HTTP 502"}, {"__ratelimit__": True}, None):
                with self.subTest(endpoint=endpoint, response=response):
                    report, _ = self.scan_repo("example/repo", responses={endpoint: response})
                    self.assertEqual(report["candidates"], [])
                    self.assertTrue(report.get("unknown"))

    def test_shared_claim_and_not_ready_checks_apply_to_body(self):
        for body in ("I can open a PR", "not ready for a PR", "I have a focused fix ready",
                     "Please approve the issue and assign it to X", "I will take this"):
            with self.subTest(body=body):
                report, _ = self.scan_repo("example/repo", {"body": body})
                self.assertEqual(report["candidates"], [])

    def test_earlier_and_later_page_comments_are_checked(self):
        for comments in (
                [[{"body": "I will take this"}] + [{"body": "Confirmed"}] * 5],
                [[{"body": "Confirmed"}], [{"body": "I can open a PR"}]],
                [[{"body": "Confirmed"}], [{"body": "Do not open a PR"}]]):
            with self.subTest(comments=comments):
                report, _ = self.scan_repo("example/repo", responses={"/comments": comments})
                self.assertEqual(report["candidates"], [])

    def test_malformed_check_pages_are_unknown(self):
        for endpoint in ("/pulls?", "/timeline?", "/comments"):
            for response in ([], {}, [[] , [None]], [[{}]]):
                with self.subTest(endpoint=endpoint, response=response):
                    report, _ = self.scan_repo("example/repo", responses={endpoint: response})
                    self.assertEqual(report["candidates"], [])
                    self.assertTrue(report.get("unknown"))

    def test_legacy_claim_phrases_remain_blocked(self):
        for body in ("Can I take it?", "I'll submit my fix tomorrow",
                     "I have a focused fix ready", "Please assign this issue to X"):
            with self.subTest(body=body):
                report, _ = self.scan_repo("example/repo", responses={"/comments": [[{"body": body}]]})
                self.assertEqual(report["candidates"], [])

    def test_numbered_pr_fix_claims_in_body_are_skipped(self):
        for body in ("A reproducible error. I see that PR #22407 fixes this, "
                     "could a maintainer approve it?",
                     "A reproducible error. #123 fixes this upstream.",
                     "A reproducible error. The pull request #45 fixes the issue."):
            with self.subTest(body=body):
                report, _ = self.scan_repo("example/repo", changes={"body": body})
                self.assertEqual(report["candidates"], [])

    def test_complete_paginated_checks_allow_candidate(self):
        report, calls = self.scan_repo("example/repo", responses={
            "/pulls?": [[], [{"title": "Unrelated fix #2", "body": None}]],
            "/timeline?": [[{"event": "labeled"}], [{"event": "commented"}]],
            "/comments": [[{"body": "Confirmed"}], [{"body": "Thanks for the report"}]],
        })
        self.assertEqual([c["number"] for c in report["candidates"]], [1])
        self.assertEqual(report["unknown"], [])
        self.assertTrue(any("/comments?per_page=100" in call for call in calls))

    def test_second_page_linked_pr_blocks(self):
        event = {"event": "cross-referenced", "source": {"issue": {"number": 9, "pull_request": {}}}}
        report, _ = self.scan_repo("example/repo", responses={"/timeline?": [[], [event]]})
        self.assertEqual(report["candidates"], [])
        self.assertEqual(report["unknown"], [])

    def test_cli_failures_become_unknown_responses(self):
        for error in (FileNotFoundError("gh"), subprocess.TimeoutExpired("gh", 90)):
            with self.subTest(error=error), patch.object(scan.subprocess, "run", side_effect=error):
                self.assertIn("__error__", scan.gh("repos/a/b/issues"))

    def test_pagination_options_reach_cli(self):
        for parse, payload, expected in (
                (scan.comment_bodies, [[{"body": "Confirmed"}], [{"body": "Later reply"}]],
                 ["Confirmed", "Later reply"]),
                (scan.linked_prs, [[], [{"event": "cross-referenced", "source": {"issue": {
                    "number": 9, "pull_request": {}}}}]], [9])):
            with self.subTest(parse=parse.__name__), patch.object(scan.subprocess, "run", return_value=
                    subprocess.CompletedProcess(["gh"], 0, json.dumps(payload), "")) as run:
                self.assertEqual(scan.checked_pages("repos/a/b/issues/1/comments?per_page=100", parse), expected)
                args = run.call_args.args[0]
                self.assertIn("--paginate", args)
                self.assertIn("--slurp", args)

    def test_unknown_report_returns_failure_without_clean_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool, ledger, out = root / "pool.json", root / "ledger.json", root / "out.json"
            pool.write_text(json.dumps({"watch": [{"repo": "example/repo"}], "blocked": {"repos": []}}))
            ledger.write_text('{"external": []}')
            with patch.multiple(scan, POOL=pool, LEDGER=ledger, OUT=out), \
                 patch.object(scan, "gh", return_value={"__error__": "offline"}), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(scan.main([]), 1)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["candidates"], [])
            self.assertTrue(report["unknown"])

    def test_relocated_checkout_runs_without_ignored_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tools = root / "tools"
            tools.mkdir()
            for name in ("scan_candidates.py", "quality_repos.json", "claim_rules.py", "gh_checks.py",
                         "pipeline_state.py", "pr_state.py", "repository_policy.py"):
                shutil.copy2(ROOT / "tools" / name, tools / name)
            (root / "work").mkdir()
            shutil.copy2(ROOT / "work/scan_candidates.py", root / "work/scan_candidates.py")
            # Import and execute in a new process so the original checkout cannot supply dependencies.
            command = (
                "import runpy,sys; sys.path.insert(0,'tools'); import scan_candidates as s; "
                "s.gh=lambda *args: []; sys.argv=['work/scan_candidates.py']; "
                "runpy.run_path('work/scan_candidates.py',run_name='__main__')"
            )
            result = subprocess.run([sys.executable, "-S", "-B", "-c", command], cwd=root,
                                    capture_output=True, text=True, encoding="utf-8", timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads((root / "work/ledger/candidates.json").read_text(encoding="utf-8"))["unknown"], [])


if __name__ == "__main__":
    unittest.main()
