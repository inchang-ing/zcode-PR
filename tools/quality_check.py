"""Offline pre-submit evidence checks for both initial PRs and revisions."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

from contributions import ROOT, require, validate, validate_sources
from pipeline_state import atomic_write_json, atomic_write_text, file_lock
from repository_policy import policy_reason


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


def fact_feedback(record):
    return {fingerprint(item): item for item in record['feedback']['items'] if item['kind'] == 'fact'}


def git(checkout, *args):
    result = subprocess.run(['git', '-C', str(checkout), *args], capture_output=True,
                            encoding='utf-8', errors='replace', timeout=30)
    require(result.returncode == 0, '无法读取 Git ' + args[0] + '；请检查工作目录和仓库配置')
    return result.stdout.strip()


def checkout_head(checkout, repo):
    head = git(checkout, 'rev-parse', 'HEAD')
    require(re.fullmatch(r'[0-9a-f]{40}', head), '无法读取完整提交 SHA')
    require(not git(checkout, 'status', '--porcelain=v1', '--untracked-files=all',
                    '--ignore-submodules=none'), '工作区存在未提交或未跟踪改动；先确定最终提交')
    remotes = git(checkout, 'config', '--get-regexp', r'^remote\..*\.url$')
    # Do not print remote URLs: a user's local config may contain credentials.
    repositories = set()
    for line in remotes.splitlines():
        url = line.split(None, 1)[-1]
        match = re.fullmatch(r'(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([\w.-]+/[\w.-]+?)(?:\.git)?/?', url)
        if match:
            repositories.add(match[1].lower())
    require(repo.lower() in repositories, 'checkout 的远端未包含记录仓库；核验 origin/upstream 后重试')
    return head


def recent(value, now):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.tzinfo is not None and timedelta(0) <= now - parsed <= timedelta(hours=24)
    except (AttributeError, ValueError):
        return False


def check(record, checkout, body, root=ROOT, now=None):
    """Check recorded assertions and artifacts, not prose semantics or human review."""
    now = now or datetime.now(timezone.utc)
    validate(record, root)
    problems = []

    def need(condition, message):
        if not condition:
            problems.append(message)

    head = checkout_head(checkout, record['repo'])
    for name in ('policy', 'collision'):
        section = record[name]
        need(section['status'] == 'verified' and recent(section['checked_at'], now),
             name + ' 未核验或超过 24 小时')
    policy = record['policy']
    labels, assignees = policy.get('labels', []), policy.get('assignees', [])
    require(all(isinstance(items, list) and all(isinstance(x, str) and x.strip() for x in items)
                for items in (labels, assignees)), 'policy.labels/assignees 必须是字符串列表')
    reason = policy_reason(record['repo'], labels, assignees)
    need(not reason, '共享政策门禁：' + reason)

    verification = record['verification']
    need(verification['status'] == 'recorded', '缺少修复前失败／修复后通过的证据')
    runs = [verification[phase] for phase in ('before', 'after')]
    for phase, run in zip(('before', 'after'), runs):
        need(isinstance(run, dict) and run.get('scope') == 'project',
             phase + ' 缺少真实项目入口验证；isolated/stub 仅为局部证据')
        if run:
            ran_at = datetime.fromisoformat(run['ran_at'].replace('Z', '+00:00'))
            need(ran_at <= now, phase + ' 测试时间在未来')
    if all(runs):
        git(checkout, 'cat-file', '-e', runs[0]['commit'] + '^{commit}')
        need(datetime.fromisoformat(runs[0]['ran_at'].replace('Z', '+00:00')) <=
             datetime.fromisoformat(runs[1]['ran_at'].replace('Z', '+00:00')), '前后测试时间顺序错误')
        need(runs[1]['commit'] == head, '修复后测试不属于当前 HEAD，修改后须重新验证')

    submission = record.get('submission')
    require(isinstance(submission, dict), '缺少 submission；先运行 quality_check.py prepare')
    need(submission.get('head') == head, '提交检查材料对应旧 HEAD；重新 prepare 并核验')
    archived_body = submission.get('body')
    require(isinstance(archived_body, dict) and archived_body.get('kind') == 'local', '缺少 PR 正文存档')
    validate_sources([archived_body], root)
    body_bytes = Path(body).read_bytes()
    need(hashlib.sha256(body_bytes).hexdigest() == archived_body['sha256'], '待提交正文与已登记正文不同；重新 prepare 并核验')
    body_text = body_bytes.decode('utf-8-sig')
    claims = submission.get('claims')
    require(isinstance(claims, list), 'claims 必须是列表')
    need(bool(claims), '尚未登记正文中的验证声明')
    for claim in claims:
        require(isinstance(claim, dict) and isinstance(claim.get('text'), str) and claim['text'].strip(), '验证声明缺少原文')
        need(claim['text'] in body_text, '正文缺少登记声明：' + claim['text'])
        need(claim.get('run') == 'after' and runs[1] is not None and
             runs[1]['exit_code'] == 0 and runs[1]['result'] == 'passed' and runs[1]['commit'] == head,
             '验证声明缺少当前提交通过的测试：' + claim['text'])
    limitations = submission.get('limitations')
    require(isinstance(limitations, list) and all(isinstance(x, str) and x.strip() for x in limitations), 'limitations 必须是非空文字的列表')
    for limitation in limitations:
        need(limitation in body_text, '正文未披露登记的未验证范围：' + limitation)

    facts = fact_feedback(record)
    if record['pr'] is not None or facts:
        need(recent(record['feedback']['checked_at'], now), '维护者反馈尚未刷新或超过 24 小时')
    resolutions = submission.get('feedback')
    require(isinstance(resolutions, list), 'feedback 处理结果必须是列表')
    seen = set()
    for resolution in resolutions:
        require(isinstance(resolution, dict), '反馈处理结果必须是对象')
        key = resolution.get('fingerprint')
        require(isinstance(key, str) and key in facts and key not in seen, '反馈处理结果错配、重复或对应旧反馈；重新 prepare')
        seen.add(key)
        status = resolution.get('status')
        require(isinstance(status, str) and status in {'addressed', 'unresolved', 'not_actionable'}, '无效反馈处理状态')
        summary = resolution.get('summary')
        need(isinstance(summary, str) and bool(summary.strip()), '反馈需说明改动、未解决原因或无需改动的理由')
        if status == 'addressed':
            need(resolution.get('test_case') == verification['case'] and bool(verification['case']),
                 '已处理反馈未关联当前回归用例')
        elif status == 'unresolved':
            need(False, '仍有未解决反馈：' + facts[key]['summary'])
    need(seen == set(facts), '存在尚未逐项处理的反馈')
    require(not problems, '\n'.join(problems))
    return len(claims)


def prepare(path, checkout, body, root=ROOT):
    """Capture the exact draft and seed unresolved fields; never attest a review."""
    with file_lock(root / 'contributions/records'):
        record = json.loads(path.read_text(encoding='utf-8-sig'))
        validate(record, root)
        require(path.stem == record['id'], '记录文件名与 ID 不匹配')
        head = checkout_head(checkout, record['repo'])
        content = Path(body).read_bytes()
        text = content.decode('utf-8-sig')
        require(text.strip(), 'PR 正文不能为空')
        # Archive canonical UTF-8 bytes; check compares exactly the supplied draft.
        require(content == text.encode('utf-8'), '正文请保存为不带 BOM 的 UTF-8')
        digest = hashlib.sha256(content).hexdigest()
        ref = f"contributions/evidence/{record['id']}--body-{digest}.md"
        atomic_write_text(root / ref, text)
        previous = record.get('submission')
        if previous:
            history = record.setdefault('submission_history', [])
            require(isinstance(previous, dict) and isinstance(history, list), '无效 submission 历史；保留记录并修正结构后重试')
            history.append(previous)
        record['submission'] = {
            'head': head, 'body': {'kind': 'local', 'ref': ref, 'sha256': digest},
            'claims': [], 'limitations': [],
            'feedback': [{'fingerprint': key, 'request': item['summary'],
                          'status': 'unresolved', 'summary': '', 'test_case': ''}
                         for key, item in fact_feedback(record).items()],
        }
        atomic_write_json(path, record)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'check'))
    parser.add_argument('record', help='贡献记录 ID（不含 .json）')
    parser.add_argument('--checkout', required=True, type=Path)
    parser.add_argument('--body', required=True, type=Path, help='实际准备提交的 UTF-8 正文文件')
    args = parser.parse_args(argv)
    try:
        require(re.fullmatch(r'[\w.-]+--[\w.-]+--issue-[1-9]\d*', args.record), '无效记录 ID')
        path = ROOT / 'contributions/records' / (args.record + '.json')
        if args.action == 'prepare':
            prepare(path, args.checkout, args.body)
            print(f'已保存正文并初始化未核验项：{path}；填写 submission 后运行 check')
        else:
            record = json.loads(path.read_text(encoding='utf-8-sig'))
            require(record.get('id') == args.record, '记录文件名与 ID 不匹配')
            count = check(record, args.checkout, args.body)
            print(f'EVIDENCE_OK: 当前提交证据一致，已核对 {count} 条登记声明；其余正文未自动审核。')
            print('未重新运行测试；scope 为录入的验证范围。不构成投稿授权或人工审阅。')
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        parser.exit(1, f'BLOCKED: {exc}\n')


if __name__ == '__main__':
    main()
