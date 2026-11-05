"""Live repository checks must gate final submission even after cached screening."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from candidate_rules import Candidate
from task_state import TaskStore
import vet


class CapacityVetTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.store = TaskStore(root=self.root)
        self.candidate = Candidate('example/project', 7, 'Bug: crash', '', is_bug=True)
        self.issue = dict(number=7, title='Bug: crash', state='OPEN', labels=[{'name': 'bug'}],
                          assignees=[], body='Crash on empty input')

    def test_live_hold_or_unknown_cannot_be_reported_clean(self):
        for status, expected in [('HOLD', 'WARN'), ('UNKNOWN', 'UNKNOWN'), ('ALLOW', 'CLEAN')]:
            decision = dict(allowed=status == 'ALLOW', status=status, reason='capacity evidence')
            with self.subTest(status=status), \
                 patch.object(vet, 'gh', side_effect=[json.dumps(self.issue), '[[]]', '[[]]']), \
                 patch.object(vet, 'live_capacity', return_value=decision) as check:
                self.assertEqual(vet.vet(self.candidate, self.store)[0], expected)
                check.assert_called_once_with('example/project', self.store, query=vet.gh)

    def test_cached_capacity_hold_reaches_live_recheck_but_policy_hold_does_not(self):
        for gate in ('capacity', 'policy'):
            with self.subTest(gate=gate), \
                 patch.object(vet, 'DispatchedStore', return_value=self.store), \
                 patch.object(vet, 'load_candidates', return_value=[self.candidate]), \
                 patch.object(vet, 'clean_decision', return_value={
                     'eligible': False, 'gate': gate, 'reason': 'cached hold'}), \
                 patch.object(vet, 'vet', return_value=('CLEAN', '')) as live, \
                 redirect_stdout(io.StringIO()) as output:
                self.assertEqual(vet.main([]), 0)
                self.assertEqual(live.call_count, int(gate == 'capacity'))
                self.assertEqual('CLEAN_CAND|' in output.getvalue(), gate == 'capacity')

    def test_live_gate_uses_all_open_prs_even_when_tracking_cache_is_empty(self):
        (self.root / 'pr_state.json').write_text('{}', encoding='utf-8')
        from repository_policy import ACCOUNT
        prs = [dict(number=n, state='open', user={'login': ACCOUNT, 'type': 'User'},
                    html_url=f'https://github.com/example/project/pull/{n}',
                    head={'sha': str(n) * 40}, draft=False,
                    created_at='2026-10-01T00:00:00Z', updated_at='2026-11-01T00:00:00Z')
               for n in (1, 2, 3)]
        def query(args):
            if args[0] == 'issue':
                return json.dumps(self.issue)
            path = args[1]
            if path.startswith('repos/example/project/pulls?'):
                self.assertIn('--paginate', args)
                self.assertIn('--slurp', args)
                return json.dumps([prs])
            if '/issues/7/' in path:
                return '[[]]'
            self.fail('Unexpected network read: ' + repr(args))
        with patch.object(vet, 'gh', side_effect=query):
            self.assertEqual(vet.vet(self.candidate, self.store)[0], 'WARN')


if __name__ == '__main__':
    unittest.main()
