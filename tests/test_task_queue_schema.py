"""Every task reader rejects queue data that could hide a blocking decision."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from task_state import TaskStore
import work_queue


class QueueSchemaTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.path = self.root / 'work_queue.json'
        self.key = 'owner/repo#1'
        self.entry = {'stage': 'stopped', 'events': [], 'signals': {}}
        self.state = {'version': 1, 'issues': {self.key: self.entry}, 'prs': {}}

    def save(self, state):
        self.path.write_bytes(json.dumps(state).encode('utf-8'))

    def test_task_and_queue_reject_invalid_decision_schema(self):
        invalid = [dict(self.state, version=2), dict(self.state, prs=[]),
                   dict(self.state, issues={'Owner/Repo#1': self.entry}),
                   dict(self.state, issues={self.key: None})]
        for fields in ({'stage': 'stoppped'}, {'stage': None}, {'events': None},
                       {'events': [None]}, {'events': [{'at': 'not a date', 'minutes': 0}]},
                       {'events': [{'at': '2026-11-01T00:00:00Z', 'minutes': -1}]},
                       {'signals': []}, {'signals': {'unknown': {}}}):
            state = deepcopy(self.state)
            state['issues'][self.key].update(fields)
            invalid.append(state)
        for state in invalid:
            with self.subTest(state=state):
                self.save(state)
                with self.assertRaises(ValueError):
                    work_queue.load_queue(self.path)
                with self.assertRaises(ValueError):
                    TaskStore(self.root / 'dispatched.json')

    def test_unknown_stage_event_cannot_reopen_stopped_task(self):
        self.entry['events'] = [{'at': '2026-11-01T00:00:00Z', 'minutes': 0,
                                'command': 'stage', 'stage': 'stoppped'}]
        self.save(self.state)
        for read in (lambda: work_queue.load_queue(self.path),
                     lambda: TaskStore(self.root / 'dispatched.json')):
            with self.assertRaises(ValueError):
                read()

    def test_missing_and_legacy_optional_fields_keep_working(self):
        self.assertFalse(TaskStore(self.root / 'dispatched.json').is_active(self.key))
        self.save(self.state)
        original = self.path.read_bytes()
        self.assertTrue(TaskStore(self.root / 'dispatched.json').is_active(self.key))
        self.assertEqual(work_queue.load_queue(self.path), self.state)
        self.assertEqual(self.path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
