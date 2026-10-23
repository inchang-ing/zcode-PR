"""A future fixer hook must not bypass final-commit evidence checks."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import auto_run as a


class AutoRunQualityTests(unittest.TestCase):
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
