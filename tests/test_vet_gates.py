"""Final vet binds issue identity and rejects known drops before extra requests."""
from dataclasses import replace
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from auto_run import Candidate
import vet


class VetGateTests(unittest.TestCase):
    def setUp(self):
        self.candidate = Candidate("example/project", 7, "Bug: crash", "", is_bug=True)
        self.issue = {"number": 7, "title": "Bug: crash", "state": "OPEN",
                      "body": "Crash on empty input", "labels": [{"name": "bug"}], "assignees": []}

    def check(self, issue, candidate=None):
        with patch.object(vet, "gh", side_effect=[json.dumps(issue), '[[]]', '[[]]']) as gh:
            result = vet.vet(candidate or self.candidate)
        return result, gh

    def test_invalid_candidate_number_is_unknown_without_requests(self):
        for number in (None, True, False, 0, -1, 7.0, "7"):
            with self.subTest(number=number):
                result, gh = self.check(self.issue, replace(self.candidate, number=number))
                self.assertEqual(result[0], "UNKNOWN")
                gh.assert_not_called()

    def test_wrong_missing_or_invalid_response_number_stops_after_issue(self):
        missing = dict(self.issue)
        missing.pop("number")
        cases = [missing] + [dict(self.issue, number=number)
                             for number in (None, True, False, 0, -1, 7.0, "7", 8)]
        for issue in cases:
            with self.subTest(issue=issue):
                result, gh = self.check(issue)
                self.assertEqual(result[0], "UNKNOWN")
                self.assertIn("number", result[1])
                self.assertEqual(gh.call_count, 1)

    def test_known_body_or_live_nonbug_drops_need_only_issue_request(self):
        for changes in ({"body": "I have a patch"}, {"body": "Do not open a PR"},
                        {"title": "New feature request", "labels": [{"name": "enhancement"}]}):
            with self.subTest(changes=changes):
                result, gh = self.check(dict(self.issue, **changes))
                self.assertEqual(result[0], "DROP")
                self.assertEqual(gh.call_count, 1)

    def test_eligible_and_warning_candidates_keep_both_paginated_checks(self):
        for labels, status in (([{"name": "bug"}], "CLEAN"),
                               ([{"name": "bug"}, {"name": "needs triage"}], "WARN")):
            with self.subTest(labels=labels):
                responses = [json.dumps(dict(self.issue, labels=labels)),
                             json.dumps([[{"event": "labeled"}], []]),
                             json.dumps([[{"body": "Confirmed"}], []])]
                with patch.object(vet, "gh", side_effect=responses) as gh:
                    result = vet.vet(self.candidate)
                self.assertEqual(result[0], status)
                self.assertEqual(gh.call_count, 3)
                for call in gh.call_args_list[1:]:
                    self.assertIn("--paginate", call.args[0])
                    self.assertIn("--slurp", call.args[0])

    def test_shared_policy_still_drops_before_pagination(self):
        for candidate, issue in ((self.candidate, dict(self.issue, assignees=[{"login": "someone"}])),
                                 (replace(self.candidate, repo="pallets/flask"), self.issue)):
            with self.subTest(candidate=candidate, issue=issue):
                result, gh = self.check(issue, candidate)
                self.assertEqual(result[0], "DROP")
                self.assertEqual(gh.call_count, 1)


if __name__ == "__main__":
    unittest.main()
