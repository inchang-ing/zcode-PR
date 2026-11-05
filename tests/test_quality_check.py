"""Pre-submit evidence checks use disposable Git repos and no network."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import contributions as c
import quality_check as q


class QualityCheckTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.checkout = self.root / 'checkout'
        self.checkout.mkdir()
        self.git('init', '-q')
        self.git('config', 'commit.gpgsign', 'false')
        self.git('remote', 'add', 'upstream', 'https://github.com/owner/repo.git')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.org',
                 'commit', '-q', '--allow-empty', '-m', 'before')
        before = self.git('rev-parse', 'HEAD')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.org',
                 'commit', '-q', '--allow-empty', '-m', 'after')
        self.head = self.git('rev-parse', 'HEAD')
        self.now = datetime.now(timezone.utc)
        self.stamp = self.now.isoformat()
        self.record = c.new_record('owner/repo', 1, 'Fix regression', 2)
        for name in ('policy', 'collision'):
            self.record[name].update(status='verified', checked_at=self.stamp, summary='Checked',
                sources=[{'kind': 'url', 'ref': 'https://github.com/owner/repo/issues/1'}])
        self.record['feedback']['checked_at'] = self.stamp
        v = self.record['verification']
        v.update(status='recorded', case='test_regression')
        for phase, commit, code, result in [('before', before, 1, 'regression_failed'),
                                           ('after', self.head, 0, 'passed')]:
            v[phase] = dict(commit=commit, command='python -m pytest tests/test_regression.py',
                           scope='project', environment='Python 3.12 with project dependencies',
                           test_case=v['case'], ran_at=self.stamp, exit_code=code, result=result,
                           log=self.evidence(phase + '.log', result))
        self.body = self.root / 'body.md'
        self.body.write_bytes(b'Fixes #1.\nRegression test passed.\nWindows was not tested.\n')
        self.record['submission'] = dict(head=self.head,
            body=self.evidence('body.md', self.body.read_text()),
            claims=[dict(text='Regression test passed.', run='after')],
            limitations=['Windows was not tested.'], feedback=[])

    def git(self, *args):
        result = subprocess.run(['git', '-C', str(self.checkout), *args], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def evidence(self, name, text):
        path = self.root / 'contributions/evidence' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode('utf-8'))
        return dict(kind='local', ref=path.relative_to(self.root).as_posix(),
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest())

    def check(self, record=None):
        return q.check(record or self.record, self.checkout, self.body, self.root, self.now)

    def fact(self, summary='Add a boundary test'):
        return dict(kind='fact', summary=summary, observed_at=self.stamp,
                    sources=[dict(kind='url', ref='https://github.com/owner/repo/pull/2#issuecomment-1')])

    def test_complete_evidence_and_explicit_limitations_pass_without_mutation(self):
        before = deepcopy(self.record)
        self.assertEqual(self.check(), 1)
        self.assertEqual(self.record, before)

    def test_new_head_dirty_tree_and_wrong_repo_rejected(self):
        (self.checkout / 'untracked.py').write_text('pass')
        with self.assertRaisesRegex(ValueError, '工作区'):
            self.check()
        self.git('add', 'untracked.py')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.org', 'commit', '-q', '-m', 'revision')
        with self.assertRaisesRegex(ValueError, '不属于当前 HEAD'):
            self.check()
        self.git('remote', 'set-url', 'upstream', 'https://github.com/other/repo.git')
        with self.assertRaisesRegex(ValueError, '远端'):
            self.check()

    def test_stubs_missing_scope_and_future_or_reversed_runs_rejected(self):
        v = self.record['verification']
        for scope in ('stub', 'isolated', None, []):
            v['after']['scope'] = scope
            with self.assertRaises(ValueError):
                self.check()
        v['after']['scope'] = 'project'
        v['after']['ran_at'] = (self.now + timedelta(days=1)).isoformat()
        with self.assertRaisesRegex(ValueError, '未来'):
            self.check()
        v['after']['ran_at'] = (self.now - timedelta(hours=1)).isoformat()
        with self.assertRaisesRegex(ValueError, '顺序'):
            self.check()

    def test_stale_policy_collision_and_feedback_rejected(self):
        for name in ('policy', 'collision', 'feedback'):
            record = deepcopy(self.record)
            record[name]['checked_at'] = (self.now - timedelta(days=2)).isoformat()
            with self.assertRaisesRegex(ValueError, '24 小时'):
                self.check(record)

    def test_missing_baseline_commit_rejected(self):
        self.record['verification']['before']['commit'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'cat-file'):
            self.check()

    def test_shared_policy_cannot_be_overridden_by_verified_flag(self):
        for repo in ('ansible/ansible', 'python-markdown/markdown', 'mem0ai/mem0'):
            record = deepcopy(self.record)
            record.update(repo=repo, id=c.record_id(repo, 1))
            self.git('remote', 'set-url', 'upstream', f'https://github.com/{repo}.git')
            with self.assertRaisesRegex(ValueError, '共享政策'):
                self.check(record)

    def test_changed_body_tampered_logs_or_unbacked_claims_rejected(self):
        self.body.write_bytes(b'All tests passed.')
        with self.assertRaisesRegex(ValueError, '正文'):
            self.check()
        self.body.write_bytes((self.root / self.record['submission']['body']['ref']).read_bytes())
        self.record['submission']['claims'][0]['run'] = 'before'
        with self.assertRaisesRegex(ValueError, '缺少当前提交'):
            self.check()
        self.record['submission']['claims'][0]['run'] = 'after'
        (self.root / self.record['verification']['after']['log']['ref']).write_text('tampered')
        with self.assertRaisesRegex(ValueError, '摘要不匹配'):
            self.check()

    def test_feedback_requires_current_mapping_and_validation(self):
        fact = self.fact()
        self.record['feedback']['items'] = [fact]
        with self.assertRaisesRegex(ValueError, '逐项处理'):
            self.check()
        resolution = dict(fingerprint=q.fingerprint(fact), status='addressed',
                          summary='Added boundary regression', test_case='test_regression')
        self.record['submission']['feedback'] = [resolution]
        self.assertEqual(self.check(), 1)
        resolution['status'] = []
        with self.assertRaisesRegex(ValueError, '无效反馈处理状态'):
            self.check()
        resolution['status'] = 'unresolved'
        with self.assertRaisesRegex(ValueError, '未解决反馈'):
            self.check()
        resolution['status'] = 'not_actionable'
        resolution['summary'] = 'Informational only; no requested change'
        self.assertEqual(self.check(), 1)
        fact['summary'] = 'Different new request'
        with self.assertRaisesRegex(ValueError, '错配'):
            self.check()

    def test_prepare_resets_checks_preserves_history_and_does_not_attest_review(self):
        path = self.root / 'contributions/records' / (self.record['id'] + '.json')
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(self.record))
        q.prepare(path, self.checkout, self.body, self.root)
        record = json.loads(path.read_text())
        self.assertEqual(record['submission_history'], [self.record['submission']])
        self.assertEqual(record['submission']['claims'], [])
        with self.assertRaisesRegex(ValueError, '尚未登记'):
            self.check(record)

    def test_legacy_record_remains_valid_but_not_submission_ready(self):
        del self.record['submission']
        for phase in ('before', 'after'):
            del self.record['verification'][phase]['scope']
        c.validate(self.record, self.root)
        with self.assertRaisesRegex(ValueError, '缺少 submission'):
            self.check()

    def test_cli_reports_missing_evidence_with_nonzero_exit(self):
        with patch.object(q, 'ROOT', self.root), patch('sys.stderr', new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as exc:
                q.main(['check', self.record['id'], '--checkout', str(self.checkout), '--body', str(self.body)])
        self.assertEqual(exc.exception.code, 1)

    def documentation_record(self):
        self.record['kind'] = 'docs'
        v = self.record['verification']
        v.update(method='documentation', base_commit=v['before']['commit'], before=None,
                 case='docs_example', summary='Corrected an inaccurate example; ran the documented example.')
        (self.checkout / 'README.md').write_text('Updated example', encoding='utf-8')
        self.git('add', 'README.md')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.org', 'commit', '-q', '-m', 'docs')
        self.head = self.git('rev-parse', 'HEAD')
        v['after'].update(commit=self.head, scope='documentation', test_case='docs_example',
                          command='python -m doctest README.md')
        self.body.write_bytes(b'Documentation example passed.\nWindows was not tested.\n')
        self.record['submission'].update(head=self.head,
            body=self.evidence('body.md', self.body.read_text()),
            claims=[dict(text='Documentation example passed.', run='after')])

    def test_documentation_evidence_uses_current_head_without_fake_failed_test(self):
        self.documentation_record()
        self.assertEqual(self.check(), 1)
        self.assertIn('已记录文档验证证据', c.render([self.record], {}))
        self.record['verification']['after']['commit'] = self.record['verification']['base_commit']
        with self.assertRaisesRegex(ValueError, '不属于当前 HEAD'):
            self.check()

    def test_documentation_policy_exception_reaches_submission_check(self):
        self.documentation_record()
        self.record.update(repo='python/mypy', id=c.record_id('python/mypy', 1))
        self.git('remote', 'set-url', 'upstream', 'https://github.com/python/mypy.git')
        self.assertEqual(self.check(), 1)

    def test_documentation_exemption_rejects_code_and_other_contribution_kinds(self):
        self.documentation_record()
        self.record['kind'] = 'small_fix'
        with self.assertRaisesRegex(ValueError, '仅适用于 docs'):
            self.check()
        self.record['kind'] = 'docs'
        (self.checkout / 'library.py').write_text('value = 1', encoding='utf-8')
        self.git('add', 'library.py')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.org', 'commit', '-q', '-m', 'code')
        self.head = self.git('rev-parse', 'HEAD')
        self.record['submission']['head'] = self.head
        self.record['verification']['after']['commit'] = self.head
        with self.assertRaisesRegex(ValueError, '纯文档文件'):
            self.check()

    def test_documentation_exemption_rejects_dependency_text_and_renamed_code(self):
        (self.checkout / 'library.py').write_bytes(b'value = 1\n')
        self.git('add', 'library.py')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.org', 'commit', '-q', '-m', 'baseline')
        base = self.git('rev-parse', 'HEAD')
        self.documentation_record()
        self.record['verification']['base_commit'] = base
        self.git('mv', 'library.py', 'library.md')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.org', 'commit', '-q', '-m', 'rename')
        self.record['submission']['head'] = self.git('rev-parse', 'HEAD')
        self.record['verification']['after']['commit'] = self.record['submission']['head']
        with self.assertRaisesRegex(ValueError, '纯文档文件'):
            self.check()
        # Exclude the rename from this separate check of a .txt toolchain input.
        self.record['verification']['base_commit'] = self.record['submission']['head']
        (self.checkout / 'requirements.txt').write_bytes(b'example==1.0\n')
        self.git('add', 'requirements.txt')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.org', 'commit', '-q', '-m', 'dependency')
        self.record['submission']['head'] = self.git('rev-parse', 'HEAD')
        self.record['verification']['after']['commit'] = self.record['submission']['head']
        with self.assertRaisesRegex(ValueError, '纯文档文件'):
            self.check()


if __name__ == '__main__':
    unittest.main()
