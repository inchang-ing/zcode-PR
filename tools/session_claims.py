"""Cross-session claim registry (multi-session collision guard).

Parallel automation sessions share E:\zcode-PR. Twice in one week (docling#5007,
psutil#3061) a session discovered mid-work that a sibling session was already
on the same target. Every session MUST consult this file before starting work
on an issue/PR and register the claim before the first push.

Usage (library):
    from session_claims import check, claim, release
    if not check("kyegomez/swarms#2879"):        # False = someone holds it
        claim("kyegomez/swarms#2879")

Usage (CLI, for quick manual checks):
    python -S tools/session_claims.py --check kyegomez/swarms#2879
    python -S tools/session_claims.py --claim kyegomez/swarms#2879
    python -S tools/session_claims.py --release kyegomez/swarms#2879
    python -S tools/session_claims.py --list

Claims auto-expire (default 48h) so a crashed session cannot block a key
forever; the expiry is recorded, not hidden.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAIMS_PATH = ROOT / "work" / "ledger" / "session_claims.json"
CLAIM_TTL_HOURS = 48


def _load() -> dict:
    try:
        data = json.loads(CLAIMS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(data: dict) -> None:
    CLAIMS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CLAIMS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _is_live(entry: dict, now: float) -> bool:
    claimed_at = entry.get("claimed_at", 0)
    return isinstance(claimed_at, (int, float)) and (
        now - claimed_at < CLAIM_TTL_HOURS * 3600
    )


def check(key: str, now: float | None = None) -> bool:
    """True when the key is free (no live claim). Expired claims are pruned."""
    now = time.time() if now is None else now
    data = _load()
    entry = data.get(key)
    if entry is None:
        return True
    if _is_live(entry, now):
        return False
    data.pop(key, None)
    _save(data)
    return True


def claim(key: str, holder: str = "session", now: float | None = None) -> bool:
    """Register a claim. Returns False when a live claim already exists."""
    now = time.time() if now is None else now
    data = _load()
    entry = data.get(key)
    if entry is not None and _is_live(entry, now):
        return False
    data[key] = {"holder": holder, "claimed_at": now,
                 "claimed_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))}
    _save(data)
    return True


def release(key: str) -> bool:
    data = _load()
    if key in data:
        data.pop(key, None)
        _save(data)
        return True
    return False


def list_claims(now: float | None = None) -> dict:
    now = time.time() if now is None else now
    data = _load()
    return {k: v for k, v in data.items() if _is_live(v, now)}


def main() -> int:
    ap = argparse.ArgumentParser(description="cross-session claim registry")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", metavar="KEY")
    group.add_argument("--claim", metavar="KEY")
    group.add_argument("--release", metavar="KEY")
    group.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.check is not None:
        free = check(args.check)
        print(f"FREE {args.check}" if free else f"CLAIMED {args.check}")
        return 0 if free else 1
    if args.claim is not None:
        ok = claim(args.claim)
        print(f"CLAIMED {args.claim}" if ok else f"BUSY {args.claim}")
        return 0 if ok else 1
    if args.release is not None:
        print(f"RELEASED {args.release}" if release(args.release)
              else f"NOT-HELD {args.release}")
        return 0
    for key, entry in sorted(list_claims().items()):
        print(f"{key}  holder={entry.get('holder')}  at={entry.get('claimed_iso')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
