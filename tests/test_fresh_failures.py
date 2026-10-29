"""Incomplete fresh scans retain failed cursors and report a failed round."""
from contextlib import nullcontext, redirect_stdout
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import monitor_fresh as fresh


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 26, 12, tzinfo=timezone.utc).astimezone(tz)


class FreshFailureTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.object(fresh, 'datetime', FixedDatetime))
        self.since = FixedDatetime.now(timezone.utc) - timedelta(hours=1)

    def issue(self, number=1, created=None):
        return dict(number=number, created_at=(created or self.since).isoformat(),
                    title='bug: crash', labels=[], user={'login': 'reporter'})

    def test_invalid_new_issue_number_discards_the_repository_result(self):
        for number in (True, False, '17', 0, -1, None):
            with self.subTest(number=number), \
                 patch.object(fresh, 'gh_api', return_value=json.dumps([self.issue(number)])) as api:
                self.assertIsNone(fresh.fetch_newest('a/b', self.since))
                api.assert_called_once()

    def test_later_invalid_number_does_not_return_partial_discoveries(self):
        with patch.object(fresh, 'PER_PAGE', 1), patch.object(fresh, 'gh_api', side_effect=[
                json.dumps([self.issue(1)]), json.dumps([self.issue(True)]), json.dumps([])]) as api:
            self.assertIsNone(fresh.fetch_newest('a/b', self.since))
        self.assertEqual(api.call_count, 2)

    def test_old_rows_and_boundary_pull_requests_do_not_require_issue_numbers(self):
        old = self.issue(None, self.since - timedelta(seconds=1))
        pr = dict(self.issue(None), pull_request={})
        with patch.object(fresh, 'gh_api', return_value=json.dumps([self.issue(7), pr, old])) as api:
            result = fresh.fetch_newest('a/b', self.since)
        self.assertEqual([item['num'] for item in result], [7])
        api.assert_called_once()

    def test_round_failure_keeps_failed_cursors_and_preserves_success(self):
        item = dict(repo='b/good', num=7, title='bug', labels='bug', age_h=0, author='reporter')
        previous = self.since.isoformat()
        initial = dict(default_since=previous, repo_last_success={'a/fail': previous, 'b/good': previous},
                       seen={})
        for init in (False, True):
            for fail_all in (False, True):
                with self.subTest(init=init, fail_all=fail_all), \
                     patch.object(fresh, 'file_lock', return_value=nullcontext()), \
                     patch.object(fresh, 'load_state', return_value=deepcopy(initial)), \
                     patch.object(fresh, 'build_tiers', return_value=(['a/fail', 'b/good'], [])), \
                     patch.object(fresh, 'ALWAYS_SLICES', 1), \
                     patch.object(fresh, 'fetch_newest', side_effect=lambda repo, since:
                                  None if fail_all or repo == 'a/fail' else [item]) as fetch, \
                     patch.object(fresh, 'persist_discoveries') as persist, \
                     patch.object(fresh, 'save_state') as save, \
                     patch('work_queue.refresh', return_value=[]) as refresh, \
                     patch.object(sys, 'argv', ['monitor_fresh.py'] + (['--init'] if init else [])), \
                     redirect_stdout(io.StringIO()):
                    self.assertEqual(fresh.main(), 1)
                    saved = save.call_args.args[0]
                    self.assertEqual(saved['repo_last_success']['a/fail'], previous)
                    self.assertEqual(saved['repo_last_success']['b/good'], previous if fail_all else
                                     FixedDatetime.now(timezone.utc).isoformat())
                    self.assertEqual(saved['default_since'], previous)
                    if init:
                        persist.assert_not_called()
                        self.assertEqual(set(saved['seen']), set() if fail_all else {'b/good#7'})
                    else:
                        persist.assert_called_once_with([] if fail_all else [item])
                    self.assertEqual(fetch.call_count, 2)
                    refresh.assert_called_once_with()

    def test_complete_round_returns_success_and_refreshes_queue(self):
        for init in (False, True):
            with self.subTest(init=init), \
                 patch.object(fresh, 'file_lock', return_value=nullcontext()), \
                 patch.object(fresh, 'load_state', return_value={}), \
                 patch.object(fresh, 'build_tiers', return_value=(['a/b'], [])), \
                 patch.object(fresh, 'ALWAYS_SLICES', 1), \
                 patch.object(fresh, 'fetch_newest', return_value=[]), \
                 patch.object(fresh, 'persist_discoveries'), patch.object(fresh, 'save_state'), \
                 patch('work_queue.refresh', return_value=[]) as refresh, \
                 patch.object(sys, 'argv', ['monitor_fresh.py'] + (['--init'] if init else [])), \
                 redirect_stdout(io.StringIO()):
                self.assertEqual(fresh.main(), 0)
                refresh.assert_called_once_with()

    def test_cli_propagates_round_status(self):
        for failed in (False, True):
            with self.subTest(failed=failed), \
                 patch('pipeline_state.file_lock', return_value=nullcontext()), \
                 patch('pipeline_state.read_json_object', return_value={}), \
                 patch('pipeline_state.atomic_write_json'), \
                 patch('concurrent.futures.ThreadPoolExecutor') as executor, \
                 patch('subprocess.run', side_effect=AssertionError('Real request prohibited')), \
                 patch('work_queue.refresh', return_value=[]) as refresh, \
                 patch.object(sys, 'argv', ['monitor_fresh.py']), \
                 redirect_stdout(io.StringIO()):
                executor.return_value.__enter__.return_value.map.return_value = [None] if failed else [[]]
                with self.assertRaises(SystemExit) as result:
                    runpy.run_path(fresh.__file__, run_name='__main__')
                self.assertEqual(result.exception.code, 1 if failed else 0)
                refresh.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
