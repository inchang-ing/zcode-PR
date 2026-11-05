"""Retry delays belong between requests, never after the final failure."""
import contextlib
import io
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import monitor_round as scan


class ScanRetryTests(unittest.TestCase):
    def call_gh(self, outcomes, retries):
        events = []
        responses = iter(outcomes)

        def request(*args, **kwargs):
            events.append('request')
            result = next(responses)
            if isinstance(result, Exception):
                raise result
            return result

        with patch.object(scan.subprocess, 'run', side_effect=request), \
             patch.object(scan.time, 'sleep', side_effect=lambda delay: events.append(('sleep', delay))), \
             contextlib.redirect_stderr(io.StringIO()):
            result = scan.gh(['issue', 'list'], retries=retries)
        return result, events

    def test_rate_limit_waits_only_between_requests(self):
        failure = SimpleNamespace(returncode=62, stdout='', stderr='API rate limit exceeded')
        for attempts in (1, 4, 6):
            with self.subTest(attempts=attempts):
                result, events = self.call_gh([failure] * attempts, attempts)
                expected = ['request']
                for retry in range(1, attempts):
                    expected.extend([('sleep', min(60, 15 * retry)), 'request'])
                self.assertIsNone(result)
                self.assertEqual(events, expected)

    def test_timeouts_wait_only_between_requests(self):
        failure = subprocess.TimeoutExpired('gh', 90)
        for attempts in (1, 4):
            with self.subTest(attempts=attempts):
                result, events = self.call_gh([failure] * attempts, attempts)
                self.assertIsNone(result)
                self.assertEqual(events, ['request'] + [('sleep', 10), 'request'] * (attempts - 1))

    def test_success_stops_retries_without_changing_prior_delays(self):
        success = SimpleNamespace(returncode=0, stdout='response', stderr='')
        for failure, delays in ((SimpleNamespace(returncode=62, stdout='', stderr='secondary limit'),
                                 [15, 30]), (subprocess.TimeoutExpired('gh', 90), [10, 10])):
            with self.subTest(delays=delays):
                result, events = self.call_gh([failure, failure, success], 4)
                self.assertEqual(result, 'response')
                self.assertEqual(events, ['request', ('sleep', delays[0]), 'request',
                                          ('sleep', delays[1]), 'request'])

    def test_permanent_failure_returns_without_sleep_or_retry(self):
        failure = SimpleNamespace(returncode=1, stdout='', stderr='permission denied')
        self.assertEqual(self.call_gh([failure], 4), (None, ['request']))


if __name__ == '__main__':
    unittest.main()
