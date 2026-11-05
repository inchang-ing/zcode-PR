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
import monitor_round


class OperationalScanTests(unittest.TestCase):
    def scan_repo(self, repo, changes=None, missing=(), blocked=False, collision=False,
                  responses=None, expected_status=None, canonical=None, legacy_repos=(), precise=False):
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
            ledger.write_text(json.dumps({"external": [
                {"repository": {"nameWithOwner": repo}} for repo in legacy_repos]}), encoding="utf-8")
            if canonical is not None:
                (root / "pr_state.json").write_text(json.dumps(canonical), encoding="utf-8")
            with patch.multiple(scan, ROOT=root, POOL=str(pool), LEDGER=str(ledger), OUT=str(out)), \
                    patch.object(sys, "argv", ["scan_candidates.py"]), \
                    patch.object(scan, "gh", side_effect=gh) as api, \
                    patch.object(scan.time, "sleep"), contextlib.redirect_stdout(io.StringIO()):
                status = scan.main()
            if expected_status is not None:
                self.assertEqual(status, expected_status)
            report = json.loads(out.read_text(encoding="utf-8"))
            calls = [c.args[0] for c in api.call_args_list]
            if report["candidates"]:
                pending = json.loads((root / "tools/fresh_candidates.json").read_text(encoding="utf-8"))
                candidate = pending[f"{repo.lower()}#1"]
                self.assertTrue(candidate["issue_unknown"] and candidate["pr_unknown"] and candidate["cmt_unknown"])
            if precise and report["candidates"]:
                exact = root / "round.json"
                with patch.object(monitor_round, "gh", side_effect=lambda args: json.dumps(gh(args[1], *args[2:]))) as checks, \
                     patch.object(monitor_round.time, "sleep"), contextlib.redirect_stdout(io.StringIO()):
                    monitor_round.scan([repo], exact, {repo: [dict(issue, state="OPEN")]})
                calls += [call.args[0][1] for call in checks.call_args_list]
                report["candidates"] = json.loads(exact.read_text(encoding="utf-8"))
            return report, calls

    def test_single_canonical_open_pr_still_allows_discovery(self):
        report, calls = self.scan_repo("example/repo", canonical={"example/repo#9": {"state": "OPEN"}})
        self.assertEqual([item["number"] for item in report["candidates"]], [1])
        self.assertEqual(report["skipped"], [])
        self.assertTrue(calls)

    def test_two_or_three_open_prs_require_capacity_before_discovery(self):
        for count in (2, 3):
            with self.subTest(count=count):
                records = {f"example/repo#{number}": {"state": "OPEN"}
                           for number in range(9, 9 + count)}
                report, calls = self.scan_repo("example/repo", canonical=records)
                self.assertEqual(report["candidates"], [])
                self.assertEqual(calls, [])
                self.assertEqual(report["skipped"][0][0], "example/repo")
                self.assertNotEqual(report["skipped"][0][1], "in-flight")

    def test_shared_capacity_result_and_root_are_used_for_prescreening(self):
        records = {"example/repo#9": {"state": "OPEN"},
                   "example/repo#10": {"state": "OPEN"}}
        for allowed in (True, False):
            with self.subTest(allowed=allowed), patch.object(scan, "cached_capacity", create=True,
                    return_value={"allowed": allowed, "count": 2,
                                  "status": "ALLOW" if allowed else "HOLD",
                                  "reason": "shared capacity decision"}) as capacity:
                report, calls = self.scan_repo("example/repo", canonical=records)
            capacity.assert_called_once()
            self.assertEqual(capacity.call_args.args[0], "example/repo")
            self.assertNotEqual(capacity.call_args.args[1].root, ROOT)
            self.assertEqual(capacity.call_args.kwargs["records"], records)
            if allowed:
                self.assertEqual([item["number"] for item in report["candidates"]], [1])
                self.assertTrue(calls)
            else:
                self.assertEqual(report["skipped"], [["example/repo", "shared capacity decision"]])
                self.assertEqual(calls, [])

    def test_canonical_ended_pr_overrides_stale_legacy_ledger(self):
        for state in ("MERGED", "CLOSED"):
            with self.subTest(state=state):
                report, calls = self.scan_repo("example/repo",
                    canonical={"example/repo#9": {"state": state}}, legacy_repos=["example/repo"])
                self.assertEqual([item["number"] for item in report["candidates"]], [1])
                self.assertEqual(report["skipped"], [])
                self.assertTrue(calls)

    def test_empty_canonical_overrides_stale_legacy_ledger(self):
        report, _ = self.scan_repo("example/repo", canonical={}, legacy_repos=["example/repo"])
        self.assertEqual([item["number"] for item in report["candidates"]], [1])
        self.assertEqual(report["skipped"], [])

    def test_legacy_repo_without_pr_identity_requires_refresh(self):
        report, calls = self.scan_repo("example/repo", legacy_repos=["example/repo"])
        self.assertEqual(report["skipped"][0][0], "example/repo")
        self.assertIn("数量未知", report["skipped"][0][1])
        self.assertIn("刷新", report["skipped"][0][1])
        self.assertEqual(calls, [])

    def test_bad_canonical_does_not_fall_back_query_or_overwrite_report(self):
        for raw in ('{broken', '[]', '{"example/repo#9": {"state": "BROKEN"}}'):
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                pool, ledger, out = root / "pool.json", root / "ledger.json", root / "out.json"
                pool.write_text(json.dumps({"watch": [{"repo": "example/repo"}], "blocked": {"repos": []}}))
                ledger.write_text('{"external": []}')
                (root / "pr_state.json").write_text(raw)
                original = b'{"previous": "keep"}\n'
                out.write_bytes(original)
                with patch.multiple(scan, ROOT=root, POOL=pool, LEDGER=ledger, OUT=out), \
                        patch.object(scan, "gh") as api, self.assertRaises(ValueError):
                    scan.main([])
                api.assert_not_called()
                self.assertEqual(out.read_bytes(), original)

    def test_shared_repository_and_assignment_gates(self):
        for repo in ("ansible/ansible", "Python-Markdown/markdown", "langchain-ai/langchain",
                     "modelcontextprotocol/servers"):
            with self.subTest(repo=repo):
                report, calls = self.scan_repo(repo, expected_status=0)
                self.assertEqual(report["candidates"], [])
                self.assertTrue(report["skipped"])
                self.assertEqual(report["unknown"], [])
                self.assertEqual(len(calls), 1)

    def test_allowed_repo_and_self_assignment_pass(self):
        for repo, changes in (("example/repo", {}), ("langchain-ai/langchain",
                {"assignees": [{"login": "inchang-ing"}]})):
            with self.subTest(repo=repo):
                report, calls = self.scan_repo(repo, changes)
                self.assertEqual([c["number"] for c in report["candidates"]], [1])
                self.assertFalse(any("/timeline?" in call for call in calls))
                self.assertFalse(any("/comments" in call for call in calls))

    def test_missing_or_malformed_policy_fields_never_pass(self):
        cases = [({}, (field,)) for field in ("labels", "assignees")]
        for field, values in (("labels", [None, {}, ["bug"], [{}], [{"name": ""}], [{"name": " "}], [{"name": 3}]]),
                              ("assignees", [None, {}, ["inchang-ing"], [{}], [{"login": ""}], [{"login": " "}], [{"login": 3}]])):
            cases += [({field: value}, ()) for value in values]
        for changes, missing in cases:
            with self.subTest(changes=changes, missing=missing):
                report, calls = self.scan_repo("example/repo", changes, missing, expected_status=1)
                self.assertEqual(report["candidates"], [])
                self.assertEqual(report["skipped"], [])
                self.assertEqual(report["unknown"][0][0], "example/repo#1")
                self.assertIn("recheck required", report["unknown"][0][1])
                self.assertEqual(len(calls), 1)

    def test_other_assignee_and_required_label_are_preserved(self):
        for repo, changes in (("example/repo", {"assignees": [{"login": "someone-else"}]}),
                              ("mlflow/mlflow", {})):
            with self.subTest(repo=repo):
                report, _ = self.scan_repo(repo, changes, expected_status=0)
                self.assertEqual(report["candidates"], [])
                self.assertTrue(report["skipped"])
                self.assertEqual(report["unknown"], [])

    def test_local_block_and_collision_checks_still_apply(self):
        report, calls = self.scan_repo("example/repo", blocked=True)
        self.assertEqual(report["candidates"], [])
        self.assertEqual(calls, [])
        report, calls = self.scan_repo("example/repo", collision=True)
        self.assertEqual(report["candidates"], [])
        self.assertFalse(any("/timeline?" in call for call in calls))

    def test_cross_repository_references_do_not_hide_local_candidates(self):
        for reference in ("other/project#1", "OTHER/PROJECT#1",
                          "https://github.com/other/project/issues/1",
                          "https://github.com/other/project/issues/1#1",
                          "https://example.org/issues/1", "https://example.org/page#1"):
            for field in ("title", "body"):
                with self.subTest(reference=reference, field=field):
                    pull = {"title": "Unrelated change", "body": ""}
                    pull[field] = f"Follow up on {reference}"
                    report, calls = self.scan_repo("example/repo", responses={"/pulls?": [[pull]]})
                    self.assertEqual([c["number"] for c in report["candidates"]], [1])
                    self.assertFalse(any("/timeline?" in call for call in calls))

    def test_local_qualified_and_independent_references_still_block(self):
        for reference in ("#1", "example/repo#1", "EXAMPLE/REPO#1",
                          "https://github.com/EXAMPLE/REPO/issues/1",
                          '`https://github.com/example/repo/issues/1`',
                          '"https://github.com/example/repo/issues/1"',
                          "https://github.com/example/repo/issues/1#issuecomment-9",
                          "other/project#1 and #1",
                          "https://github.com/other/project/issues/1 and #1"):
            with self.subTest(reference=reference):
                report, calls = self.scan_repo("example/repo", responses={
                    "/pulls?": [[], [{"title": "Follow-up", "body": f"Fixes {reference}"}]],
                })
                self.assertEqual(report["candidates"], [])
                self.assertFalse(any("/timeline?" in call for call in calls))

    def test_failed_repository_collision_check_is_unknown(self):
        for endpoint in ("/pulls?",):
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
                report, _ = self.scan_repo("example/repo", responses={"/comments": comments}, precise=True)
                self.assertEqual(report["candidates"], [])

    def test_malformed_repository_pull_pages_are_unknown(self):
        for endpoint in ("/pulls?",):
            for response in ([], {}, [[] , [None]], [[{}]]):
                with self.subTest(endpoint=endpoint, response=response):
                    report, _ = self.scan_repo("example/repo", responses={endpoint: response})
                    self.assertEqual(report["candidates"], [])
                    self.assertTrue(report.get("unknown"))

    def test_legacy_claim_phrases_remain_blocked(self):
        for body in ("Can I take it?", "I'll submit my fix tomorrow",
                     "I have a focused fix ready", "Please assign this issue to X"):
            with self.subTest(body=body):
                report, _ = self.scan_repo("example/repo", responses={"/comments": [[{"body": body}]]}, precise=True)
                self.assertEqual(report["candidates"], [])

    def test_numbered_pr_fix_claims_in_body_are_skipped(self):
        for body in ("A reproducible error. I see that PR #22407 fixes this, "
                     "could a maintainer approve it?",
                     "A reproducible error. #123 fixes this upstream.",
                     "A reproducible error. The pull request #45 fixes the issue."):
            with self.subTest(body=body):
                report, _ = self.scan_repo("example/repo", changes={"body": body})
                self.assertEqual(report["candidates"], [])

    def test_discovery_then_precise_scan_checks_comments_and_timeline_once(self):
        report, calls = self.scan_repo("example/repo", responses={
            "/pulls?": [[], [{"title": "Unrelated fix #2", "body": None}]],
            "/timeline?": [[{"event": "labeled"}], [{"event": "commented"}]],
            "/comments": [[{"body": "Confirmed"}], [{"body": "Thanks for the report"}]],
        }, precise=True)
        self.assertEqual([c["number"] for c in report["candidates"]], [1])
        self.assertEqual(report["unknown"], [])
        self.assertEqual(sum("/comments?per_page=100" in call for call in calls), 1)
        self.assertEqual(sum("/timeline?per_page=100" in call for call in calls), 1)
        self.assertEqual(sum("/pulls?" in call for call in calls), 1)
        self.assertFalse(report["candidates"][0]["pr_unknown"])
        self.assertFalse(report["candidates"][0]["cmt_unknown"])

    def test_second_page_linked_pr_blocks(self):
        event = {"event": "cross-referenced", "source": {"issue": {"number": 9, "pull_request": {}}}}
        report, _ = self.scan_repo("example/repo", responses={"/timeline?": [[], [event]]}, precise=True)
        self.assertEqual(report["candidates"], [])
        self.assertEqual(report["unknown"], [])

    def test_cli_failures_become_unknown_responses(self):
        for error in (FileNotFoundError("gh"), subprocess.TimeoutExpired("gh", 90)):
            with self.subTest(error=error), patch.object(scan.subprocess, "run", side_effect=error):
                self.assertIn("__error__", scan.gh("repos/a/b/issues"))

    def test_pull_pagination_options_reach_cli(self):
        payload = [[{"title": "First", "body": ""}], [{"title": "Second", "body": None}]]
        with patch.object(scan.subprocess, "run", return_value=
                subprocess.CompletedProcess(["gh"], 0, json.dumps(payload), "")) as run:
            self.assertEqual(scan.checked_pages("repos/a/b/pulls?per_page=100", scan.paginated_items),
                             payload[0] + payload[1])
            self.assertIn("--paginate", run.call_args.args[0])
            self.assertIn("--slurp", run.call_args.args[0])

    def test_unknown_report_returns_failure_without_clean_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool, ledger, out = root / "pool.json", root / "ledger.json", root / "out.json"
            pool.write_text(json.dumps({"watch": [{"repo": "example/repo"}], "blocked": {"repos": []}}))
            ledger.write_text('{"external": []}')
            with patch.multiple(scan, ROOT=root, POOL=pool, LEDGER=ledger, OUT=out), \
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
            # Copy source modules, not live business state or ignored workspaces.
            # Shared module extraction must not require a hand-maintained import list.
            for source in (ROOT / "tools").glob("*.py"):
                shutil.copy2(source, tools / source.name)
            shutil.copy2(ROOT / "tools/quality_repos.json", tools / "quality_repos.json")
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
