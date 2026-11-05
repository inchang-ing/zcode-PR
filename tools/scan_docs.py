"""Scan the watch pool for documentation / low-risk small-fix candidates.

Different track from scan_candidates.py (which hunts fresh bug reports):
merges are less contested here, so the filter is about eligibility, not speed.
Output: work/ledger/docs_candidates.json
"""
import json
import subprocess
import sys
import time
from pathlib import Path
from repository_pools import load_quality_pool, normalize_repos
from claim_rules import SOFT, NOT_READY, FIXED_IN_PR
from candidate_rules import Candidate, contribution_kind, enqueue_candidates
from pipeline_state import atomic_write_json, file_lock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import repository_policy as pol  # noqa: E402

GH = r"C:\Program Files\GitHub CLI\gh.exe" if Path(r"C:\Program Files\GitHub CLI\gh.exe").exists() else "gh"
OUT = ROOT / "work" / "ledger" / "docs_candidates.json"

LABEL_SETS = [
    ("documentation",),
    ("docs",),
    ("good first issue",),
]


def gh_json(args, retries=2):
    for i in range(retries + 1):
        try:
            r = subprocess.run([GH, "api"] + args, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=90)
        except subprocess.TimeoutExpired:
            if i == retries:
                return None, "timeout"
            time.sleep(3)
            continue
        if r.returncode == 0:
            try:
                return json.loads(r.stdout), None
            except json.JSONDecodeError:
                return None, "bad json"
        low = (r.stderr or "") + (r.stdout or "")
        if "rate limit" in low.lower() or "403" in low:
            return None, "rate-limited"
        if i == retries:
            return None, low.strip()[:160]
        time.sleep(3)
    return None, "exhausted"


def load_repos():
    pool = load_quality_pool(ROOT / "tools" / "quality_repos.json")
    blocked = set(pool["blocked"]["repos"])
    return [item["repo"] for item in pool["watch"]
            if item["repo"] not in blocked and not pol.policy_reason(item["repo"], kind="docs")]


def interesting(issue):
    """Cheap local prefilter before spending a timeline call."""
    if issue.get("pull_request"):
        return False, "is-pr"
    if issue.get("assignees"):
        return False, "assigned"
    if (issue.get("comments") or 0) > 12:
        return False, "hot-thread"
    labels = [l["name"].lower() for l in issue.get("labels", [])]
    for bad in ("in progress", "in-progress", "wontfix", "duplicate", "invalid",
                "needs design", "stale", "on hold", "blocked"):
        if bad in labels:
            return False, "label:" + bad
    body = issue.get("body") or ""
    if SOFT.search(body) or NOT_READY.search(body):
        return False, "claimed"
    if FIXED_IN_PR.search(body):
        return False, "already-fixed"
    return True, ""


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    extra = sys.argv[2].split(",") if len(sys.argv) > 2 and sys.argv[2] else []
    if extra:
        repos = normalize_repos(extra)
    else:
        repos = load_repos()[:limit]
    found, skipped = [], []
    for repo in repos:
        got_any = False
        for labels in LABEL_SETS:
            q = "labels={}&state=open&sort=updated&direction=desc&per_page=12".format(
                ",".join(l.replace(" ", "+") for l in labels))
            data, err = gh_json([f"repos/{repo}/issues?{q}"])
            if err:
                skipped.append({"repo": repo, "labels": labels[0], "err": err})
                if err == "rate-limited":
                    print("!! rate limited, stopping", flush=True)
                    dump(found, skipped, repos)
                    return 1
                continue
            for it in data or []:
                ok, why = interesting(it)
                labels = [label["name"] for label in it.get("labels", [])]
                kind = contribution_kind(labels)
                reason = pol.policy_reason(repo, labels,
                    [user["login"] for user in it.get("assignees", [])], kind=kind)
                if reason:
                    ok, why = False, reason
                rec = {
                    "repo": repo,
                    "number": it["number"],
                    "title": it["title"],
                    "labels": labels,
                    "kind": kind,
                    "updated": it.get("updated_at"),
                    "comments": it.get("comments"),
                    "url": it["html_url"],
                }
                if ok:
                    found.append(rec)
                    got_any = True
                else:
                    skipped.append(dict(rec, why=why))
        print(f"{repo}: {'+' + str(len([f for f in found if f['repo'] == repo])) if got_any else '0'}", flush=True)
        time.sleep(0.4)
    dump(found, skipped, repos)
    return int(any("err" in item for item in skipped))


def dump(found, skipped, repos):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {"scanned": len(repos), "repos": repos,
               "candidates": found, "skipped": skipped,
               "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with file_lock(OUT):
        atomic_write_json(OUT, payload)
    enqueue_candidates([Candidate(item['repo'], item['number'], item['title'], item['url'],
        labels=item['labels'], kind=item['kind'], issue_unknown=True, pr_unknown=True, cmt_unknown=True,
        check_errors=['文档/小修初筛，待共享精确核验']) for item in found], ROOT)
    print(f"\ncandidates={len(found)} skipped={len(skipped)} -> {OUT}")


if __name__ == "__main__":
    sys.exit(main())
