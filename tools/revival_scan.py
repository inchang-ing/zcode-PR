#!/usr/bin/env python
"""Revival scan: find candidate issues whose claiming PR has gone stale.

Reads work/ledger/maintainer_candidates.json (written by maintainer_sweep
--json). For every open cross-referenced PR on a candidate issue, reports
PRs with no activity for >= --stale-days (default 10): the rich#4233
revival pattern — an issue is "claimed" only while its PR is alive.

Usage:
  python -S tools/revival_scan.py [--stale-days 10] [--json]
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from pipeline_state import read_json_object, atomic_write_json  # noqa: E402

GH = r"C:\Program Files\GitHub CLI\gh.exe"
CANDIDATES = ROOT / "work/ledger/maintainer_candidates.json"
DEFAULT_STALE_DAYS = 10


def claimant_prs(repo: str, num: int) -> list[dict]:
    r = subprocess.run(
        [GH, "api", f"repos/{repo}/issues/{num}/timeline", "--paginate", "--jq",
         '[.[] | select(.event=="cross-referenced") | .source.issue | '
         'select(.pull_request != null) | {n:.number, updated:.updated_at, state:.state}]'],
        capture_output=True, text=True, timeout=90)
    try:
        return json.loads(r.stdout) if r.stdout.strip() else []
    except ValueError:
        return []


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stale-days", type=int, default=DEFAULT_STALE_DAYS)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    now = datetime.now(timezone.utc)

    data = read_json_object(CANDIDATES)
    candidates = data.get("candidates", [])
    if not candidates:
        print(f"no candidates in {CANDIDATES}; run maintainer_sweep.py --json first")
        return

    revival = []
    for c in candidates:
        for pr in claimant_prs(c["repo"], c["num"]):
            if pr.get("state") != "open":
                continue
            updated = datetime.fromisoformat(pr["updated"].replace("Z", "+00:00"))
            stale_days = (now - updated).days
            if stale_days >= args.stale_days:
                revival.append({"issue": c["key"], "pr": pr["n"],
                                "stale_days": stale_days, "title": c["title"],
                                "url": c.get("url", "")})

    print(f"revival scan: {len(candidates)} candidates, {len(revival)} with "
          f"a claiming PR stale >= {args.stale_days}d")
    for x in sorted(revival, key=lambda x: -x["stale_days"]):
        print(f"REVIVAL {x['issue']} <- PR #{x['pr']} stale {x['stale_days']}d  {x['title'][:70]}")
    if args.json:
        out = ROOT / "work/ledger/revival_candidates.json"
        atomic_write_json(out, {"scanned_at": now.isoformat(),
                                "stale_days": args.stale_days,
                                "revival": revival})
        print(f"revival list written to {out}")


if __name__ == "__main__":
    main()
