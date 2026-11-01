"""Fast-lane fresh-issue poller for GitHub Actions.

The desktop app's automation scheduler cannot fire more often than once an
hour, and a good-first-issue is usually claimed within ~15 minutes. This
script runs on a *much* shorter cycle in Actions, does only the cheap
deterministic part (find newly opened issues in the watched pool), and
appends them to a single inbox issue with an @mention so the notification
lands on the phone.

It deliberately does not judge, claim, or comment on the upstream issue --
that stays with the hourly pipeline, which has the model and the checks.

State: none. Dedupe is derived from the inbox issue's own comments, so a
lost run or a re-run cannot double-post.

Usage:
    GITHUB_TOKEN=... python tools/poll_fresh.py            # post to inbox
    GITHUB_TOKEN=... python tools/poll_fresh.py --dry-run  # print only
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://api.github.com"
ROOT = Path(__file__).resolve().parents[1]
POOL_FILE = ROOT / "tools" / "fresh_pool.json"
POOL = json.loads(POOL_FILE.read_text(encoding="utf-8"))
INBOX_LABEL = "inbox:fresh"
INBOX_TITLE = "Fresh issue inbox (fast lane)"
KEY_RE = re.compile(r"\b([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(\d+)\b")
TZ = timezone.utc


def token() -> str:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not tok:
        sys.exit("GITHUB_TOKEN is not set")
    return tok


def call(method: str, path: str, payload: dict | None = None) -> object:
    url = path if path.startswith("http") else API + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token()}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "zcode-pr-fresh-poller")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        raise SystemExit(f"{method} {path} -> {exc.code}: {detail}") from exc


def load_pool() -> set[str]:
    return {r.lower() for r in json.loads(POOL_FILE.read_text(encoding="utf-8"))}


def last_success_gap(repo: str) -> int | None:
    """Minutes since this workflow last succeeded, or None if unknown.

    The cron is best-effort, not a real 5-minute timer: on 2026-11-01 this
    workflow fired once at 13:09Z and then stayed silent for 145 minutes.
    A fixed lookback therefore has to be sized for the gap, not the cadence.
    """
    try:
        runs = call(
            "GET",
            f"/repos/{repo}/actions/workflows/fresh-issue-poll.yml/runs"
            "?status=success&per_page=5",
        )
    except SystemExit as exc:  # a lookup failure must not stop the poll
        print(f"WARN last-run lookup failed: {exc}")
        return None
    current = os.environ.get("GITHUB_RUN_ID")
    stamps = [
        r["created_at"]
        for r in (runs or {}).get("workflow_runs", [])
        if current is None or str(r.get("id")) != current
    ]
    if not stamps:
        return None
    try:
        prev = datetime.fromisoformat(stamps[0].replace("Z", "+00:00"))
    except ValueError:
        return None
    return max(1, int((datetime.now(TZ) - prev).total_seconds() // 60))


def search_new_issues(since: str) -> list[dict]:
    """Poll every watched repo for issues created at or after `since`.

    A global search is not usable here: `created:>=` over even one hour returns
    far more than the 1000-result search cap, so pool issues get pushed out of
    the result set. One cheap call per repo is bounded and exact.

    The repo endpoint's `since` filters on last-updated, not created, so results
    are ordered newest-created first and paging stops as soon as a page reaches
    past `since` -- that keeps a widened lookback cheap.
    """
    out: list[dict] = []

    def one(repo: str):
        got: list[dict] = []
        for page in range(1, 6):
            qs = urllib.parse.urlencode({
                "since": since, "state": "all", "sort": "created",
                "direction": "desc", "per_page": 100, "page": page,
            })
            try:
                batch = call("GET", f"/repos/{repo}/issues?{qs}") or []
            except SystemExit as exc:  # one bad repo must not kill the run
                print(f"WARN {repo}: {exc}")
                break
            got.extend(batch)
            if len(batch) < 100 or any(
                (it.get("created_at") or "9999") < since for it in batch
            ):
                break
        return repo, got

    with ThreadPoolExecutor(max_workers=10) as pool:
        for repo, items in pool.map(one, sorted(POOL)):
            for it in items or []:
                if it.get("pull_request"):
                    continue
                if it.get("created_at", "") < since:
                    continue
                it["_slug"] = repo.lower()
                out.append(it)
    return out


def inbox_issue(repo: str) -> int:
    qs = urllib.parse.urlencode({"labels": INBOX_LABEL, "state": "open", "per_page": 5})
    found = call("GET", f"/repos/{repo}/issues?{qs}") or []
    if found:
        return int(found[0]["number"])
    created = call("POST", f"/repos/{repo}/issues", {
        "title": INBOX_TITLE,
        "labels": [INBOX_LABEL],
        "body": (
            "Fast-lane poller output. Each new issue in the watched pool shows up as a "
            "comment here with an `@mention`, which is what triggers the notification.\n\n"
            "Claiming, checking for duplicates, and writing code stay in the hourly "
            "pipeline -- this issue only reports what appeared."
        ),
    })
    return int(created["number"])


def already_reported(repo: str, number: int) -> set[str]:
    seen: set[str] = set()
    for page in range(1, 11):
        qs = urllib.parse.urlencode({"per_page": 100, "page": page})
        batch = call("GET", f"/repos/{repo}/issues/{number}/comments?{qs}") or []
        for c in batch:
            for owner_repo, num in KEY_RE.findall(c.get("body") or ""):
                seen.add(f"{owner_repo.lower()}#{num}")
        if len(batch) < 100:
            break
    return seen


def render(items: list[dict], window_min: int) -> str:
    now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"**{len(items)} new issue(s)** — window {window_min}m, checked {now}", ""]
    for it in items:
        repo = it.get("_canon") or it.get("_slug") or it["repository_url"].rsplit("/repos/", 1)[-1]
        labels = ", ".join(lb["name"] for lb in it.get("labels", [])) or "-"
        age = ""
        try:
            created = datetime.fromisoformat(it["created_at"].replace("Z", "+00:00"))
            age = f"{(datetime.now(TZ) - created).total_seconds() / 60:.0f}m"
        except Exception:
            pass
        lines.append(
            f"- `{repo}#{it['number']}` {age} [{labels}] {it['title']} "
            f"— {it['html_url']}"
        )
    lines += ["", "@inchang-ing"]
    return "\n".join(lines)


def main() -> int:
    dry = "--dry-run" in sys.argv
    window = int(os.environ.get("WINDOW_MIN", "40"))
    cap = int(os.environ.get("WINDOW_MAX_MIN", "360"))
    repo = os.environ.get("GITHUB_REPOSITORY", "inchang-ing/zcode-PR")

    gap = last_success_gap(repo)
    if gap is not None:
        # Overlap by two minutes: a run that starts mid-minute would otherwise
        # skip anything opened between the previous run's start and its finish.
        window = max(window, min(cap, gap + 2))
        print(f"last success {gap}m ago -> window {window}m")

    since = (datetime.now(TZ) - timedelta(minutes=window)).strftime("%Y-%m-%dT%H:%M:%SZ")
    hits = []
    dedupe: dict[str, dict] = {}
    for it in search_new_issues(since):
        login = (it.get("user") or {}).get("login", "")
        if login.endswith("[bot]") or login.endswith("-bot"):
            continue
        # A renamed repo keeps its old slug alive as a pool entry (e.g.
        # embedchain/embedchain -> mem0ai/mem0), so the same issue arrives twice.
        # Canonicalise on the html_url GitHub itself redirects to.
        canonical = it.get("html_url", "").split("/issues/")[0].rsplit("/", 2)[-2:]
        it["_canon"] = "/".join(canonical).lower() if canonical else it.get("_slug", "")
        key = it.get("html_url") or f"{it.get('_slug')}#{it.get('number')}"
        dedupe.setdefault(key, it)
    hits = list(dedupe.values())

    if not hits:
        print(f"no new issues in pool ({len(POOL)} repos, {window}m window)")
        return 0

    if dry:
        print(render(hits, window))
        return 0

    box = inbox_issue(repo)
    seen = already_reported(repo, box)
    fresh = [it for it in hits if f"{it.get('_canon') or it['_slug']}#{it['number']}" not in seen]
    if not fresh:
        print(f"{len(hits)} hit(s), all already reported")
        return 0

    call("POST", f"/repos/{repo}/issues/{box}/comments", {"body": render(fresh, window)})
    print(f"reported {len(fresh)} new issue(s) to {repo}#{box}")
    for it in fresh:
        print(f"  {it.get('_canon') or it['_slug']}#{it['number']}  {it['title'][:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
