import io
import json
from contextlib import redirect_stdout
from functools import partial
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import work_queue as q


class QueueCliRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        refresh = partial(q.refresh, self.root)
        self.enterContext(patch.object(q, 'ROOT', self.root))
        self.enterContext(patch.object(q, 'refresh', refresh))
        self.enterContext(redirect_stdout(io.StringIO()))

    def test_saved_registration_reports_view_failure_and_refresh_preserves_effort(self):
        candidates = self.root / 'round_candidates.json'
        candidates.write_bytes(b'{broken')
        reports = {name: ('previous ' + name).encode() for name in
                   ('WORK_QUEUE.md', 'WEEKLY_CONTRIBUTIONS.md', 'work_queue_view.json')}
        for name, contents in reports.items():
            (self.root / name).write_bytes(contents)

        with self.assertRaisesRegex(RuntimeError, '状态已保存，视图未刷新；用 refresh 重试，勿重复登记'):
            q.main(['stage', 'Example/Repo#1', 'stopped', '--note', 'Cannot reproduce',
                    '--minutes', '20'])

        state_path = self.root / 'task_state.json'
        saved = state_path.read_bytes()
        events = json.loads(saved)['queue']['issues']['example/repo#1']['events']
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['minutes'], 20)
        for name, contents in reports.items():
            self.assertEqual((self.root / name).read_bytes(), contents)

        candidates.write_bytes(b'[]')
        q.main(['refresh'])
        self.assertEqual(state_path.read_bytes(), saved)
        self.assertIn('20 分钟', (self.root / 'WEEKLY_CONTRIBUTIONS.md').read_text(encoding='utf-8'))

    def test_plain_refresh_failure_does_not_claim_registration_was_saved(self):
        (self.root / 'round_candidates.json').write_bytes(b'{broken')
        with self.assertRaises(json.JSONDecodeError) as error:
            q.main(['refresh'])
        self.assertNotIn('状态已保存', str(error.exception))
        self.assertFalse((self.root / 'work_queue.json').exists())
        self.assertFalse((self.root / 'task_state.json').exists())

    def test_assess_stage_and_pr_action_save_and_refresh_normally(self):
        source = 'https://example.com/proof'
        q.main(['assess', 'Example/Repo#1', 'policy', 'yes', '--source', source,
                '--note', 'Read current policy', '--minutes', '5'])
        q.main(['stage', 'Example/Repo#1', 'probe', '--note', 'Start reproduction',
                '--minutes', '10'])
        q.main(['pr-action', 'Example/Repo#2', 'wait', '--source', source,
                '--note', 'Await review', '--minutes', '2'])

        ledger = json.loads((self.root / 'task_state.json').read_text(encoding='utf-8'))
        state = ledger['queue']
        self.assertEqual(q.load_queue(self.root / 'work_queue.json'), state)
        self.assertFalse((self.root / 'work_queue.json').exists())
        issue = state['issues']['example/repo#1']
        self.assertEqual(issue['stage'], 'probe')
        self.assertEqual(issue['signals']['policy']['source'], source)
        self.assertIs(issue['signals']['policy']['value'], True)
        self.assertEqual([event['minutes'] for event in issue['events']], [5, 10])
        pr = state['prs']['example/repo#2']
        self.assertEqual(pr['action'], 'wait')
        self.assertEqual(pr['source'], source)
        self.assertEqual([event['minutes'] for event in pr['events']], [2])
        self.assertIn('17 分钟', (self.root / 'WEEKLY_CONTRIBUTIONS.md').read_text(encoding='utf-8'))

    def test_programming_error_is_not_relabelled_as_view_failure(self):
        (self.root / 'round_candidates.json').write_bytes(b'[{}]')
        with self.assertRaises(TypeError):
            q.main(['stage', 'Example/Repo#1', 'probe', '--note', 'Start reproduction'])


if __name__ == '__main__':
    unittest.main()
