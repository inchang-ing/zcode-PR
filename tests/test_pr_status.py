"""Single-PR diagnostics must not hide later pages or failed reads."""
import io
import json
from pathlib import Path
import subprocess
import runpy
import sys
from types import SimpleNamespace
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import pr_status as p


class PRStatusTests(unittest.TestCase):
    def response(self, cmd, **kwargs):
        path = cmd[-1]
        endpoint = path.split('?')[0]
        if endpoint.endswith('/reviews'):
            items = [dict(user={'login': f'reviewer-{n}'}, state='APPROVED', submitted_at=str(n))
                     for n in range(1, 106)]
        elif endpoint.endswith('/comments'):
            items = [dict(user={'login': 'maintainer'}, body=f'feedback-{n}', created_at=str(n),
                          path='module.py', line=n) for n in range(1, 106)]
        elif endpoint.endswith('/check-runs'):
            items = [dict(name=f'check-{n}', status='completed',
                          conclusion='failure' if n == 105 else 'success', html_url='https://example.com')
                     for n in range(1, 106)]
        elif endpoint.endswith('/status'):
            items = [dict(context=f'external-{n}', state='failure' if n == 105 else 'success',
                          target_url='https://ci.example.com/build') for n in range(1, 106)]
        else:
            return SimpleNamespace(returncode=0, stdout=json.dumps(
                dict(state='open', head={'sha': 'a' * 40}, title='Example')), stderr='')
        size = 100 if 'per_page=100' in path else 30
        pages = [items[i:i + size] for i in range(0, len(items), size)]
        if endpoint.endswith('/check-runs'):
            pages = [dict(total_count=len(items), check_runs=page) for page in pages]
        elif endpoint.endswith('/status'):
            pages = [dict(total_count=len(items), statuses=page) for page in pages]
        result = pages if '--paginate' in cmd and '--slurp' in cmd else pages[0]
        return SimpleNamespace(returncode=0, stdout=json.dumps(result), stderr='')

    def test_latest_feedback_and_late_ci_failure_are_visible(self):
        output = io.StringIO()
        with patch.object(p.subprocess, 'run', side_effect=self.response) as run, redirect_stdout(output):
            result = p.check('a/b', 1)
        text = output.getvalue()
        self.assertIn('reviewer-105', text)
        self.assertIn('feedback-105', text)
        self.assertIn('COMMENTS: 105', text)
        self.assertIn('INLINE: 105', text)
        self.assertIn('CHECKS: total=105 ok=104', text)
        self.assertIn('check-105 -> failure', text)
        self.assertIn('STATUSES: total=105 ok=104 pending=0', text)
        self.assertIn('external-105 -> failure', text)
        self.assertTrue(result)
        self.assertEqual(sum('--paginate' in call.args[0] for call in run.call_args_list), 5)

    def test_later_page_failure_is_unknown_instead_of_empty_or_partial(self):
        for suffix, label in (('/reviews', 'REVIEW'), ('/issues/1/comments', 'COMMENTS'),
                              ('/pulls/1/comments', 'INLINE'), ('/check-runs', 'CHECKS'),
                              ('/status', 'STATUSES')):
            def response(cmd, **kwargs):
                if cmd[-1].split('?')[0].endswith(suffix):
                    return SimpleNamespace(returncode=1, stdout='[[{"body":"partial"}]]',
                                           stderr='page 2 unavailable')
                return self.response(cmd, **kwargs)
            with self.subTest(label=label), patch.object(p.subprocess, 'run', side_effect=response):
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertFalse(p.check('a/b', 1))
                self.assertIn(label + ': UNKNOWN', output.getvalue())
                self.assertNotIn('partial', output.getvalue())
                self.assertNotIn(label + ': none', output.getvalue())

    def test_paginated_response_validation_and_empty_results(self):
        for data, key in (([], None), ({}, None), ([{}], None), ([[1]], None),
                          ([{}], 'check_runs'), ([[]], 'check_runs'),
                          ([{'check_runs': None}], 'check_runs')):
            with self.subTest(data=data, key=key), patch.object(p.subprocess, 'run', return_value=
                    SimpleNamespace(returncode=0, stdout=json.dumps(data), stderr='')):
                self.assertIn('__error__', p.api('endpoint', paginate=True, item_key=key))
        for data, key in (([[]], None), ([{'check_runs': []}], 'check_runs')):
            with self.subTest(data=data, key=key), patch.object(p.subprocess, 'run', return_value=
                    SimpleNamespace(returncode=0, stdout=json.dumps(data), stderr='')):
                self.assertEqual(p.api('endpoint', paginate=True, item_key=key), [])

    def test_request_and_json_failures_are_reported(self):
        for error in (OSError('unavailable'), subprocess.TimeoutExpired('gh', 60)):
            with self.subTest(error=error), patch.object(p.subprocess, 'run', side_effect=error):
                self.assertIn('__error__', p.api('endpoint'))
        with patch.object(p.subprocess, 'run', return_value=
                SimpleNamespace(returncode=0, stdout='invalid JSON', stderr='')):
            self.assertIn('__error__', p.api('endpoint'))

    def test_empty_collections_are_complete(self):
        def response(cmd, **kwargs):
            if '--paginate' not in cmd:
                return self.response(cmd, **kwargs)
            data = ([{'check_runs': []}] if '/check-runs?' in cmd[-1] else
                    [{'statuses': []}] if '/status?' in cmd[-1] else [[]])
            return SimpleNamespace(returncode=0, stdout=json.dumps(data), stderr='')
        output = io.StringIO()
        with patch.object(p.subprocess, 'run', side_effect=response), redirect_stdout(output):
            self.assertTrue(p.check('a/b', 1))
        for expected in ('REVIEW: none', 'COMMENTS: 0', 'INLINE: 0', 'CHECKS: total=0',
                         'STATUSES: total=0'):
            self.assertIn(expected, output.getvalue())

    def test_commit_status_failures_are_visible_without_check_runs(self):
        def response(cmd, **kwargs):
            if '/check-runs?' in cmd[-1]:
                return SimpleNamespace(returncode=0, stdout='[{"check_runs": []}]', stderr='')
            if '/status?' in cmd[-1]:
                statuses = [dict(context=name, state=state, target_url='https://ci.example.com/build')
                            for name, state in [('external-ci', 'failure'), ('lint', 'error'),
                                                ('deploy', 'pending'), ('unit', 'success')]]
                return SimpleNamespace(returncode=0, stdout=json.dumps([{'statuses': statuses}]), stderr='')
            return self.response(cmd, **kwargs)
        output = io.StringIO()
        with patch.object(p.subprocess, 'run', side_effect=response), redirect_stdout(output):
            self.assertTrue(p.check('a/b', 1))
        self.assertIn('CHECKS: total=0', output.getvalue())
        self.assertIn('STATUSES: total=4 ok=1 pending=1', output.getvalue())
        self.assertIn('external-ci -> failure', output.getvalue())
        self.assertIn('lint -> error', output.getvalue())

    def test_incomplete_commit_status_is_unknown(self):
        for status in ({}, {'context': 'ci'}, {'context': 'ci', 'state': 'future'},
                       {'context': None, 'state': 'success'}):
            def response(cmd, **kwargs):
                if '/status?' in cmd[-1]:
                    return SimpleNamespace(returncode=0, stdout=json.dumps([{'statuses': [status]}]), stderr='')
                return self.response(cmd, **kwargs)
            output = io.StringIO()
            with self.subTest(status=status), patch.object(p.subprocess, 'run', side_effect=response), \
                    redirect_stdout(output):
                self.assertFalse(p.check('a/b', 1))
            self.assertIn('STATUSES: UNKNOWN', output.getvalue())

    def test_invalid_detail_stops_before_collection_requests(self):
        with patch.object(p.subprocess, 'run', return_value=SimpleNamespace(
                returncode=0, stdout='[]', stderr='')) as run, redirect_stdout(io.StringIO()):
            self.assertFalse(p.check('a/b', 1))
        self.assertEqual(run.call_count, 1)

    def test_cli_reports_failure_after_checking_remaining_prs(self):
        for failed in (True, False):
            def response(cmd, **kwargs):
                if failed and cmd[-1].endswith('/pulls/1'):
                    return SimpleNamespace(returncode=1, stdout='', stderr='unavailable')
                return self.response(cmd, **kwargs)
            with self.subTest(failed=failed), patch.object(p.subprocess, 'run', side_effect=response), \
                    patch.object(sys, 'argv', ['pr_status.py', 'a/b', '1', '2']):
                output = io.StringIO()
                with redirect_stdout(output), self.assertRaises(SystemExit) as exit_result:
                    runpy.run_path(p.__file__, run_name='__main__')
                self.assertEqual(exit_result.exception.code, 1 if failed else 0)
                self.assertIn('### a/b#2', output.getvalue())


if __name__ == '__main__':
    unittest.main()
