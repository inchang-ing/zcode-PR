"""Task decisions and execution leases share ownership without live state writes."""
import contextlib
from datetime import datetime
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import auto_run as auto
import filter_cands
import session_claims as claims
import task_state
import work_queue as queue


class TaskStoreTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.path = self.root / 'dispatched.json'
        self.handled = self.root / 'tools/inbox_handled.json'
        self.key = 'owner/repo#1'
        self.candidate = auto.Candidate('owner/repo', 1, 'Bug: crash', '', is_bug=True)
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.enterContext(patch.object(queue, 'ROOT', self.root))
        self.enterContext(patch.object(queue, 'refresh', return_value=[]))
        self.enterContext(patch.object(claims, 'CLAIMS_PATH', self.root / 'work/ledger/session_claims.json'))

    def store(self):
        return auto.DispatchedStore(self.path)

    def stage(self, stage):
        queue.main(['stage', self.key, stage, '--note', 'Explicit decision'])

    def test_done_blocks_filter_and_runner_including_stale_store(self):
        stale = self.store()
        task_state.record_handled(self.handled, [self.key], 'Already resolved')
        before = stale.path.read_bytes()
        self.assertEqual(filter_cands.fresh_candidates([self.candidate], self.store()), [])
        auto.run(self.candidate, stale)
        self.assertEqual(stale.path.read_bytes(), before)
        self.assertNotIn(self.key, self.store().data)
        self.assertFalse(self.path.exists())

    def test_reopen_overrides_old_dispatch_but_new_terminal_decision_wins(self):
        self.store().mark(self.key, 'dropped')
        task_state.record_handled(self.handled, [self.key], 'New evidence', 'open')
        self.assertFalse(self.store().is_active(self.key))
        self.assertEqual(filter_cands.fresh_candidates([self.candidate], self.store()), [self.candidate])
        self.store().mark(self.key, 'closed')
        self.assertTrue(self.store().is_active(self.key))

    def test_stage_and_handled_decisions_use_latest_time(self):
        task_state.record_handled(self.handled, [self.key], 'Done')
        self.stage('probe')
        self.assertFalse(self.store().is_active(self.key))
        self.stage('stopped')
        self.assertTrue(self.store().is_active(self.key))
        task_state.record_handled(self.handled, [self.key], 'Resume', 'open')
        self.assertFalse(self.store().is_active(self.key))

    def test_reopen_never_steals_active_preparation(self):
        for status in ('running', 'pr_opened', 'needs_fix', 'needs_verification'):
            with self.subTest(status=status):
                self.store().mark(self.key, status)
                task_state.record_handled(self.handled, [self.key], 'Resume', 'open')
                original = self.store().path.read_bytes()
                store = self.store()
                self.assertTrue(store.is_active(self.key))
                self.assertFalse(store.mark(self.key, 'running', only_if_inactive=True))
                self.assertEqual(self.store().path.read_bytes(), original)

    def test_unified_reads_do_not_rewrite_state(self):
        self.store().mark(self.key, 'dropped')
        task_state.record_handled(self.handled, [self.key], 'Resume', 'open')
        before = {self.store().path: self.store().path.read_bytes()}
        self.store().is_active(self.key)
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_latest_dispatch_pending_reopens_stopped_queue(self):
        self.stage('stopped')
        self.store().mark(self.key, 'pending')
        decision = self.store().decision(self.key)
        self.assertFalse(decision['blocked'])
        self.assertEqual(decision['stage'], 'new')
        self.assertIsNotNone(decision['resume_at'])

    def test_deferred_stage_resume_and_deadline_are_shared(self):
        at = '2026-11-01T00:00:00+00:00'
        retry = '2026-11-02T00:00:00+00:00'
        issue = {'stage': 'deferred', 'retry_at': retry,
                 'events': [{'command': 'stage', 'at': at, 'stage': 'deferred'}]}
        before = self.store().decision(self.key, datetime.fromisoformat(at), issue=issue)
        after = self.store().decision(self.key, datetime.fromisoformat(retry), issue=issue)
        self.assertEqual(before['resume_at'], at)
        self.assertTrue(before['blocked'])
        self.assertFalse(after['blocked'])

    def test_equal_timestamp_preserves_terminal_decision(self):
        at = '2026-11-01T00:00:00+00:00'
        handled = {self.key: {'at': at, 'note': 'Done', 'status': 'done'}}
        issue = {'stage': 'probe', 'events': [{'command': 'stage', 'at': at, 'stage': 'probe'}]}
        decision = self.store().decision(self.key, handled=handled, issue=issue)
        self.assertTrue(decision['blocked'])
        self.assertEqual(decision['reason'], 'Done')

    def test_retry_observation_cannot_reopen_explicit_done(self):
        task_state.record_handled(self.handled, [self.key], 'Already resolved')
        for status in ('needs_repro', 'repro_failed', 'dry_run'):
            with self.subTest(status=status):
                store = self.store()
                store.mark(self.key, status, retry_after='2000-01-01T00:00:00Z')
                self.assertTrue(store.is_active(self.key))


class LeaseTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.path = self.root / 'work/ledger/session_claims.json'
        self.enterContext(patch.object(claims, 'CLAIMS_PATH', self.path))
        self.key = 'owner/repo#1'

    def test_expired_owner_cannot_release_or_renew_successor(self):
        first = claims.claim(self.key, 'first', now=100)
        second = claims.claim(self.key, 'second', now=100 + 49 * 3600)
        self.assertIsInstance(first, str)
        self.assertNotEqual(first, second)
        original = self.path.read_bytes()
        self.assertFalse(claims.release(self.key, first))
        self.assertFalse(claims.renew(self.key, first, now=100 + 49 * 3600))
        self.assertEqual(self.path.read_bytes(), original)
        self.assertTrue(claims.release(self.key, second))

    def test_owner_can_renew_but_expired_token_cannot_revive_lease(self):
        token = claims.claim(self.key, now=100)
        self.assertTrue(claims.renew(self.key, token, now=100 + 47 * 3600))
        self.assertFalse(claims.check(self.key, now=100 + 49 * 3600))
        self.assertFalse(claims.renew(self.key, token, now=100 + 96 * 3600))
        self.assertTrue(claims.check(self.key, now=100 + 96 * 3600))

    def test_cli_rejects_unowned_release_before_mutation(self):
        claims.claim(self.key)
        original = self.path.read_bytes()
        with patch.object(sys, 'argv', ['session_claims.py', '--release', self.key]), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
            claims.main()
        self.assertEqual(result.exception.code, 2)
        self.assertEqual(self.path.read_bytes(), original)

    def test_cli_claim_and_owned_renew_release(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(claims.main(['--claim', self.key, '--holder', 'manual']), 0)
            token = output.getvalue().split('token=')[1].strip()
            self.assertEqual(claims.main(['--release', self.key, '--token', 'wrong']), 1)
            self.assertEqual(claims.main(['--renew', self.key, '--token', token]), 0)
            self.assertEqual(claims.main(['--release', self.key, '--token', token]), 0)

    def test_expired_runner_cannot_finish_or_release_successor(self):
        candidate = auto.Candidate('owner/repo', 1, 'Bug: crash', '', is_bug=True)
        store = auto.DispatchedStore(self.root / 'dispatched.json')
        successor = []

        def clone(repo):
            data = json.loads(self.path.read_text())
            data[self.key]['claimed_at'] -= 49 * 3600
            self.path.write_bytes(json.dumps(data).encode('utf-8'))
            successor.append(claims.claim(self.key, 'successor'))
            return str(self.root)

        with patch.dict(auto.REPROS, {self.key: lambda c, p: True}, clear=True), \
                patch.object(auto, '_clone_via_tarball', side_effect=clone), \
                patch.object(auto, '_reproduce') as reproduce, contextlib.redirect_stdout(io.StringIO()):
            auto.run(candidate, store)
        reproduce.assert_not_called()
        self.assertEqual(store.status_of(self.key), 'running')
        self.assertFalse(claims.check(self.key))
        self.assertTrue(claims.release(self.key, successor[0]))

    def test_auto_run_obeys_manual_claim(self):
        token = claims.claim(self.key, 'manual-session')
        candidate = auto.Candidate('owner/repo', 1, 'Bug: crash', '', is_bug=True)
        store = auto.DispatchedStore(self.root / 'dispatched.json')
        with patch.dict(auto.REPROS, {self.key: lambda c, p: False}, clear=True), \
                patch.object(auto, '_clone_via_tarball') as clone, contextlib.redirect_stdout(io.StringIO()):
            auto.run(candidate, store)
        clone.assert_not_called()
        self.assertFalse((self.root / 'dispatched.json').exists())
        self.assertFalse(store.path.exists())
        self.assertTrue(claims.release(self.key, token))

    def test_auto_run_releases_claim_after_error_and_interrupt(self):
        candidate = auto.Candidate('owner/repo', 1, 'Bug: crash', '', is_bug=True)
        for error in (OSError('offline'), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                store = auto.DispatchedStore(self.root / 'dispatched.json')
                store.mark(self.key, 'pending')
                with patch.dict(auto.REPROS, {self.key: lambda c, p: False}, clear=True), \
                        patch.object(auto, '_clone_via_tarball', side_effect=error), \
                        contextlib.redirect_stdout(io.StringIO()):
                    if isinstance(error, KeyboardInterrupt):
                        with self.assertRaises(KeyboardInterrupt):
                            auto.run(candidate, store)
                    else:
                        auto.run(candidate, store)
                self.assertTrue(claims.check(self.key))
                self.assertEqual(store.status_of(self.key), 'repro_failed')


if __name__ == '__main__':
    unittest.main()
