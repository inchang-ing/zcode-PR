"""Repository capacity stays consistent across offline candidate entry points."""
import builtins
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import candidate_rules as rules
import maintainer_sweep as maintainers
import monitor_fresh as fresh
import repo_capacity as capacity
import work_queue as queue
from pr_state import load_pr_state
from repository_policy import ACCOUNT
from task_state import TaskStore


class CapacityEntrypointTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.now = datetime.now(timezone.utc)
        self.stamp = self.now.isoformat()
        self.path = self.root / 'pr_state.json'

    def write_open(self, count):
        records = {f'Owner/Repo#{number}': {
            'state': 'OPEN', 'checked_at': self.stamp,
            'updatedAt': (self.now - timedelta(days=10)).isoformat(),
            'headRefOid': str(number) * 40,
        } for number in range(1, count + 1)}
        self.path.write_text(json.dumps(records), encoding='utf-8')
        return load_pr_state(self.path, ())

    def candidate(self, number=100, repo='OWNER/REPO'):
        return rules.Candidate(repo, number, 'Bug: wrong parser result', '',
                               is_bug=True, checked_at=self.stamp)

    def github(self, args):
        """Complete two-PR responses; unexpected requests fail instead of reaching GitHub."""
        if args[0] == 'pr':
            number = int(args[2])
            return json.dumps({
                'number': number, 'state': 'OPEN', 'author': {'login': ACCOUNT},
                'url': f'https://github.com/owner/repo/pull/{number}',
                'headRefOid': str(number) * 40, 'isDraft': False, 'mergeable': 'MERGEABLE',
                'reviewDecision': '', 'updatedAt': (self.now - timedelta(days=10)).isoformat(),
                'statusCheckRollup': [],
            })
        self.assertEqual(args[0], 'api')
        if args[1] == 'repos/owner/repo/pulls?state=open&per_page=100':
            return json.dumps([[{
                'number': number, 'state': 'open', 'user': {'login': ACCOUNT},
                'html_url': f'https://github.com/owner/repo/pull/{number}',
                'draft': False, 'head': {'sha': str(number) * 40},
                'updated_at': (self.now - timedelta(days=10)).isoformat(),
            } for number in (1, 2)]])
        self.assertIn(args[1], {
            f'repos/owner/repo/{kind}/{number}/{activity}?per_page=100'
            for number in (1, 2)
            for kind, activity in (('issues', 'comments'), ('pulls', 'reviews'), ('pulls', 'comments'))
        })
        return '[[]]'

    def test_known_two_and_three_open_prs_block_without_hiding_candidates(self):
        for count in (2, 3):
            with self.subTest(count=count):
                records = self.write_open(count)
                store = TaskStore(root=self.root)
                original = self.path.read_bytes()
                for repo in ('Owner/Repo', 'OWNER/REPO', 'owner/repo'):
                    candidate = self.candidate(repo=repo)
                    allowed, reason = rules.is_clean(candidate, store)
                    self.assertFalse(allowed)
                    row = queue.rank_candidates([candidate], store.queue, store, records, self.now)[0]
                    self.assertFalse(row['hidden'])
                    self.assertFalse(row['ready'])
                    self.assertEqual(row['stage'], 'capacity_hold')
                    self.assertIn(reason, row['next'])
                self.assertEqual(self.path.read_bytes(), original)
                self.assertFalse((self.root / 'task_state.json').exists())

    def test_maintainer_pool_uses_same_capacity_and_keeps_policy_blocks(self):
        self.write_open(2)
        with patch.object(maintainers, 'ROOT', self.root), \
                patch.object(fresh, 'build_tiers', return_value=(
                    ['OWNER/REPO', 'owner/repo', 'Other/Project', 'PaLlEtS/FlAsK'], [])), \
                patch.object(maintainers.subprocess, 'run') as request:
            self.assertEqual(maintainers.build_pool(), ['Other/Project'])
        request.assert_not_called()

    def test_confirmed_wait_allows_third_across_entrypoints_but_never_fourth(self):
        records = self.write_open(2)
        store = TaskStore(root=self.root)
        sources = [f'https://github.com/owner/repo/pull/{number}' for number in (1, 2)]
        first = capacity.live_capacity('OWNER/REPO', store, query=self.github,
                                       now=self.now - timedelta(days=8), confirm_wait=True,
                                       sources=sources, note='Both PRs ready; awaiting maintainers')
        self.assertEqual(first['status'], 'HOLD')
        current = capacity.live_capacity('owner/repo', store, query=self.github, now=self.now)
        self.assertTrue(current['allowed'])
        with store.transaction() as ledger:
            ledger['queue']['issues']['owner/repo#100'] = {
                'stage': 'probe', 'events': [], 'signals': {
                    name: {'value': True, 'at': self.stamp, 'source': sources[0]}
                    for name in queue.SIGNALS
                },
            }
        for repo in ('owner/repo', 'OWNER/REPO'):
            candidate = self.candidate(repo=repo)
            self.assertTrue(rules.is_clean(candidate, store)[0])
            row = queue.rank_candidates([candidate], store.queue, store, records, self.now)[0]
            self.assertFalse(row['hidden'])
            self.assertTrue(row['ready'])
            self.assertIn(current['reason'], row['reasons'])
        with patch.object(maintainers, 'ROOT', self.root), \
                patch.object(fresh, 'build_tiers', return_value=(['OWNER/REPO', 'owner/repo'], [])):
            self.assertEqual(maintainers.build_pool(), ['OWNER/REPO'])

        records = self.write_open(3)
        store = TaskStore(root=self.root)
        self.assertFalse(rules.is_clean(self.candidate(), store)[0])
        row = queue.rank_candidates([self.candidate()], store.queue, store, records, self.now)[0]
        self.assertFalse(row['hidden'])
        self.assertFalse(row['ready'])
        self.assertEqual(row['stage'], 'capacity_hold')

    def test_failed_pr_observation_is_visible_for_capacity_verification(self):
        records = self.write_open(1)
        records['owner/repo#1']['query_error'] = 'offline'
        self.path.write_text(json.dumps(records), encoding='utf-8')
        store = TaskStore(root=self.root)
        allowed, reason = rules.is_clean(self.candidate(), store)
        self.assertFalse(allowed)
        row = queue.rank_candidates([self.candidate()], store.queue, store, records, self.now)[0]
        self.assertFalse(row['hidden'])
        self.assertFalse(row['ready'])
        self.assertEqual(row['stage'], 'capacity_unknown')
        self.assertIn(reason, row['next'])

    def test_bulk_screen_and_queue_refresh_read_pr_cache_once_each(self):
        self.write_open(2)
        store = TaskStore(root=self.root)
        candidates = [self.candidate(number) for number in range(100, 1000)]
        read = builtins.open

        def count_reads(mock):
            def is_cache(path):
                try:
                    # Windows runner temp paths can use a short-name alias;
                    # TaskStore resolves it before opening the same file.
                    return Path(path).samefile(self.path)
                except OSError:
                    return False
            return sum(is_cache(call.args[0]) for call in mock.call_args_list
                       if call.args and isinstance(call.args[0], (str, Path)))

        with patch('builtins.open', wraps=read) as opened:
            decisions = [rules.is_clean(candidate, store) for candidate in candidates]
        self.assertTrue(all(not allowed for allowed, _ in decisions))
        self.assertEqual(count_reads(opened), 1)

        (self.root / 'round_candidates.json').write_text(
            json.dumps([asdict(candidate) for candidate in candidates]), encoding='utf-8')
        with patch('builtins.open', wraps=read) as opened:
            rows = queue.refresh(self.root)
        self.assertEqual(count_reads(opened), 1)
        issue_rows = [row for row in rows if row['kind'] == 'issue']
        self.assertEqual(len(issue_rows), len(candidates))
        self.assertTrue(all(not row['hidden'] and row['stage'] == 'capacity_hold' for row in issue_rows))
        self.assertIn('待名额', (self.root / 'WORK_QUEUE.md').read_text(encoding='utf-8'))
        self.assertFalse((self.root / 'task_state.json').exists())


if __name__ == '__main__':
    unittest.main()
