"""Multiple discovery sources share decisions, kinds and the rendered queue."""
import contextlib
from dataclasses import asdict
from datetime import datetime, timezone
from functools import partial
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import candidate_rules as rules
from auto_run import DispatchedStore
import inbox
import monitor_round
import scan_docs
import task_state
import vet
import work_queue as queue


class TaskFlowTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.handled = self.root / 'tools/inbox_handled.json'
        self.enterContext(patch.object(inbox, 'ROOT', self.root))
        self.enterContext(patch.object(inbox, 'STATE', self.handled))
        self.enterContext(patch.object(queue, 'ROOT', self.root))
        self.enterContext(patch.object(queue, 'refresh', partial(queue.refresh, self.root)))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.candidate = rules.Candidate('owner/repo', 1, 'Bug: wrong parser output', '',
                                         is_bug=True, checked_at=datetime.now(timezone.utc).isoformat())
        rules.enqueue_candidates([self.candidate], self.root)
        self.comments = [{'created_at': '2026-11-01T00:00:00Z',
                          'body': '- `owner/repo#1` 1m [`bug`] `Wrong parser output`'}]

    def test_inbox_done_hides_queue_and_queue_reopen_is_shared(self):
        task_state.record_handled(self.handled, ['Owner/Repo#1'], 'Already fixed')
        self.assertTrue(queue.refresh()[0]['hidden'])
        self.assertEqual(inbox.pending(self.comments, None), [])
        queue.main(['stage', 'owner/repo#1', 'probe', '--note', 'New evidence'])
        self.assertFalse(queue.refresh()[0]['hidden'])
        self.assertEqual(len(inbox.pending(self.comments, None)), 1)
        self.assertIn('owner/repo#1', task_state.load_handled(self.handled))

    def test_queue_stop_is_seen_by_inbox_and_inbox_reopen_is_shared(self):
        queue.main(['stage', 'owner/repo#1', 'stopped', '--note', 'Cannot reproduce'])
        self.assertEqual(inbox.pending(self.comments, None), [])
        task_state.record_handled(self.handled, ['owner/repo#1'], 'Environment repaired', 'open')
        self.assertEqual(len(inbox.pending(self.comments, None)), 1)
        self.assertFalse(queue.refresh()[0]['hidden'])

    def test_inbox_and_queue_commands_share_ledger_without_rewriting_legacy(self):
        legacy = {
            self.handled: {'other/repo#9': {'at': '2026-11-01T00:00:00Z', 'note': 'Already checked'}},
            self.root / 'work_queue.json': {'version': 1, 'issues': {}, 'prs': {}},
            self.root / 'dispatched.json': {'other/repo#8': {'status': 'needs_repro', 'ts': 1}},
        }
        for path, value in legacy.items():
            path.write_text(json.dumps(value), encoding='utf-8')
        before = {path: path.read_bytes() for path in legacy}
        with patch.object(sys, 'argv', ['inbox.py', 'done', 'Owner/Repo#1', '--note', 'Already resolved']):
            self.assertEqual(inbox.main(), 0)
        path = self.root / 'task_state.json'
        self.assertTrue(path.is_file(), 'inbox done must commit the unified ledger')
        self.assertEqual(inbox.pending(self.comments, None), [])
        queue.main(['stage', 'owner/repo#1', 'probe', '--note', 'New evidence', '--minutes', '5'])
        ledger = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(ledger['handled']['owner/repo#1']['status'], 'done')
        self.assertEqual(ledger['queue']['issues']['owner/repo#1']['stage'], 'probe')
        self.assertEqual(ledger['queue']['issues']['owner/repo#1']['events'][0]['minutes'], 5)
        self.assertEqual(ledger['dispatched']['other/repo#8']['status'], 'needs_repro')
        self.assertEqual(len(inbox.pending(self.comments, None)), 1)
        with patch.object(sys, 'argv', ['inbox.py', 'reopen', 'Owner/Repo#1', '--note', 'Recheck']):
            self.assertEqual(inbox.main(), 0)
        self.assertEqual(inbox.load_state()['owner/repo#1']['status'], 'open')
        self.assertEqual({old: old.read_bytes() for old in legacy}, before)

    def test_summary_limit_preserves_complete_json(self):
        candidates = [rules.Candidate('owner/repo', n, 'Bug: failure', '', is_bug=True) for n in range(2, 82)]
        rules.enqueue_candidates(candidates, self.root)
        rows = queue.refresh(limit=10)
        report = (self.root / 'WORK_QUEUE.md').read_text(encoding='utf-8')
        self.assertEqual(report.count('| issue |'), 10)
        self.assertIn('10/81', report)
        self.assertEqual(len(rows), 81)
        self.assertEqual(len(json.loads((self.root / 'work_queue_view.json').read_text(encoding='utf-8'))['tasks']), 81)

    def test_docs_discovery_precise_scan_queue_and_final_vet(self):
        record = dict(repo='other/repo', number=2, title='Correct parameter documentation',
                      labels=['documentation'], kind='docs', url='https://github.com/other/repo/issues/2')
        with patch.multiple(scan_docs, ROOT=self.root, OUT=self.root / 'docs.json'):
            scan_docs.dump([record], [], ['other/repo'])
        raw = json.loads((self.root / 'tools/fresh_candidates.json').read_text(encoding='utf-8'))['other/repo#2']
        self.assertEqual(raw['kind'], 'docs')
        self.assertTrue(raw['issue_unknown'])
        live = dict(number=2, title=record['title'], state='OPEN', body='The parameter name is inaccurate.',
                    labels=[{'name': 'documentation'}], assignees=[], _kind=raw['kind'])
        out = self.root / 'round_candidates.json'
        with patch.object(monitor_round, 'has_linked_pr', return_value=False), patch.object(monitor_round, 'get_comments', return_value=[]), patch.object(monitor_round.time, 'sleep'):
            self.assertEqual(monitor_round.scan(['other/repo'], out, {'other/repo': [live]}), 0)
        candidate = rules.load_candidates(out)[0]
        self.assertEqual(candidate.kind, 'docs')
        self.assertTrue(rules.is_clean(candidate, DispatchedStore(str(self.root / 'dispatched.json')))[0])
        with patch.object(vet, 'gh', side_effect=[json.dumps(live), '[[]]', '[[]]']) as api, \
             patch.object(vet, 'live_capacity', return_value={'allowed': True}), \
             patch.object(vet, 'DispatchedStore', return_value=task_state.TaskStore(root=self.root)):
            self.assertEqual(vet.vet(candidate)[0], 'CLEAN')
            self.assertEqual(api.call_count, 3)
        row = next(row for row in queue.refresh() if row['key'] == 'other/repo#2')
        self.assertFalse(row['hidden'])
        self.assertFalse(row['ready'])  # Classification never supplies policy/intent evidence.

    def test_new_kinds_keep_policy_and_design_gates(self):
        for kind in ('docs', 'small_fix', 'tooling'):
            candidate = rules.Candidate('pallets/flask', 1, 'Small change', '', kind=kind)
            self.assertFalse(rules.is_clean(candidate, DispatchedStore(str(self.root / 'empty.json')))[0])
            candidate.repo = 'owner/repo'
            candidate.labels = ['enhancement']
            self.assertFalse(rules.is_clean(candidate, DispatchedStore(str(self.root / 'empty.json')))[0])

    def test_cloud_import_preserves_decisions_and_requires_precise_vetting(self):
        task_state.record_handled(self.handled, ['owner/repo#1'], 'Already handled')
        comments = self.comments + [{
            'created_at': '2026-11-04T00:00:00Z',
            'body': '- `Other/Repo#2` 3m [`documentation, help wanted`] `Fix example`',
        }]
        with patch.object(inbox, 'comments', return_value=comments), patch.object(sys, 'argv', ['inbox.py', 'import']):
            self.assertEqual(inbox.main(), 0)
            path = self.root / 'tools/fresh_candidates.json'
            first = path.read_bytes()
            self.assertEqual(inbox.main(), 0)
            self.assertEqual(path.read_bytes(), first)
        rows = json.loads(first)
        self.assertEqual(len(rows), 2)  # One existing local issue plus one imported issue.
        candidate = rules.Candidate(**rows['other/repo#2'])
        self.assertEqual(candidate.kind, 'docs')
        self.assertEqual(candidate.labels, ['documentation', 'help wanted'])
        self.assertEqual(candidate.createdAt, '')  # Comment time is not issue creation time.
        self.assertTrue(candidate.issue_unknown and candidate.pr_unknown and candidate.cmt_unknown)
        self.assertFalse(rules.is_clean(candidate, DispatchedStore(str(self.root / 'empty.json')))[0])
        self.assertTrue(task_state.completion_reason('owner/repo#1', task_state.load_handled(self.handled), {}, datetime.now(timezone.utc)))


if __name__ == '__main__':
    unittest.main()
