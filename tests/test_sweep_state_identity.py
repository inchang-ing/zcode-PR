"""Auxiliary sweeps consume canonical PR identities without rewriting the cache."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import maintainer_sweep as maintainers
import monitor_fresh as fresh
import review_sweep as reviews


class SweepStateIdentityTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.path = self.root / 'pr_state.json'
        self.enterContext(redirect_stdout(io.StringIO()))

    def record(self, state, minute):
        stamp = f'2026-10-25T12:{minute:02d}:00Z'
        return dict(state=state, checked_at=stamp, updatedAt=stamp)

    def write(self, records):
        self.path.write_bytes(json.dumps(records).encode('utf-8'))
        return self.path.read_bytes()

    def test_review_queries_each_latest_open_identity_only_once(self):
        for latest_state, requests in (('OPEN', 2), ('CLOSED', 0)):
            for reverse in (False, True):
                with self.subTest(latest_state=latest_state, reverse=reverse):
                    entries = [('Owner/Repo#1', self.record('OPEN', 0)),
                               ('owner/repo#1', self.record(latest_state, 5))]
                    original = self.write(dict(reversed(entries) if reverse else entries))
                    with patch.object(reviews, 'STATE', self.path), \
                         patch.object(sys, 'argv', ['review_sweep.py', '--since', '2026-10-25T11:00:00Z']), \
                         patch.object(reviews.subprocess, 'run', return_value=SimpleNamespace(
                             returncode=0, stdout='[[]]')) as request:
                        self.assertEqual(reviews.main(), 0)
                    self.assertEqual(request.call_count, requests)
                    if requests:
                        self.assertIn('repos/owner/repo/', request.call_args.args[0][2])
                    self.assertEqual(self.path.read_bytes(), original)

    def test_maintainer_capacity_counts_unique_current_open_prs(self):
        for old, new, sibling, eligible in (('OPEN', 'OPEN', False, True),
                                            ('OPEN', 'CLOSED', True, True),
                                            ('CLOSED', 'OPEN', True, False)):
            for reverse in (False, True):
                with self.subTest(old=old, new=new, sibling=sibling, reverse=reverse):
                    entries = [('Owner/Repo#1', self.record(old, 0)),
                               ('owner/repo#1', self.record(new, 5))]
                    if sibling:
                        entries.append(('owner/repo#2', self.record('OPEN', 5)))
                    original = self.write(dict(reversed(entries) if reverse else entries))
                    with patch.object(maintainers, 'ROOT', self.root), \
                         patch.object(fresh, 'build_tiers', return_value=(['owner/repo'], [])), \
                         patch.object(maintainers.subprocess, 'run') as request:
                        self.assertEqual(maintainers.build_pool(), ['owner/repo'] if eligible else [])
                    request.assert_not_called()
                    self.assertEqual(self.path.read_bytes(), original)

    def test_ambiguous_cache_blocks_both_sweeps_before_requests(self):
        original = self.write({'Owner/Repo#1': self.record('OPEN', 0),
                               'owner/repo#1': self.record('CLOSED', 0)})
        with patch.object(reviews, 'STATE', self.path), \
             patch.object(sys, 'argv', ['review_sweep.py', '--since', '2026-10-25T11:00:00Z']), \
             patch.object(reviews.subprocess, 'run') as request, redirect_stdout(io.StringIO()) as output:
            self.assertEqual(reviews.main(), 1)
        request.assert_not_called()
        self.assertIn('UNKNOWN', output.getvalue())
        with patch.object(maintainers, 'ROOT', self.root), \
             patch.object(fresh, 'build_tiers', return_value=(['owner/repo'], [])), \
             patch.object(maintainers.subprocess, 'run') as request:
            with self.assertRaises(ValueError):
                maintainers.build_pool()
        request.assert_not_called()
        self.assertEqual(self.path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
