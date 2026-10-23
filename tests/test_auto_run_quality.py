"""A future fixer hook must not bypass final-commit evidence checks."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import auto_run as a


class AutoRunQualityTests(unittest.TestCase):
    def test_owner_can_record_normal_fix_and_error_outcomes(self):
        with tempfile.TemporaryDirectory() as folder:
            candidate = a.Candidate('a/b', 1, 'bug', '')
            for result in ('repro_failed', 'no_fixer', 'no_change', 'error'):
                with self.subTest(result=result):
                    store = a.DispatchedStore(str(Path(folder) / 'dispatched.json'))
                    store.mark(candidate.key, 'pending', pr_url='https://example.com/pr')
                    fixers = {candidate.key: lambda c, p: None} if result == 'no_change' else {}
                    failure = OSError('offline') if result == 'error' else None
                    with patch.dict(a.REPROS, {candidate.key: lambda c, p: result != 'repro_failed'}, clear=True), \
                         patch.dict(a.FIXERS, fixers, clear=True), \
                         patch.object(a, '_clone_via_tarball', return_value=folder, side_effect=failure), \
                         patch.object(a, '_snapshot_hashes', return_value={'a.py': 'unchanged'}), \
                         patch.object(a.subprocess, 'run') as external:
                        a.run(candidate, store)
                    external.assert_not_called()
                    self.assertEqual(store.status_of(candidate.key),
                                     'repro_failed' if result in ('repro_failed', 'error') else 'needs_fix')
                    self.assertEqual(store.data[candidate.key]['pr_url'], 'https://example.com/pr')

    def test_owner_completion_and_error_preserve_new_terminal_state(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'dispatched.json'
            candidate = a.Candidate('a/b', 1, 'bug', '')
            for status in ('closed', 'merged'):
                for result in ('repro_failed', 'no_fixer', 'no_change', 'changed', 'error'):
                    with self.subTest(status=status, result=result):
                        store = a.DispatchedStore(str(path))
                        store.mark(candidate.key, 'pending')
                        target = Path(folder) / 'module.py'
                        target.write_text('broken', encoding='utf-8')
                        fixers = {}
                        if result in ('no_change', 'changed'):
                            fixers[candidate.key] = lambda c, p: target.write_text(
                                'fixed' if result == 'changed' else 'broken', encoding='utf-8')
                        terminal = []
                        def clone(repo):
                            a.DispatchedStore(str(path)).mark(candidate.key, status,
                                reason='Maintainer finished', pr_url='https://example.com/pr')
                            terminal.append(path.read_bytes())
                            if result == 'error':
                                raise OSError('offline')
                            return folder
                        with patch.dict(a.REPROS, {candidate.key: lambda c, p: result != 'repro_failed'}, clear=True), \
                             patch.dict(a.FIXERS, fixers, clear=True), \
                             patch.object(a, '_clone_via_tarball', side_effect=clone), \
                             patch.object(a.subprocess, 'run') as external:
                            a.run(candidate, store)
                        external.assert_not_called()
                        self.assertEqual(path.read_bytes(), terminal[0])

    def test_changed_patch_stops_for_verification_without_external_write(self):
        with tempfile.TemporaryDirectory() as folder:
            store = a.DispatchedStore(str(Path(folder) / 'dispatched.json'))
            candidate = a.Candidate('a/b', 1, 'bug', '')
            with patch.dict(a.FIXERS, {candidate.key: lambda c, p: None}), \
                 patch.object(a, '_clone_via_tarball', return_value=folder), \
                 patch.object(a, '_reproduce', return_value=True), \
                 patch.object(a, '_snapshot_hashes', side_effect=[{'a.py': 'old'}, {'a.py': 'new'}]), \
                 patch.object(a, '_push_via_api') as push, \
                 patch.object(a.subprocess, 'run') as external:
                a.run(candidate, store)
            push.assert_not_called()
            external.assert_not_called()
            self.assertEqual(store.status_of(candidate.key), 'needs_verification')
            self.assertTrue(store.is_active(candidate.key))


if __name__ == '__main__':
    unittest.main()
