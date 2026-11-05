"""Failure recovery and interleaved sessions, without touching live ledgers."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import inbox
import pipeline_switch as switch
import session_claims as claims


class StateBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch.object(claims, 'CLAIMS_PATH', self.root / 'claims.json'))
        self.enterContext(patch.object(inbox, 'STATE', self.root / 'handled.json'))
        self.enterContext(patch.object(switch, 'FLAG', self.root / 'enabled'))

    def test_claim_is_exclusive_during_read_modify_write(self):
        entered, release = threading.Event(), threading.Event()
        save = claims._save
        def pause_save(data, path=None):
            if threading.current_thread().name.startswith('claim-worker'):
                entered.set()
                if not release.wait(5):
                    raise RuntimeError('test timed out')
            save(data, path)
        with patch.object(claims, '_save', side_effect=pause_save), ThreadPoolExecutor(1, thread_name_prefix='claim-worker') as pool:
            first = pool.submit(claims.claim, 'owner/repo#1', 'first')
            try:
                self.assertTrue(entered.wait(5))
                with self.assertRaises(RuntimeError):
                    claims.claim('owner/repo#1', 'second')
            finally:
                release.set()
            self.assertTrue(first.result())
        self.assertFalse(claims.claim('Owner/Repo#1', 'second'))
        self.assertEqual(claims.list_claims()['owner/repo#1']['holder'], 'first')

    def test_corrupt_claims_are_not_free_and_aliases_are_normalized(self):
        claims.CLAIMS_PATH.write_text('{broken', encoding='utf-8')
        with self.assertRaises(ValueError):
            claims.check('o/r#1')
        claims.CLAIMS_PATH.write_text(json.dumps({'O/R#1': {'holder': 'old', 'claimed_at': 100}}))
        self.assertFalse(claims.check('o/r#1', now=101))
        self.assertFalse(claims.release('o/r#1', 'unowned'))
        token = claims.claim('o/r#1', now=100 + 49 * 3600)
        self.assertTrue(claims.release('o/r#1', token))

    def test_inbox_save_failure_preserves_old_file(self):
        inbox.STATE.write_text('{"o/r#1":{"at":"2026-11-01T00:00:00Z","note":"old"}}')
        before = inbox.STATE.read_bytes()
        with patch('pipeline_state.os.replace', side_effect=PermissionError('busy')):
            with self.assertRaises(PermissionError):
                inbox.save_state({'new': {}})
        self.assertEqual(inbox.STATE.read_bytes(), before)
        inbox.STATE.write_text('{broken')
        with self.assertRaises(ValueError):
            inbox.load_state()

    def test_off_alias_and_unknown_remote_never_report_on(self):
        self.assertFalse(switch.is_on('off'))
        switch.FLAG.write_text('off')
        output = io.StringIO()
        with patch.object(switch, 'gh', return_value=(1, '', 'network unavailable')), contextlib.redirect_stdout(output):
            self.assertNotEqual(switch.status(), 0)
        self.assertNotIn('effective          : ON', output.getvalue())
        self.assertIn('UNKNOWN', output.getvalue())

    def test_switch_writes_canonical_boolean(self):
        with patch.object(switch, 'gh', return_value=(0, '', '')), patch.object(switch, 'running_shifts', return_value=[]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(switch.set_switch(False, cancel=False), 0)
        self.assertEqual(switch.FLAG.read_text().strip(), 'false')


if __name__ == '__main__':
    unittest.main()
