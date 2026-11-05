"""Exercise the real poll round against a fake inbox and paginated GitHub API."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import poll_fresh as poll


class FastLaneTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch.object(poll, 'ROOT', self.root))
        self.enterContext(patch.object(poll, 'load_pool', return_value={'a/b', 'c/d'}))
        self.enterContext(patch.object(poll, 'switch_on', return_value=True))
        self.enterContext(patch.object(sys, 'argv', ['poll_fresh.py']))
        self.enterContext(patch.dict(os.environ, {'GITHUB_REPOSITORY': 'self/pipeline'}))
        self.state = {'version': 1, 'default_since': '2026-10-01T00:00:00Z',
                      'repo_last_success': {'a/b': '2026-10-02T00:00:00Z'}}
        self.body = 'Human notes\n\n<!-- zcode-poll-state\n' + json.dumps(self.state) + '\n-->'
        self.comments, self.requests = [], []
        self.pages = {'a/b': [[]], 'c/d': [[]]}
        self.fail_post = self.fail_checkpoint = False
        self.enterContext(patch.object(poll, 'call', side_effect=self.api))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.enterContext(contextlib.redirect_stderr(io.StringIO()))

    def item(self, number=1, repo='a/b'):
        return {'number': number, 'title': 'Bug in parser', 'created_at': '2026-10-03T00:00:00Z',
                'html_url': f'https://github.com/{repo}/issues/{number}', 'labels': [],
                'user': {'login': 'reporter'}}

    def api(self, method, path, payload=None):
        self.requests.append((method, path, copy.deepcopy(payload)))
        route = urlsplit(path)
        if route.path == '/repos/self/pipeline/issues':
            return [{'number': 9}]
        if route.path == '/repos/self/pipeline/issues/9/comments':
            if method == 'POST':
                if self.fail_post:
                    raise poll.PollError('notification unavailable')
                self.comments.append(payload)
                return {'id': len(self.comments)}
            return self.comments
        if route.path == '/repos/self/pipeline/issues/9':
            if method == 'PATCH':
                if self.fail_checkpoint:
                    raise poll.PollError('checkpoint unavailable')
                self.body = payload['body']
            return {'body': self.body}
        repo = route.path.split('/repos/')[1].rsplit('/issues', 1)[0]
        page = int(parse_qs(route.query)['page'][0])
        value = self.pages[repo][page - 1]
        if isinstance(value, Exception):
            raise value
        return copy.deepcopy(value)

    def saved(self):
        return json.loads(poll.CHECKPOINT_RE.search(self.body)[1])

    def test_all_failed_is_not_empty_success_and_preserves_checkpoint(self):
        self.pages = {key: [poll.PollError('503')] for key in self.pages}
        before = self.body
        self.assertEqual(poll.main(), 1)
        self.assertEqual(self.body, before)
        self.assertFalse(any(method != 'GET' for method, _, _ in self.requests))

    def test_partial_page_failure_discards_partial_hits_and_retries_old_boundary(self):
        self.pages['a/b'] = [[self.item()]]
        self.pages['c/d'] = [[self.item(n, 'c/d') for n in range(1, 101)], poll.PollError('503')]
        self.assertEqual(poll.main(), 2)
        saved = self.saved()
        self.assertEqual(saved['default_since'], self.state['default_since'])
        self.assertNotIn('c/d', saved['repo_last_success'])
        self.assertIn('a/b', saved['repo_last_success'])
        self.assertEqual(len(self.comments), 1)
        self.assertNotIn('c/d#', self.comments[0]['body'])
        self.pages['c/d'] = [[self.item(101, 'c/d')]]
        self.requests.clear()
        self.assertEqual(poll.main(), 0)
        query = next(path for _, path, _ in self.requests if path.startswith('/repos/c/d/issues?'))
        self.assertEqual(parse_qs(urlsplit(query).query)['since'], ['2026-10-01T00:00:00Z'])
        self.assertTrue(self.body.startswith('Human notes'))

    def test_send_failure_never_advances_watermarks(self):
        self.pages['a/b'] = [[self.item()]]
        self.fail_post = True
        self.assertEqual(poll.main(), 1)
        self.assertEqual(self.saved(), self.state)

    def test_checkpoint_failure_replays_without_duplicate_notification(self):
        self.pages['a/b'] = [[self.item()]]
        self.fail_checkpoint = True
        self.assertEqual(poll.main(), 1)
        self.assertEqual(self.saved(), self.state)
        self.fail_checkpoint = False
        self.assertEqual(poll.main(), 0)
        self.assertEqual(len(self.comments), 1)

    def test_corrupt_checkpoint_fails_before_scanning(self):
        self.body = '<!-- zcode-poll-state\n{broken\n-->'
        self.assertEqual(poll.main(), 1)
        self.assertFalse(any('/repos/a/b/' in path for _, path, _ in self.requests))

    def test_dry_run_does_not_write(self):
        self.pages['a/b'] = [[self.item()]]
        with patch.object(sys, 'argv', ['poll_fresh.py', '--dry-run']):
            self.assertEqual(poll.main(), 0)
        self.assertEqual(self.saved(), self.state)
        self.assertTrue(all(method == 'GET' for method, _, _ in self.requests))

    def test_deduplication_reads_past_one_thousand_comments(self):
        pages = [[{'body': ''}] * 100 for _ in range(11)] + [[{'body': '- `a/b#900` reported'}]]
        with patch.object(poll, 'call', side_effect=pages) as api:
            self.assertEqual(poll.already_reported('self/pipeline', 9), {'a/b#900'})
        self.assertEqual(api.call_count, 12)

    def test_later_round_only_reads_comments_in_the_recovery_window(self):
        self.pages['a/b'] = [[self.item()]]
        self.assertEqual(poll.main(), 0)
        since = self.saved()['comments_since']
        self.requests.clear()
        # The fake issue API deliberately replays a discovery at the new boundary.
        self.pages['a/b'] = [[dict(self.item(), created_at=self.saved()['repo_last_success']['a/b'])]]
        self.assertEqual(poll.main(), 0)
        paths = [path for method, path, _ in self.requests
                 if method == 'GET' and '/comments?' in path]
        self.assertEqual(len(paths), 1)
        self.assertEqual(parse_qs(urlsplit(paths[0]).query)['since'], [since])
        self.assertEqual(len(self.comments), 1)

    def test_large_notifications_split_without_losing_machine_events(self):
        from notification_contract import decode_events
        items = [dict(self.item(n), title='界' * 600, _slug='a/b') for n in range(1, 12)]
        bodies = poll.render_batches(items, 40, max_chars=8000)
        self.assertGreater(len(bodies), 1)
        self.assertTrue(all(len(body) <= 8000 for body in bodies))
        self.assertEqual([event['number'] for body in bodies for event in decode_events(body)],
                         list(range(1, 12)))
        with self.assertRaises(poll.PollError):
            poll.render_batches(items, 40, max_chars=100)

    def test_partial_failure_keeps_old_comments_visible_when_repo_recovers(self):
        from datetime import datetime
        self.comments = [{'body': '- `a/b#1` already reported',
                          'created_at': '2026-10-02T00:00:00Z'}]
        def api(method, path, payload=None):
            value = self.api(method, path, payload)
            if method == 'GET' and '/comments?' in path:
                since = parse_qs(urlsplit(path).query).get('since')
                if since:
                    cutoff = datetime.fromisoformat(since[0].replace('Z', '+00:00'))
                    value = [row for row in value if datetime.fromisoformat(
                        row['created_at'].replace('Z', '+00:00')) >= cutoff]
            return value
        with patch.object(poll, 'call', side_effect=api):
            self.pages['a/b'] = [poll.PollError('503')]
            self.assertEqual(poll.main(), 2)
            self.pages['a/b'] = [[dict(self.item(), created_at='2026-10-02T00:00:00Z')]]
            self.assertEqual(poll.main(), 0)
        self.assertEqual(len(self.comments), 1)


class SwitchLookupTests(unittest.TestCase):
    def test_lookup_failure_requires_explicit_workflow_value(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(poll, 'call', side_effect=poll.PollError('forbidden', 403)):
            with self.assertRaises(poll.PollError):
                poll.switch_on('self/pipeline')
            with patch.dict(os.environ, {'PIPELINE_ENABLED': 'false'}):
                self.assertFalse(poll.switch_on('self/pipeline'))
            with patch.dict(os.environ, {'PIPELINE_ENABLED': 'true'}):
                self.assertTrue(poll.switch_on('self/pipeline'))


if __name__ == '__main__':
    unittest.main()
