#!/usr/bin/env python3
"""Fetch status of in-flight PRs: state, mergeable, CI, comments, reviews.

Usage: python pr_status.py <owner/repo> <pr_num> [<pr_num> ...]
"""
import json
import subprocess
import sys

GH = r"C:\Program Files\GitHub CLI\gh.exe"


def api(path, accept="application/vnd.github+json", *, paginate=False, item_key=None):
    cmd = [GH, "api", "-H", f"Accept: {accept}"]
    if paginate:
        cmd += ["--paginate", "--slurp"]
    cmd.append(path)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return {"__error__": "GitHub CLI unavailable or request timed out"}
    if r.returncode != 0:
        return {"__error__": r.stderr.strip()[:300]}
    try:
        data = json.loads(r.stdout)
    except ValueError:
        return {"__error__": "Invalid JSON response"}
    if not paginate:
        return data if isinstance(data, dict) else {"__error__": "Expected an object response"}
    if not isinstance(data, list) or not data:
        return {"__error__": "Missing paginated response"}
    items = []
    for page in data:
        if item_key is not None:
            page = page.get(item_key) if isinstance(page, dict) else None
        if not isinstance(page, list) or any(not isinstance(item, dict) for item in page):
            return {"__error__": "Invalid page response"}
        items.extend(page)
    return items


def check(repo, num):
    pr = api(f"repos/{repo}/pulls/{num}")
    if "__error__" in pr:
        print(f"### {repo}#{num}: ERROR {pr['__error__']}")
        return False
    head = pr.get("head", {}).get("sha", "")
    state = pr.get("state")
    merged = pr.get("merged")
    ms = pr.get("mergeable_state")
    print(f"### {repo}#{num}  state={state} merged={merged} mergeable={pr.get('mergeable')} "
          f"mergeable_state={ms} head={head[:8]} title={pr.get('title')!r}")

    def listing(label, path, item_key=None):
        result = api(path + "?per_page=100", paginate=True, item_key=item_key)
        if isinstance(result, dict):
            print(f"   {label}: UNKNOWN {result['__error__']}")
            return None
        return result

    # Only report complete collections; failed later pages are not empty results.
    rv = listing("REVIEW", f"repos/{repo}/pulls/{num}/reviews")
    if rv:
        for r in rv[-4:]:
            print(f"   REVIEW {r.get('user', {}).get('login')} -> {r.get('state')} "
                  f"@ {r.get('submitted_at')}")
    elif rv == []:
        print("   REVIEW: none")

    # comments
    cm = listing("COMMENTS", f"repos/{repo}/issues/{num}/comments")
    if cm is not None:
        print(f"   COMMENTS: {len(cm)}")
        for c in cm[-4:]:
            print(f"     - {c.get('user', {}).get('login')} @ {c.get('created_at')}: "
                  f"{c.get('body','')[:200].replace(chr(10),' | ')}")
    # review comments (inline)
    rc = listing("INLINE", f"repos/{repo}/pulls/{num}/comments")
    if rc is not None:
        print(f"   INLINE: {len(rc)}")
        for c in rc[-4:]:
            print(f"     - {c.get('user', {}).get('login')} {c.get('path')}:{c.get('line')} "
                  f"{c.get('body','')[:180].replace(chr(10),' | ')}")

    # CI
    runs = listing("CHECKS", f"repos/{repo}/commits/{head}/check-runs", "check_runs")
    if runs is not None:
        bad = [r for r in runs if r.get("conclusion") not in ("success", "neutral", "skipped", None)]
        print(f"   CHECKS: total={len(runs)} "
              f"ok={sum(1 for r in runs if r.get('conclusion')=='success')} "
              f"pending={sum(1 for r in runs if r.get('status')!='completed')}")
        for r in bad:
            print(f"     !! {r.get('name')} -> {r.get('conclusion')} ({r.get('html_url')})")
    print()
    return all(result is not None for result in (rv, cm, rc, runs))


if __name__ == "__main__":
    repo = sys.argv[1]
    results = [check(repo, n) for n in sys.argv[2:]]
    sys.exit(0 if all(results) else 1)
