#!/usr/bin/env python3
"""Recon scanner: pull recent open issues from a repo list, filter for clean candidates.

Filters:
- is an issue (not a PR)
- no assignee
- comments <= 2
- created within the since window (passed via CLI)
Outputs a compact table sorted by repo then created_at desc.
"""
import subprocess, json, sys, datetime, os, time

GH = r"C:/Program Files/GitHub CLI/gh.exe"

def gh_api(path, params=None):
    url = path
    if params:
        q = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{path}?{q}" if "?" not in path else f"{path}&{q}"
    cmd = [GH, "api", url]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if out.returncode != 0:
            return None
        return json.loads(out.stdout)
    except Exception as e:
        return None

def main():
    repos = sys.argv[1].split(",")
    since = sys.argv[2]  # ISO timestamp (filters by updated_at)
    max_age_h = float(sys.argv[3]) if len(sys.argv) > 3 else 48.0
    now = datetime.datetime.now(datetime.timezone.utc)
    results = []
    for repo in repos:
        repo = repo.strip()
        time.sleep(1.5)  # throttle to avoid secondary rate limits
        data = gh_api(f"repos/{repo}/issues",
                      {"state": "open", "since": since, "sort": "created",
                       "direction": "desc", "per_page": "20"})
        if data is None:
            print(f"  [skip/err] {repo}")
            continue
        for it in data:
            if it.get("pull_request"):
                continue  # skip PRs
            assignee = it.get("assignee") or it.get("assignees")
            if assignee:
                continue
            comments = it.get("comments", 0)
            if comments > 2:
                continue
            created = it.get("created_at")
            try:
                cdt = datetime.datetime.fromisoformat(created.replace("Z", "+00:00"))
                age_h = (now - cdt).total_seconds() / 3600.0
            except Exception:
                age_h = -1
            labels = [l["name"] for l in it.get("labels", [])]
            if age_h < 0 or age_h > max_age_h:
                continue  # created outside the requested window
            results.append({
                "repo": repo, "num": it["number"], "title": it["title"],
                "created": created, "age_h": round(age_h, 1),
                "comments": comments, "labels": labels,
                "url": it["html_url"],
            })
    # sort by age ascending (freshest first)
    results.sort(key=lambda r: r["age_h"])
    print(f"\n=== CANDIDATES (created within {max_age_h}h of now, {len(results)} found) ===")
    for r in results:
        print(f"{r['repo']} #{r['num']} | {r['age_h']}h | c={r['comments']} | {r['title'][:70]}")
        print(f"    labels={r['labels']}  {r['url']}")

if __name__ == "__main__":
    main()
