#!/usr/bin/env python
"""Review sweep: find OPEN in-flight PRs with unresponded human activity.

Incremental over pr_state.json's updatedAt: only PRs touched since --since
(default: 12h ago) are checked, and only HUMAN comments/reviews count (bots
filtered). Exit code 0 always; prints actionable lines for the round log.

Usage:
  python -S tools/review_sweep.py [--since ISO8601]
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from pipeline_state import read_json_object  # noqa: E402
from repository_policy import ACCOUNT  # noqa: E402

GH = r"C:\Program Files\GitHub CLI\gh.exe"
STATE = ROOT / "pr_state.json"
BOT_RE = re.compile(r"bot|dashboard", re.IGNORECASE)
SKIP_OWNERS = {"textualize"}  # handoff-only; no automated comments


def gh_jq(path: str, jq: str) -> str:
    r = subprocess.run([GH, "api", path, "--jq", jq],
                       capture_output=True, text=True, timeout=60)
    return r.stdout.strip() if r.returncode == 0 else ""


def human_count(repo: str, num: str, kind: str, since: str) -> int:
    if kind == "comments":
        path = f"repos/{repo}/issues/{num}/comments?since={since}"
        key = "created_at"
    else:
        path = f"repos/{repo}/pulls/{num}/reviews"
        key = "submitted_at"
    out = gh_jq(path, f'[.[] | select(.{key} >= "{since}" and '
                      f'(.user.login | test("{BOT_RE.pattern}") | not) and '
                      f'.user.login != "{ACCOUNT}")] | length')
    try:
        return int(out)
    except ValueError:
        return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=None,
                    help="ISO8601 lower bound (default: 12h ago)")
    args = ap.parse_args()
    since = args.since or (datetime.now(timezone.utc) - timedelta(hours=12)
                           ).strftime("%Y-%m-%dT%H:%M:%SZ")

    state = read_json_object(STATE)
    checked, actionable = 0, []
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
        nc = human_count(repo, num, "comments", since)
        nr = human_count(repo, num, "reviews", since)
        if nc or nr:
            actionable.append(f"ACTION {key}: {nc} human comments, "
                              f"{nr} human reviews since {since}")

    print(f"review sweep: {checked} PRs updated since {since}, "
          f"{len(actionable)} with human activity")
    for line in actionable:
        print(line)


if __name__ == "__main__":
    main()
