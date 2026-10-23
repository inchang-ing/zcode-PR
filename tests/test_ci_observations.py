"""CI observation identities and unknown handling; no GitHub or persistent writes."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import monitor_oss as monitor


class CIObservationTests(unittest.TestCase):
    def setUp(self):
        self.run = dict(__typename='CheckRun', name='unit', status='COMPLETED', conclusion='FAILURE',
                        detailsUrl='https://github.com/a/b/actions/runs/1/job/2', startedAt='2026-10-23T01:00:00Z')
        self.status = dict(__typename='StatusContext', context='external', state='SUCCESS',
                           targetUrl='https://ci.example.com/build/1', createdAt='2026-10-23T01:00:00Z')

    def test_fingerprint_is_order_independent_but_tracks_failure_identity(self):
        original = [self.run, self.status]
        self.assertEqual(monitor.ci_fingerprint(original), monitor.ci_fingerprint(list(reversed(original))))
        changed = [dict(self.run, conclusion='SUCCESS'), dict(self.status, state='FAILURE')]
        self.assertEqual(monitor.ci_summary(original), monitor.ci_summary(changed))
        self.assertNotEqual(monitor.ci_fingerprint(original), monitor.ci_fingerprint(changed))

    def test_reruns_and_reposted_statuses_change_fingerprint_without_count_change(self):
        cases = [(self.run, dict(self.run, detailsUrl='https://github.com/a/b/actions/runs/3/job/4')),
                 (self.run, dict(self.run, startedAt='2026-10-23T02:00:00Z')),
                 (self.status, dict(self.status, createdAt='2026-10-23T02:00:00Z')),
                 (self.status, dict(self.status, targetUrl='https://ci.example.com/build/2'))]
        for before, after in cases:
            with self.subTest(after=after):
                self.assertEqual(monitor.ci_summary([before]), monitor.ci_summary([after]))
                self.assertNotEqual(monitor.ci_fingerprint([before]), monitor.ci_fingerprint([after]))

    def test_incomplete_unknown_or_malformed_checks_cannot_be_acknowledged(self):
        cases = [None, {}, 'no-checks', [None], [{}], [dict(self.run, name=None)],
                 [dict(self.run, detailsUrl=None, startedAt=None)], [dict(self.run, status='FUTURE')],
                 [dict(self.run, status='SUCCESS')],
                 [dict(self.run, conclusion=None)], [dict(self.run, detailsUrl=[])],
                 [dict(self.status, context='')], [dict(self.status, state='FUTURE')],
                 [dict(self.status, __typename='OtherCheck')]]
        for roll in cases:
            with self.subTest(roll=roll):
                self.assertIsNone(monitor.ci_fingerprint(roll))
        self.assertEqual(len(monitor.ci_fingerprint([])), 64)
        self.assertEqual(monitor.ci_summary([]), 'no-checks')

    def test_fetch_binds_ci_and_activity_to_the_same_response_head(self):
        data = dict(state='OPEN', headRefOid='a' * 40, updatedAt='2026-10-23T01:00:00Z',
                    statusCheckRollup=[self.run, self.status])
        with patch.object(monitor, 'gh', return_value=json.dumps(data)) as gh:
            result = monitor.fetch('a/b#1')
        self.assertIn('updatedAt', gh.call_args.args[0][-1])
        self.assertEqual(result['ci_head_oid'], data['headRefOid'])
        self.assertEqual(result['headRefOid'], data['headRefOid'])
        self.assertEqual(result['updatedAt'], data['updatedAt'])
        self.assertEqual(result['ci_fingerprint'], monitor.ci_fingerprint(data['statusCheckRollup']))


if __name__ == '__main__':
    unittest.main()
