"""Fast-lane fresh-issue poller for GitHub Actions.

The desktop app's automation scheduler cannot fire more often than once an
hour, and a good-first-issue is usually claimed within ~15 minutes. This
script runs on a *much* shorter cycle in Actions, does only the cheap
deterministic part (find newly opened issues in the watched pool), and
appends them to a single inbox issue with an @mention so the notification
lands on the phone.

It deliberately does not judge, claim, or comment on the upstream issue --
that stays with the hourly pipeline, which has the model and the checks.

Per-repository checkpoints live in the inbox body. They advance only after
complete scans and successful reporting; comments provide retry deduplication.

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
from pipeline_state import file_lock
from pipeline_switch import is_on
from repository_pools import normalize_repos
from notification_contract import code, encode_events

API = "https://api.github.com"
ROOT = Path(__file__).resolve().parents[1]
POOL_FILE = ROOT / "tools" / "fresh_pool.json"
POOL = json.loads(POOL_FILE.read_text(encoding="utf-8"))
INBOX_LABEL = "inbox:fresh"
INBOX_TITLE = "Fresh issue inbox (fast lane)"
# Anchored to the start of a line, because every line this script writes that
# should be remembered starts with its own key. A looser pattern also matched
# `owner/repo#num` appearing inside an upstream issue *title*, which then got
# recorded as "already reported" and suppressed a different issue later.
KEY_RE = re.compile(r"^- `([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(\d+)`", re.MULTILINE)
TZ = timezone.utc
CHECKPOINT_RE = re.compile(r'<!-- zcode-poll-state\n(.*?)\n-->', re.DOTALL)


class PollError(RuntimeError):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


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
        raise PollError(f"{method} {path} -> {exc.code}: {detail}", exc.code) from exc
    except (OSError, ValueError) as exc:
        raise PollError(f'{method} {path}: {exc}') from exc


def load_pool() -> set[str]:
    return set(normalize_repos(json.loads(POOL_FILE.read_text(encoding="utf-8")),
                               exclude_restricted=False))


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
    except PollError as exc:  # bootstrap may use the configured initial lookback
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


def search_new_issues(since: dict[str, str]) -> dict[str, list | None]:
    """A failed or malformed page discards that repository's partial scan."""
    def one(repo):
        got, page = [], 1
        try:
            cutoff = datetime.fromisoformat(since[repo].replace('Z', '+00:00'))
            while True:
                qs = urllib.parse.urlencode({
                    'since': since[repo], 'state': 'all', 'sort': 'created',
                    'direction': 'desc', 'per_page': 100, 'page': page,
                })
                batch = call('GET', f'/repos/{repo}/issues?{qs}')
                if not isinstance(batch, list):
                    raise ValueError('issues response is not a list')
                boundary = False
                for item in batch:
                    created = item['created_at']
                    if not isinstance(created, str) or not datetime.fromisoformat(created.replace('Z', '+00:00')).tzinfo:
                        raise ValueError('invalid creation time')
                    if datetime.fromisoformat(created.replace('Z', '+00:00')) < cutoff:
                        boundary = True
                        continue
                    if 'pull_request' in item:
                        continue
                    if type(item.get('number')) is not int or item['number'] <= 0 or not isinstance(item.get('title'), str):
                        raise ValueError('invalid issue identity/title')
                    got.append(dict(item, _slug=repo))
                if len(batch) < 100 or boundary:
                    return repo, got
                page += 1
        except (PollError, ValueError, TypeError, KeyError, AttributeError) as exc:
            print(f'WARN {repo}: {exc}; checkpoint unchanged')
            return repo, None
    with ThreadPoolExecutor(max_workers=10) as pool:
        return dict(pool.map(one, sorted(since)))


def inbox_issue(repo: str, create=True) -> int | None:
    qs = urllib.parse.urlencode({"labels": INBOX_LABEL, "state": "open", "per_page": 5})
    found = call("GET", f"/repos/{repo}/issues?{qs}") or []
    if found:
        return int(found[0]["number"])
    if not create:
        return None
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


