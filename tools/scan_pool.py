"""Shared read-only discovery command used by legacy pool scan entry points.

These cheap list filters report leads; monitor_round/vet perform exact checks.
"""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import github_read

from repository_pools import normalize_repos

NOISE = ("ScreenContextAgent",)


def api(path):
    try:
        data = json.loads(github_read.output(["api", path], timeout=60))
        return data if isinstance(data, list) else None
    except (github_read.GitHubReadError, ValueError):
        return None


def fetch(repo, since_iso):
    data = api(f"repos/{repo}/issues?state=open&since={since_iso}&sort=created&direction=desc&per_page=25")
    return repo, data, None if data is not None else "query failed"


def scan(repos, max_age_h, label, *, per_page=25, workers=1, noise=(), since=False):
    repos = normalize_repos(repos)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=max_age_h)
    query = f"state=open&sort=created&direction=desc&per_page={per_page}"
    if since:
        query += "&since=" + cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    out = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for repo, data in zip(repos, executor.map(lambda repo: api(f"repos/{repo}/issues?{query}"), repos)):
            if data is None:
                print(f"[skip] {repo}", flush=True)
                continue
            for item in data:
                if (not isinstance(item, dict) or "pull_request" in item
                        or item.get("assignee") or item.get("assignees")):
                    continue
                try:
                    created = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
                    title = item["title"]
                    comments = item.get("comments", 0)
                    if created < cutoff or comments > 2 or any(part in title for part in noise):
                        continue
                    labels = ",".join(label["name"] for label in item.get("labels", []))
                    out.append((repo, item["number"], round((now - created).total_seconds() / 3600, 1),
                                comments, labels, title[:110]))
                except (KeyError, TypeError, ValueError, AttributeError):
                    continue
            print(f"[ok] {repo}", flush=True)
    out.sort(key=lambda item: item[2])
    print(f"\n===== {label}: {len(out)} candidates (<= {max_age_h}h) =====")
    for repo, number, age, comments, labels, title in out:
        print(f"{age:6.1f}h c={comments} {repo}#{number} [{labels}] {title}")
    return out
