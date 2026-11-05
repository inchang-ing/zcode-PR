import json
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import work_queue as q
from monitor_oss import ci_fingerprint, ci_summary
from auto_run import Candidate, DispatchedStore
from pr_state import merge_observations
from contributions import new_record


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.now = datetime.now(timezone.utc)
        self.stamp = self.now.isoformat()
        self.state = q.load_queue(self.root / 'state.json')
        self.store = DispatchedStore(str(self.root / 'dispatched.json'))
        self.c = Candidate('example/repo', 1, 'Bug: crash', '', is_bug=True, checked_at=self.stamp)

    def rank(self):
        return q.rank_candidates([self.c, self.c], self.state, self.store, {}, self.now)[0]

    def verified(self):
        self.state['issues'][self.c.key] = {'stage': 'probe', 'signals': {
            s: {'value': True, 'at': self.stamp, 'source': 'https://example.com/proof'} for s in q.SIGNALS}, 'events': []}

    def pr(self, checks=None):
        checks = [] if checks is None else checks
        return dict(state='OPEN', checked_at=self.stamp, updatedAt=self.stamp,
                    reviewDecision='-', headRefOid='a' * 40, ci_head_oid='a' * 40,
                    ci=ci_summary(checks), ci_fingerprint=ci_fingerprint(checks),
                    ci_checked_at=self.stamp)

    def failure(self, name='test', run=1):
        return dict(name=name, status='COMPLETED', conclusion='FAILURE',
                    detailsUrl=f'https://example.com/checks/{run}')

    def test_unknown_not_ready_even_with_bug_label(self):
        self.assertFalse(self.rank()['ready'])

    def test_gate_overrides_score_and_expiry(self):
        self.verified()
        self.assertTrue(self.rank()['ready'])
        self.state['issues'][self.c.key]['signals']['policy']['value'] = False
        self.assertFalse(self.rank()['ready'])
        self.state['issues'][self.c.key]['signals']['policy']['value'] = True
        self.c.checked_at = (self.now - timedelta(days=2)).isoformat()
        self.assertFalse(self.rank()['ready'])

    def test_restrictions_and_dedup(self):
        self.verified()
        self.store.mark(self.c.key, 'dropped', reason='claimed')
        self.assertTrue(self.rank()['hidden'])
        self.c.repo = 'stanfordnlp/dspy'
        self.assertFalse(self.rank()['ready'])

    def test_stopped_requires_explicit_reopen(self):
        self.verified()
        self.state['issues'][self.c.key]['stage'] = 'stopped'
        self.assertTrue(self.rank()['hidden'])
        self.state['issues'][self.c.key]['stage'] = 'deferred'
        self.state['issues'][self.c.key]['retry_at'] = (self.now + timedelta(days=1)).isoformat()
        self.assertTrue(self.rank()['hidden'])
        self.state['issues'][self.c.key]['retry_at'] = (self.now - timedelta(days=1)).isoformat()
        self.assertFalse(self.rank()['hidden'])

    def test_explicit_untestable_blocks_even_when_old_until_reassessed(self):
        self.verified()
        signal = self.state['issues'][self.c.key]['signals']['testable']
        signal['value'] = False
        for stage in ('new', 'probe', 'fixing'):
            self.state['issues'][self.c.key]['stage'] = stage
            for age in (0, 3):
                signal['at'] = (self.now - timedelta(days=age)).isoformat()
                row = self.rank()
                self.assertFalse(row['ready'])
                self.assertIn('延期或退出', row['next'])
                self.assertNotIn('限时 20 分钟复现探路', row['next'])
        signal.update(value=True, at=self.stamp)
        self.assertTrue(self.rank()['ready'])

    def test_unknown_testability_can_be_probed_but_not_fixed(self):
        self.verified()
        del self.state['issues'][self.c.key]['signals']['testable']
        self.assertTrue(self.rank()['ready'])
        self.state['issues'][self.c.key]['stage'] = 'fixing'
        self.assertFalse(self.rank()['ready'])

    def test_pr_order_and_stale_observations(self):
        pr = self.pr()
        pr['reviewDecision'] = 'CHANGES_REQUESTED'
        cache = {'example/repo#2': pr,
                 'example/repo#3': {'state': 'MERGED', 'ci': '1✗'}}
        rows = q.pr_tasks(cache, self.state, [], self.now)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['score'], 85)
        cache['example/repo#2']['query_error'] = 'offline'
        self.assertFalse(q.pr_tasks(cache, self.state, [], self.now)[0]['ready'])

    def test_first_pr_query_failure_stays_visible_for_verification(self):
        cache = merge_observations(
            {'a/b#3': {'state': 'CLOSED'}, 'a/b#4': {'state': 'MERGED'}},
            {key: {'state': 'QUERY_ERROR', '_err': 'timeout'}
             for key in ('a/b#2', 'a/b#3', 'a/b#4')})
        (self.root / 'pr_state.json').write_text(json.dumps(cache), encoding='utf-8')
        rows = q.refresh(self.root)
        self.assertEqual([row['key'] for row in rows], ['a/b#2'])
        self.assertFalse(rows[0]['ready'])
        self.assertIn('查询失败', rows[0]['next'])
        self.assertIn('缓存 OPEN 数：0', (self.root / 'WORK_QUEUE.md').read_text(encoding='utf-8'))

    def test_weekly_does_not_use_import_or_update_date_as_merge_date(self):
        cache = {'a/b#1': {'state': 'MERGED', 'updatedAt': self.stamp},
                 'a/b#2': {'state': 'OPEN', 'createdAt': self.stamp},
                 'a/b#3': {'state': 'MERGED', 'createdAt': self.stamp, 'mergedAt': self.stamp}}
        report = '\n'.join(q.weekly(cache, self.state, self.now))
        self.assertIn('本周合并：1；已合并但缺日期：1', report)
        self.assertIn('等待 1', report)
        self.assertIn('100%', report)

    def test_ci_unknown_and_independent_freshness(self):
        cache = {'example/repo#2': {'state': 'OPEN', 'checked_at': self.stamp, 'ci': '1UNKNOWN'}}
        self.assertFalse(q.pr_tasks(cache, self.state, [], self.now)[0]['ready'])
        cache['example/repo#2']['ci_checked_at'] = self.stamp
        self.assertFalse(q.pr_tasks(cache, self.state, [], self.now)[0]['ready'])
        self.assertIsNone(q.observation_ack(cache['example/repo#2'], self.now))
        cache['example/repo#2'] = self.pr([self.failure()])
        self.assertTrue(q.pr_tasks(cache, self.state, [], self.now)[0]['ready'])

    def test_acknowledgement_expires_on_new_activity(self):
        key = 'example/repo#2'
        self.state['prs'][key] = {'action': 'done', 'at': self.stamp}
        cache = {key: self.pr()}
        cache[key]['reviewDecision'] = 'CHANGES_REQUESTED'
        self.state['prs'][key]['ack'] = q.observation_ack(cache[key], self.now)
        self.assertEqual(q.pr_tasks(cache, self.state, [], self.now), [])
        cache[key]['updatedAt'] = (self.now + timedelta(seconds=1)).isoformat()
        self.assertEqual(len(q.pr_tasks(cache, self.state, [], self.now)), 1)

    def test_confirmed_merge_conflict_enters_work_queue(self):
        pr = dict(self.pr(), mergeable='CONFLICTING')
        rows = q.pr_tasks({'a/b#1': pr}, self.state, [], self.now)
        self.assertEqual([(row['key'], row['score'], row['ready']) for row in rows],
                         [('a/b#1', 90, True)])
        self.assertIn('冲突', rows[0]['next'])
        pr['reviewDecision'] = 'CHANGES_REQUESTED'
        self.assertEqual(q.pr_tasks({'a/b#1': pr}, self.state, [], self.now)[0]['score'], 90)
        pr['query_error'] = 'offline'
        self.assertEqual(q.pr_tasks({'a/b#1': pr}, self.state, [], self.now)[0]['score'], 10)
        with patch.dict(q.INTERACTION_HOLDS, {'a/b': 'Policy hold'}):
            row = q.pr_tasks({'a/b#1': pr}, self.state, [], self.now)[0]
            self.assertEqual((row['score'], row['ready'], row['stage']), (0, False, 'policy_hold'))

    def test_new_conflict_reopens_wait_and_done_but_same_conflict_stays_acknowledged(self):
        key, pr = 'a/b#1', dict(self.pr(), mergeable='MERGEABLE')
        conflicting = dict(pr, mergeable='CONFLICTING')
        for action in ('wait', 'done'):
            with self.subTest(action=action):
                self.state['prs'][key] = {'action': action, 'ack': q.observation_ack(pr, self.now)}
                row = q.pr_tasks({key: conflicting}, self.state, [], self.now)[0]
                self.assertEqual((row['score'], row['stage']), (90, 'review'))
                self.state['prs'][key]['ack'] = q.observation_ack(conflicting, self.now)
                self.assertEqual(q.pr_tasks({key: conflicting}, self.state, [], self.now), [])

    def test_nonconflicting_mergeability_does_not_reopen_wait_and_done(self):
        key, pr = 'a/b#1', dict(self.pr(), mergeable='MERGEABLE')
        for action in ('wait', 'done'):
            self.state['prs'][key] = {'action': action, 'ack': q.observation_ack(pr, self.now)}
            for mergeable in ('UNKNOWN', 'MERGEABLE', '-', None):
                with self.subTest(action=action, mergeable=mergeable):
                    current = dict(pr, mergeable=mergeable)
                    self.assertEqual(q.pr_tasks({key: current}, self.state, [], self.now), [])
                    self.assertEqual(q.pr_tasks({key: current}, {'prs': {}}, [], self.now), [])

    def test_resolved_or_unknown_conflict_requires_reconfirmation_without_conflict_priority(self):
        key, pr = 'a/b#1', dict(self.pr(), mergeable='CONFLICTING')
        for action in ('wait', 'done'):
            self.state['prs'][key] = {'action': action, 'ack': q.observation_ack(pr, self.now)}
            for mergeable in ('MERGEABLE', 'UNKNOWN'):
                with self.subTest(action=action, mergeable=mergeable):
                    row = q.pr_tasks({key: dict(pr, mergeable=mergeable)}, self.state, [], self.now)[0]
                    self.assertEqual((row['score'], row['stage']), (15, 'review'))
                    self.assertNotIn('冲突', row['next'])

    def test_legacy_ack_without_conflict_binding_only_covers_nonconflicting_state(self):
        key, pr = 'a/b#1', dict(self.pr(), mergeable='MERGEABLE')
        ack = q.observation_ack(pr, self.now)
        ack.pop('merge_conflict', None)
        for action in ('wait', 'done'):
            with self.subTest(action=action):
                self.state['prs'][key] = {'action': action, 'ack': ack}
                self.assertEqual(q.pr_tasks({key: pr}, self.state, [], self.now), [])
                rows = q.pr_tasks({key: dict(pr, mergeable='CONFLICTING')}, self.state, [], self.now)
                self.assertEqual([row['score'] for row in rows], [90])

    def test_local_feedback_changes_reopen_wait_and_done(self):
        key, pr = 'a/b#1', self.pr()
        record = new_record('a/b', 2, 'Regression', 1)
        item = dict(kind='fact', summary='Add a boundary test', observed_at=self.stamp,
                    sources=[dict(kind='url', ref='https://github.com/a/b/pull/1#issuecomment-2')])
        for action in ('wait', 'done'):
            for previous_items, current_items in (([], [item]), ([item], [dict(item, summary='Fix cleanup too')])):
                with self.subTest(action=action, previous_items=previous_items):
                    record['feedback']['items'] = deepcopy(previous_items)
                    with patch.object(q, 'ROOT', self.root), patch.object(q, 'refresh', return_value=[]), \
                         patch.object(q, 'load_records', return_value=[record]), \
                         patch.object(q, 'load_pr_state', return_value={key: pr}):
                        q.main(['pr-action', key, action, '--source', 'https://example.com/review',
                                '--note', 'Reviewed current feedback'])
                    state = q.load_queue(self.root / 'work_queue.json')
                    self.assertEqual(q.pr_tasks({key: pr}, state, [record], self.now), [])
                    record['feedback']['items'] = deepcopy(current_items)
                    rows = q.pr_tasks({key: pr}, state, [record], self.now)
                    self.assertEqual([(row['key'], row['score']) for row in rows], [(key, 15)])

    def test_feedback_reordering_and_check_time_do_not_reopen_action(self):
        key, pr = 'a/b#1', self.pr()
        record = new_record('a/b', 2, 'Regression', 1)
        sources = [dict(kind='url', ref='https://example.com/one'),
                   dict(kind='url', ref='https://example.com/two')]
        record['feedback']['items'] = [dict(kind='fact', summary=summary, observed_at=self.stamp,
                                          sources=deepcopy(sources)) for summary in ('One', 'Two')]
        with patch.object(q, 'ROOT', self.root), patch.object(q, 'refresh', return_value=[]), \
             patch.object(q, 'load_records', return_value=[record]), \
             patch.object(q, 'load_pr_state', return_value={key: pr}):
            q.main(['pr-action', key, 'done', '--source', 'https://example.com/review', '--note', 'Reviewed'])
        state = q.load_queue(self.root / 'work_queue.json')
        record['feedback']['checked_at'] = (self.now + timedelta(minutes=1)).isoformat()
        record['feedback']['items'].reverse()
        for item in record['feedback']['items']:
            item['sources'].reverse()
        self.assertEqual(q.pr_tasks({key: pr}, state, [record], self.now), [])

    def test_old_ack_without_feedback_binding_requires_reconfirmation(self):
        key, pr = 'a/b#1', self.pr()
        old_ack = {'version': 2, **{name: pr.get(name) for name in
                   ('updatedAt', 'reviewDecision', 'headRefOid', 'ci', 'ci_head_oid', 'ci_fingerprint')}}
        self.state['prs'][key] = {'action': 'done', 'ack': old_ack}
        rows = q.pr_tasks({key: pr}, self.state, [], self.now)
        self.assertEqual([(row['key'], row['score']) for row in rows], [(key, 15)])

    def test_unsafe_evidence_is_rejected_before_queue_write(self):
        for source in ('https://:DEMO_PASSWORD@example.com/proof',
                       'https://user:DEMO_PASSWORD@example.com/proof', 'https://@example.com/proof',
                       'https:///missing-host', 'https://example.com:DEMO_PASSWORD/proof',
                       'https://[broken/proof'):
            for command in (['pr-action', 'a/b#1', 'done'], ['assess', 'a/b#1', 'policy', 'yes']):
                with self.subTest(source=source, command=command), \
                     patch.object(q, 'ROOT', self.root), patch.object(q, 'refresh', return_value=[]) as refresh:
                    with self.assertRaises(ValueError) as error:
                        q.main(command + ['--source', source, '--note', 'Checked'])
                    self.assertNotIn('DEMO_PASSWORD', str(error.exception))
                    self.assertFalse((self.root / 'work_queue.json').exists())
                    self.assertFalse((self.root / 'task_state.json').exists())
                    refresh.assert_not_called()

    def test_green_ci_is_not_current_without_fresh_matching_commit(self):
        for change in ({'headRefOid': 'b' * 40}, {'ci_checked_at': (self.now - timedelta(days=2)).isoformat()},
                       {'ci_fingerprint': None}, {'ci_head_oid': None}):
            with self.subTest(change=change):
                pr = self.pr()
                pr.update(change)
                rows = q.pr_tasks({'a/b#1': pr}, self.state, [], self.now)
                self.assertFalse(rows[0]['ready'])
                self.assertIn('CI', rows[0]['next'])

    def test_missing_ci_is_not_explicit_no_checks(self):
        pr = self.pr()
        self.assertEqual(q.pr_tasks({'a/b#1': pr}, self.state, [], self.now), [])
        del pr['ci']
        self.assertFalse(q.pr_tasks({'a/b#1': pr}, self.state, [], self.now)[0]['ready'])

    def test_ack_does_not_hide_replaced_failure_or_rerun(self):
        key, pr = 'a/b#1', self.pr([self.failure()])
        self.state['prs'][key] = {'action': 'done', 'ack': q.observation_ack(pr, self.now)}
        self.assertEqual(q.pr_tasks({key: pr}, self.state, [], self.now), [])
        for checks in ([self.failure(name='other')], [self.failure(run=2)]):
            with self.subTest(checks=checks):
                current = self.pr(checks)
                self.assertEqual(current['ci'], pr['ci'])
                row = q.pr_tasks({key: current}, self.state, [], self.now)[0]
                self.assertEqual(row['score'], 70)
                self.assertEqual(row['stage'], 'review')

    def test_manual_discussion_expires_for_new_review_failure_and_unknown(self):
        key, pr = 'a/b#1', self.pr()
        self.state['prs'][key] = {'action': 'discussion', 'note': 'Waiting for design feedback',
                                  'ack': q.observation_ack(pr, self.now)}
        self.assertEqual(q.pr_tasks({key: pr}, self.state, [], self.now)[0]['score'], 20)
        for changes, score in (({'reviewDecision': 'CHANGES_REQUESTED'}, 85),
                               ({'ci': ci_summary([self.failure()]),
                                 'ci_fingerprint': ci_fingerprint([self.failure()])}, 70),
                               ({'query_error': 'offline'}, 10)):
            with self.subTest(changes=changes):
                row = q.pr_tasks({key: dict(pr, **changes)}, self.state, [], self.now)[0]
                self.assertEqual(row['score'], score)
                self.assertEqual(row['stage'], 'review')

    def test_changed_activity_reopens_manual_judgement_even_without_failure(self):
        key, pr = 'a/b#1', self.pr()
        for action in ('discussion', 'small_fix', 'wait', 'done'):
            with self.subTest(action=action):
                self.state['prs'][key] = {'action': action, 'ack': q.observation_ack(pr, self.now)}
                current = dict(pr, updatedAt=(self.now + timedelta(seconds=1)).isoformat())
                row = q.pr_tasks({key: current}, self.state, [], self.now)[0]
                self.assertEqual(row['score'], 15)
                self.assertEqual(row['stage'], 'review')

    def test_legacy_and_incomplete_ack_cannot_suppress_failure(self):
        key, pr = 'a/b#1', self.pr([self.failure()])
        legacy = {k: pr.get(k) for k in ('updatedAt', 'reviewDecision', 'ci', 'headRefOid')}
        for ack in (None, legacy, {}, dict(q.observation_ack(pr, self.now), ci_fingerprint=None)):
            with self.subTest(ack=ack):
                self.state['prs'][key] = {'action': 'done', 'ack': ack}
                self.assertEqual(q.pr_tasks({key: pr}, self.state, [], self.now)[0]['score'], 70)

    def test_malformed_review_never_suppresses_work_or_crashes(self):
        pr = self.pr()
        for review in (None, [], {}, 'FUTURE_STATE'):
            with self.subTest(review=review):
                pr['reviewDecision'] = review
                self.assertIsNone(q.observation_ack(pr, self.now))
                self.assertFalse(q.pr_tasks({'a/b#1': pr}, self.state, [], self.now)[0]['ready'])

    def test_cli_binds_manual_action_to_current_checks(self):
        pr = self.pr([self.failure()])
        (self.root / 'pr_state.json').write_text(json.dumps({'a/b#1': pr}), encoding='utf-8')
        with patch.object(q, 'ROOT', self.root), patch.object(q, 'refresh', return_value=[]):
            q.main(['pr-action', 'a/b#1', 'wait', '--source', 'https://example.com/check', '--note', 'Known baseline failure'])
        self.assertEqual(q.load_queue(self.root / 'work_queue.json')['prs']['a/b#1']['ack'],
                         q.observation_ack(pr, self.now))

    def test_corrupt_state_preserves_report(self):
        (self.root / 'work_queue.json').write_text('{"version":99}', encoding='utf-8')
        report = self.root / 'WORK_QUEUE.md'
        report.write_text('keep', encoding='utf-8')
        with self.assertRaises(ValueError):
            q.refresh(self.root)
        self.assertEqual(report.read_text(), 'keep')

    def test_cli_records_effort_and_requires_defer_date(self):
        with patch.object(q, 'ROOT', self.root), patch.object(q, 'refresh', return_value=[]):
            q.main(['stage', 'Example/Repo#1', 'stopped', '--note', '无法复现', '--minutes', '20'])
            state = q.load_queue(self.root / 'work_queue.json')
            self.assertEqual(state['issues']['example/repo#1']['events'][0]['minutes'], 20)
            before = (self.root / 'task_state.json').read_bytes()
            self.assertFalse((self.root / 'work_queue.json').exists())
            with self.assertRaises(ValueError):
                q.main(['stage', 'Example/Repo#1', 'deferred', '--note', 'later'])
            self.assertEqual(before, (self.root / 'task_state.json').read_bytes())

    def test_refresh_offline_and_case_dedup(self):
        (self.root / 'round_candidates.json').write_text(json.dumps([self.c.__dict__, self.c.__dict__]), encoding='utf-8')
        rows = q.refresh(self.root)
        self.assertEqual(len(rows), 1)
        self.assertTrue((self.root / 'WEEKLY_CONTRIBUTIONS.md').exists())
        self.assertFalse((self.root / 'task_state.json').exists())


if __name__ == '__main__':
    unittest.main()
