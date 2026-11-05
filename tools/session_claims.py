r"""Cross-session claim registry (multi-session collision guard).

Parallel automation sessions share E:\zcode-PR. Twice in one week (docling#5007,
psutil#3061) a session discovered mid-work that a sibling session was already
on the same target. Every session MUST consult this file before starting work
on an issue/PR and register the claim before the first push.

Usage (library):
    from session_claims import check, claim, release
    token = claim("kyegomez/swarms#2879")
    if token:  # Only a successful claim permits work.
        try:
            pass  # perform the work; renew(key, token) before the lease expires
        finally:
            release("kyegomez/swarms#2879", token)

Usage (CLI, for quick manual checks):
    python -S tools/session_claims.py --check kyegomez/swarms#2879
    python -S tools/session_claims.py --claim kyegomez/swarms#2879
    python -S tools/session_claims.py --release kyegomez/swarms#2879 --token TOKEN
    python -S tools/session_claims.py --renew kyegomez/swarms#2879 --token TOKEN
    python -S tools/session_claims.py --list

Claims auto-expire (default 48h) so a crashed session cannot block a key
forever; the expiry is recorded, not hidden.
"""
import argparse
import math
import sys
import time
import uuid
from pathlib import Path
from pipeline_state import atomic_write_json, file_lock, read_json_object
from task_state import task_key

ROOT = Path(__file__).resolve().parents[1]
CLAIMS_PATH = ROOT / "work" / "ledger" / "session_claims.json"
CLAIM_TTL_HOURS = 48


def _load(path=None) -> dict:
    result = {}
    for raw_key, entry in read_json_object(path or CLAIMS_PATH).items():
        key = task_key(raw_key)
        if (not isinstance(entry, dict) or not isinstance(entry.get('holder'), str)
                or type(entry.get('claimed_at')) not in (int, float)
                or not math.isfinite(entry['claimed_at'])
                or ('token' in entry and (not isinstance(entry['token'], str) or not entry['token']))):
            raise ValueError('Invalid claim: ' + key)
        if key in result and result[key] != entry:
            raise ValueError('Conflicting claim aliases: ' + key)
        result[key] = entry
    return result


def _save(data: dict, path=None) -> None:
    atomic_write_json(path or CLAIMS_PATH, data)


def _is_live(entry: dict, now: float) -> bool:
    claimed_at = entry.get("claimed_at", 0)
    return isinstance(claimed_at, (int, float)) and (
        now - claimed_at < CLAIM_TTL_HOURS * 3600
    )


def check(key: str, now: float | None = None, *, path=None) -> bool:
    """True when the key is free (no live claim). This read-only check does not reserve the task."""
    now = time.time() if now is None else now
    key = task_key(key)
    entry = _load(path).get(key)
    return entry is None or not _is_live(entry, now)


def claim(key: str, holder: str = "session", now: float | None = None, *, path=None) -> str | None:
    """Return an ownership token, or None while another live claim exists."""
    now = time.time() if now is None else now
    key = task_key(key)
    with file_lock(path or CLAIMS_PATH):
        data = _load(path)
        entry = data.get(key)
        if entry is not None and _is_live(entry, now):
            return None
        token = uuid.uuid4().hex
        data[key] = {"holder": holder, "token": token, "claimed_at": now,
                     "claimed_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))}
        _save(data, path)
        return token


def release(key: str, token: str, *, path=None) -> bool:
    """Only the recorded owner can release a lease, including after expiry."""
    key = task_key(key)
    with file_lock(path or CLAIMS_PATH):
        data = _load(path)
        if token and data.get(key, {}).get('token') == token:
            data.pop(key, None)
            _save(data, path)
            return True
        return False


def renew(key: str, token: str, now: float | None = None, *, path=None) -> bool:
    """Extend a live owned lease; an expired owner must acquire a new token."""
    now = time.time() if now is None else now
    key = task_key(key)
    with file_lock(path or CLAIMS_PATH):
        data = _load(path)
        entry = data.get(key, {})
        if not token or entry.get('token') != token or not _is_live(entry, now):
            return False
        entry.update(claimed_at=now, claimed_iso=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now)))
        _save(data, path)
        return True


def list_claims(now: float | None = None, *, path=None) -> dict:
    now = time.time() if now is None else now
    data = _load(path)
    return {k: v for k, v in data.items() if _is_live(v, now)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="cross-session claim registry")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", metavar="KEY")
    group.add_argument("--claim", metavar="KEY")
    group.add_argument("--release", metavar="KEY")
    group.add_argument("--renew", metavar="KEY")
    group.add_argument("--list", action="store_true")
    ap.add_argument('--token', help='ownership token returned by --claim')
    ap.add_argument('--holder', default='session')
    args = ap.parse_args(argv)
    if (args.release is not None or args.renew is not None) and not args.token:
        ap.error('--release/--renew requires the token returned by --claim')
    if args.check is not None:
        free = check(args.check)
        print(f"FREE {args.check}" if free else f"CLAIMED {args.check}")
        return 0 if free else 1
    if args.claim is not None:
        ok = claim(args.claim, args.holder)
        print(f"CLAIMED {args.claim} token={ok}" if ok else f"BUSY {args.claim}")
        return 0 if ok else 1
    if args.release is not None:
        ok = release(args.release, args.token)
        print(f"RELEASED {args.release}" if ok
              else f"NOT-HELD {args.release}")
        return 0 if ok else 1
    if args.renew is not None:
        ok = renew(args.renew, args.token)
        print(f"RENEWED {args.renew}" if ok else f"NOT-HELD {args.renew}")
        return 0 if ok else 1
    for key, entry in sorted(list_claims().items()):
        print(f"{key}  holder={entry.get('holder')}  at={entry.get('claimed_iso')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
