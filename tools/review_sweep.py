#!/usr/bin/env python
"""Review sweep: find OPEN in-flight PRs with unresponded human activity.

Incremental over pr_state.json's updatedAt: only PRs touched since --since
(default: 12h ago) are checked, and only HUMAN comments/reviews count (bots
filtered). Prints UNKNOWN and exits 1 if any activity query is incomplete.

Usage:
  python -S tools/review_sweep.py [--since ISO8601]
"""
import argparse
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from pr_state import load_pr_state  # noqa: E402
from repository_policy import ACCOUNT  # noqa: E402
from gh_checks import paginated_items  # noqa: E402

GH = r"C:\Program Files\GitHub CLI\gh.exe"
STATE = ROOT / "pr_state.json"
BOT_RE = re.compile(r"bot|dashboard|assistant", re.IGNORECASE)
SKIP_OWNERS = {"textualize"}  # handoff-only; no automated comments


def parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("invalid or timezone-less timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone missing")
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise ValueError("invalid or timezone-less timestamp") from exc


def human_activity(repo: str, num: str, kind: str, since_time: datetime):
    """Return (count_since, latest_human).

    count_since = non-bot, non-self items at/after since_time (the ACTION
    signal). latest_human = the newest non-bot item overall as
    (login, datetime), ours included — when it is us and postdates the last
    human item, we already replied and the PR resolves without an ACTION.
    """
    if kind == "comments":
        path = f"repos/{repo}/issues/{num}/comments?per_page=100"
        key = "created_at"
    else:
        path = f"repos/{repo}/pulls/{num}/reviews?per_page=100"
        key = "submitted_at"
    try:
        r = subprocess.run([GH, "api", path, "--paginate", "--slurp"],
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
    except (OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
        raise ValueError("request failed or timed out") from exc
    items = paginated_items(r.stdout if r.returncode == 0 else None)
    count = 0
    latest: tuple[str, datetime, str | None] | None = None
    for item in items:
        # Pending reviews have no submission time and are not human feedback yet.
        timestamp = item.get(key)
        if kind == "reviews" and timestamp is None and item.get("state") == "PENDING":
            continue
        user = item.get("user")
        if (not isinstance(timestamp, str) or not isinstance(user, dict)
                or not isinstance(user.get("login"), str)):
            raise ValueError("activity timestamp or author missing")
        login = user["login"]
        if BOT_RE.search(login):
            continue
        ts = parse_timestamp(timestamp)
        state = item.get("state") if kind == "reviews" else None
        if latest is None or ts > latest[1]:
            latest = (login, ts, state)
        if (ts >= since_time and login.lower() != ACCOUNT.lower()):
            count += 1
    return count, latest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=None,
                    help="ISO8601 lower bound (default: 12h ago)")
    args = ap.parse_args()
    try:
        since_time = (parse_timestamp(args.since) if args.since is not None else
                      (datetime.now(timezone.utc) - timedelta(hours=12)).replace(microsecond=0))
    except ValueError:
        ap.error("--since must be an ISO8601 timestamp with a timezone")
    since = since_time.isoformat().replace("+00:00", "Z")

    try:
        state = load_pr_state(STATE, ())
    except (ValueError, OSError) as exc:
        print(f"UNKNOWN PR cache: {exc}")
        return 1
    checked, actionable, unknown, resolved = 0, [], [], []
    for key, v in state.items():
        if v.get("state") != "OPEN" or v.get("query_error"):
            continue
        if key.lower().split("/", 1)[0] in SKIP_OWNERS:
            continue
        try:
            updated = parse_timestamp(v.get("updatedAt"))
        except ValueError as exc:
            unknown.append(f"UNKNOWN {key}: updatedAt {exc}")
            continue
        if updated < since_time:
            continue
        repo, num = key.rsplit("#", 1)
        checked += 1
        try:
            nc, latest_c = human_activity(repo, num, "comments", since_time)
            nr, latest_r = human_activity(repo, num, "reviews", since_time)
        except ValueError as exc:
            unknown.append(f"UNKNOWN {key}: {exc}")
            continue
        if nc or nr:
            # Auto-resolve: our reply postdates the last human item (already
            # answered), or the latest human item is an APPROVED review —
            # nothing left to respond to; re-flagging either is noise.
            candidates = [x for x in (latest_c, latest_r) if x]
            latest = max(candidates, key=lambda x: x[1]) if candidates else None
            if latest and (latest[0].lower() == ACCOUNT.lower()
                           or latest[2] == "APPROVED"):
                resolved.append(key)
                continue
            actionable.append(f"ACTION {key}: {nc} human comments, "
                              f"{nr} human reviews since {since}")

    print(f"review sweep: {checked} PRs updated since {since}, "
          f"{len(actionable)} with human activity, "
          f"{len(resolved)} resolved (we replied last), "
          f"{len(unknown)} unknown")
    for line in actionable + unknown:
        print(line)
    return int(bool(unknown))


if __name__ == "__main__":
    sys.exit(main())
