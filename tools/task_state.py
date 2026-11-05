"""Shared task identity and completion decisions for inbox and queue readers."""
from datetime import datetime, timezone
from pathlib import Path
import math
import re
import time

from pipeline_state import atomic_write_json, file_lock, read_json_object

SIGNALS = {'policy', 'collision', 'intent', 'reproduced', 'testable', 'small'}
STAGES = {'new', 'probe', 'fixing', 'submitted', 'stopped', 'deferred'}
ACTIONS = {'small_fix': 100, 'ci': 80, 'discussion': 20, 'wait': 0, 'done': 0}


def task_key(value):
    if not isinstance(value, str) or not re.fullmatch(r'[\w.-]+/[\w.-]+#[1-9]\d*', value, re.ASCII):
        raise ValueError('无效 owner/repo#编号')
    if any(part in {'.', '..'} for part in value.split('#')[0].split('/')):
        raise ValueError('无效仓库')
    return value.lower()


def timestamp(value):
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('处理时间必须包含时区')
    return stamp


def load_handled(path):
    result = {}
    for raw_key, entry in read_json_object(path).items():
        key = task_key(raw_key)
        if (not isinstance(entry, dict) or not isinstance(entry.get('at'), str)
                or not isinstance(entry.get('note'), str)
                or not isinstance(entry.get('status', 'done'), str)
                or entry.get('status', 'done') not in {'done', 'open'}
                or not isinstance(entry.get('history', []), list)):
            raise ValueError('无效处理记录: ' + key)
        at = timestamp(entry['at'])
        if key not in result or at > timestamp(result[key]['at']):
            result[key] = entry
        elif at == timestamp(result[key]['at']) and entry != result[key]:
            raise ValueError('同一时间的处理记录冲突: ' + key)
    return result


def record_handled(path, keys, note, status='done'):
    keys = [task_key(key) for key in keys]
    if not isinstance(note, str) or not note.strip() or status not in {'done', 'open'}:
        raise ValueError('需说明处理/重开理由')
    with file_lock(path):
        state = load_handled(path)
        for key in keys:
            previous = state.get(key, {})
            history = list(previous.get('history', []))
            if previous:
                history.append({k: v for k, v in previous.items() if k != 'history'})
            state[key] = {'at': datetime.now(timezone.utc).isoformat(), 'note': note,
                          'status': status, 'history': history}
        atomic_write_json(path, state)


def completion_reason(key, handled, issue, now):
    return _decision(task_key(key), handled, issue, None, now)['reason']


def effective_stage(key, handled, issue):
    return _decision(task_key(key), handled, issue, None, datetime.now(timezone.utc))['stage']


def issue_states(root):
    return load_queue_state(Path(root) / 'work_queue.json')['issues']


def load_queue_state(path):
    """Validate decision data identically for queue, inbox and execution readers."""
    state = read_json_object(path)
    if not state:
        return {'version': 1, 'issues': {}, 'prs': {}}

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    def valid_time(value):
        try:
            return timestamp(value)
        except (AttributeError, TypeError, ValueError):
            return None

    require(state.get('version') == 1, '不支持的队列版本')
    for section in ('issues', 'prs'):
        require(isinstance(state.get(section), dict), '队列缺少对象: ' + section)
        for key, entry in state[section].items():
            require(task_key(key) == key and isinstance(entry, dict), '无效队列记录')
            require(isinstance(entry.get('events'), list), '缺少事件列表')
            for event in entry['events']:
                require(isinstance(event, dict) and valid_time(event.get('at')), '无效事件时间')
                require(type(event.get('minutes')) is int and event['minutes'] >= 0, '无效工时')
                if section == 'issues' and event.get('command') == 'stage':
                    require(isinstance(event.get('stage'), str) and event['stage'] in STAGES, '无效事件阶段')
            if section == 'issues':
                require(isinstance(entry.get('stage'), str) and entry['stage'] in STAGES, '无效处理阶段')
                if entry.get('retry_at') is not None:
                    require(valid_time(entry['retry_at']), '无效复查时间')
                require(isinstance(entry.get('signals'), dict), '无效核验信息')
                for name, signal in entry['signals'].items():
                    require(name in SIGNALS and isinstance(signal, dict), '无效信号')
                    require(type(signal.get('value')) is bool and valid_time(signal.get('at')), '无效信号值')
            else:
                require(isinstance(entry.get('action'), str) and entry['action'] in ACTIONS
                        and valid_time(entry.get('at')), '无效 PR 待办')
    return state


