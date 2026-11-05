"""Sweep the FULL pipeline pool (~390 repos) for maintainer-filed, unfixed bug issues.

Filters: author is MEMBER/OWNER/COLLABORATOR, age 5-180 days, a bug-ish label,
repos not blocked by repository_policy, and shared cached capacity permits pre-screening.
Submission still requires a live capacity check.

Usage:
  python -S tools/maintainer_sweep.py                      # full pool
  python -S tools/maintainer_sweep.py --slice 0 --slices 3 # rotation (rate-limit friendly)
  python -S tools/maintainer_sweep.py --json               # candidates -> work/ledger/maintainer_candidates.json
"""
import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

from repository_policy import BLOCKED_OWNERS, BLOCKED_REPOS  # noqa: E402
from pipeline_state import atomic_write_json  # noqa: E402
from pr_state import load_pr_state  # noqa: E402
from task_state import TaskStore  # noqa: E402
from repo_capacity import cached_capacity  # noqa: E402

GH = "C:/Program Files/GitHub CLI/gh.exe"
NOW = datetime.now(timezone.utc)
BUG_LABELS = {"bug", "type:bug", "bug (upstream)", "type: bug", "confirmed",
              "defect", "crash", "regression"}
DISPOSITIONS_PATH = ROOT / "tools" / "dispositions.json"


def load_dispositions() -> dict:
    """issue -> {date, reason} registry; new faces lack an entry."""
    try:
        data = json.loads(DISPOSITIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in data.items() if not k.startswith("_") and isinstance(v, dict)}


def build_pool() -> list[str]:
    """Full 391-repo universe, deduped, minus blocked and full-in-flight repos."""
    sys.path.insert(0, str(ROOT / "tools"))
    from monitor_fresh import build_tiers

    always, rotating = build_tiers()
    pool = {}
    for repo in always + rotating:
        pool.setdefault(repo.lower(), repo)
    records = load_pr_state(ROOT / "pr_state.json", ())
    store = TaskStore(root=ROOT)
    now = datetime.now(timezone.utc)
    out = []
    for key, repo in pool.items():
        if key in BLOCKED_REPOS or key.split("/", 1)[0] in BLOCKED_OWNERS:
            continue
        if not cached_capacity(key, store, records=records, now=now)['allowed']:
            continue
        out.append(repo)
    return out


def gh_api(path: str):
    cmd = [GH, "api", path]
    for attempt in (1, 2):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            if r.returncode == 0:
                return json.loads(r.stdout)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
        if attempt == 1:
            import time
            time.sleep(5)
    return None


def sweep_repo(repo: str) -> dict:
    """Return {"ok": [...]} for a clean repo or {"skip": reason} on failure."""
    issues = gh_api(f"repos/{repo}/issues?state=open&sort=created&direction=desc&per_page=100")
    if not isinstance(issues, list):
        return {"skip": repo}
    hits = []
    for it in issues:
        if "pull_request" in it:
            continue
        created = datetime.fromisoformat(it["created_at"].replace("Z", "+00:00"))
        age_days = (NOW - created).days
        if not 5 <= age_days <= 180:
            continue
        labels = {l["name"] for l in it.get("labels", [])}
        if not labels & BUG_LABELS:
            continue
        if it.get("author_association") not in ("MEMBER", "OWNER", "COLLABORATOR"):
            continue
        hits.append({"key": f"{repo}#{it['number']}", "repo": repo, "num": it["number"],
                     "author_association": it["author_association"], "age_days": age_days,
                     "comments": it["comments"], "title": it["title"],
                     "url": it.get("html_url", "")})
    return {"ok": hits}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", type=int, default=0, help="slice index (0-based)")
    ap.add_argument("--slices", type=int, default=1, help="slice count for rotation")
    ap.add_argument("--json", action="store_true",
                    help="write the candidate list to work/ledger/maintainer_candidates.json")
    ap.add_argument("--show-skips", action="store_true")
    args = ap.parse_args()

    pool = build_pool()
    if args.slices > 1:
        pool = [r for i, r in enumerate(pool) if i % args.slices == args.slice % args.slices]
    print(f"sweeping {len(pool)} repos "
          f"(slice {args.slice}/{args.slices}, blocked/full-in-flight excluded)...", flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        for res in ex.map(sweep_repo, pool):
            results.append(res)
    candidates = [h for res in results for h in res.get("ok", [])]
    skips = [res["skip"] for res in results if "skip" in res]
    dispositions = load_dispositions()
    for h in sorted(candidates, key=lambda h: h["key"]):
        seen = dispositions.get(h["key"])
        tag = f" [DISPOSITIONED {seen['date']}: {seen['reason']}]" if seen else ""
        print(f"{h['key']} [{h['author_association']},{h['age_days']}d,"
              f"{h['comments']}c] {h['title'][:90]}{tag}")
    if args.show_skips:
        for s in sorted(skips):
            print(f"SKIP {s}")
    print(f"done: {len(pool) - len(skips)} repos ok, {len(skips)} failed, "
          f"{len(candidates)} candidates")
    if args.json:
        for h in candidates:
            seen = dispositions.get(h["key"])
            if seen:
                h["dispositioned"] = seen
        out = ROOT / "work/ledger/maintainer_candidates.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(out, {"swept_at": NOW.isoformat(),
                                "slice": f"{args.slice}/{args.slices}",
                                "candidates": candidates})
        print(f"candidates written to {out}")


if __name__ == "__main__":
    main()
