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
from pipeline_state import read_json_object  # noqa: E402
from repository_policy import ACCOUNT  # noqa: E402
from gh_checks import paginated_items  # noqa: E402

GH = r"C:\Program Files\GitHub CLI\gh.exe"
STATE = ROOT / "pr_state.json"
BOT_RE = re.compile(r"bot|dashboard", re.IGNORECASE)
SKIP_OWNERS = {"textualize"}  # handoff-only; no automated comments


def human_count(repo: str, num: str, kind: str, since: str) -> int:
    if kind == "comments":
        path = f"repos/{repo}/issues/{num}/comments?since={since}&per_page=100"
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
        if timestamp >= since and not BOT_RE.search(login) and login.lower() != ACCOUNT.lower():
            count += 1
    return count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=None,
                    help="ISO8601 lower bound (default: 12h ago)")
    args = ap.parse_args()
    since = args.since or (datetime.now(timezone.utc) - timedelta(hours=12)
                           ).strftime("%Y-%m-%dT%H:%M:%SZ")

    state = read_json_object(STATE)
    checked, actionable, unknown = 0, [], []
    for key, v in state.items():
        if v.get("state") != "OPEN" or v.get("query_error"):
            continue
        if key.lower().split("/", 1)[0] in SKIP_OWNERS:
            continue
        updated = v.get("updatedAt", "")
        if updated < since:
            continue
        repo, num = key.rsplit("#", 1)
        checked += 1
        try:
            nc = human_count(repo, num, "comments", since)
            nr = human_count(repo, num, "reviews", since)
        except ValueError as exc:
            unknown.append(f"UNKNOWN {key}: {exc}")
            continue
        if nc or nr:
            actionable.append(f"ACTION {key}: {nc} human comments, "
                              f"{nr} human reviews since {since}")

    print(f"review sweep: {checked} PRs updated since {since}, "
          f"{len(actionable)} with human activity, {len(unknown)} unknown")
    for line in actionable + unknown:
        print(line)
    return int(bool(unknown))


if __name__ == "__main__":
    sys.exit(main())
