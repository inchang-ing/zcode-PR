#!/usr/bin/env python3
"""Fetch status of in-flight PRs: state, mergeable, CI, comments, reviews.

Usage: python pr_status.py <owner/repo> <pr_num> [<pr_num> ...]
"""
import json
import subprocess
import sys
import os

GH = r"C:\Program Files\GitHub CLI\gh.exe"
TOKEN = os.environ.get("GH_TOKEN") or subprocess.run(
    [GH, "auth", "token"], capture_output=True, text=True
).stdout.strip()


def api(path, accept="application/vnd.github+json"):
    cmd = [GH, "api", "-H", f"Accept: {accept}", "-H", f"Authorization: Bearer {TOKEN}", path]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        return {"__error__": r.stderr.strip()[:300]}
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"__raw__": r.stdout[:500]}


def check(repo, num):
    pr = api(f"repos/{repo}/pulls/{num}")
    if "__error__" in pr:
        print(f"### {repo}#{num}: ERROR {pr['__error__']}")
        return
    head = pr.get("head", {}).get("sha", "")
    state = pr.get("state")
    merged = pr.get("merged")
    ms = pr.get("mergeable_state")
    print(f"### {repo}#{num}  state={state} merged={merged} mergeable={pr.get('mergeable')} "
          f"mergeable_state={ms} head={head[:8]} title={pr.get('title')!r}")

    # reviews
    rv = api(f"repos/{repo}/pulls/{num}/reviews")
    if isinstance(rv, list) and rv:
        for r in rv[-4:]:
            print(f"   REVIEW {r.get('user', {}).get('login')} -> {r.get('state')} "
                  f"@ {r.get('submitted_at')}")
    else:
        print("   REVIEW: none")

    # comments
    cm = api(f"repos/{repo}/issues/{num}/comments")
    if isinstance(cm, list):
        print(f"   COMMENTS: {len(cm)}")
        for c in cm[-4:]:
            print(f"     - {c.get('user', {}).get('login')} @ {c.get('created_at')}: "
                  f"{c.get('body','')[:200].replace(chr(10),' | ')}")
    # review comments (inline)
    rc = api(f"repos/{repo}/pulls/{num}/comments")
    if isinstance(rc, list):
        print(f"   INLINE: {len(rc)}")
        for c in rc[-4:]:
            print(f"     - {c.get('user', {}).get('login')} {c.get('path')}:{c.get('line')} "
                  f"{c.get('body','')[:180].replace(chr(10),' | ')}")

    # CI
    cr = api(f"repos/{repo}/commits/{head}/check-runs")
    if isinstance(cr, dict) and "check_runs" in cr:
        runs = cr["check_runs"]
        bad = [r for r in runs if r.get("conclusion") not in ("success", "neutral", "skipped", None)]
        print(f"   CHECKS: total={len(runs)} "
              f"ok={sum(1 for r in runs if r.get('conclusion')=='success')} "
              f"pending={sum(1 for r in runs if r.get('status')!='completed')}")
        for r in bad:
            print(f"     !! {r.get('name')} -> {r.get('conclusion')} ({r.get('html_url')})")
    else:
        print(f"   CHECKS: {cr if isinstance(cr, dict) else 'n/a'}")
    print()


if __name__ == "__main__":
    repo = sys.argv[1]
    for n in sys.argv[2:]:
        check(repo, n)
