"""Sweep the FULL pipeline pool (~390 repos) for maintainer-filed, unfixed bug issues.

Filters: author is MEMBER/OWNER/COLLABORATOR, age 5-180 days, a bug-ish label,
repos not blocked by repository_policy, and the repo has < 2 open PRs from us.
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

from repository_policy import BLOCKED_OWNERS, BLOCKED_REPOS  # noqa: E402

GH = "C:/Program Files/GitHub CLI/gh.exe"
NOW = datetime.now(timezone.utc)
BUG_LABELS = {"bug", "type:bug", "bug (upstream)", "type: bug", "confirmed",
              "defect", "crash", "regression"}


def build_pool() -> list[str]:
    """Full 391-repo universe, deduped, minus blocked and full-in-flight repos."""
    sys.path.insert(0, str(ROOT / "tools"))
    from monitor_fresh import build_tiers

    always, rotating = build_tiers()
    pool = list(dict.fromkeys(always + rotating))

    # Skip repos where we already have 2 open PRs (same-repo cap).
    full = set()
    state_path = ROOT / "pr_state.json"
    if state_path.exists():
        counts: dict[str, int] = {}
        for key, v in json.loads(state_path.read_text(encoding="utf-8")).items():
            if v.get("state") == "OPEN":
                counts[key.rsplit("#", 1)[0].lower()] = counts.get(key.rsplit("#", 1)[0].lower(), 0) + 1
        full = {r for r, c in counts.items() if c >= 2}

    out = []
    for repo in pool:
        if repo in BLOCKED_REPOS or repo.split("/", 1)[0] in BLOCKED_OWNERS or repo in full:
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


def sweep_repo(repo: str) -> list[str]:
    issues = gh_api(f"repos/{repo}/issues?state=open&sort=created&direction=desc&per_page=100")
    if not isinstance(issues, list):
        return [f"SKIP {repo}"]
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
        hits.append(f"{repo}#{it['number']} [{it['author_association']},{age_days}d,"
                    f"{it['comments']}c] {it['title'][:90]}")
    return hits


def main() -> None:
    pool = build_pool()
    print(f"sweeping {len(pool)} repos (full pool, blocked/full-in-flight excluded)...")
    hits = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        for results in ex.map(sweep_repo, pool):
            hits.extend(results)
    skip = sum(1 for h in hits if h.startswith("SKIP"))
    for h in sorted(h for h in hits if not h.startswith("SKIP")):
        print(h)
    print(f"done: {len(pool) - skip} repos ok, {skip} failed, "
          f"{len(hits) - skip} candidates")


if __name__ == "__main__":
    main()
