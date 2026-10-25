#!/usr/bin/env python
"""Revival scan: find candidate issues whose claiming PR has gone stale.

Reads work/ledger/maintainer_candidates.json (written by maintainer_sweep
--json). For every open cross-referenced PR on a candidate issue, reports
PRs with no activity for >= --stale-days (default 10): the rich#4233
revival pattern — an issue is "claimed" only while its PR is alive.
Incomplete lookups are reported as UNKNOWN and exit with status 1.

Usage:
  python -S tools/revival_scan.py [--stale-days 10] [--json]
"""
import argparse
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from pipeline_state import read_json_object, atomic_write_json  # noqa: E402
from gh_checks import paginated_items  # noqa: E402

GH = r"C:\Program Files\GitHub CLI\gh.exe"
CANDIDATES = ROOT / "work/ledger/maintainer_candidates.json"
DEFAULT_STALE_DAYS = 10


def pr_author_association(repo: str, num: int) -> str:
    try:
        r = subprocess.run([GH, "api", f"repos/{repo}/pulls/{num}", "--jq",
                            ".author_association"], capture_output=True, text=True, encoding="utf-8", timeout=60)
    except (OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
        raise ValueError("PR author lookup failed or timed out") from exc
    association = r.stdout.strip()
    if r.returncode or association not in {
        "MEMBER", "OWNER", "COLLABORATOR", "CONTRIBUTOR", "FIRST_TIMER",
        "FIRST_TIME_CONTRIBUTOR", "MANNEQUIN", "NONE",
    }:
        raise ValueError("PR author association unavailable")
    return association


def claimant_prs(repo: str, num: int) -> list[dict]:
    try:
        r = subprocess.run(
            [GH, "api", f"repos/{repo}/issues/{num}/timeline?per_page=100", "--paginate", "--slurp"],
            capture_output=True, text=True, encoding="utf-8", timeout=60)
    except (OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
        raise ValueError("timeline request failed or timed out") from exc
    prs = []
    for event in paginated_items(r.stdout if r.returncode == 0 else None):
        if not isinstance(event.get("event"), str):
            raise ValueError("timeline event missing")
        if event.get("event") != "cross-referenced":
            continue
        source = event.get("source")
        issue = source.get("issue") if isinstance(source, dict) else None
        if not isinstance(issue, dict):
            raise ValueError("timeline source issue missing")
        if issue.get("pull_request") is None:
            continue
        pr = issue["pull_request"]
        url = pr.get("url") if isinstance(pr, dict) else None
        identity = re.fullmatch(
            r"https://api\.github\.com/repos/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/pulls/([1-9][0-9]*)",
            url if isinstance(url, str) else "")
        if not identity or issue.get("number") != int(identity[2]):
            raise ValueError("timeline PR identity missing or invalid")
        if issue.get("state") not in ("open", "closed") or not isinstance(issue.get("updated_at"), str):
            raise ValueError("timeline PR state or timestamp missing")
        user = issue.get("user") or {}
        if not isinstance(user, dict):
            raise ValueError("timeline PR author invalid")
        prs.append({"n": int(identity[2]), "repo": identity[1],
                    "url": f"https://github.com/{identity[1]}/pull/{identity[2]}",
                    "updated": issue["updated_at"], "state": issue["state"],
                    "author": user.get("login", "?")})
    return prs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stale-days", type=int, default=DEFAULT_STALE_DAYS)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    now = datetime.now(timezone.utc)

    data = read_json_object(CANDIDATES)
    candidates = data.get("candidates", [])
    if not candidates:
        print(f"no candidates in {CANDIDATES}; run maintainer_sweep.py --json first")
        return 0

    revival, unknown = [], []
    for c in candidates:
        try:
            prs = claimant_prs(c["repo"], c["num"])
        except ValueError as exc:
            unknown.append({"issue": c["key"], "reason": str(exc)})
            continue
        for pr in prs:
            if pr.get("state") != "open":
                continue
            try:
                updated = datetime.fromisoformat(pr["updated"].replace("Z", "+00:00"))
                stale_days = (now - updated).days
                if stale_days < args.stale_days:
                    continue
                assoc = pr_author_association(pr["repo"], pr["n"])
            except (ValueError, TypeError) as exc:
                unknown.append({"issue": c["key"], "pr": pr["n"],
                                "pr_repo": pr["repo"], "reason": str(exc)})
                continue
            revival.append({"issue": c["key"], "pr": pr["n"],
                            "pr_repo": pr["repo"], "pr_url": pr.get("url", ""),
                            "stale_days": stale_days, "title": c["title"],
                            "pr_author": pr.get("author", "?"),
                            "pr_author_association": assoc,
                            "maintainer_owned": assoc in ("MEMBER", "OWNER", "COLLABORATOR"),
                            "url": c.get("url", "")})

    print(f"revival scan: {len(candidates)} candidates, {len(revival)} with "
          f"a claiming PR stale >= {args.stale_days}d, {len(unknown)} unknown")
    for x in sorted(revival, key=lambda x: -x["stale_days"]):
        marker = (" [MAINTAINER-OWNED - do not revive]"
                  if x.get("maintainer_owned") else "")
        pr_ref = f"#{x['pr']}" if x["pr_repo"] == x["issue"].rsplit("#", 1)[0] else f"{x['pr_repo']}#{x['pr']}"
        print(f"REVIVAL {x['issue']} <- PR {pr_ref} stale {x['stale_days']}d "
              f"@{x['pr_author']}({x.get('pr_author_association', '?')}){marker}  "
              f"{x['title'][:60]}")
    for x in unknown:
        print(f"UNKNOWN {x['issue']}: {x['reason']}")
    if args.json:
        out = ROOT / "work/ledger/revival_candidates.json"
        atomic_write_json(out, {"scanned_at": now.isoformat(),
                                "stale_days": args.stale_days,
                                "revival": revival, "unknown": unknown})
        print(f"revival list written to {out}")
    return int(bool(unknown))


if __name__ == "__main__":
    sys.exit(main())
