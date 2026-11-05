"""Historical evidence failures cannot hide unrelated current work."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import hashlib
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import contributions as c
import work_queue as q


class QueueRecordIsolationTests(unittest.TestCase):
    def test_missing_historical_evidence_is_visible_without_blocking_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = c.new_record('old/repo', 1, 'Historical contribution', 2)
            record['provenance'] = [{'kind': 'local', 'ref': 'contributions/evidence/missing.log',
                                     'sha256': '0' * 64}]
            path = root / 'contributions/records' / (record['id'] + '.json')
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(record), encoding='utf-8')
            (root / 'round_candidates.json').write_text(json.dumps([
                dict(repo='new/repo', number=3, title='Bug: crash', url='', is_bug=True)
            ]), encoding='utf-8')
            rows = q.refresh(root)
            self.assertEqual(rows[0]['key'], 'new/repo#3')
            view = json.loads((root / 'work_queue_view.json').read_text(encoding='utf-8'))
            self.assertIn('missing.log', str(view['record_errors']))
            self.assertIn('贡献记录异常', (root / 'WORK_QUEUE.md').read_text(encoding='utf-8'))
            with self.assertRaises(ValueError):
                c.load_records(root)  # Submission checks remain strict.

    def test_queue_does_not_hash_test_logs_but_strict_checks_detect_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = root / 'contributions/evidence/old.log'
            log.parent.mkdir(parents=True)
            log.write_bytes(b'changed')
            record = c.new_record('old/repo', 1, 'History', 2)
            record['provenance'] = [dict(kind='local', ref='contributions/evidence/old.log',
                                         sha256=hashlib.sha256(b'original').hexdigest())]
            path = root / 'contributions/records' / (record['id'] + '.json')
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(record), encoding='utf-8')
            with patch.object(Path, 'read_bytes', side_effect=AssertionError('log read in view')):
                records, errors = c.load_queue_records(root)
            self.assertEqual(records, [record])
            self.assertEqual(errors, [])
            with self.assertRaisesRegex(ValueError, '摘要不匹配'):
                c.load_records(root)

    def test_corrupt_feedback_evidence_is_never_used_for_acknowledgement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = root / 'contributions/evidence/feedback.log'
            log.parent.mkdir(parents=True)
            log.write_bytes(b'changed')
            record = c.new_record('old/repo', 1, 'History', 2)
            record['feedback']['items'] = [dict(kind='interpretation', summary='Needs work',
                observed_at='2026-11-01T00:00:00Z', sources=[dict(kind='local',
                ref='contributions/evidence/feedback.log', sha256='0' * 64)])]
            path = root / 'contributions/records' / (record['id'] + '.json')
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(record), encoding='utf-8')
            records, errors = c.load_queue_records(root)
            self.assertEqual(records, [])
            self.assertEqual(errors[0]['pr_key'], 'old/repo#2')

    def test_bad_field_type_is_quarantined_and_unmapped_record_expires_wait(self):
        from pr_monitor import ci_fingerprint
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = c.new_record('old/repo', 1, 'History', 2)
            record['kind'] = []
            path = root / 'contributions/records' / (record['id'] + '.json')
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(record), encoding='utf-8')
            records, errors = c.load_queue_records(root)
            self.assertFalse(records)
            self.assertEqual(errors[0]['pr_key'], 'old/repo#2')
            path.write_text('{broken', encoding='utf-8')
            records, errors = c.load_queue_records(root)
            now = datetime.now(timezone.utc)
            pr = dict(state='OPEN', checked_at=now.isoformat(), updatedAt=now.isoformat(),
                      reviewDecision='-', headRefOid='a' * 40, ci_head_oid='a' * 40,
                      ci='no-checks', ci_fingerprint=ci_fingerprint([]), ci_checked_at=now.isoformat())
            state = {'issues': {}, 'prs': {'old/repo#2': {
                'action': 'wait', 'note': 'Previously checked', 'ack': q.observation_ack(pr, now)}}}
            self.assertEqual(q.pr_tasks({'old/repo#2': pr}, state, [], now), [])
            rows = q.pr_tasks({'old/repo#2': pr}, state, records, now, errors)
            self.assertEqual(len(rows), 1)
            self.assertFalse(rows[0]['ready'])


if __name__ == '__main__':
    unittest.main()