def _decision(key, handled, issue, dispatch, now):
    """Reduce legacy records without migrating them; scans cannot undo decisions."""
    oldest = datetime.min.replace(tzinfo=timezone.utc)
    stage = issue.get('stage', 'new')
    blocked = stage in {'stopped', 'submitted'}
    if stage == 'deferred':
        blocked = not issue.get('retry_at') or timestamp(issue['retry_at']) > now
    latest, reason, resume_at = oldest, '队列已处理' if blocked else '', None
    events = []
    disposition = handled.get(key, {})
    if disposition:
        events.append((timestamp(disposition['at']), disposition.get('status', 'done') == 'done',
                       'new', disposition.get('note') or '已处理'))
    for event in issue.get('events', []):
        if event.get('command') == 'stage':
            event_stage = event.get('stage')
            closed = event_stage in {'stopped', 'submitted'}
            if event_stage == 'deferred':
                closed = not issue.get('retry_at') or timestamp(issue['retry_at']) > now
            events.append((timestamp(event['at']), closed, event_stage,
                           event.get('note') or '队列已处理'))
    dispatch = dispatch or {}
    status = dispatch.get('status', 'none')
    if (status in TaskStore.TERMINAL | {'pending', 'deferred'}
            or (dispatch.get('retry_after') is not None and TaskStore._entry_active(dispatch, now))):
        stamp = dispatch.get('ts', 0)
        try:
            at = datetime.fromtimestamp(float(stamp), timezone.utc)
        except (TypeError, ValueError, OverflowError, OSError):
            at = oldest
        events.append((at, TaskStore._entry_active(dispatch, now),
                       'deferred' if status == 'deferred' else 'new',
                       dispatch.get('reason') or '已派发: ' + status))
    for at, closed, event_stage, note in events:
        # Ties retain a closed decision. An executing task is protected separately below.
        if at > latest or (at == latest and closed):
            latest, blocked, stage, reason = at, closed, event_stage, note if closed else ''
    resumes = [timestamp(event['at']) for event in issue.get('events', [])
               if event.get('command') == 'stage' and event.get('stage') not in {'stopped', 'submitted'}]
    if disposition.get('status') == 'open':
        resumes.append(timestamp(disposition['at']))
    if status == 'pending' and events:
        resumes.append(events[-1][0])
    if resumes:
        resume_at = max(resumes).isoformat()
    if dispatch and (status in TaskStore.ACTIVE or status not in TaskStore.ACTIVE | TaskStore.TERMINAL | TaskStore.RETRYABLE | {'deferred'}):
        blocked, reason = True, '已派发: ' + str(status)
    return {'blocked': blocked, 'reason': reason, 'stage': stage,
            'status': status, 'resume_at': resume_at}


class TaskStore:
    """One decision boundary over dispatch, inbox disposition and queue stages.

    Reads are snapshots; acquiring execution rechecks all records under their locks.
    Existing JSON formats remain readable and are only written by their own commands.
    """
    ACTIVE = {'running', 'pr_opened', 'needs_fix', 'needs_verification'}
    TERMINAL = {'dropped', 'merged', 'closed'}
    RETRYABLE = {'pending', 'needs_repro', 'repro_failed', 'dry_run'}

    def __init__(self, path=None):
        self.path = Path(path) if path is not None else Path(__file__).resolve().parents[1] / 'dispatched.json'
        self.root = self.path.parent
        self.handled_path = self.root / 'tools/inbox_handled.json'
        self.queue_path = self.root / 'work_queue.json'
        self._reload()

    def _reload(self):
        self.data = self._normalize(read_json_object(self.path))
        self.handled = load_handled(self.handled_path)
        self.issues = issue_states(self.root)

    @staticmethod
    def _validate(data):
        if any(not isinstance(value, dict) for value in data.values()):
            raise ValueError('Invalid dispatched state: each candidate must be an object')

    @classmethod
    def _normalize(cls, data):
        cls._validate(data)
        normalized, priorities = {}, {}
        for key, entry in data.items():
            key = key.lower()
            status = entry.get('status')
            # Preserve conservative legacy alias resolution, especially in-flight work.
            rank = (3 if status in cls.ACTIVE else
                    2 if status not in cls.RETRYABLE | {'deferred'} else int(cls._entry_active(entry)))
            stamp = entry.get('ts', 0)
            if not isinstance(stamp, (int, float)) or not math.isfinite(stamp):
                stamp = 0
            priority = (rank, stamp)
            if key not in normalized or priority > priorities[key]:
                normalized[key], priorities[key] = entry, priority
        return normalized

    @classmethod
    def _entry_active(cls, entry, now=None):
        if entry is None:
            return False
        status = entry.get('status')
        if status in cls.ACTIVE | cls.TERMINAL or status not in cls.RETRYABLE | {'deferred'}:
            return True
        retry_after = entry.get('retry_after')
        if retry_after is not None:
            try:
                if isinstance(retry_after, str):
                    retry_after = timestamp(retry_after).timestamp()
                retry_after = float(retry_after)
                return not math.isfinite(retry_after) or retry_after > (now.timestamp() if now else time.time())
            except (TypeError, ValueError, OverflowError):
                return True
        return status not in cls.RETRYABLE

    def decision(self, key, now=None, *, handled=None, issue=None):
        key = key.lower()
        return _decision(key, self.handled if handled is None else handled,
                         self.issues.get(key, {}) if issue is None else issue,
                         self.data.get(key), now or datetime.now(timezone.utc))

    def is_active(self, key):
        return self.decision(key)['blocked']

    def status_of(self, key):
        return self.data.get(key.lower(), {}).get('status', 'none')

    def repo_inflight(self, repo):
        return any(key.startswith(repo.lower() + '#') and entry.get('status') in self.ACTIVE
                   for key, entry in self.data.items())

    def mark(self, key, status, *, only_if_inactive=False, expected=None, **extra):
        if status not in self.ACTIVE | self.TERMINAL | self.RETRYABLE | {'deferred'}:
            raise ValueError(f'Unknown candidate status: {status}')
        # Queue refresh only takes the queue lock and never waits for the dispatch lock.
        with file_lock(self.path), file_lock(self.handled_path), file_lock(self.queue_path):
            self._reload()
            current = self.data.get(key.lower())
            if ((only_if_inactive and self.is_active(key))
                    or (expected is not None and current != expected)):
                return False
            entry = {**(current or {}), 'status': status, 'ts': time.time(), **extra}
            if 'retry_after' not in extra:
                entry.pop('retry_after', None)
            self.data[key.lower()] = entry
            atomic_write_json(self.path, self.data)
            return True


DispatchedStore = TaskStore
