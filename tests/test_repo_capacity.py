"""Repository capacity is checked against complete, isolated GitHub fixtures."""
from copy import deepcopy
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import json
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import repo_capacity as capacity
from task_state import TaskStore
from repository_policy import ACCOUNT


class GitHub:
    def __init__(self, numbers=(1, 2)):
        self.repo = 'owner/repo'
        self.calls = []
        self.rows = [{'number': n, 'state': 'open', 'user': {'login': ACCOUNT},
                      'html_url': f'https://github.com/{self.repo}/pull/{n}',
                      'draft': False, 'head': {'sha': str(n) * 40},
                      'updated_at': '2026-11-01T00:00:00Z'} for n in numbers]
        self.views = {n: {'number': n, 'state': 'OPEN', 'author': {'login': ACCOUNT},
                         'url': f'https://github.com/{self.repo}/pull/{n}',
                         'headRefOid': str(n) * 40, 'isDraft': False, 'mergeable': 'MERGEABLE',
                         'reviewDecision': '', 'updatedAt': '2026-11-01T00:00:00Z',
                         'statusCheckRollup': []} for n in numbers}
        self.activity = {}
        self.second_rows = None
        self.list_calls = 0

    def __call__(self, args):
        self.calls.append(args)
        if args[0] == 'pr':
            return json.dumps(self.views[int(args[2])])
        path = args[1]
        if path.endswith('/pulls?state=open&per_page=100'):
            self.list_calls += 1
            rows = self.second_rows if self.second_rows is not None and self.list_calls % 2 == 0 else self.rows
            return json.dumps([rows])
        return json.dumps([self.activity.get(path, [])])


class CapacityTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.store = TaskStore(root=self.root)
        self.now = datetime(2026, 11, 5, tzinfo=timezone.utc)
        self.repo = 'owner/repo'
        self.gh = GitHub()
        self.sources = [f'https://github.com/{self.repo}/pull/{n}' for n in (1, 2)]

    def check(self, **kwargs):
        return capacity.live_capacity(self.repo, self.store, query=self.gh, now=self.now, **kwargs)

    def confirm(self):
        return self.check(confirm_wait=True, sources=self.sources, note='Both PRs ready; waiting for maintainers')

    def state(self):
        return TaskStore(root=self.root).queue['capacity'][self.repo]

    def human(self, number=1, login='maintainer', body='Please look at this'):
        self.gh.activity[f'repos/{self.repo}/issues/{number}/comments?per_page=100'] = [
            {'id': 10, 'body': body, 'user': {'login': login, 'type': 'User'},
             'created_at': '2026-11-01T00:00:00Z', 'updated_at': '2026-11-01T00:00:00Z'}]

    def test_two_open_prs_need_confirmation_and_seven_full_days(self):
        self.assertEqual(self.check()['status'], 'HOLD')
        self.assertEqual(self.confirm()['status'], 'HOLD')
        self.now += timedelta(days=7) - timedelta(seconds=1)
        self.assertFalse(self.check()['allowed'])
        self.now += timedelta(seconds=1)
        self.assertTrue(self.check()['allowed'])

    def test_repeated_confirmation_keeps_since_without_backdating(self):
        self.confirm()
        since = self.state()['wait']['since']
        self.now += timedelta(days=2)
        self.confirm()
        self.assertEqual(self.state()['wait']['since'], since)
        self.assertEqual(since, '2026-11-05T00:00:00+00:00')

    def test_three_open_is_absolute_cap_even_with_old_wait(self):
        self.confirm()
        self.now += timedelta(days=30)
        self.gh = GitHub((1, 2, 3))
        self.assertEqual(self.check()['count'], 3)
        self.assertFalse(self.check()['allowed'])
        self.assertNotIn('wait', self.state())

    def test_zero_and_one_are_allowed_but_known_own_work_blocks(self):
        for numbers in ((), (1,)):
            self.gh = GitHub(numbers)
            self.assertTrue(self.check()['allowed'])
        self.gh.views[1]['reviewDecision'] = 'CHANGES_REQUESTED'
        self.assertEqual(self.check()['status'], 'HOLD')

    def test_sources_must_cover_both_real_prs_and_note_is_required(self):
        for sources, note in ((self.sources[:1], 'checked'), (self.sources, ''),
                              (['https://evil.test/owner/repo/pull/1', self.sources[1]], 'checked')):
            result = self.check(confirm_wait=True, sources=sources, note=note)
            self.assertFalse(result['allowed'])
            self.assertNotIn('wait', self.state())
        sources = ['https://github.com/OWNER/REPO/issues/1#issuecomment-12', self.sources[1]]
        self.check(confirm_wait=True, sources=sources, note='reviewed both')
        self.assertIn('wait', self.state())

    def test_new_commit_or_human_feedback_invalidates_wait(self):
        self.confirm()
        self.now += timedelta(days=8)
        self.gh.rows[0]['head']['sha'] = self.gh.views[1]['headRefOid'] = 'a' * 40
        self.assertFalse(self.check()['allowed'])
        self.assertNotIn('wait', self.state())
        self.confirm()
        self.now += timedelta(days=8)
        self.human()
        self.assertFalse(self.check()['allowed'])
        self.assertNotIn('wait', self.state())

    def test_bot_and_self_comments_do_not_restart_wait_but_human_edits_do(self):
        self.human(body='Initial feedback')
        self.confirm()
        self.now += timedelta(days=8)
        path = f'repos/{self.repo}/issues/1/comments?per_page=100'
        self.gh.activity[path] += [
            {'id': 11, 'body': 'CI', 'user': {'login': 'ci[bot]', 'type': 'Bot'},
             'created_at': '2026-11-06T00:00:00Z', 'updated_at': '2026-11-06T00:00:00Z'},
            {'id': 12, 'body': 'Reminder', 'user': {'login': ACCOUNT.upper(), 'type': 'User'},
             'created_at': '2026-11-06T00:00:00Z', 'updated_at': '2026-11-06T00:00:00Z'}]
        self.assertTrue(self.check()['allowed'])
        self.gh.activity[path][0]['body'] = 'Actually fix this first'
        self.assertFalse(self.check()['allowed'])

    def test_human_name_containing_bot_is_not_ignored(self):
        self.confirm()
        self.now += timedelta(days=8)
        self.human(login='robotics-developer')
        self.assertFalse(self.check()['allowed'])

    def test_reviews_and_inline_comments_are_included_with_complete_pagination(self):
        self.confirm()
        self.now += timedelta(days=8)
        self.gh.activity[f'repos/{self.repo}/pulls/1/comments?per_page=100'] = [
            {'id': 13, 'body': 'Inline feedback', 'user': {'login': 'reviewer', 'type': 'User'},
             'created_at': '2026-11-06T00:00:00Z', 'updated_at': '2026-11-06T00:00:00Z'}]
        self.assertFalse(self.check()['allowed'])
        paths = [args[1] for args in self.gh.calls if args[0] == 'api']
        self.assertIn(f'repos/{self.repo}/pulls/1/reviews?per_page=100', paths)
        self.assertIn(f'repos/{self.repo}/pulls/1/comments?per_page=100', paths)
        self.assertTrue(all('--paginate' in args and '--slurp' in args for args in self.gh.calls if args[0] == 'api'))

    def test_readiness_loss_clears_wait_even_if_next_check_recovers(self):
        self.confirm()
        self.now += timedelta(days=8)
        self.gh.views[1]['isDraft'] = True
        self.assertFalse(self.check()['allowed'])
        self.gh.views[1]['isDraft'] = False
        self.assertFalse(self.check()['allowed'])

    def test_query_failure_or_inconsistent_second_list_cannot_preserve_wait(self):
        self.confirm()
        self.now += timedelta(days=8)
        result = capacity.live_capacity(self.repo, self.store, query=lambda args: None, now=self.now)
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertNotIn('wait', self.state())
        self.gh.second_rows = []
        self.assertEqual(self.check()['status'], 'UNKNOWN')

    def test_foreign_author_is_not_counted_and_invalid_pages_fail_closed(self):
        self.gh = GitHub((1,))
        foreign = deepcopy(self.gh.rows[0])
        foreign['number'] = 99
        foreign['user']['login'] = 'someone-else'
        self.gh.rows.append(foreign)
        self.assertEqual(self.check()['count'], 1)
        for raw in ('[]', '{}', '[{}]', '[[null]]', 'not json'):
            result = capacity.live_capacity(self.repo, self.store, query=lambda args: raw, now=self.now)
            self.assertEqual(result['status'], 'UNKNOWN')

    def test_late_old_response_cannot_overwrite_new_observation(self):
        original_query = self.gh
        called = False

        def delayed(args):
            nonlocal called
            if not called:
                called = True
                newer = self.now + timedelta(seconds=1)
                capacity.live_capacity(self.repo, self.store, query=GitHub((1, 2, 3)), now=newer)
            return original_query(args)

        result = capacity.live_capacity(self.repo, self.store, query=delayed, now=self.now)
        self.assertFalse(result['allowed'])
        self.assertEqual(len(self.state()['open']), 3)

    def test_cached_prefilter_keeps_new_repositories_but_not_full_ones(self):
        self.assertTrue(capacity.cached_capacity('New/Repo', self.store, records={}, now=self.now)['allowed'])
        records = {f'{self.repo}#{n}': {'state': 'OPEN'} for n in (1, 2)}
        self.assertEqual(capacity.cached_capacity(self.repo, self.store, records=records, now=self.now)['status'], 'HOLD')
        self.assertFalse(self.store.path.exists())

    def test_cached_snapshot_expires_and_new_pr_observation_blocks_wait(self):
        self.confirm()
        self.now += timedelta(days=8)
        self.check()
        self.assertTrue(capacity.cached_capacity(self.repo, self.store, records={}, now=self.now)['allowed'])
        records = {f'{self.repo}#1': {'state': 'OPEN', 'headRefOid': 'f' * 40,
                                    'checked_at': (self.now + timedelta(seconds=1)).isoformat()}}
        self.assertFalse(capacity.cached_capacity(self.repo, self.store, records=records, now=self.now)['allowed'])
        self.now += timedelta(days=2)
        self.assertFalse(capacity.cached_capacity(self.repo, self.store, records={}, now=self.now)['allowed'])

    def test_network_queries_never_hold_task_store_lock(self):
        query = self.gh

        def check_lock(args):
            with self.store.transaction():
                pass
            return query(args)

        self.assertEqual(capacity.live_capacity(self.repo, self.store, query=check_lock, now=self.now)['status'], 'HOLD')

    def test_monitor_failure_marker_survives_recovery_and_requires_new_confirmation(self):
        self.confirm()
        self.now += timedelta(days=8)
        marker = (self.now - timedelta(days=1)).isoformat()
        (self.root / 'pr_state.json').write_bytes(json.dumps({f'{self.repo}#1': {
            'state': 'OPEN', 'capacity_invalidated_at': marker}}).encode())
        self.assertFalse(self.check()['allowed'])
        self.assertNotIn('wait', self.state())
        self.confirm()
        self.assertEqual(self.state()['wait']['since'], self.now.isoformat())
        self.assertFalse(self.check()['allowed'])

    def test_marker_written_during_network_query_invalidates_old_wait(self):
        self.confirm()
        self.now += timedelta(days=8)
        query = self.gh
        called = False

        def monitor_update(args):
            nonlocal called
            if not called:
                called = True
                (self.root / 'pr_state.json').write_bytes(json.dumps({f'{self.repo}#1': {
                    'state': 'OPEN', 'capacity_invalidated_at': self.now.isoformat()}}).encode())
            return query(args)

        result = capacity.live_capacity(self.repo, self.store, query=monitor_update, now=self.now)
        self.assertFalse(result['allowed'])
        self.assertNotIn('wait', self.state())

    def test_activity_change_during_query_is_unknown_without_permanent_bot_binding(self):
        self.confirm()
        since = self.state()['wait']['since']
        self.now += timedelta(days=8)
        self.gh.second_rows = deepcopy(self.gh.rows)
        self.gh.second_rows[0]['updated_at'] = '2026-11-06T00:00:00Z'
        self.assertEqual(self.check()['status'], 'UNKNOWN')
        self.assertEqual(self.state()['wait']['since'], since)
        self.gh.rows = self.gh.second_rows
        self.gh.second_rows = None
        self.assertTrue(self.check()['allowed'])
        self.assertEqual(self.state()['wait']['since'], since)

    def test_corrupt_ready_snapshot_without_human_evidence_cannot_allow_third(self):
        self.confirm()
        self.now += timedelta(days=8)
        self.check()
        with self.store.transaction() as ledger:
            ledger['queue']['capacity'][self.repo]['open'][f'{self.repo}#1'].pop('human_fingerprint')
        self.assertEqual(capacity.cached_capacity(self.repo, self.store, records={}, now=self.now)['status'], 'UNKNOWN')

    def test_neutral_and_skipped_checks_are_not_invented_failures(self):
        for result in ('NEUTRAL', 'SKIPPED'):
            self.gh.views[1]['statusCheckRollup'] = [
                {'name': 'optional', 'detailsUrl': 'https://example.com/check',
                 'status': 'COMPLETED', 'conclusion': result}]
            self.confirm()
            self.assertIn('wait', self.state())

    def test_implicit_cache_reads_pr_state_only_once_per_store(self):
        with patch.object(capacity, 'load_pr_state', return_value={}) as read:
            for repo in ('o/a', 'o/b', 'o/a'):
                self.assertTrue(capacity.cached_capacity(repo, self.store, now=self.now)['allowed'])
            self.assertEqual(read.call_count, 1)

    def local_action(self, action):
        with self.store.transaction() as ledger:
            entry = ledger['queue']['prs'].setdefault(f'{self.repo}#1', {'events': []})
            event = {'at': self.now.isoformat(), 'action': action, 'minutes': 0,
                     'source': self.sources[0], 'note': 'Manual assessment'}
            entry.update(event)
            entry['events'].append(event)

    def test_local_pending_work_blocks_live_cached_and_confirmation(self):
        self.confirm()
        self.now += timedelta(days=8)
        for action in ('small_fix', 'ci', 'discussion'):
            self.local_action(action)
            self.assertFalse(capacity.cached_capacity(self.repo, self.store, records={}, now=self.now)['allowed'])
            self.assertEqual(self.confirm()['status'], 'HOLD')
            self.assertNotIn('wait', self.state())
        self.gh = GitHub((1,))
        self.assertEqual(self.check()['status'], 'HOLD')

    def test_local_pending_work_then_done_cannot_revive_old_wait(self):
        self.confirm()
        old_since = self.state()['wait']['since']
        self.now += timedelta(days=8)
        self.local_action('small_fix')
        self.local_action('done')
        self.assertFalse(self.check()['allowed'])
        self.assertNotIn('wait', self.state())
        self.now += timedelta(seconds=1)
        self.confirm()
        self.assertNotEqual(self.state()['wait']['since'], old_since)
        self.assertEqual(self.state()['wait']['since'], self.now.isoformat())

    def test_local_action_added_during_queries_is_reloaded_before_saving(self):
        self.confirm()
        self.now += timedelta(days=8)
        called = False

        def new_action(args):
            nonlocal called
            if not called:
                called = True
                self.local_action('ci')
            return self.gh(args)

        self.assertFalse(capacity.live_capacity(self.repo, self.store, query=new_action, now=self.now)['allowed'])
        self.assertNotIn('wait', self.state())

    def test_cli_exit_codes_are_admission_codes_and_corrupt_state_is_friendly(self):
        for gh, expected in ((GitHub(()), 0), (GitHub(), 2)):
            with patch.object(capacity, 'output', side_effect=gh), redirect_stdout(io.StringIO()) as out:
                self.assertEqual(capacity.main(['--root', str(self.root), 'check', self.repo]), expected)
            self.assertIn(json.loads(out.getvalue())['status'], ('ALLOW', 'HOLD'))
        self.store.path.write_bytes(b'broken')
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(capacity.main(['--root', str(self.root), 'check', self.repo]), 1)
        self.assertEqual(json.loads(out.getvalue())['status'], 'UNKNOWN')

    def test_cached_pending_ci_without_a_monitor_marker_is_not_ignored(self):
        records = {f'{self.repo}#1': {'state': 'OPEN', 'ci': '0✓/0✗/1…/0ERR/0SKIP/0UNKNOWN'}}
        self.assertEqual(capacity.cached_capacity(self.repo, self.store, records=records, now=self.now)['status'], 'HOLD')


if __name__ == '__main__':
    unittest.main()
