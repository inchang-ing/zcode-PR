"""Canonical PR state migration and generated report tests; temporary files only."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from pr_state import load_pr_state, merge_observations, render_pr_status, save_observations, write_pr_status
from monitor_oss import ci_fingerprint


class PRStateTests(unittest.TestCase):
    def test_new_head_preserves_ci_only_as_historical_evidence(self):
        original = {'state': 'OPEN', 'headRefOid': 'a' * 40, 'ci_head_oid': 'a' * 40,
                    'ci': 'no-checks', 'ci_fingerprint': ci_fingerprint([]),
                    'ci_checked_at': '2026-10-23T01:00:00Z'}
        for head in ('a' * 40, 'b' * 40):
            with self.subTest(head=head):
                merged = merge_observations({'a/b#1': original}, {'a/b#1': {
                    'state': 'OPEN', 'headRefOid': head, 'checked_at': '2026-10-23T02:00:00Z'}})
                self.assertEqual(merged['a/b#1']['ci_head_oid'], 'a' * 40)
                self.assertEqual(merged['a/b#1']['ci_checked_at'], original['ci_checked_at'])
                report = render_pr_status(merged)
                self.assertEqual('当前版本 CI 未验证' in report, head != original['headRefOid'])
                self.assertIn('CI 核验：2026-10-23T01:00:00Z', report)
        self.assertEqual(original['headRefOid'], 'a' * 40)

    def test_legacy_sources_merge_in_memory_until_first_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            canonical, report = directory / "pr_state.json", directory / "PR_STATUS.md"
            scope, oss = directory / "scope.json", directory / "oss.json"
            scope.write_text(json.dumps({"a/b#1": {"state": "OPEN", "url": "https://example.invalid/pr"}}), encoding="utf-8")
            oss.write_text(json.dumps({"a/b#1": {"state": "OPEN", "ci": "no-checks", "title": "Title"},
                                       "a/b#2": {"state": "QUERY_ERROR", "_err": "offline"}}), encoding="utf-8")
            originals = [p.read_bytes() for p in (scope, oss)]
            migrated = load_pr_state(canonical, (scope, oss))
            self.assertEqual(migrated["a/b#1"]["ci"], "no-checks")
            self.assertIn("url", migrated["a/b#1"])
            self.assertNotIn("state", migrated["a/b#2"])
            self.assertFalse(canonical.exists())
            self.assertFalse(save_observations(canonical, migrated,
                {"a/b#1": {"state": "QUERY_ERROR", "_err": "again"}}, report))
            self.assertFalse(canonical.exists())
            self.assertFalse(report.exists())
            self.assertTrue(save_observations(canonical, migrated,
                {"a/b#1": {"state": "MERGED", "checked_at": "2026-10-15T01:00:00+00:00"}}, report))
            self.assertEqual(load_pr_state(canonical)["a/b#1"]["state"], "MERGED")
            self.assertEqual([p.read_bytes() for p in (scope, oss)], originals)
            self.assertIn("MERGED", report.read_text(encoding="utf-8"))

    def test_existing_canonical_is_authoritative_even_if_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            canonical, legacy = Path(tmp) / "pr_state.json", Path(tmp) / "old.json"
            legacy.write_text(json.dumps({"a/b#1": {"state": "OPEN", "ci": "old"}}), encoding="utf-8")
            for data in ({}, {"a/b#1": {"state": "MERGED"}}):
                canonical.write_text(json.dumps(data), encoding="utf-8")
                self.assertEqual(load_pr_state(canonical, (legacy,)), data)
            canonical.write_text("{broken", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                load_pr_state(canonical, (legacy,))
            self.assertEqual(canonical.read_text(encoding="utf-8"), "{broken")

    def test_failure_preserves_success_time_and_recovery_clears_error(self):
        previous = {"a/b#1": {"state": "OPEN", "ci": "success", "checked_at": "old"}}
        failed = merge_observations(previous, {"a/b#1": {
            "state": "QUERY_ERROR", "ci": "-", "checked_at": "failed", "_err": "timeout"}})
        self.assertEqual(failed["a/b#1"]["state"], "OPEN")
        self.assertEqual(failed["a/b#1"]["ci"], "success")
        self.assertEqual(failed["a/b#1"]["checked_at"], "old")
        self.assertEqual(failed["a/b#1"]["query_error_at"], "failed")
        recovered = merge_observations(failed, {"a/b#1": {"state": "MERGED", "checked_at": "new"}})
        self.assertEqual(recovered["a/b#1"]["ci"], "success")
        self.assertNotIn("query_error", recovered["a/b#1"])
        self.assertNotIn("query_error_at", recovered["a/b#1"])
        self.assertEqual(previous["a/b#1"]["state"], "OPEN")

    def test_report_displays_times_errors_and_escapes_external_fields(self):
        records = {"a/b#1": {"state": "OPEN", "checked_at": "2026-10-15T01:00:00+00:00",
            "query_error": "bad | response\n<script>", "query_error_at": "2026-10-15T02:00:00+00:00",
            "title": "one | two", "ci": "no-checks"}}
        report = render_pr_status(records, "2026-10-15T03:00:00+00:00")
        self.assertIn("生成时间：2026-10-15T03:00:00+00:00", report)
        self.assertIn("2026-10-15T01:00:00+00:00", report)
        self.assertIn("2026-10-15T02:00:00+00:00", report)
        self.assertIn("bad \\| response<br>&lt;script&gt;", report)
        self.assertIn("[a/b#1](https://github.com/a/b/pull/1)", report)
        self.assertIn("one \\| two", report)

    def test_report_reads_canonical_and_never_initializes_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            canonical, report = Path(tmp) / "pr_state.json", Path(tmp) / "PR_STATUS.md"
            with self.assertRaises(FileNotFoundError):
                write_pr_status(canonical, report)
            canonical.write_text(json.dumps({"a/b#1": {"state": "CLOSED"}}), encoding="utf-8")
            write_pr_status(canonical, report)
            self.assertIn("CLOSED", report.read_text(encoding="utf-8"))
            self.assertIn("未记录", report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
