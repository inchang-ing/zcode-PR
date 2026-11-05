#!/usr/bin/env python3
"""Fetch status of in-flight PRs: state, mergeable, CI, comments, reviews.

Usage: python pr_status.py <owner/repo> <pr_num> [<pr_num> ...]
"""
import subprocess
import sys

import github_read


def api(path, accept="application/vnd.github+json", *, paginate=False, item_key=None):
    try:
        return github_read.api(path, accept, paginate=paginate, item_key=item_key)
    except (github_read.GitHubReadError, OSError, subprocess.TimeoutExpired) as exc:
        return {"__error__": str(exc)}


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
    # The combined status endpoint returns the latest result for each CI context.
    statuses = listing("STATUSES", f"repos/{repo}/commits/{head}/status", "statuses")
    if statuses is not None and any(
            not isinstance(s.get('context'), str) or not s['context'].strip()
            or s.get('state') not in ('success', 'failure', 'error', 'pending') for s in statuses):
        print("   STATUSES: UNKNOWN incomplete context or state")
        statuses = None
    if statuses is not None:
        print(f"   STATUSES: total={len(statuses)} "
              f"ok={sum(s['state'] == 'success' for s in statuses)} "
              f"pending={sum(s['state'] == 'pending' for s in statuses)}")
        for status in statuses:
            if status['state'] in ('failure', 'error'):
                print(f"     !! {status['context']} -> {status['state']} ({status.get('target_url')})")
    print()
    return all(result is not None for result in (rv, cm, rc, runs, statuses))


if __name__ == "__main__":
    repo = sys.argv[1]
    results = [check(repo, n) for n in sys.argv[2:]]
    sys.exit(0 if all(results) else 1)
