"""Repository admission: two ordinary PRs, at most one confirmed waiting exception."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from github_read import output, paginated_items
from pipeline_state import file_lock
from pr_monitor import ci_fingerprint, ci_summary
from pr_state import load_pr_state
from repository_policy import ACCOUNT
from task_state import TaskStore, task_key, timestamp

MAX_AGE = timedelta(hours=24)
WAIT = timedelta(days=7)
VIEW_FIELDS = 'number,state,author,url,headRefOid,isDraft,mergeable,reviewDecision,updatedAt,statusCheckRollup'


def _repo(repo):
    return task_key(repo + '#1').rsplit('#', 1)[0]


def _decision(status, reason, count=None):
    return {'allowed': status == 'ALLOW', 'reason': reason, 'count': count, 'status': status}


def _time(value):
    try:
        return timestamp(value)
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError('无效容量观测时间') from exc


def _source_key(url):
    if not isinstance(url, str):
        raise ValueError('缺少同一 PR 的 GitHub 证据 URL')
    parsed = urlsplit(url)
    match = re.fullmatch(r'/([\w.-]+/[\w.-]+)/(pull|issues)/([1-9]\d*)(?:/(?:files|commits))?/?', parsed.path, re.ASCII)
    if parsed.scheme != 'https' or parsed.netloc.lower() != 'github.com' or parsed.query or not match:
        raise ValueError('证据 URL 必须指向同一 GitHub PR/同号讨论')
    return task_key(match[1] + '#' + match[3])


def _records(store, records=None, *, fresh=False):
    implicit = records is None
    if records is None:
        if not fresh and hasattr(store, '_capacity_normalized_records'):
            return store._capacity_normalized_records
        if fresh or not hasattr(store, '_capacity_records'):
            store._capacity_records = load_pr_state(store.root / 'pr_state.json', ())
        records = store._capacity_records
    if not isinstance(records, dict):
        raise ValueError('PR 缓存必须是对象')
    result = {}
    for key, value in records.items():
        key = task_key(key)
        if not isinstance(value, dict) or value.get('state') not in {'OPEN', 'CLOSED', 'MERGED', None}:
            raise ValueError('PR 缓存记录损坏')
        if key in result and result[key] != value:
            raise ValueError('PR 缓存别名冲突')
        result[key] = value
    if implicit:
        store._capacity_normalized_records = result
    return result


def _known_problem(record):
    if record.get('reviewDecision') == 'CHANGES_REQUESTED':
        return '已有 PR 保留请求修改，需核验是否仍有未完成修改；目前不能自动释放'
    if record.get('mergeable') == 'CONFLICTING':
        return '已有 PR 存在冲突，需核验；目前不能自动释放'
    if isinstance(record.get('ci'), str) and any(int(n) for n in re.findall(r'(\d+)(?:✗|…|ERR|UNKNOWN)', record['ci'])):
        return '已有 PR 的 CI 失败/未完成/错误/未知，需核验原因；目前不能自动释放'
    return ''


def _binding(opened):
    return {key: {field: row[field] for field in ('headRefOid', 'human_fingerprint')}
            for key, row in opened.items()}


def _validate_snapshot(repo, snapshot):
    if (not isinstance(snapshot, dict) or type(snapshot.get('version')) is not int
            or snapshot['version'] != 1 or snapshot.get('repo') != repo
            or snapshot.get('author') != ACCOUNT.lower()
            or snapshot.get('status') not in {'ok', 'unknown'}
            or type(snapshot.get('complete')) is not bool
            or not isinstance(snapshot.get('open'), dict)):
        raise ValueError('容量快照结构损坏')
    _time(snapshot.get('started_at'))
    _time(snapshot.get('checked_at'))
    if snapshot['status'] == 'ok' and not snapshot['complete']:
        raise ValueError('容量快照缺少完整 OPEN 核验')
    for key, row in snapshot['open'].items():
        if (not isinstance(row, dict) or task_key(key) != key or key.rsplit('#', 1)[0] != repo
                or type(row.get('number')) is not int or key != f'{repo}#{row["number"]}'
                or row.get('author') != ACCOUNT.lower() or _source_key(row.get('url')) != key
                or '/pull/' not in row['url'].lower() or type(row.get('isDraft')) is not bool
                or not isinstance(row.get('headRefOid'), str) or not re.fullmatch('[0-9a-f]{40}', row['headRefOid'])):
            raise ValueError('容量快照的 PR 身份不完整')
        _time(row.get('updated_at'))
        if snapshot['status'] == 'ok' and len(snapshot['open']) < 3:
            if (type(row.get('ready')) is not bool or not isinstance(row.get('reason'), str)
                    or row.get('reviewDecision') not in {'-', 'APPROVED', 'REVIEW_REQUIRED', 'CHANGES_REQUESTED'}
                    or row.get('mergeable') not in {'MERGEABLE', 'CONFLICTING'}
                    or not isinstance(row.get('ci_fingerprint'), str)
                    or not re.fullmatch('[0-9a-f]{64}', row['ci_fingerprint'])
                    or not isinstance(row.get('ci'), str)
                    or (row['ci'] != 'no-checks' and not re.fullmatch(r'\d+✓/\d+✗/\d+…/\d+ERR/\d+SKIP/\d+UNKNOWN', row['ci']))):
                raise ValueError('容量快照的就绪核验不完整')
            _time(row.get('updatedAt'))
            problem = (row['isDraft'] or row['mergeable'] == 'CONFLICTING'
                       or row['reviewDecision'] == 'CHANGES_REQUESTED'
                       or any(int(n) for n in re.findall(r'(\d+)(?:✗|…|ERR|UNKNOWN)', row['ci'])))
            if row['ready'] == bool(problem):
                raise ValueError('容量快照的 ready 与实际核验字段矛盾')
            if len(snapshot['open']) == 2 and (not isinstance(row.get('human_fingerprint'), str)
                    or not re.fullmatch('[0-9a-f]{64}', row['human_fingerprint'])):
                raise ValueError('容量快照缺少完整人类活动指纹')


def _local_problem(keys, prs):
    for key in keys:
        action = prs.get(key, {}).get('action')
        if action in {'small_fix', 'ci', 'discussion'}:
            return f'{key} 仍有本地 {action} 待办；先通过 work_queue pr-action 核验/处理，不能自动释放'
    return ''


def _valid_wait(wait, opened, records, now, prs):
    if not isinstance(wait, dict) or wait.get('binding') != _binding(opened):
        return False
    since = _time(wait.get('since'))
    if since > now or not isinstance(wait.get('note'), str) or not wait['note'].strip():
        return False
    if not isinstance(wait.get('sources'), list) or {_source_key(url) for url in wait['sources']} != set(opened):
        return False
    for key in opened:
        marker = records.get(key, {}).get('capacity_invalidated_at')
        if marker is not None and (_time(marker) > since or _time(marker) > now):
            return False
        entry = prs.get(key, {})
        if any(event.get('action') in {'small_fix', 'ci', 'discussion'} and _time(event.get('at')) > since
               for event in [entry, *entry.get('events', [])]):
            return False
    return True


def _evaluate(snapshot, records, now, prs):
    opened = snapshot['open']
    count = len(opened) if snapshot['complete'] else None
    if count is not None and count >= 3:
        return _decision('HOLD', '同仓 OPEN 已达 3 个绝对上限，不按周累加名额', count)
    if snapshot.get('status') != 'ok':
        return _decision('UNKNOWN', snapshot.get('reason') or '容量核验不完整，需实时终检', count)
    problem = _local_problem(opened, prs)
    if problem:
        return _decision('HOLD', problem, count)
    if any(not row.get('ready') for row in opened.values()):
        return _decision('HOLD', next(row.get('reason') or '现有 PR 尚未就绪' for row in opened.values() if not row.get('ready')), count)
    if count < 2:
        return _decision('ALLOW', '同仓现有 OPEN 少于 2 个；提交前仍须实时核验', count)
    if not _valid_wait(snapshot.get('wait'), opened, records, now, prs):
        return _decision('HOLD', '两个 PR 均须确认等待维护者；缺少有效等待声明或绑定已变化', count)
    if now - _time(snapshot['wait']['since']) < WAIT:
        return _decision('HOLD', '两个 PR 的人工等待确认尚未连续满 7 天', count)
    return _decision('ALLOW', '两个 PR 均确认等待维护者满 7 天，仅允许第 3 个 OPEN', count)


def cached_capacity(repo, store, *, records=None, now=None):
    """Read-only prefilter. A missing full snapshot is never submission permission."""
    now = now or datetime.now(timezone.utc)
    try:
        repo = _repo(repo)
        if repo in getattr(store, '_capacity_save_errors', {}):
            return _decision('UNKNOWN', store._capacity_save_errors[repo])
        records = {k: v for k, v in _records(store, records).items() if k.rsplit('#', 1)[0] == repo}
        known = {k: v for k, v in records.items() if v.get('state') == 'OPEN'}
        count = len(known)
        if count >= 3:
            return _decision('HOLD', '已知同仓 OPEN 至少 3 个，达到绝对上限', count)
        for value in known.values():
            if _known_problem(value):
                return _decision('HOLD', _known_problem(value), count)
        local_keys = [key for key in store.queue['prs'] if key.rsplit('#', 1)[0] == repo
                      and records.get(key, {}).get('state') not in {'CLOSED', 'MERGED'}]
        problem = _local_problem(local_keys, store.queue['prs'])
        if problem:
            return _decision('HOLD', problem, count)
        if any(value.get('query_error') for value in records.values()):
            return _decision('UNKNOWN', 'PR 状态查询失败，需实时终检', count)
        snapshots = store.queue.get('capacity', {})
        if not isinstance(snapshots, dict):
            raise ValueError('容量快照损坏')
        snapshot = snapshots.get(repo)
        if snapshot is None:
            if count >= 2:
                return _decision('HOLD', '已知同仓 2 个 OPEN，缺少完整实时快照与等待证据', count)
            return _decision('ALLOW', '仅候选预筛：未有完整仓库快照，提交前必须实时终检', count)
        _validate_snapshot(repo, snapshot)
        opened = snapshot['open']
        if len(opened) >= 3:
            return _decision('HOLD', '完整快照同仓 OPEN 已达 3 个；需实时确认退出后才能新增', len(opened))
        age = now - _time(snapshot.get('checked_at'))
        if age < timedelta(0) or age > MAX_AGE:
            return _decision('UNKNOWN', '完整容量快照超过 24 小时或时间无效，需实时核验', len(opened))
        for key, observation in records.items():
            observed = observation.get('checked_at')
            if observed and _time(observed) > _time(snapshot['checked_at']):
                previous = opened.get(key)
                if observation.get('state') == 'OPEN' and previous is None:
                    return _decision('HOLD', '较新观测发现新增 OPEN，需重新核验全仓集合', len(opened))
                if previous is not None and (observation.get('state') != 'OPEN'
                        or observation.get('headRefOid') != previous.get('headRefOid')
                        or observation.get('updatedAt') != previous.get('updatedAt')):
                    return _decision('HOLD', '较新 PR 观测与等待快照不一致，需实时复核', len(opened))
        return _evaluate(snapshot, records, now, store.queue['prs'])
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        return _decision('UNKNOWN', str(exc))


def _open_prs(repo, query):
    rows = paginated_items(query(['api', f'repos/{repo}/pulls?state=open&per_page=100', '--paginate', '--slurp']))
    opened, seen = {}, set()
    for row in rows:
        number, user = row.get('number'), row.get('user')
        if (type(number) is not int or number <= 0 or number in seen or row.get('state') != 'open'
                or not isinstance(user, dict) or not isinstance(user.get('login'), str) or not user['login']):
            raise ValueError('OPEN 列表身份/分页记录缺失或重复')
        seen.add(number)
        if user['login'].lower() != ACCOUNT.lower():
            continue
        key = f'{repo}#{number}'
        url, head = row.get('html_url'), row.get('head')
        if (not isinstance(head, dict) or not isinstance(head.get('sha'), str)
                or not re.fullmatch('[0-9a-f]{40}', head['sha']) or type(row.get('draft')) is not bool
                or _source_key(url) != key or '/pull/' not in url.lower()):
            raise ValueError('OPEN 列表缺少当前 head/draft/同仓 PR URL')
        opened[key] = {'number': number, 'author': ACCOUNT.lower(), 'url': url,
                       'headRefOid': head['sha'], 'isDraft': row['draft'], 'updated_at': row.get('updated_at')}
        _time(row.get('updated_at'))
    return opened


def _human_fingerprint(repo, number, query):
    activity = []
    for kind, path in (('comment', f'issues/{number}/comments'),
                       ('review', f'pulls/{number}/reviews'), ('inline', f'pulls/{number}/comments')):
        items = paginated_items(query(['api', f'repos/{repo}/{path}?per_page=100', '--paginate', '--slurp']))
        seen = set()
        for item in items:
            user = item.get('user')
            if (not isinstance(user, dict) or not isinstance(user.get('login'), str)
                    or not user['login'] or user.get('type') not in {'User', 'Bot'}):
                raise ValueError('人类活动作者信息缺失')
            if user['login'].lower() == ACCOUNT.lower() or user['type'] == 'Bot' or user['login'].lower().endswith('[bot]'):
                continue
            if kind == 'review' and item.get('state') == 'PENDING':
                continue
            identity = item.get('id')
            if type(identity) is not int or identity <= 0 or identity in seen or not isinstance(item.get('body'), str):
                raise ValueError('人类活动内容或身份缺失/重复')
            seen.add(identity)
            at = item.get('submitted_at') if kind == 'review' else item.get('created_at')
            _time(at)
            updated = item.get('updated_at', at)
            _time(updated)
            if kind == 'review' and item.get('state') not in {'APPROVED', 'CHANGES_REQUESTED', 'COMMENTED', 'DISMISSED'}:
                raise ValueError('正式评审状态未知')
            activity.append({'kind': kind, 'id': identity, 'author': user['login'].lower(),
                             'at': at, 'updated_at': updated, 'body': item['body'], 'state': item.get('state')})
    encoded = sorted(json.dumps(value, sort_keys=True, ensure_ascii=False) for value in activity)
    return hashlib.sha256(json.dumps(encoded, ensure_ascii=False).encode('utf-8')).hexdigest()


def _observe(repo, row, query, *, activity):
    raw = query(['pr', 'view', str(row['number']), '--repo', repo, '--json', VIEW_FIELDS])
    view = json.loads(raw)
    if (not isinstance(view, dict) or type(view.get('number')) is not int or view['number'] != row['number']
            or view.get('state') != 'OPEN' or view.get('headRefOid') != row['headRefOid']
            or not isinstance(view.get('author'), dict) or view['author'].get('login', '').lower() != ACCOUNT.lower()
            or _source_key(view.get('url')) != f'{repo}#{row["number"]}'
            or '/pull/' not in view['url'].lower()
            or type(view.get('isDraft')) is not bool or 'reviewDecision' not in view
            or view['reviewDecision'] not in {None, '', 'APPROVED', 'REVIEW_REQUIRED', 'CHANGES_REQUESTED'}
            or view.get('mergeable') not in {'MERGEABLE', 'CONFLICTING', 'UNKNOWN'}):
        raise ValueError('PR 实时身份/head/评审/冲突信息缺失或变化')
    _time(view.get('updatedAt'))
    roll = view.get('statusCheckRollup')
    fingerprint, summary = ci_fingerprint(roll), ci_summary(roll)
    if fingerprint is None or view['mergeable'] == 'UNKNOWN':
        raise ValueError('CI/合并状态不完整，不能确认等待维护者')
    reason = ''
    if view['isDraft']:
        reason = '现有 PR 仍是 draft'
    elif view['mergeable'] == 'CONFLICTING':
        reason = '现有 PR 有合并冲突'
    elif view['reviewDecision'] == 'CHANGES_REQUESTED':
        reason = '现有 PR 保留请求修改，需核验；目前不能自动确认等待'
    elif summary != 'no-checks' and any(int(n) for n in re.findall(r'(\d+)(?:✗|…|ERR|UNKNOWN)', summary)):
        reason = 'CI 尚未全部通过，不能确认等待维护者'
    return {**row, 'updatedAt': view['updatedAt'], 'reviewDecision': view['reviewDecision'] or '-',
            'mergeable': view['mergeable'], 'isDraft': view['isDraft'], 'ci': summary,
            'ci_fingerprint': fingerprint, 'ready': not bool(reason), 'reason': reason,
            'human_fingerprint': _human_fingerprint(repo, row['number'], query) if activity else None}


def live_capacity(repo, store, *, query=None, now=None, confirm_wait=False, sources=(), note=''):
    """Fetch outside the lock, then save only if no newer request has committed."""
    started = datetime.now(timezone.utc).isoformat()
    now = now or datetime.now(timezone.utc)
    query = query or output
    try:
        repo = _repo(repo)
    except (ValueError, TypeError) as exc:
        return _decision('UNKNOWN', str(exc))
    snapshot = {'version': 1, 'repo': repo, 'author': ACCOUNT.lower(),
                'started_at': started, 'checked_at': now.isoformat(),
                'status': 'unknown', 'complete': False, 'open': {}}
    records = {}
    retry_activity = False
    try:
        first = _open_prs(repo, query)
        snapshot['open'] = first
        snapshot['complete'] = True
        if len(first) < 3:
            snapshot['open'] = {key: _observe(repo, row, query, activity=len(first) == 2)
                                for key, row in first.items()}
        second = _open_prs(repo, query)
        if second != first:
            without_activity = lambda rows: {key: {k: v for k, v in row.items() if k != 'updated_at'}
                                             for key, row in rows.items()}
            retry_activity = (without_activity(first) == without_activity(second) and len(first) == 2
                              and all(row.get('ready') for row in snapshot['open'].values()))
            raise ValueError('核验期间 OPEN 集合或 head 变化，请重试')
        snapshot['status'] = 'ok'
        if confirm_wait:
            if len(first) != 2 or any(not row.get('ready') for row in snapshot['open'].values()):
                raise ValueError('仅恰好两个均已就绪的 PR 可声明等待维护者')
            if not isinstance(note, str) or not note.strip() or {_source_key(url) for url in sources} != set(first):
                raise ValueError('需填写无我方待办说明，并为每个 PR 提供同 PR 证据 URL')
    except Exception as exc:
        snapshot.update(status='unknown', reason=str(exc) or 'GitHub 容量查询失败')
    try:
        with file_lock(store.root / 'pr_state.json'), store.transaction() as ledger:
            records = _records(store, fresh=True)
            _validate_snapshot(repo, snapshot)
            capacities = ledger['queue'].setdefault('capacity', {})
            if not isinstance(capacities, dict):
                raise ValueError('容量快照结构损坏')
            previous = capacities.get(repo, {})
            if previous and _time(previous.get('started_at')) >= _time(started):
                return _decision('UNKNOWN', '较新容量核验已经保存，请使用最新结果重新终检')
            prs = ledger['queue']['prs']
            if retry_activity and previous.get('wait') and not _local_problem(snapshot['open'], prs):
                # UNKNOWN cannot admit; the next complete read must recheck the old binding.
                snapshot['wait'] = previous['wait']
            ready = (snapshot['status'] == 'ok' and len(snapshot['open']) == 2
                     and all(row.get('ready') for row in snapshot['open'].values())
                     and not _local_problem(snapshot['open'], prs))
            if ready:
                old_wait = previous.get('wait')
                try:
                    valid = _valid_wait(old_wait, snapshot['open'], records, now, prs)
                except (ValueError, TypeError, KeyError):
                    valid = False
                if valid:
                    snapshot['wait'] = old_wait
                elif confirm_wait:
                    # A declaration starts now, never from PR age or inferred inactivity.
                    snapshot['wait'] = {'since': now.isoformat(), 'binding': _binding(snapshot['open']),
                                        'sources': list(sources), 'note': note.strip()}
            capacities[repo] = snapshot
        getattr(store, '_capacity_save_errors', {}).pop(repo, None)
        return _evaluate(snapshot, records, now, store.queue['prs'])
    except (OSError, ValueError, RuntimeError, TypeError, KeyError) as exc:
        reason = '容量结果未可靠保存: ' + str(exc)
        if not hasattr(store, '_capacity_save_errors'):
            store._capacity_save_errors = {}
        store._capacity_save_errors[repo] = reason
        return _decision('UNKNOWN', reason)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('check', 'confirm-wait'):
        sub = commands.add_parser(name)
        sub.add_argument('repo')
        sub.add_argument('--root', type=Path, default=argparse.SUPPRESS)
        if name == 'confirm-wait':
            sub.add_argument('--source', action='append', required=True)
            sub.add_argument('--note', required=True)
    args = parser.parse_args(argv)
    try:
        decision = live_capacity(args.repo, TaskStore(root=args.root), confirm_wait=args.command == 'confirm-wait',
                                 sources=getattr(args, 'source', ()), note=getattr(args, 'note', ''))
    except (OSError, ValueError, RuntimeError) as exc:
        decision = _decision('UNKNOWN', str(exc))
    print(json.dumps(decision, ensure_ascii=False))
    return {'ALLOW': 0, 'HOLD': 2, 'UNKNOWN': 1}[decision['status']]


if __name__ == '__main__':
    raise SystemExit(main())
