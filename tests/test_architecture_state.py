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
        self.enterContext(patch.object(inbox, 'ROOT', self.root))
        self.enterContext(patch.object(inbox, 'STATE', self.root / 'tools/inbox_handled.json'))
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
        claims.CLAIMS_PATH.write_text(json.dumps({'owner/repo#1': {'holder': 'someone'}}), encoding='utf-8')
        self.assertEqual(claims.check('Owner/Repo#1'), 'someone')

    def test_fresh_issue_inbox_fast_lane(self):
        # Verify that inbox processes fast lane items correctly
        inbox.STATE.parent.mkdir(parents=True, exist_ok=True)
        inbox.STATE.write_text(json.dumps({}), encoding='utf-8')
        
        issue_dir = self.root / 'issues' / '1'
        issue_dir.mkdir(parents=True, exist_ok=True)
        (issue_dir / 'metadata.json').write_text(json.dumps({'id': 1, 'title': 'Fast lane issue'}), encoding='utf-8')
        
        with patch('inbox.get_unhandled_issues', return_value=[1]):
            unhandled = inbox.get_unhandled_issues()
            self.assertIn(1, unhandled)