"""Offline regressions for incomplete checks and multi-page GitHub responses."""
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from copy import deepcopy
from dataclasses import replace
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import monitor_round
import vet
from auto_run import Candidate


ISSUE = {
    "number": 7, "title": "Bug: crash", "state": "OPEN", "body": "Crash on empty input",
    "assignees": [], "labels": [{"name": "bug"}], "createdAt": "2026-10-15T00:00:00Z",
}
CANDIDATE = Candidate(repo="example/project", number=7, title="Bug: crash", url="",
                      is_bug=True)
EMPTY_PAGES = "[[]]"
LINKED_PR = {"event": "cross-referenced", "source": {"issue": {
    "number": 99, "pull_request": {"url": "https://api.github.com/repos/example/project/pulls/99"},
}}}


class VetTests(unittest.TestCase):
    def check(self, issue=ISSUE, timeline=EMPTY_PAGES, comments=EMPTY_PAGES):
        output = json.dumps(issue) if not isinstance(issue, str) else issue
        with patch.object(vet, "gh", side_effect=[output, timeline, comments]) as gh:
            result = vet.vet(CANDIDATE)
        return result, gh

    def test_complete_clean_check(self):
        result, gh = self.check()
        self.assertEqual(result, ("CLEAN", ""))
        for call in gh.call_args_list[1:]:
            self.assertIn("--paginate", call.args[0])
            self.assertIn("--slurp", call.args[0])
            self.assertNotIn("--jq", call.args[0])

    def test_failed_timeline_or_comments_is_unknown(self):
        for check in ("timeline", "comments"):
            with self.subTest(check=check):
                result, _ = self.check(**{check: None})
                self.assertEqual(result[0], "UNKNOWN")
                self.assertIn(check, result[1])

    def test_invalid_paginated_payload_is_unknown(self):
        for output in ("not json", "{}", "[]", "[{}]", '[[], ["bad"]]', '[[], [{}]]'):
            for check in ("timeline", "comments"):
                with self.subTest(output=output, check=check):
                    result, _ = self.check(**{check: output})
                    self.assertEqual(result[0], "UNKNOWN")
                    self.assertIn(check, result[1])

    def test_invalid_issue_payload_is_unknown(self):
        for issue in ("not json", [], None):
            with self.subTest(issue=issue):
                result, _ = self.check(issue=issue)
                self.assertEqual(result[0], "UNKNOWN")

    def test_missing_issue_fields_are_unknown(self):
        for field in ("state", "assignees", "labels", "body"):
            for missing in (True, False):
                with self.subTest(field=field, missing=missing):
                    issue = deepcopy(ISSUE)
                    if missing:
                        del issue[field]
                    else:
                        issue[field] = None
                    result, gh = self.check(issue=issue)
                    self.assertEqual(result[0], "UNKNOWN")
                    self.assertIn(field, result[1])
                    self.assertEqual(gh.call_count, 1)

    def test_second_page_pr_blocks_even_without_nested_pr_number(self):
        result, _ = self.check(timeline=json.dumps([[{"event": "labeled"}], [LINKED_PR]]))
        self.assertEqual(result[0], "DROP")
        self.assertIn("99", result[1])

    def test_pull_request_key_presence_is_enough_to_block(self):
        event = deepcopy(LINKED_PR)
        event["source"]["issue"]["pull_request"] = {}
        result, _ = self.check(timeline=json.dumps([[event]]))
        self.assertEqual(result[0], "DROP")

    def test_second_page_claim_blocks(self):
        comments = json.dumps([[{"body": "Confirmed this crash"}], [{"body": "I can take this"}]] )
        result, _ = self.check(comments=comments)
        self.assertEqual(result, ("DROP", "评论软认领"))

    def test_second_page_not_ready_notice_blocks(self):
        result, _ = self.check(comments=json.dumps([[], [{"body": "Do not open a PR"}]]))
        self.assertEqual(result[0], "DROP")

    def test_timeout_missing_cli_or_nonzero_exit_is_unknown(self):
        for exc in (subprocess.TimeoutExpired("gh", 60), FileNotFoundError("gh")):
            with self.subTest(exc=exc), patch.object(vet.subprocess, "run", side_effect=exc):
                self.assertEqual(vet.vet(CANDIDATE)[0], "UNKNOWN")
        with patch.object(vet.subprocess, "run", return_value=subprocess.CompletedProcess(
            ["gh"], 1, stdout="", stderr="request failed"
        )):
            self.assertEqual(vet.vet(CANDIDATE)[0], "UNKNOWN")

    def test_closed_assigned_or_blocked_issue_never_passes(self):
        for changes, status in (({"state": "CLOSED"}, "DROP"),
                                ({"assignees": [{"login": "someone"}]}, "DROP"),
                                ({"labels": [{"name": "needs triage"}]}, "WARN")):
            with self.subTest(changes=changes):
                result, _ = self.check(issue={**ISSUE, **changes})
                self.assertEqual(result[0], status)

    def test_cli_candidate_override_and_unknown_exit(self):
        with patch.object(vet, "load_candidates", return_value=[CANDIDATE]) as load, \
                patch.object(vet, "DispatchedStore"), \
                patch.object(vet, "is_clean", return_value=(True, "clean")), \
                patch.object(vet, "vet", return_value=("UNKNOWN", "comments: 请求失败")), \
                redirect_stdout(io.StringIO()) as output:
            status = vet.main(["--candidates", "custom.json"])
        load.assert_called_once_with("custom.json")
        self.assertEqual(status, 1)
        self.assertIn("UNKNOWN=1", output.getvalue())
        self.assertIn("comments", output.getvalue())

    def test_cli_snapshot_unknown_is_reported_without_live_vet(self):
        for flag in ("issue_unknown", "pr_unknown", "cmt_unknown"):
            candidate = replace(CANDIDATE, **{flag: True}, check_errors=["response incomplete"])
            with self.subTest(flag=flag), \
                    patch.object(vet, "load_candidates", return_value=[candidate]), \
                    patch.object(vet, "DispatchedStore") as store, \
                    patch.object(vet, "vet") as live_vet, \
                    redirect_stdout(io.StringIO()) as output:
                store.return_value.is_active.return_value = False
                status = vet.main([])
            self.assertEqual(status, 1)
            self.assertIn("UNKNOWN=1", output.getvalue())
            self.assertIn("response incomplete", output.getvalue())
            live_vet.assert_not_called()
            self.assertTrue(getattr(candidate, flag))

    def test_cli_snapshot_unknown_still_applies_policy_and_dedup(self):
        for constrained, active in ((True, False), (False, True)):
            candidate = replace(CANDIDATE, pr_unknown=True,
                                repo="pallets/flask" if constrained else CANDIDATE.repo)
            with self.subTest(constrained=constrained, active=active), \
                    patch.object(vet, "load_candidates", return_value=[candidate]), \
                    patch.object(vet, "DispatchedStore") as store, \
                    patch.object(vet, "vet") as live_vet, \
                    redirect_stdout(io.StringIO()) as output:
                store.return_value.is_active.return_value = active
                store.return_value.status_of.return_value = "running"
                status = vet.main([])
            self.assertEqual(status, 0)
            self.assertIn("SKIP", output.getvalue())
            self.assertIn("UNKNOWN=0", output.getvalue())
            live_vet.assert_not_called()


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.stdout = self.enterContext(redirect_stdout(io.StringIO()))
        self.enterContext(redirect_stderr(io.StringIO()))
        self.enterContext(patch.object(monitor_round.time, "sleep"))

    def test_second_page_pr_and_comments_are_seen(self):
        with patch.object(monitor_round, "gh", return_value=json.dumps([[], [LINKED_PR]])) as gh:
            self.assertTrue(monitor_round.has_linked_pr("example/project", 7))
            self.assertIn("--slurp", gh.call_args.args[0])
        with patch.object(monitor_round, "gh", return_value=json.dumps([
            [{"body": "First page"}], [{"body": "I can take this"}]
        ])) as gh:
            self.assertEqual(monitor_round.get_comments("example/project", 7),
                             ["First page", "I can take this"])
            self.assertIn("--paginate", gh.call_args.args[0])

    def test_malformed_or_failed_pages_return_unknown(self):
        for payload in (None, "bad JSON", "{}", "[{}]", '[[], [{}]]'):
            with self.subTest(payload=payload), patch.object(monitor_round, "gh", return_value=payload):
                self.assertIsNone(monitor_round.has_linked_pr("example/project", 7))
                self.assertIsNone(monitor_round.get_comments("example/project", 7))

    def test_invalid_issue_list_fails_entire_repository(self):
        for payload in ("null", "{}", "[null]", "[{}]", '[{"number": 7}]'):
            with self.subTest(payload=payload), patch.object(monitor_round, "gh", return_value=payload):
                self.assertIsNone(monitor_round.get_issues("example/project"))

    def test_unknown_flags_and_reasons_survive_atomic_save(self):
        issue = deepcopy(ISSUE)
        del issue["body"]
        with patch.object(monitor_round, "get_issues", return_value=[issue]), \
                patch.object(monitor_round, "has_linked_pr", return_value=None), \
                patch.object(monitor_round, "get_comments", return_value=None), \
                patch.object(monitor_round, "atomic_write_json") as save:
            self.assertEqual(monitor_round.scan(["example/project"], "snapshot.json"), 0)
        saved = save.call_args.args[1][0]
        self.assertTrue(saved["pr_unknown"])
        self.assertTrue(saved["cmt_unknown"])
        self.assertTrue(saved["issue_unknown"])
        self.assertEqual(len(saved["check_errors"]), 3)
        self.assertIn("body", saved["check_errors"][0])

    def test_second_page_claim_is_excluded_from_snapshot(self):
        with patch.object(monitor_round, "get_issues", return_value=[deepcopy(ISSUE)]), \
                patch.object(monitor_round, "gh", side_effect=[EMPTY_PAGES, json.dumps([
                    [{"body": "Confirmed"}], [{"body": "I can take this"}]
                ])]), patch.object(monitor_round, "atomic_write_json") as save:
            monitor_round.scan(["example/project"], "snapshot.json")
        save.assert_called_once_with("snapshot.json", [])

    def test_total_failure_does_not_overwrite_snapshot(self):
        with patch.object(monitor_round, "get_issues", return_value=None), \
                patch.object(monitor_round, "atomic_write_json") as save:
            self.assertEqual(monitor_round.scan(["example/project"], "existing.json"), 1)
        save.assert_not_called()

    def test_confirmed_empty_list_replaces_old_candidates(self):
        with patch.object(monitor_round, "get_issues", return_value=[]), \
                patch.object(monitor_round, "atomic_write_json") as save:
            self.assertEqual(monitor_round.scan(["example/project"], "snapshot.json"), 0)
        save.assert_called_once_with("snapshot.json", [])

    def test_cli_locks_entire_scan_and_accepts_spaced_output_option(self):
        locked = False

        @contextmanager
        def lock(path):
            nonlocal locked
            self.assertEqual(path, "custom.json")
            locked = True
            yield
            locked = False

        def scan(repos, path):
            self.assertTrue(locked)
            self.assertEqual(repos, ["example/project"])
            self.assertEqual(path, "custom.json")
            return 0

        with patch.object(monitor_round, "file_lock", side_effect=lock), \
                patch.object(monitor_round, "scan", side_effect=scan):
            self.assertEqual(monitor_round.main(["--out", "custom.json", "example/project"]), 0)
        self.assertFalse(locked)


if __name__ == "__main__":
    unittest.main()