def already_reported(repo: str, number: int, since: str | None = None) -> set[str]:
    seen: set[str] = set()
    page = 1
    while True:
        query = {"per_page": 100, "page": page}
        if since:
            query['since'] = since
        qs = urllib.parse.urlencode(query)
        batch = call("GET", f"/repos/{repo}/issues/{number}/comments?{qs}")
        if not isinstance(batch, list):
            raise PollError('Invalid inbox comments response')
        for c in batch:
            for owner_repo, num in KEY_RE.findall(c.get("body") or ""):
                seen.add(f"{owner_repo.lower()}#{num}")
        if len(batch) < 100:
            break
        page += 1
    return seen


def render(items: list[dict], window_min: int) -> str:
    now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"**{len(items)} new issue(s)** — window {window_min}m, checked {now}", ""]
    events = []
    for it in items:
        repo = it.get("_canon") or it.get("_slug") or it["repository_url"].rsplit("/repos/", 1)[-1]
        labels = ", ".join(lb["name"] for lb in it.get("labels", [])) or "-"
        age = ""
        try:
            created = datetime.fromisoformat(it["created_at"].replace("Z", "+00:00"))
            age = f"{(datetime.now(TZ) - created).total_seconds() / 60:.0f}m"
        except Exception:
            pass
        # No URL here, and that is deliberate. A bare issue URL in an issue body
        # is a cross-reference: GitHub files it on the target issue's timeline
        # and notifies its watchers. Reporting 28 new issues therefore pinged 28
        # upstream repositories, which is what a maintainer complained about on
        # 2026-11-02. The backticked `repo#num` is enough to find the issue and
        # a code span is not linkified, so this stays local.
        #
        # The title and labels are wrapped for the same reason: they are text
        # someone else wrote, and an @mention or an owner/repo#num inside a
        # title would reach out exactly the same way.
        lines.append(
            f"- `{repo}#{it['number']}` {age} "
            f"[{code(labels)}] {code(it['title'])}"
        )
        events.append({"repo": repo, "number": it["number"], "title": it["title"],
                       "labels": [label["name"] for label in it.get("labels", [])],
                       "url": f"https://github.com/{repo}/issues/{it['number']}",
                       "created_at": it["created_at"]})
    lines += ["", "@inchang-ing", "", encode_events(events)]
    return "\n".join(lines)


def render_batches(items, window_min, max_chars=48000):
    """Bound the complete presentation + machine payload before any POST."""
    batches, pending, body = [], [], ''
    for item in items:
        trial = render([*pending, item], window_min)
        if pending and (len(trial) > max_chars or len(pending) >= 50):
            batches.append(body)
            pending = []
            trial = render([item], window_min)
        if len(trial) > max_chars:
            raise PollError('One notification exceeds the comment size budget')
        pending.append(item)
        body = trial
    if pending:
        batches.append(body)
    return batches


def switch_on(repo: str) -> bool:
    """Use a verified value; a failed lookup is never an implicit enable."""
    env = os.environ.get('PIPELINE_ENABLED')
    if env is not None and not is_on(env):
        return False
    try:
        value = call('GET', f'/repos/{repo}/actions/variables/PIPELINE_ENABLED')
    except PollError:
        # Actions supplies its start-of-job value. Stop a running shift with
        # pipeline_switch off (cancellation); GITHUB_TOKEN may lack Variables access.
        if env in {'true', 'false'}:
            return is_on(env)
        raise
    return is_on(value['value'])


