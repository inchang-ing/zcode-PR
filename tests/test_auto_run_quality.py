"""A future fixer hook must not bypass final-commit evidence checks."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import auto_run as a


class AutoRunQualityTests(unittest.TestCase):
    def test_candidates_without_hooks_do_not_starve_preparation_limits(self):
        for limit in ([], ['--max=1']):
            with self.subTest(limit=limit), tempfile.TemporaryDirectory() as folder:
                candidates = [a.Candidate(repo, number, 'bug: crash', '') for repo, number in
                              (('a/b', 1), ('a/b', 2), ('a/b', 3), ('other/repo', 1))]
                store = a.DispatchedStore(str(Path(folder) / 'dispatched.json'))
                repros = {candidate.key: lambda c, p: False for candidate in candidates[1:]}
                with patch.object(a, 'load_candidates', return_value=candidates), \
                     patch.object(a, 'DispatchedStore', return_value=store), \
                     patch.dict(a.REPROS, repros, clear=True), patch.dict(a.FIXERS, {}, clear=True), \
                     patch.object(a, '_clone_via_tarball', return_value=folder) as clone, \
                     patch.object(sys, 'argv', ['auto_run.py', *limit]), \
                     patch.object(a.subprocess, 'run') as external:
                    a.main()
                external.assert_not_called()
                self.assertEqual(store.status_of(candidates[0].key), 'needs_repro')
                self.assertEqual(store.status_of(candidates[1].key), 'repro_failed')
                self.assertEqual(store.status_of(candidates[2].key), 'none')
                self.assertEqual([call.args[0] for call in clone.call_args_list],
                                 ['a/b'] if limit else ['a/b', 'other/repo'])

    def test_deleted_files_are_included_in_patch_changes(self):
        for mode in ('delete_only', 'rename', 'mixed'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                checkout = root / 'checkout'
                checkout.mkdir()
                deleted = checkout / 'obsolete.py'
                deleted.write_bytes(b'old code')
                other = checkout / 'module.py'
                other.write_bytes(b'unchanged')
                renamed = checkout / 'renamed.py'
                store = a.DispatchedStore(str(root / 'dispatched.json'))
                candidate = a.Candidate('a/b', 1, 'bug', '')

                def fix(c, path):
                    if mode == 'rename':
                        deleted.rename(renamed)
                    else:
                        deleted.unlink()
                    if mode == 'mixed':
                        other.write_bytes(b'fixed')

                with patch.dict(a.REPROS, {candidate.key: lambda c, p: True}, clear=True), \
                     patch.dict(a.FIXERS, {candidate.key: fix}, clear=True), \
                     patch.object(a, '_clone_via_tarball', return_value=str(checkout)), \
                     patch.object(a.subprocess, 'run') as external:
                    a.run(candidate, store)
                external.assert_not_called()
                self.assertEqual(store.status_of(candidate.key), 'needs_verification')
                expected = [str(deleted)]
                if mode == 'rename':
                    expected.append(str(renamed))
                elif mode == 'mixed':
                    expected.append(str(other))
                self.assertEqual(store.data[candidate.key]['changed'], sorted(expected))

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
                 patch.object(a.subprocess, 'run') as external:
                a.run(candidate, store)
            external.assert_not_called()
            self.assertEqual(store.status_of(candidate.key), 'needs_verification')
            self.assertTrue(store.is_active(candidate.key))


if __name__ == '__main__':
    unittest.main()
