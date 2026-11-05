"""A recovered PR cannot erase an interruption in its seven-day waiting period."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from pr_state import merge_observations


class CapacityObservationTests(unittest.TestCase):
    def test_failure_or_new_head_survives_later_recovery(self):
        initial = {'state': 'OPEN', 'headRefOid': 'a' * 40,
                   'reviewDecision': 'REVIEW_REQUIRED', 'mergeable': 'MERGEABLE',
                   'ci': 'no-checks', 'ci_head_oid': 'a' * 40,
                   'ci_fingerprint': 'b' * 64, 'checked_at': '2026-11-01T00:00:00Z'}
        interruptions = [
            {'state': 'QUERY_ERROR', '_err': 'timeout'},
            {'reviewDecision': 'CHANGES_REQUESTED'},
            {'mergeable': 'CONFLICTING'},
            {'headRefOid': 'c' * 40},
            {'ci': '0✓/1✗/0…/0ERR/0SKIP/0UNKNOWN'},
            {'ci': '0✓/0✗/1…/0ERR/0SKIP/0UNKNOWN'},
        ]
        for interruption in interruptions:
            with self.subTest(interruption=interruption):
                observed = dict(initial, **interruption)
                observed['checked_at'] = '2026-11-04T00:00:00Z'
                changed = merge_observations({'o/r#1': initial}, {'o/r#1': observed})
                recovered = merge_observations(changed, {'o/r#1': dict(
                    initial, checked_at='2026-11-05T00:00:00Z')})
                self.assertGreaterEqual(recovered['o/r#1']['capacity_invalidated_at'],
                                        '2026-11-04T00:00:00Z')

    def test_only_updated_time_or_green_check_refresh_does_not_reset_wait(self):
        initial = {'state': 'OPEN', 'headRefOid': 'a' * 40,
                   'ci': 'no-checks', 'ci_head_oid': 'a' * 40, 'ci_fingerprint': 'b' * 64}
        observed = dict(initial, updatedAt='2026-11-05T01:00:00Z',
                        checked_at='2026-11-05T02:00:00Z')
        self.assertNotIn('capacity_invalidated_at', merge_observations(
            {'o/r#1': initial}, {'o/r#1': observed})['o/r#1'])


if __name__ == '__main__':
    unittest.main()