def load_checkpoint(repo, box):
    if box is None:
        return {}
    body = call('GET', f'/repos/{repo}/issues/{box}').get('body') or ''
    matches = CHECKPOINT_RE.findall(body)
    if not matches:
        if 'zcode-poll-state' in body:
            raise ValueError('Malformed inbox checkpoint; refusing to reset')
        return {}
    if len(matches) != 1:
        raise ValueError('Duplicate inbox checkpoints')
    state = json.loads(matches[0])
    if state.get('version') != 1 or not isinstance(state.get('repo_last_success'), dict):
        raise ValueError('Invalid inbox checkpoint schema')
    stamps = [state.get('default_since'), *state['repo_last_success'].values()]
    if 'comments_since' in state:
        stamps.append(state['comments_since'])
    for stamp in stamps:
        if not isinstance(stamp, str) or not datetime.fromisoformat(stamp.replace('Z', '+00:00')).tzinfo:
            raise ValueError('Invalid checkpoint timestamp')
    return state


def save_checkpoint(repo, box, state):
    path = f'/repos/{repo}/issues/{box}'
    body = call('GET', path).get('body') or ''
    block = '<!-- zcode-poll-state\n' + json.dumps(state, sort_keys=True) + '\n-->'
    if CHECKPOINT_RE.search(body):
        body = CHECKPOINT_RE.sub(lambda _: block, body)
    else:
        body = body.rstrip() + '\n\n' + block
    call('PATCH', path, {'body': body})


def run_round() -> int:
    dry = '--dry-run' in sys.argv
    window = int(os.environ.get('WINDOW_MIN', '40'))
    if window <= 0:
        raise ValueError('WINDOW_MIN must be positive')
    repo = os.environ.get('GITHUB_REPOSITORY', 'inchang-ing/zcode-PR')
    if not switch_on(repo):
        print('PIPELINE_ENABLED=false, not polling')
        return 42
    box = inbox_issue(repo, create=False)
    state = load_checkpoint(repo, box)
    now = datetime.now(TZ).replace(microsecond=0)
    if not state:
        gap = last_success_gap(repo)
        window = max(window, gap + 2 if gap is not None else window)
        state = {'version': 1, 'default_since': (now - timedelta(minutes=window)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                 'repo_last_success': {}}
    watermarks = state['repo_last_success']
    since = {name: watermarks.get(name, state['default_since']) for name in load_pool()}
    results = search_new_issues(since)
    successes = {name for name, items in results.items() if items is not None}
    if not successes:
        print('FAILED: no repository completed; checkpoint preserved')
        return 1
    status = 0 if len(successes) == len(since) else 2
    dedupe = {}
    for items in results.values():
        for item in items or []:
            login = (item.get('user') or {}).get('login', '')
            if login.endswith(('[bot]', '-bot')):
                continue
            match = re.fullmatch(r'https://github.com/([\w.-]+/[\w.-]+)/issues/([1-9]\d*)', item.get('html_url', ''))
            canonical = match[1].lower() if match else item['_slug']
            item['_canon'] = canonical
            dedupe.setdefault(f"{canonical}#{item['number']}", item)
    if dry:
        print(render(list(dedupe.values()), window))
        return status
    box = box if box is not None else inbox_issue(repo)
    seen = already_reported(repo, box, state.get('comments_since')) if dedupe else set()
    fresh = [item for key, item in dedupe.items() if key not in seen]
    for body in render_batches(fresh, window):
        call('POST', f'/repos/{repo}/issues/{box}/comments', {'body': body})
    # No cursor advances before every discovered item has been durably reported.
    for name in successes:
        watermarks[name] = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    # Failed repositories can replay an older boundary. Keep its comments until recovery.
    floor = min(datetime.fromisoformat(watermarks.get(name, state['default_since']).replace('Z', '+00:00'))
                for name in since)
    state['comments_since'] = (floor - timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    save_checkpoint(repo, box, state)
    print(f'reported {len(fresh)} issues; completed {len(successes)}/{len(since)} repos')
    return status


def main() -> int:
    try:
        with file_lock(ROOT / 'work/poll_fresh'):
            return run_round()
    except (PollError, ValueError, OSError, RuntimeError) as exc:
        print(f'FAILED: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
