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
    d = json.loads((ROOT / "tools" / "quality_repos.json").read_text(encoding="utf-8"))
    watch = d.get("watch", [])
    names = [x if isinstance(x, str) else x.get("repo") for x in watch]
    out = []
    for n in names:
        if not n:
            continue
        if pol.policy_reason(n):
            continue
        out.append(n)
    return out


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
    body = (issue.get("body") or "").lower()
    for claim in ("i will open a pr", "i'll open a pr", "i have a patch", "i have a fix",
                  "already fixed", "fixed by #", "opened #", "submitted pr",
                  "i am working on", "i'm working on", "assigned to me"):
        if claim in body:
            return False, "claimed"
    return True, ""


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    extra = sys.argv[2].split(",") if len(sys.argv) > 2 and sys.argv[2] else []
    if extra:
        repos = [r.strip() for r in extra if r.strip()]
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
                    return
                continue
            for it in data or []:
                ok, why = interesting(it)
                rec = {
                    "repo": repo,
                    "n": it["number"],
                    "title": it["title"],
                    "labels": labels[0],
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


def dump(found, skipped, repos):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {"scanned": len(repos), "repos": repos,
               "candidates": found, "skipped": skipped,
               "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(OUT)
    print(f"\ncandidates={len(found)} skipped={len(skipped)} -> {OUT}")


if __name__ == "__main__":
    main()
