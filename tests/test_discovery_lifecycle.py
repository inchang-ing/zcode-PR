"""A checked discovery is consumed once, including drops and explicit retries."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import inbox
import monitor_round as scan
import work_queue
from task_state import record_handled
from notification_contract import encode_events


class DiscoveryLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch.object(inbox, 'ROOT', self.root))
        self.enterContext(patch.object(inbox, 'STATE', self.root / 'tools/inbox_handled.json'))
        self.enterContext(patch.object(scan, '__file__', str(self.root / 'tools/monitor_round.py')))
        self.enterContext(patch.object(scan.time, 'sleep'))
        self.enterContext(patch.object(work_queue, 'refresh'))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.enterContext(contextlib.redirect_stderr(io.StringIO()))
        self.rows = [{'id': 10, 'created_at': '2026-11-01T00:00:00Z',
                      'updated_at': '2026-11-01T00:00:00Z',
                      'body': '- `a/b#1` 1m [`bug`] `Bug: parser crash`'}]
        self.enterContext(patch.object(inbox, 'comments', side_effect=lambda: self.rows))
        self.lookup = self.enterContext(patch.object(scan, 'get_issue', return_value={
            'number': 1, 'title': 'Bug: parser crash', 'state': 'CLOSED',
            'body': '', 'labels': [], 'assignees': []}))

    def import_and_check(self):
        with patch.object(sys, 'argv', ['inbox.py', 'import']):
            self.assertEqual(inbox.main(), 0)
        self.assertEqual(scan.main(['--pending']), 0)

    def test_closed_discovery_is_not_imported_again(self):
        self.import_and_check()
        self.import_and_check()
        self.lookup.assert_called_once_with('a/b', 1)
        self.assertEqual(json.loads((self.root / 'tools/fresh_candidates.json').read_text()), {})

    def test_new_source_version_and_explicit_reopen_are_checked_again(self):
        self.import_and_check()
        self.rows[0]['updated_at'] = '2026-11-02T00:00:00Z'
        self.rows[0]['body'] += ' changed'
        self.import_and_check()
        self.assertEqual(self.lookup.call_count, 2)
        record_handled(inbox.STATE, ['a/b#1'], 'New evidence', 'open')
        self.import_and_check()
        self.import_and_check()
        self.assertEqual(self.lookup.call_count, 3)

    def test_structured_event_ignores_presentation_and_rejects_broken_payload(self):
        event = dict(repo='A/B', number=7, title='A [title] with `formatting`',
                     labels=['documentation'], url='https://github.com/A/B/issues/7',
                     created_at='2026-11-01T00:00:00Z')
        self.rows[0]['body'] = 'Any presentation\n' + encode_events([event])
        parsed = inbox.parse(self.rows)['a/b#7']
        self.assertEqual(parsed['title'], event['title'])
        self.assertEqual(parsed['labels'], 'documentation')
        self.rows[0]['body'] = '<!-- zcode-events-v1\nbroken!\n-->'
        with self.assertRaises(ValueError):
            inbox.parse(self.rows)

    def test_receipt_survives_failed_inbox_deletion_without_requery(self):
        import discovery_state
        from pipeline_state import atomic_write_json
        with patch.object(sys, 'argv', ['inbox.py', 'import']):
            inbox.main()
        def save(path, value):
            if Path(path).name == 'fresh_candidates.json':
                raise OSError('inbox is temporarily locked')
            atomic_write_json(path, value)
        with patch.object(scan, 'atomic_write_json', side_effect=save), self.assertRaises(OSError):
            scan.main(['--pending'])
        self.assertTrue(discovery_state.load_consumed(self.root))
        self.assertEqual(scan.main(['--pending']), 0)
        self.lookup.assert_called_once_with('a/b', 1)


class CommentCacheTests(unittest.TestCase):
    def test_incremental_fetch_keeps_older_entries_and_retries_failed_read(self):
        from urllib.parse import parse_qs, urlsplit
        with tempfile.TemporaryDirectory() as tmp, patch.object(inbox, 'ROOT', Path(tmp)), \
                patch.object(inbox, 'inbox_number', return_value=9):
            row = dict(id=1, body='legacy', created_at='2026-11-01T00:00:00Z',
                       updated_at='2026-11-01T00:00:00Z')
            # Use the real cache function even if another test mocks comments.
            with patch.object(inbox, 'gh', return_value=json.dumps(row)) as api:
                self.assertEqual(inbox.comments(), [row])
                self.assertNotIn('since', parse_qs(urlsplit(api.call_args.args[2]).query))
            path = Path(tmp) / 'tools/inbox_comments.json'
            before = path.read_bytes()
            with patch.object(inbox, 'gh', side_effect=RuntimeError('offline')):
                with self.assertRaises(RuntimeError):
                    inbox.comments()
            self.assertEqual(path.read_bytes(), before)
            with patch.object(inbox, 'gh', return_value='') as api:
                self.assertEqual(inbox.comments(), [row])
                self.assertIn('since', parse_qs(urlsplit(api.call_args.args[2]).query))


if __name__ == '__main__':
    unittest.main()
