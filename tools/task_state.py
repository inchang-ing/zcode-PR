"""One atomic task ledger, with read-only compatibility for the legacy files."""
from contextlib import contextmanager, ExitStack
from copy import deepcopy
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import math
import re
import sys
import time
import uuid

from pipeline_state import atomic_write_json, file_lock

SIGNALS = {'policy', 'collision', 'intent', 'reproduced', 'testable', 'small'}
STAGES = {'new', 'probe', 'fixing', 'submitted', 'stopped', 'deferred'}
ACTIONS = {'small_fix': 100, 'ci': 80, 'discussion': 20, 'wait': 0, 'done': 0}


def _path_identity(path):
    """Compare resolved Windows names consistently without changing I/O paths."""
    resolved = Path(path).resolve()
    if isinstance(resolved, PureWindowsPath):
        value = str(resolved)
        # Missing-path races in ntpath.realpath can retain an extended prefix.
        if value.upper().startswith('\\\\?\\UNC\\'):
            value = '\\\\' + value[8:]
        elif value.startswith('\\\\?\\') and re.match(r'[A-Za-z]:\\', value[4:]):
            value = value[4:]
        return PureWindowsPath(value)
    return resolved


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
    path = Path(path)
    root = path.parent.parent if path.parent.name == 'tools' else path.parent
    return TaskStore(root=root, _handled_path=path).handled


def _validate_handled(data):
    if not isinstance(data, dict):
        raise ValueError('处理记录必须是对象')
    result = {}
    for raw_key, entry in data.items():
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
    path = Path(path)
    root = path.parent.parent if path.parent.name == 'tools' else path.parent
    with TaskStore(root=root, _handled_path=path).transaction() as ledger:
        state = ledger['handled']
        for key in keys:
            previous = _validate_handled(state).get(key, {})
            history = list(previous.get('history', []))
            if previous:
                history.append({k: v for k, v in previous.items() if k != 'history'})
            for alias in [alias for alias in state if alias.lower() == key]:
                if state[alias] != previous:
                    history.append(deepcopy(state[alias]))
                del state[alias]
            state[key] = {**previous, 'at': datetime.now(timezone.utc).isoformat(),
                          'note': note, 'status': status, 'history': history}


def completion_reason(key, handled, issue, now):
    return _decision(task_key(key), handled, issue, None, now)['reason']


def effective_stage(key, handled, issue):
    return _decision(task_key(key), handled, issue, None, datetime.now(timezone.utc))['stage']


def issue_states(root):
    return load_queue_state(Path(root) / 'work_queue.json')['issues']


def load_queue_state(path):
    path = Path(path)
    return TaskStore(root=path.parent, _queue_path=path).queue


