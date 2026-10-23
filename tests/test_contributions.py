"""Evidence integrity, honest historical imports, and generated views; no network."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import contributions as c


class ContributionTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.record = c.new_record('owner/repo', 1, 'Regression', 2)

    def evidence(self, name='test.log', text='sample output'):
        path = self.root / 'contributions/evidence' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return dict(kind='local', ref=path.relative_to(self.root).as_posix(),
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest())

    def save(self):
        path = self.root / 'contributions/records' / (self.record['id'] + '.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.record), encoding='utf-8')
        return path

    def complete_verification(self):
        v = self.record['verification']
        v.update(status='recorded', case='test_regression')
        for phase, sha, code, result in [('before', 'a', 1, 'regression_failed'),
                                         ('after', 'b', 0, 'passed')]:
            v[phase] = dict(commit=sha*40, command='python -m pytest test.py',
                            environment='Python 3.12; lock hash example', test_case='test_regression',
                            ran_at='2026-10-18T12:00:00Z', exit_code=code, result=result,
                            log=self.evidence(phase+'.log', result))

    def test_history_cannot_become_verified_from_summary_alone(self):
        self.record['verification']['summary'] = 'Historical log says 2 failed then 2 passed'
        self.record['provenance'] = [self.evidence()]
        c.validate(self.record, self.root)
        report = c.render([self.record], {})
        self.assertIn('测试**：未核验', report)
        self.record['verification']['status'] = 'recorded'
        with self.assertRaises(ValueError):
            c.validate(self.record, self.root)

    def test_verified_policy_needs_source_and_time(self):
        self.record['policy'].update(status='verified', summary='Allowed')
        with self.assertRaises(ValueError):
            c.validate(self.record, self.root)
        self.record['policy'].update(checked_at='2026-10-18T12:00:00Z',
            sources=[dict(kind='url', ref='https://github.com/owner/repo/blob/main/CONTRIBUTING.md')])
        c.validate(self.record, self.root)

    def test_missing_section_fields_are_validation_errors(self):
        for section, field in [('policy', 'checked_at'), ('feedback', 'checked_at'),
                               ('verification', 'before'), ('verification', 'after')]:
            with self.subTest(section=section, field=field):
                record = deepcopy(self.record)
                del record[section][field]
                with self.assertRaises(ValueError):
                    c.validate(record, self.root)

    def test_complete_pair_and_tampered_log(self):
        self.complete_verification()
        c.validate(self.record, self.root)
        (self.root / self.record['verification']['before']['log']['ref']).write_text('changed')
        with self.assertRaisesRegex(ValueError, '摘要不匹配'):
            c.validate(self.record, self.root)

    def test_environment_failure_and_mismatched_pair_are_rejected(self):
        self.complete_verification()
        original = deepcopy(self.record)
        for phase, field, value in [('before', 'result', 'environment_error'),
                                   ('before', 'exit_code', 0), ('after', 'exit_code', 1),
                                   ('after', 'environment', 'different'),
                                   ('after', 'test_case', 'different'),
                                   ('after', 'commit', 'a'*40), ('before', 'commit', None)]:
            with self.subTest(field=field, value=value):
                record = deepcopy(original)
                record['verification'][phase][field] = value
                with self.assertRaises(ValueError):
                    c.validate(record, self.root)

    def test_unsafe_or_missing_evidence_and_bad_url_rejected(self):
        for ref in [dict(kind='local', ref='../outside', sha256='x'),
                    dict(kind='local', ref='contributions/evidence/missing.log', sha256='x'),
                    dict(kind='url', ref='javascript:alert(1)'),
                    dict(kind='url', ref='https://user:secret@example.org')]:
            with self.subTest(ref=ref):
                with self.assertRaises(ValueError):
                    c.validate_sources([ref], self.root)

    def test_https_sources_reject_credentials_and_invalid_authorities(self):
        for ref in ('https://:DEMO_PASSWORD@example.org/proof',
                    'https://user:DEMO_PASSWORD@example.org/proof', 'https://@example.org/proof',
                    'https:///missing-host', 'https://:443/proof', 'https://example.org:bad/proof',
                    'https://example.org:65536/proof', 'https://[broken/proof',
                    'https://example.org\\evil/proof', 'https://example.org/\x00proof',
                    'https://example.org/\nproof', 'http://example.org/proof'):
            with self.subTest(ref=ref):
                with self.assertRaises(ValueError) as error:
                    c.validate_sources([dict(kind='url', ref=ref)], self.root)
                self.assertNotIn('DEMO_PASSWORD', str(error.exception))
        for ref in ('https://github.com/a/b/pull/1#issuecomment-2',
                    'https://example.org:8443/proof?lang=zh&item=1',
                    'https://[2001:db8::1]:443/proof'):
            with self.subTest(ref=ref):
                c.validate_sources([dict(kind='url', ref=ref)], self.root)

    def test_credential_source_cannot_replace_existing_report(self):
        report = self.root / 'CONTRIBUTIONS.md'
        report.write_text('previous report', encoding='utf-8')
        self.record['provenance'] = [dict(kind='url', ref='https://:DEMO_PASSWORD@example.org/proof')]
        self.save()
        with self.assertRaises(ValueError):
            c.generate(self.root)
        self.assertEqual(report.read_text(encoding='utf-8'), 'previous report')

    def test_feedback_and_attribution_need_original_links(self):
        self.record['feedback']['items'] = [dict(kind='fact', summary='Needs tests',
            observed_at='2026-10-18T12:00:00Z', sources=[self.evidence()])]
        with self.assertRaises(ValueError):
            c.validate(self.record, self.root)
        link = dict(kind='url', ref='https://github.com/owner/repo/pull/2#issuecomment-1')
        self.record['feedback']['items'][0]['sources'] = [link]
        c.validate(self.record, self.root)
        self.record['outcome'].update(reason_category='tests', summary='Needs tests')
        with self.assertRaises(ValueError):
            c.validate(self.record, self.root)
        self.record['outcome']['sources'] = [link]
        c.validate(self.record, self.root)

    def test_duplicate_pr_and_wrong_filename_rejected(self):
        path = self.save()
        other = c.new_record('owner/repo', 3, 'Same PR', 2)
        path.with_name(other['id']+'.json').write_text(json.dumps(other))
        with self.assertRaisesRegex(ValueError, '重复 PR'):
            c.load_records(self.root)
        path.rename(path.with_name('wrong.json'))
        with self.assertRaises(ValueError):
            c.load_records(self.root)

    def test_generation_joins_cache_without_changing_record_or_state(self):
        path = self.save()
        cache = self.root / 'pr_state.json'
        cache.write_text(json.dumps({'owner/repo#2': {'state': 'MERGED', 'checked_at': '2026-10-18T12:00:00Z'}}))
        before = path.read_bytes(), cache.read_bytes()
        self.assertEqual(c.generate(self.root), 1)
        report = (self.root / 'CONTRIBUTIONS.md').read_text(encoding='utf-8')
        self.assertIn('MERGED / 2026-10-18T12:00:00Z', report)
        self.assertIn('| 1/1 |', report)
        self.assertEqual(before, (path.read_bytes(), cache.read_bytes()))

    def test_open_and_query_errors_excluded_from_terminal_denominator(self):
        for obs in ({'state': 'OPEN', 'checked_at': 'old'},
                    {'state': 'MERGED', 'checked_at': 'old', 'query_error': 'offline'},
                    {'state': None, 'query_error': 'initial failure'}, {}):
            report = c.render([self.record], {'owner/repo#2': obs})
            self.assertIn('不适用', report)
            self.assertNotIn('| 1/1 |', report)

    def test_bad_record_or_cache_preserves_previous_report(self):
        path = self.save()
        report = self.root / 'CONTRIBUTIONS.md'
        report.write_text('previous')
        path.write_text('{broken')
        with self.assertRaises(ValueError):
            c.generate(self.root)
        self.assertEqual(report.read_text(), 'previous')
        self.save()
        (self.root / 'pr_state.json').write_text('{broken')
        with self.assertRaises(ValueError):
            c.generate(self.root)
        self.assertEqual(report.read_text(), 'previous')

    def test_new_command_does_not_overwrite_existing(self):
        with patch.object(c, 'ROOT', self.root), redirect_stdout(io.StringIO()):
            c.main(['new', 'owner/repo', '1', 'First'])
            path = self.root / 'contributions/records' / (self.record['id']+'.json')
            before = path.read_bytes()
            with self.assertRaises(SystemExit) as exc:
                c.main(['new', 'owner/repo', '1', 'Overwrite'])
            self.assertEqual(exc.exception.code, 1)
            self.assertEqual(path.read_bytes(), before)

    def test_report_escapes_text_and_distinguishes_unknown_feedback(self):
        self.record['title'] = '<script>x</script> | title\nnew'
        report = c.render([self.record], {})
        self.assertNotIn('<script>', report)
        self.assertIn('\\| title<br>new', report)
        self.assertIn('不等于维护者没有回复', report)


if __name__ == '__main__':
    unittest.main()
