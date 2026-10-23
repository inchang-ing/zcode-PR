import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import monitor_round as scan
import monitor_fresh as fresh
import work_queue as queue
from monitor_oss import ci_fingerprint, ci_summary
from repository_policy import policy_reason


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(redirect_stdout(io.StringIO()))
        self.enterContext(patch.object(scan.time, 'sleep'))

    def pending_inbox(self, *numbers):
        folder = self.root / 'tools'
        folder.mkdir()
        inbox = folder / 'fresh_candidates.json'
        inbox.write_text(json.dumps({f'a/b#{n}': dict(repo='a/b', number=n, title='bug')
                                     for n in numbers}), encoding='utf-8')
        self.enterContext(patch.object(scan, '__file__', str(folder / 'monitor_round.py')))
        self.enterContext(patch.object(queue, 'refresh'))
        return inbox, self.root / 'round_candidates.json'

    def pr_observation(self, now, **overrides):
        return dict(dict(state='OPEN', checked_at=now.isoformat(), updatedAt=now.isoformat(),
                         headRefOid='a' * 40, reviewDecision='-', ci='no-checks',
                         ci_checked_at=now.isoformat(), ci_head_oid='a' * 40,
                         ci_fingerprint=ci_fingerprint([])), **overrides)

    def test_discovery_is_durable_deduplicated_and_visible_but_not_ready(self):
        (self.root / 'tools').mkdir()
        item = dict(repo='outside/pool', num=42, title='bug: crash', labels='bug')
        with patch.object(fresh, 'STATE_PATH', str(self.root / 'tools/monitor_state.json')):
            fresh.persist_discoveries([item, item])
        rows = queue.refresh(self.root)
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]['ready'])
        self.assertFalse(rows[0]['hidden'])

    def test_partial_and_total_failure_preserve_candidates_as_unknown(self):
        path = self.root / 'c.json'
        old = dict(repo='bad/repo', number=1, title='bug', checked_at='2026-10-21T00:00:00Z')
        for responses in ([[], None], [None, None]):
            path.write_text(json.dumps([old]), encoding='utf-8')
            with patch.object(scan, 'get_issues', side_effect=responses):
                self.assertEqual(scan.scan(['ok/repo', 'bad/repo'], path), 1)
            saved = json.loads(path.read_text())
            self.assertEqual(saved[0]['number'], 1)
            self.assertTrue(saved[0]['issue_unknown'])
            self.assertEqual(saved[0]['checked_at'], '')

    def test_targeted_scan_does_not_remove_sibling_candidate(self):
        path = self.root / 'c.json'
        path.write_text(json.dumps([dict(repo='a/b', number=2, title='bug')]))
        issue = dict(number=1, title='bug', state='CLOSED', body='', labels=[], assignees=[])
        scan.scan(['a/b'], path, {'a/b': [issue]})
        self.assertEqual(json.loads(path.read_text())[0]['number'], 2)

    def test_full_scan_rechecks_old_candidate_outside_latest_page(self):
        path = self.root / 'c.json'
        path.write_text(json.dumps([dict(repo='A/B', number=1, title='bug: old',
                                        checked_at='2026-10-21T00:00:00Z')]))
        issue = dict(number=1, title='bug: still open', state='OPEN', body='',
                     labels=[], assignees=[])
        latest = [dict(issue, number=n) for n in range(2, scan.LIMIT + 2)]
        with patch.object(scan, 'get_issues', return_value=latest), \
             patch.object(scan, 'gh', return_value=json.dumps(issue)) as gh, \
             patch.object(scan, 'has_linked_pr', return_value=False), \
             patch.object(scan, 'get_comments', return_value=[]):
            self.assertEqual(scan.scan(['a/b'], path), 0)
        saved = {item['number']: item for item in json.loads(path.read_text())}
        self.assertEqual(set(saved), set(range(1, scan.LIMIT + 2)))
        self.assertFalse(saved[1]['issue_unknown'])
        self.assertEqual(saved[1]['title'], 'bug: still open')
        self.assertIn('1', gh.call_args.args[0])
        self.assertIn('view', gh.call_args.args[0])

    def test_empty_list_rechecks_old_candidate_before_removal(self):
        path = self.root / 'c.json'
        old = dict(repo='a/b', number=1, title='bug: old')
        for state, body in (('OPEN', ''), ('CLOSED', ''), ('OPEN', 'I have a patch')):
            path.write_text(json.dumps([old]))
            issue = dict(number=1, title='bug: old', state=state, body=body,
                         labels=[], assignees=[])
            with self.subTest(state=state, body=body), \
                 patch.object(scan, 'get_issues', return_value=[]), \
                 patch.object(scan, 'gh', return_value=json.dumps(issue)) as gh, \
                 patch.object(scan, 'has_linked_pr', return_value=False), \
                 patch.object(scan, 'get_comments', return_value=[]):
                self.assertEqual(scan.scan(['a/b'], path), 0)
                saved = json.loads(path.read_text())
                self.assertEqual([item['number'] for item in saved],
                                 [1] if state == 'OPEN' and not body else [])
                gh.assert_called_once()

    def test_failed_precise_recheck_retains_unknown_candidate_and_can_retry(self):
        path = self.root / 'c.json'
        old = dict(repo='a/b', number=1, title='bug: old',
                   checked_at='2026-10-21T00:00:00Z')
        untouched = dict(repo='other/repo', number=2, title='bug: unscanned')
        issue = dict(number=1, title='bug: old', state='OPEN', body='', labels=[], assignees=[])
        for raw in (None, json.dumps(dict(issue, number=2)), json.dumps(dict(issue, body=None))):
            path.write_text(json.dumps([old, untouched]))
            with self.subTest(raw=raw), \
                 patch.object(scan, 'get_issues', return_value=[]), \
                 patch.object(scan, 'gh', side_effect=[raw, json.dumps(issue)]), \
                 patch.object(scan, 'has_linked_pr', return_value=False), \
                 patch.object(scan, 'get_comments', return_value=[]):
                self.assertEqual(scan.scan(['a/b'], path), 1)
                saved = {item['repo']: item for item in json.loads(path.read_text())}
                self.assertTrue(saved['a/b']['issue_unknown'])
                self.assertEqual(saved['a/b']['checked_at'], '')
                self.assertTrue(saved['a/b']['check_errors'])
                self.assertEqual(saved['other/repo'], untouched)
                self.assertEqual(scan.scan(['a/b'], path), 0)
                saved = {item['repo']: item for item in json.loads(path.read_text())}
                self.assertFalse(saved['a/b']['issue_unknown'])
                self.assertTrue(saved['a/b']['checked_at'])
                self.assertEqual(saved['other/repo'], untouched)

    def test_acknowledged_pr_still_reports_failure_and_query_error(self):
        now = datetime.now(timezone.utc)
        pr = self.pr_observation(now)
        ack = queue.observation_ack(pr)
        state = {'prs': {'a/b#1': {'action': 'done', 'ack': ack}}}
        pr['query_error'] = 'offline'
        self.assertFalse(queue.pr_tasks({'a/b#1': pr}, state, [], now)[0]['ready'])
        del pr['query_error']
        checks = [dict(name='test', status='COMPLETED', conclusion='FAILURE',
                       detailsUrl='https://example.com/runs/1')]
        pr.update(ci=ci_summary(checks), ci_fingerprint=ci_fingerprint(checks))
        self.assertEqual(queue.pr_tasks({'a/b#1': pr}, state, [], now)[0]['score'], 70)

    def test_local_operational_gates(self):
        for repo in ('PyCQA/bandit', 'sqlalchemy/alembic', 'frappe/frappe',
                     'geopandas/geopandas', 'modelcontextprotocol/python-sdk'):
            self.assertTrue(policy_reason(repo))
        self.assertEqual(policy_reason('modelcontextprotocol/python-sdk', [], ['inchang-ing']), '')

    def test_autonomous_contribution_restrictions_block_new_and_existing_work(self):
        now = datetime.now(timezone.utc)
        for repo in ('ansible/ansible', 'python-markdown/markdown'):
            self.assertTrue(policy_reason(repo))
            key = repo + '#1'
            cache = {key: self.pr_observation(now, reviewDecision='CHANGES_REQUESTED')}
            rows = queue.pr_tasks(cache, {'prs': {}}, [], now)
            self.assertFalse(rows[0]['ready'])
            self.assertEqual(rows[0]['stage'], 'policy_hold')
        rows = queue.pr_tasks({'a/b#1': self.pr_observation(now, reviewDecision='CHANGES_REQUESTED')},
                              {'prs': {}}, [], now)
        self.assertTrue(rows[0]['ready'])
        self.assertNotIn('人工评审', rows[0]['next'])

    def test_recorded_submission_bans_keep_existing_prs_visible_but_pause_writes(self):
        now = datetime.now(timezone.utc)
        for repo in ('pypa/packaging', 'google/jax', 'jax-ml/jax'):
            key = repo + '#1'
            with self.subTest(repo=repo):
                rows = queue.pr_tasks({key: self.pr_observation(now, reviewDecision='CHANGES_REQUESTED')},
                                      {'prs': {}}, [], now)
                self.assertEqual(len(rows), 1)
                self.assertFalse(rows[0]['hidden'])
                self.assertFalse(rows[0]['ready'])
                self.assertEqual(rows[0]['stage'], 'policy_hold')
                self.assertIn('只读', rows[0]['next'])

    def test_cheap_gates_skip_timeline_and_comments(self):
        base = dict(number=1, title='bug: crash', state='OPEN', body='', labels=[], assignees=[])
        cases = [('stanfordnlp/dspy', base), ('mem0ai/mem0', base),
                 ('langchain-ai/langchain', base),
                 ('a/b', dict(base, assignees=[{'login': 'someone'}]))]
        for index, (repo, issue) in enumerate(cases):
            with self.subTest(repo=repo), \
                 patch.object(scan, 'get_issues', return_value=[issue]), \
                 patch.object(scan, 'has_linked_pr') as timeline, \
                 patch.object(scan, 'get_comments') as comments:
                scan.scan([repo], self.root / f'{index}.json')
                timeline.assert_not_called()
                comments.assert_not_called()

    def test_eligible_candidate_still_gets_both_network_checks(self):
        issue = dict(number=1, title='bug: crash', state='OPEN', body='',
                     labels=[{'name': 'accepted'}], assignees=[])
        with patch.object(scan, 'get_issues', return_value=[issue]), \
             patch.object(scan, 'has_linked_pr', return_value=False) as timeline, \
             patch.object(scan, 'get_comments', return_value=[]) as comments:
            scan.scan(['mem0ai/mem0'], self.root / 'eligible.json')
        timeline.assert_called_once_with('mem0ai/mem0', 1)
        comments.assert_called_once_with('mem0ai/mem0', 1)

    def test_pending_promotes_exact_issue_and_drains_inbox(self):
        inbox, output = self.pending_inbox(123)
        issue = dict(number=123, title='bug: crash', state='OPEN', body='', labels=[], assignees=[])
        with patch.object(scan, 'gh', return_value=json.dumps(issue)) as gh, \
             patch.object(scan, 'has_linked_pr', return_value=False), \
             patch.object(scan, 'get_comments', return_value=[]):
            self.assertEqual(scan.main(['--pending']), 0)
        self.assertIn('123', gh.call_args.args[0])
        self.assertEqual(json.loads(output.read_text())[0]['number'], 123)
        self.assertEqual(json.loads(inbox.read_text()), {})

    def test_pending_retries_unknown_checks_until_success(self):
        inbox, output = self.pending_inbox(1)
        issue = dict(number=1, title='bug', state='OPEN', body='', labels=[], assignees=[])
        original = inbox.read_text()
        for timeline, comments, unknown_flag in ((None, [], 'pr_unknown'),
                                                  (False, None, 'cmt_unknown')):
            with self.subTest(unknown_flag=unknown_flag):
                inbox.write_text(original, encoding='utf-8')
                with patch.object(scan, 'gh', return_value=json.dumps(issue)), \
                     patch.object(scan, 'has_linked_pr', side_effect=[timeline, False]), \
                     patch.object(scan, 'get_comments', side_effect=[comments, []]):
                    self.assertEqual(scan.main(['--pending']), 1)
                    self.assertIn('a/b#1', json.loads(inbox.read_text()))
                    self.assertTrue(json.loads(output.read_text())[0][unknown_flag])
                    self.assertEqual(scan.main(['--pending']), 0)
                    self.assertEqual(json.loads(inbox.read_text()), {})
                    self.assertFalse(json.loads(output.read_text())[0][unknown_flag])

    def test_pending_issue_read_failure_does_not_block_sibling(self):
        inbox, output = self.pending_inbox(1, 2)
        old = [dict(repo='a/b', number=n, title='bug', issue_unknown=False,
                    checked_at='2026-10-23T00:00:00Z') for n in (1, 2)]
        output.write_text(json.dumps(old), encoding='utf-8')
        issue = dict(number=2, title='bug', state='OPEN', body='', labels=[], assignees=[])
        with patch.object(scan, 'gh', side_effect=[None, json.dumps(issue)]), \
             patch.object(scan, 'has_linked_pr', return_value=False) as timeline, \
             patch.object(scan, 'get_comments', return_value=[]):
            self.assertEqual(scan.main(['--pending']), 1)
        timeline.assert_called_once_with('a/b', 2)
        self.assertEqual(set(json.loads(inbox.read_text())), {'a/b#1'})
        saved = {item['number']: item for item in json.loads(output.read_text())}
        self.assertTrue(saved[1]['issue_unknown'])
        self.assertEqual(saved[1]['checked_at'], '')
        self.assertFalse(saved[2]['issue_unknown'])
        with patch.object(scan, 'gh', return_value=json.dumps(dict(issue, number=1))), \
             patch.object(scan, 'has_linked_pr', return_value=False), \
             patch.object(scan, 'get_comments', return_value=[]):
            self.assertEqual(scan.main(['--pending']), 0)
        self.assertEqual(json.loads(inbox.read_text()), {})
        self.assertEqual({item['number'] for item in json.loads(output.read_text())}, {1, 2})

    def test_pending_definite_drop_drains_inbox(self):
        inbox, output = self.pending_inbox(1)
        issue = dict(number=1, title='bug', state='OPEN', body='', labels=[], assignees=[])
        original = inbox.read_text()
        for fields, timeline, comments in (({'state': 'CLOSED'}, False, []),
                                           ({'body': 'I can open a PR'}, False, []),
                                           ({'assignees': [{'login': 'someone'}]}, False, []),
                                           ({}, True, []), ({}, False, ['I have a patch'])):
            with self.subTest(fields=fields, timeline=timeline, comments=comments):
                inbox.write_text(original, encoding='utf-8')
                with patch.object(scan, 'gh', return_value=json.dumps(dict(issue, **fields))), \
                     patch.object(scan, 'has_linked_pr', return_value=timeline), \
                     patch.object(scan, 'get_comments', return_value=comments):
                    self.assertEqual(scan.main(['--pending']), 0)
                self.assertEqual(json.loads(inbox.read_text()), {})
                self.assertEqual(json.loads(output.read_text()), [])

    def test_pending_custom_output_does_not_consume_canonical_inbox(self):
        inbox, canonical = self.pending_inbox(1)
        issue = dict(number=1, title='bug', state='OPEN', body='', labels=[], assignees=[])
        custom = self.root / 'custom.json'
        with patch.object(scan, 'gh', return_value=json.dumps(issue)), \
             patch.object(scan, 'has_linked_pr', return_value=False), \
             patch.object(scan, 'get_comments', return_value=[]):
            self.assertEqual(scan.main(['--pending', '--out', str(custom)]), 0)
        self.assertFalse(canonical.exists())
        self.assertEqual(json.loads(custom.read_text())[0]['number'], 1)
        self.assertEqual(set(json.loads(inbox.read_text())), {'a/b#1'})

    def test_pending_incomplete_or_wrong_issue_response_is_retryable(self):
        inbox, output = self.pending_inbox(1)
        issue = dict(number=1, title='bug', state='OPEN', body='', labels=[], assignees=[])
        for invalid in (dict(issue, number=2), dict(issue, number=True), dict(issue, title=None)):
            with self.subTest(invalid=invalid), \
                 patch.object(scan, 'gh', return_value=json.dumps(invalid)), \
                 patch.object(scan, 'has_linked_pr') as timeline:
                self.assertEqual(scan.main(['--pending']), 1)
                timeline.assert_not_called()
                self.assertEqual(set(json.loads(inbox.read_text())), {'a/b#1'})
                self.assertEqual(json.loads(output.read_text()), [])


if __name__ == '__main__':
    unittest.main()
