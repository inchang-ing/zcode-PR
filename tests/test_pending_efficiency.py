"""Pending scans avoid completed work without blocking or losing new discoveries."""
import contextlib
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import candidate_rules
import monitor_round as scan
from pipeline_state import atomic_write_json, file_lock
from task_state import record_handled, TaskStore
import work_queue


class PendingEfficiencyTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.inbox = self.root / 'tools/fresh_candidates.json'
        self.output = self.root / 'round_candidates.json'
        self.handled = self.inbox.with_name('inbox_handled.json')
        self.enterContext(patch.object(scan, '__file__', str(self.inbox.with_name('monitor_round.py'))))
        self.enterContext(patch.object(scan.time, 'sleep'))
        self.enterContext(patch.object(work_queue, 'refresh'))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.enterContext(contextlib.redirect_stderr(io.StringIO()))
        self.timeline = self.enterContext(patch.object(scan, 'has_linked_pr', return_value=False))
        self.comments = self.enterContext(patch.object(scan, 'get_comments', return_value=[]))
        self.lookup = self.enterContext(patch.object(scan, 'get_issue', side_effect=self.live_issue))
        self.now = datetime.now(timezone.utc)

    def live_issue(self, repo, number):
        return dict(number=number, title='bug: crash', state='OPEN', body='', labels=[], assignees=[])

    def seed(self, *numbers):
        atomic_write_json(self.inbox, {f'a/b#{n}': dict(repo='a/b', number=n, title='bug: crash') for n in numbers})

    def defer(self, retry_at):
        with TaskStore(root=self.root).transaction() as ledger:
            ledger['queue']['issues']['a/b#2'] = {
                'stage': 'deferred', 'retry_at': retry_at.isoformat(), 'signals': {},
                'events': [{'command': 'stage', 'stage': 'deferred', 'note': 'Wait for evidence',
                            'minutes': 0, 'at': self.now.isoformat()}],
            }

    def test_completed_and_deferred_entries_make_no_api_calls(self):
        self.seed(1, 2, 3)
        record_handled(self.handled, ['a/b#1'], 'Already fixed')
        self.defer(self.now + timedelta(days=1))
        decisions = (self.root / 'task_state.json').read_bytes()
        self.assertEqual(scan.main(['--pending']), 0)
        self.lookup.assert_called_once_with('a/b', 3)
        self.timeline.assert_called_once_with('a/b', 3)
        self.comments.assert_called_once_with('a/b', 3)
        self.assertEqual(set(json.loads(self.inbox.read_text())), {'a/b#1', 'a/b#2'})
        self.assertEqual((self.root / 'task_state.json').read_bytes(), decisions)
        self.assertEqual(json.loads(self.output.read_text())[0]['number'], 3)

    def test_reopened_and_due_entries_resume_checks(self):
        self.seed(1, 2)
        record_handled(self.handled, ['a/b#1'], 'Done')
        record_handled(self.handled, ['a/b#1'], 'New evidence', 'open')
        self.defer(self.now - timedelta(days=1))
        self.assertEqual(scan.main(['--pending']), 0)
        self.assertEqual(self.lookup.call_count, 2)
        self.assertEqual(json.loads(self.inbox.read_text()), {})

    def test_all_completed_does_not_rewrite_snapshots(self):
        self.seed(1)
        record_handled(self.handled, ['a/b#1'], 'Done')
        atomic_write_json(self.output, [{'repo': 'a/b', 'number': 1, 'title': 'bug: crash'}])
        before = (self.inbox.read_bytes(), self.output.read_bytes())
        self.assertEqual(scan.main(['--pending']), 0)
        self.lookup.assert_not_called()
        self.assertEqual((self.inbox.read_bytes(), self.output.read_bytes()), before)

    def test_discovery_can_write_during_network_and_newer_values_survive(self):
        self.seed(1)
        def lookup(repo, number):
            # The scan's output lock still serializes scanners, while discoveries can write.
            with self.assertRaises(RuntimeError), file_lock(self.output):
                pass
            with file_lock(self.inbox):
                current = json.loads(self.inbox.read_text())
                current['a/b#1']['title'] = 'Updated while scanning'
                current['a/b#2'] = dict(repo='a/b', number=2, title='New discovery')
                atomic_write_json(self.inbox, current)
            return self.live_issue(repo, number)
        self.lookup.side_effect = lookup
        self.assertEqual(scan.main(['--pending']), 0)
        current = json.loads(self.inbox.read_text())
        self.assertEqual(set(current), {'a/b#1', 'a/b#2'})
        self.assertEqual(current['a/b#1']['title'], 'Updated while scanning')
        self.assertEqual(json.loads(self.output.read_text())[0]['number'], 1)

    def test_competing_scan_is_rejected_before_network(self):
        self.seed(1)
        with file_lock(self.output), self.assertRaises(RuntimeError):
            scan.main(['--pending'])
        self.lookup.assert_not_called()

    def test_failed_snapshot_write_keeps_pending_for_retry(self):
        self.seed(1)
        before = self.inbox.read_bytes()
        with patch.object(scan, 'atomic_write_json', side_effect=OSError('disk unavailable')):
            with self.assertRaises(OSError):
                scan.main(['--pending'])
        self.assertEqual(self.inbox.read_bytes(), before)
        self.assertEqual(scan.main(['--pending']), 0)
        self.assertEqual(json.loads(self.inbox.read_text()), {})

    def test_repeated_or_empty_import_does_not_write(self):
        candidate = candidate_rules.Candidate('a/b', 1, 'bug: crash', '')
        self.assertEqual(candidate_rules.enqueue_candidates([candidate], self.root), 1)
        with patch.object(candidate_rules, 'atomic_write_json') as write:
            self.assertEqual(candidate_rules.enqueue_candidates([candidate], self.root), 0)
            self.assertEqual(candidate_rules.enqueue_candidates([], self.root), 0)
        write.assert_not_called()


if __name__ == '__main__':
    unittest.main()
