"""Case aliases must not hide newer PR observations or their query failures."""
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from copy import deepcopy
import io
from itertools import permutations
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import monitor_oss as oss
import monitor_scope as scope
import pr_state as state
import work_queue as queue


class PRIdentityTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.path = self.root / 'pr_state.json'
        self.now = datetime.now(timezone.utc)

    def stamp(self, minutes=0):
        return (self.now - timedelta(minutes=minutes)).isoformat()

    def observation(self, minutes=0, **changes):
        result = dict(state='OPEN', checked_at=self.stamp(minutes),
                      updatedAt=self.stamp(minutes), headRefOid='a' * 40,
                      reviewDecision='-', mergeable='MERGEABLE',
                      ci='no-checks', ci_head_oid='a' * 40,
                      ci_fingerprint=oss.ci_fingerprint([]), ci_checked_at=self.stamp(minutes))
        result.update(changes)
        return result

    def write(self, records):
        self.path.write_bytes(json.dumps(records).encode('utf-8'))
        return self.path.read_bytes()

    def test_load_merge_and_queue_keep_the_latest_reopened_pr(self):
        self.write({'Owner/Repo#1': self.observation(10)})
        records = state.load_pr_state(self.path, ())
        records = state.merge_observations(records, {
            'owner/repo#1': self.observation(5, state='CLOSED')})
        records = state.merge_observations(records, {
            'Owner/Repo#1': self.observation(reviewDecision='CHANGES_REQUESTED')})
        self.write(records)
        rows = queue.refresh(self.root)
        self.assertEqual([(row['key'], row['score']) for row in rows], [('owner/repo#1', 85)])
        self.assertEqual(list(records), ['owner/repo#1'])

    def test_existing_aliases_choose_the_latest_whole_observation_in_either_order(self):
        older = self.observation(10, title='Historical title')
        newer = self.observation(1, reviewDecision='CHANGES_REQUESTED', ci_fingerprint='b' * 64)
        for reverse in (False, True):
            entries = [('Owner/Repo#1', older), ('owner/repo#1', newer)]
            self.write(dict(reversed(entries) if reverse else entries))
            records = state.load_pr_state(self.path, ())
            self.assertEqual(records, {'owner/repo#1': dict(older, **newer)})
        self.assertNotIn('title', newer)

    def test_identical_undated_aliases_collapse_without_inventing_freshness(self):
        original = {'state': 'OPEN', 'title': 'Legacy'}
        self.write({'Owner/Repo#1': original, 'owner/repo#1': deepcopy(original)})
        self.assertEqual(state.load_pr_state(self.path, ()), {'owner/repo#1': original})

    def test_ambiguous_aliases_do_not_change_the_cache_or_report(self):
        older = self.observation(10)
        cases = [self.observation(10, state='CLOSED'),
                 self.observation(1, checked_at='invalid'),
                 self.observation(1, checked_at='2026-10-26T10:00:00'),
                 {key: value for key, value in self.observation(1).items() if key != 'checked_at'}]
        report = self.root / 'PR_STATUS.md'
        for newer in cases:
            with self.subTest(newer=newer):
                records = {'Owner/Repo#1': older, 'owner/repo#1': newer}
                original = self.write(records)
                report.write_bytes(b'previous report')
                with self.assertRaises(ValueError):
                    state.load_pr_state(self.path, ())
                with self.assertRaises(ValueError):
                    state.save_observations(self.path, records, {}, report)
                self.assertEqual(self.path.read_bytes(), original)
                self.assertEqual(report.read_bytes(), b'previous report')

    def test_invalid_alias_state_is_rejected_before_selecting_a_successful_alias(self):
        records = {'Owner/Repo#1': self.observation(10, state='invalid'),
                   'owner/repo#1': self.observation(1)}
        original = self.write(records)
        report = self.root / 'PR_STATUS.md'
        report.write_bytes(b'previous report')
        with self.assertRaisesRegex(ValueError, 'Invalid PR state'):
            state.load_pr_state(self.path, ())
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(report.read_bytes(), b'previous report')

    def test_old_query_failure_does_not_override_a_later_recovery(self):
        older = self.observation(10, query_error='old timeout', query_error_at=self.stamp(5))
        newer = self.observation(1, reviewDecision='APPROVED')
        for entries in ((older, newer), (newer, older)):
            self.write(dict(zip(('Owner/Repo#1', 'owner/repo#1'), entries)))
            result = state.load_pr_state(self.path, ())['owner/repo#1']
            self.assertEqual(result['reviewDecision'], 'APPROVED')
            self.assertNotIn('query_error', result)
            self.assertNotIn('query_error_at', result)

    def test_new_query_failure_survives_a_newer_success_from_another_alias(self):
        failed = self.observation(10, query_error='new timeout', query_error_at=self.stamp())
        recovered_earlier = self.observation(5, reviewDecision='APPROVED')
        for entries in ((failed, recovered_earlier), (recovered_earlier, failed)):
            self.write(dict(zip(('Owner/Repo#1', 'owner/repo#1'), entries)))
            result = state.load_pr_state(self.path, ())['owner/repo#1']
            self.assertEqual(result['reviewDecision'], 'APPROVED')
            self.assertEqual(result['query_error'], 'new timeout')
            self.assertEqual(result['query_error_at'], self.stamp())

    def test_ambiguous_error_times_are_not_silently_dropped(self):
        newer = self.observation(1)
        for error_time in (None, 'invalid', self.stamp(1)):
            with self.subTest(error_time=error_time):
                failed = self.observation(10, query_error='timeout', query_error_at=error_time)
                original = self.write({'Owner/Repo#1': failed, 'owner/repo#1': newer})
                with self.assertRaises(ValueError):
                    state.load_pr_state(self.path, ())
                self.assertEqual(self.path.read_bytes(), original)

    def test_old_ci_history_stays_bound_to_its_original_head_and_render_is_unique(self):
        older = self.observation(10)
        newer = dict(state='OPEN', checked_at=self.stamp(), headRefOid='b' * 40)
        self.write({'Owner/Repo#1': older, 'owner/repo#1': newer})
        records = state.load_pr_state(self.path, ())
        result = records['owner/repo#1']
        self.assertEqual(result['ci_head_oid'], 'a' * 40)
        self.assertEqual(result['headRefOid'], 'b' * 40)
        text = state.render_pr_status({'Owner/Repo#1': older, 'owner/repo#1': newer})
        self.assertEqual(text.count('| [owner/repo#1]'), 1)
        self.assertIn('当前版本 CI 未验证', text)

    def test_ci_group_uses_its_own_time_across_three_alias_permutations(self):
        metadata = self.observation(ci_checked_at=self.stamp(20))
        failed = self.observation(10, ci='0✓/1✗/0…/0ERR/0SKIP/0UNKNOWN', ci_fingerprint='b' * 64)
        entries = [('Owner/Repo#1', metadata), ('owner/repo#1', failed),
                   ('OWNER/REPO#1', self.observation(30, state='CLOSED'))]
        for ordering in permutations(entries):
            self.write(dict(ordering))
            result = state.load_pr_state(self.path, ())['owner/repo#1']
            self.assertEqual(result['state'], 'OPEN')
            self.assertEqual(result['checked_at'], metadata['checked_at'])
            self.assertEqual(result['ci'], failed['ci'])
            self.assertEqual(result['ci_fingerprint'], failed['ci_fingerprint'])
            self.assertEqual(result['ci_checked_at'], failed['ci_checked_at'])
            self.assertEqual(state.ci_binding_error(result), '')

    def test_conflicting_ci_requires_valid_distinct_ci_times(self):
        older = self.observation(10)
        for ci_time in (None, 'invalid', '2026-10-26T10:00:00', older['ci_checked_at']):
            with self.subTest(ci_time=ci_time):
                newer = self.observation(1, ci='0✓/1✗/0…/0ERR/0SKIP/0UNKNOWN',
                                         ci_checked_at=ci_time)
                original = self.write({'Owner/Repo#1': older, 'owner/repo#1': newer})
                with self.assertRaises(ValueError):
                    state.load_pr_state(self.path, ())
                self.assertEqual(self.path.read_bytes(), original)

    def test_new_incomplete_ci_group_does_not_inherit_old_binding_fields(self):
        older = self.observation(10)
        newer = dict(state='OPEN', checked_at=self.stamp(), headRefOid='a' * 40,
                     ci='0✓/1✗/0…/0ERR/0SKIP/0UNKNOWN', ci_checked_at=self.stamp())
        self.write({'Owner/Repo#1': older, 'owner/repo#1': newer})
        result = state.load_pr_state(self.path, ())['owner/repo#1']
        self.assertNotIn('ci_head_oid', result)
        self.assertNotIn('ci_fingerprint', result)
        self.assertTrue(state.ci_binding_error(result))

    def test_mixed_success_and_error_observation_aliases_do_not_write(self):
        previous = {'owner/repo#1': self.observation(20)}
        original = self.write(previous)
        report = self.root / 'PR_STATUS.md'
        report.write_bytes(b'previous report')
        observations = {'Owner/Repo#1': self.observation(5), 'owner/repo#1': {
            'state': 'QUERY_ERROR', '_err': 'timeout', 'checked_at': self.stamp()}}
        with self.assertRaises(ValueError):
            state.save_observations(self.path, previous, observations, report)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(report.read_bytes(), b'previous report')

    def test_monitor_loaders_and_diff_comparisons_use_the_same_identity(self):
        ledger = self.root / 'STATE.md'
        ledger.write_text('| [#1](https://github.com/Owner/Repo/pull/1) | OPEN(today) |', encoding='utf-8')
        for module in (oss, scope):
            loader = 'load_keys' if module is oss else 'load_state_keys'
            with self.subTest(module=module.__name__), patch.object(module, 'STATE', str(ledger)):
                self.assertEqual(list(getattr(module, loader)()), ['owner/repo#1'])
            self.write({'owner/repo#1': self.observation(1)})
            output = io.StringIO()
            with patch.object(module, 'CANONICAL', str(self.path)), \
                    patch.object(module, 'REPORT', str(self.root / 'PR_STATUS.md')), \
                    patch.object(module, 'STATE', str(ledger)), \
                    patch.object(module, 'LEGACY_PATHS', ()), \
                    patch.object(module, loader, return_value={'Owner/Repo#1': {}}), \
                    patch.object(module, 'fetch', return_value=self.observation(
                        reviewDecision='CHANGES_REQUESTED', title='New feedback')), \
                    patch.object(oss, 'audit_scope'), \
                    redirect_stdout(output):
                self.assertEqual(module.main(), 0)
            self.assertIn('-> CHANGES_REQUESTED', output.getvalue())
            self.assertNotIn('新增在飞', output.getvalue())

    def test_closed_pr_removes_a_ledger_row_with_different_case(self):
        ledger = self.root / 'STATE.md'
        row = '| [#1](https://github.com/Owner/Repo/pull/1) | OPEN(today) |'
        ledger.write_text('## OSS 贡献在飞（1）\n' + row + '\n', encoding='utf-8')
        self.assertEqual(oss.reconcile_state_ledger(
            {'owner/repo#1': {'state': 'MERGED'}}, str(ledger)), [row])
        self.assertNotIn('/pull/1', ledger.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
