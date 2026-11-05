"""Durable consumption receipts; task decisions remain owned by task_state."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from pipeline_state import atomic_write_json, file_lock, read_json_object
from task_state import task_key, timestamp


def discovery_version(item):
    version = item.get('source_version')
    if version:
        if not isinstance(version, str) or not re.fullmatch(r'[0-9a-f]{64}', version):
            raise ValueError('Invalid discovery version')
        return version
    # Ignore scan flags and observation times: rediscovery alone is not new evidence.
    payload = {name: item.get(name) for name in ('title', 'labels', 'kind', 'createdAt')}
    payload['key'] = task_key(f"{item['repo']}#{item['number']}")
    payload['labels'] = sorted(payload['labels'] or [])
    payload['kind'] = payload['kind'] or 'bug'
    payload['createdAt'] = payload['createdAt'] or ''
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def load_consumed(root):
    state = read_json_object(Path(root) / 'tools/discovery_state.json')
    if not state:
        return {}
    if state.get('version') != 1 or not isinstance(state.get('items'), dict):
        raise ValueError('Invalid discovery consumption state')
    for key, versions in state['items'].items():
        if task_key(key) != key or not isinstance(versions, dict):
            raise ValueError('Invalid consumed task')
        for version, checked_at in versions.items():
            if not re.fullmatch(r'[0-9a-f]{64}', version) or not isinstance(checked_at, str):
                raise ValueError('Invalid consumption receipt')
            timestamp(checked_at)
    return state['items']


def is_consumed(receipts, key, item, decision):
    checked_at = receipts.get(task_key(key), {}).get(discovery_version(item))
    if not checked_at:
        return False
    resume_at = decision.get('resume_at')
    return not resume_at or timestamp(resume_at) <= timestamp(checked_at)


def record_consumed(root, items, *, checked_at=None):
    if not items:
        return
    path = Path(root) / 'tools/discovery_state.json'
    with file_lock(path):
        receipts = load_consumed(root)
        now = checked_at or datetime.now(timezone.utc).isoformat()
        timestamp(now)
        for key, item in items.items():
            receipts.setdefault(task_key(key), {})[discovery_version(item)] = now
        atomic_write_json(path, {'version': 1, 'items': receipts})