def _validate_queue(state):
    """Validate decision data identically for queue, inbox and execution readers."""
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

    require(isinstance(state, dict) and type(state.get('version')) is int
            and state['version'] == 1, '不支持的队列版本')
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
    """Snapshot reads and one lock/atomic replacement for all task mutations.

    Legacy sources are frozen after migration. Their locks and fingerprints reject
    old writers instead of silently merging an obsolete snapshot over new decisions.
    """
    ACTIVE = {'running', 'pr_opened', 'needs_fix', 'needs_verification'}
    TERMINAL = {'dropped', 'merged', 'closed'}
    RETRYABLE = {'pending', 'needs_repro', 'repro_failed', 'dry_run'}

    def __init__(self, path=None, *, root=None, _handled_path=None, _queue_path=None):
        if path is not None and root is not None:
            raise ValueError('Specify root or a legacy dispatched path, not both')
        self.root = Path(root if root is not None else Path(path).parent if path is not None
                         else Path(__file__).resolve().parents[1]).resolve()
        self.path = self.root / 'task_state.json'
        self.source_paths = {
            'dispatched': Path(path).resolve() if path is not None else self.root / 'dispatched.json',
            'handled': Path(_handled_path).resolve() if _handled_path else self.root / 'tools/inbox_handled.json',
            'queue': Path(_queue_path).resolve() if _queue_path else self.root / 'work_queue.json',
        }
        for source in self.source_paths.values():
            self._relative(source)
        self._reload()

    def _relative(self, path):
        identity = _path_identity(path)
        try:
            relative = identity.relative_to(_path_identity(self.root))
        except ValueError as exc:
            raise ValueError('Legacy source must remain inside the task root') from exc
        if not relative.parts or identity == _path_identity(self.path):
            raise ValueError('Invalid legacy source path')
        return relative.as_posix()

    @staticmethod
    def _bytes(path):
        try:
            return path.read_bytes()
        except FileNotFoundError:
            return None

    @staticmethod
    def _digest(raw):
        return None if raw is None else hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _parse(raw):
        result = {} if raw is None else json.loads(raw.decode('utf-8-sig'))
        if not isinstance(result, dict):
            raise ValueError('Task state must be a JSON object')
        return result

    def _sources(self, ledger):
        migration = ledger.get('migration')
        if not isinstance(migration, dict) or not isinstance(migration.get('sources'), dict):
            raise ValueError('Unified task state has no migration source fingerprints')
        sources = migration['sources']
        if set(sources) != {'dispatched', 'handled', 'queue'}:
            raise ValueError('Invalid migration source partitions')
        result = {}
        for section, entry in sources.items():
            if (not isinstance(entry, dict) or not isinstance(entry.get('path'), str)
                    or 'sha256' not in entry
                    or (entry['sha256'] is not None and
                        (not isinstance(entry['sha256'], str)
                         or not re.fullmatch('[0-9a-f]{64}', entry['sha256'])))):
                raise ValueError('Invalid migration fingerprint: ' + section)
            relative = Path(entry['path'])
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Invalid migration source path: ' + entry['path'])
            source = self.root / relative
            self._relative(source)
            result[section] = source
        if len({_path_identity(path) for path in result.values()}) != 3:
            raise ValueError('Migration sources must be different files')
        return result

    def _validate_ledger(self, ledger):
        if (not isinstance(ledger, dict) or type(ledger.get('version')) is not int
                or ledger['version'] != 1):
            raise ValueError('Unsupported unified task state version')
        if any(not isinstance(ledger.get(section), dict) for section in ('dispatched', 'handled', 'queue')):
            raise ValueError('Unified task state is missing a partition')
        self._normalize(ledger['dispatched'])
        _validate_handled(ledger['handled'])
        if not ledger['queue']:
            raise ValueError('Unified task queue is missing its schema')
        _validate_queue(ledger['queue'])
        self._sources(ledger)

    def _check_sources(self, ledger):
        for section, source in self._sources(ledger).items():
            if self._digest(self._bytes(source)) != ledger['migration']['sources'][section]['sha256']:
                raise RuntimeError(f'Legacy task source changed after migration: {source}. '
                                   'Stop the old writer and reconcile the old data; do not re-import over task_state.json.')

    def _install(self, ledger):
        self._state = deepcopy(ledger)
        self.data = self._normalize(deepcopy(ledger['dispatched']))
        self.handled = _validate_handled(deepcopy(ledger['handled']))
        self.queue = deepcopy(ledger['queue'])
        self.issues = self.queue['issues']
        self.handled_path = self.source_paths['handled']
        self.queue_path = self.source_paths['queue']

    def _reload(self):
        raw = self._bytes(self.path)
        if raw is not None:
            ledger = self._parse(raw)
            self._validate_ledger(ledger)
            self.source_paths = self._sources(ledger)
            self._check_sources(ledger)
            self._source_bytes = None
        else:
            self._source_bytes = {name: self._bytes(path) for name, path in self.source_paths.items()}
            ledger = {name: self._parse(value) for name, value in self._source_bytes.items()}
            ledger['queue'] = _validate_queue(ledger['queue'])
            ledger.update(version=1, migration={'sources': {
                name: {'path': self._relative(self.source_paths[name]), 'sha256': self._digest(value)}
                for name, value in self._source_bytes.items()}})
            self._validate_ledger(ledger)
        self._install(ledger)

    def _backup(self, ledger, original_bytes):
        directory = self.root / 'task_state.backups' / uuid.uuid4().hex
        directory.mkdir(parents=True)
        for section, raw in original_bytes.items():
            if raw is None:
                continue
            target = directory / 'legacy' / ledger['migration']['sources'][section]['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            if target.read_bytes() != raw:
                raise OSError('Legacy backup verification failed: ' + str(target))
        atomic_write_json(directory / 'manifest.json', {
            'version': 1, 'sources': ledger['migration']['sources'],
            'files': {name: 'legacy/' + ledger['migration']['sources'][name]['path']
                      if value is not None else None for name, value in original_bytes.items()},
            'created_at': datetime.now(timezone.utc).isoformat()})
        return directory.relative_to(self.root).as_posix()

    def _verify_migration(self, ledger):
        """Check the exact serialized representation before publishing authority."""
        restored = json.loads(json.dumps(ledger, ensure_ascii=False))
        self._validate_ledger(restored)
        now = datetime.now(timezone.utc)
        old_data, new_data = self._normalize(ledger['dispatched']), self._normalize(restored['dispatched'])
        old_handled, new_handled = _validate_handled(ledger['handled']), _validate_handled(restored['handled'])
        keys = set(old_data) | set(old_handled) | set(ledger['queue']['issues'])
        for key in keys:
            before = _decision(key, old_handled, ledger['queue']['issues'].get(key, {}), old_data.get(key), now)
            after = _decision(key, new_handled, restored['queue']['issues'].get(key, {}), new_data.get(key), now)
            if before != after:
                raise ValueError('Migration would change a task decision: ' + key)

    @contextmanager
    def transaction(self, *, _migrate=False):
        with file_lock(self.path):
            self._reload()
            with ExitStack() as locks:
                for section in ('dispatched', 'handled', 'queue'):
                    locks.enter_context(file_lock(self.source_paths[section]))
                self._reload()
                original = deepcopy(self._state)
                ledger = deepcopy(original)
                original_bytes = self._source_bytes
                try:
                    yield ledger
                    if ledger == original and not (_migrate and original_bytes is not None):
                        return
                    if ledger.get('migration') != original['migration']:
                        raise ValueError('Transactions cannot replace migration provenance')
                    self._validate_ledger(ledger)
                    if original_bytes is not None:
                        self._verify_migration(original)
                        ledger['migration']['backup'] = self._backup(original, original_bytes)
                        ledger['migration']['created_at'] = datetime.now(timezone.utc).isoformat()
                    self._check_sources(ledger)
                    atomic_write_json(self.path, ledger)
                    self._source_bytes = None
                    self._install(ledger)
                except BaseException:
                    self._install(original)
                    raise

    def migrate(self):
        """Explicitly migrate once. Existing unified data is never re-imported."""
        with self.transaction(_migrate=True):
            changed = self._source_bytes is not None
        return changed

    def export_legacy(self, destination):
        """Export latest partitions to a new directory; never roll back live data."""
        destination = Path(destination).resolve()
        with self.transaction() as ledger:
            identity, root_identity = _path_identity(destination), _path_identity(self.root)
            protected = [_path_identity(path) for path in (self.path, *self.source_paths.values())]
            if (destination.exists() or identity == root_identity or identity in root_identity.parents
                    or any(path.is_relative_to(identity) or identity.is_relative_to(path) for path in protected)):
                raise ValueError('Export destination must be a new directory, not the running task root')
            # A complete manifest is written last, so interrupted exports are identifiable.
            destination.mkdir(parents=True)
            files = {'dispatched': 'dispatched.json', 'handled': 'tools/inbox_handled.json',
                     'queue': 'work_queue.json'}
            for section, relative in files.items():
                atomic_write_json(destination / relative, ledger[section])
            atomic_write_json(destination / 'manifest.json', {
                'version': 1, 'exported_at': datetime.now(timezone.utc).isoformat(),
                'files': {name: {'path': relative, 'sha256': self._digest(self._bytes(destination / relative))}
                          for name, relative in files.items()}})
        return destination

    @staticmethod
    def _validate(data):
        if (not isinstance(data, dict)
                or any(not isinstance(key, str) or not isinstance(value, dict)
                       for key, value in data.items())):
            raise ValueError('Invalid dispatched state: each candidate must be an object')
        if any(entry.get('status') is not None and not isinstance(entry['status'], str)
               for entry in data.values()):
            raise ValueError('Invalid dispatched state: status must be a string')

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
        with self.transaction() as ledger:
            current = self.data.get(key.lower())
            if ((only_if_inactive and self.is_active(key))
                    or (expected is not None and current != expected)):
                return False
            entry = {**(current or {}), 'status': status, 'ts': time.time(), **extra}
            if 'retry_after' not in extra:
                entry.pop('retry_after', None)
            for alias in [alias for alias in ledger['dispatched'] if alias.lower() == key.lower()]:
                del ledger['dispatched'][alias]
            ledger['dispatched'][key.lower()] = entry
            return True


DispatchedStore = TaskStore


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    commands = parser.add_subparsers(dest='command', required=True)
    migrate = commands.add_parser('migrate', help='Back up legacy bytes and publish the unified ledger once')
    export = commands.add_parser('export-legacy', help='Export latest state into a new rollback directory')
    export.add_argument('destination', type=Path)
    for command in (migrate, export):
        command.add_argument('--root', type=Path, default=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        store = TaskStore(root=args.root)
        if args.command == 'migrate':
            print(('Migrated: ' if store.migrate() else 'Already migrated: ') + str(store.path))
        else:
            print('Exported: ' + str(store.export_legacy(args.destination)))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
