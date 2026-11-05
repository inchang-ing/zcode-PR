"""Read the fast-lane inbox as a work queue instead of a comment stream.

The poller appends new issues to a single inbox issue. Reading that as prose
means re-deciding every hour which entries were already handled, and the answer
lives nowhere, so the list only grows. This script keeps that decision: it
flattens the comments into `owner/repo#num` entries, subtracts the ones marked
done, and prints what is left.

Marking is deliberately separate from handling. A candidate that fails the
duplicate/policy checks still gets marked done, with the reason recorded, because
"looked at and rejected" is a decision too -- leaving it pending means reviewing
the same entry every hour.

    python tools/inbox.py list                # pending entries, newest first
    python tools/inbox.py list --hours 6      # only what appeared recently
    python tools/inbox.py done foo/bar#12 --note "self-claimed in body"
    python tools/inbox.py reopen foo/bar#12 --note "new evidence"
    python tools/inbox.py import              # pending entries -> local precise scan
    python tools/inbox.py stats

Task decisions live in the root task_state.json alongside queue and dispatch
records. Legacy tools/inbox_handled.json remains readable until the first write
backs it up and migrates all three ledgers together.
"""

from __future__ import annotations

import json
import hashlib
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from pipeline_state import atomic_write_json, file_lock, read_json_object
from candidate_rules import Candidate, contribution_kind, enqueue_candidates
from task_state import record_handled, TaskStore, timestamp
from discovery_state import is_consumed, load_consumed
from notification_contract import decode_events
from github_read import output, GitHubReadError
from urllib.parse import urlencode

REPO = "inchang-ing/zcode-PR"
LABEL = "inbox:fresh"
ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "tools" / "inbox_handled.json"
TZ = timezone.utc

# Anchored at the line start and limited to the shape the poller writes, so a
# `owner/repo#num` that happens to sit inside an upstream issue title is not
# mistaken for a report of its own.
KEY_RE = re.compile(r"^- `([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(\d+)`", re.MULTILINE)
# "- `owner/repo#12` 7m [`bug, help wanted`] `Title text`"
LINE_RE = re.compile(
    r"^-\s+`(?P<key>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#\d+)`\s+(?P<age>\S+)\s+"
    r"\[(?P<labels>[^\]]*)\]\s+(?P<title>.+?)\s*$"
)


def gh(*args: str) -> str:
    try:
        return output(list(args), timeout=90)
    except GitHubReadError as exc:
        raise SystemExit(f"gh {' '.join(args[:3])} -> {exc}") from exc


def inbox_number() -> int:
    out = gh("api", f"repos/{REPO}/issues?labels={LABEL}&state=open&per_page=5")
    found = json.loads(out or "[]")
    if not found:
        raise SystemExit(f"no open issue labelled {LABEL} in {REPO}")
    return int(found[0]["number"])


def comments() -> list[dict]:
    """Cache complete comments; fetch only updates since the last successful read."""
    number = inbox_number()
    path = ROOT / 'tools/inbox_comments.json'
    with file_lock(path):
        cache = read_json_object(path)
        if cache and (cache.get('version') != 1 or not isinstance(cache.get('rows'), dict)):
            raise ValueError('Invalid inbox comment cache')
        if cache.get('issue') != number:
            cache = {'version': 1, 'issue': number, 'rows': {}}
        started = datetime.now(TZ).replace(microsecond=0) - timedelta(seconds=1)
        query = {'per_page': 100}
        if cache.get('since'):
            timestamp(cache['since'])
            query['since'] = cache['since']
        out = gh('api', '--paginate',
                 f'repos/{REPO}/issues/{number}/comments?' + urlencode(query),
                 '--jq', '.[] | {id, body, created_at, updated_at}')
        for line in out.splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if (not isinstance(row, dict) or type(row.get('id')) is not int
                    or row['id'] <= 0 or not isinstance(row.get('body'), str)):
                raise ValueError('Invalid inbox comment')
            timestamp(row['created_at'])
            timestamp(row['updated_at'])
            cache['rows'][str(row['id'])] = row
        cache['since'] = started.isoformat()
        atomic_write_json(path, cache)
    return sorted(cache['rows'].values(), key=lambda row: (row['created_at'], row['id']))


def _parse_legacy(rows: list[dict]) -> dict[str, dict]:
    """Flatten comment bodies into one entry per `repo#num`, newest wins."""
    entries: dict[str, dict] = {}
    for row in rows:
        body = row.get("body") or ""
        seen_at = row.get("created_at") or ""
        for line in body.splitlines():
            line = line.strip()
            match = LINE_RE.match(line)
            if match:
                key = match.group("key").lower()
                title = match.group("title").strip()
                labels = match.group("labels").strip()
                # The poller renders both inside code spans so GitHub will not
                # mention or reference anything inside them; they read the same
                # once the delimiter is off.
                title = title[1:-1] if title.startswith("`") and title.endswith("`") and len(title) > 1 else title
                labels = labels[1:-1] if labels.startswith("`") and labels.endswith("`") and len(labels) > 1 else labels
                owner_repo, _, number = key.partition("#")
                entries[key] = {
                    "key": key,
                    "title": title,
                    "labels": labels,
                    # Built from the key rather than read from the comment: the
                    # poller stopped writing URLs, which is the whole point.
                    "url": f"https://github.com/{owner_repo}/issues/{number}",
                    "posted": seen_at,
                    "age": match.group("age"),
                }
                continue
            for owner_repo, num in KEY_RE.findall(line):
                key = f"{owner_repo.lower()}#{num}"
                entries.setdefault(key, {
                    "key": key, "title": line[:120], "labels": "",
                    "url": f"https://github.com/{owner_repo}/issues/{num}",
                    "posted": seen_at, "age": "",
                })
    return entries


def parse(rows: list[dict]) -> dict[str, dict]:
    entries = {}
    for row in rows:
        events = decode_events(row.get('body') or '')
        if events is None:
            current = _parse_legacy([row])
        else:
            current = {event['key']: {
                'key': event['key'], 'title': event['title'],
                'labels': ', '.join(event['labels']),
                'url': f"https://github.com/{event['repo']}/issues/{event['number']}",
                'posted': row.get('created_at', ''), 'age': '',
            } for event in events}
        for key, entry in current.items():
            identity = [row.get('id'), row.get('updated_at') or row.get('created_at'),
                        key, entry['title'], entry['labels']]
            entry['source_version'] = hashlib.sha256(
                json.dumps(identity, ensure_ascii=False).encode()).hexdigest()
            entries[key] = entry
    return entries


def load_state() -> dict:
    return TaskStore(root=ROOT).handled


def pending(rows: list[dict], hours: int | None, *, tasks=None) -> list[dict]:
    tasks = tasks if tasks is not None else TaskStore(root=ROOT)
    receipts = load_consumed(ROOT)
    now = datetime.now(TZ)
    cutoff = datetime.now(TZ) - timedelta(hours=hours) if hours else None
    out = []
    for key, entry in parse(rows).items():
        decision = tasks.decision(key, now)
        if decision['blocked'] or is_consumed(receipts, key, entry, decision):
            continue
        if cutoff and entry["posted"]:
            try:
                posted = datetime.fromisoformat(entry["posted"].replace("Z", "+00:00"))
            except ValueError:
                posted = None
            if posted and posted < cutoff:
                continue
        out.append(entry)
    out.sort(key=lambda e: e["posted"], reverse=True)
    return out


def main() -> int:
    args = sys.argv[1:]
    action = args[0] if args and not args[0].startswith("-") else "list"
    hours = None
    if "--hours" in args:
        try:
            hours = int(args[args.index("--hours") + 1])
        except (IndexError, ValueError):
            raise SystemExit("--hours needs a number")

    if action == "import":
        candidates = []
        for entry in pending(comments(), hours):
            repo, number = entry['key'].split('#')
            labels = [label.strip() for label in entry['labels'].split(',') if label.strip() != '-']
            candidates.append(Candidate(
                repo, int(number), entry['title'], entry['url'], labels=labels,
                source_version=entry['source_version'],
                kind=contribution_kind(labels), issue_unknown=True,
                pr_unknown=True, cmt_unknown=True,
                check_errors=['云端收件箱导入，待共享精确核验'],
            ))
        added = enqueue_candidates(candidates, ROOT)
        print(f'imported {added} new pending entries; run tools/monitor_round.py --pending')
        return 0

    if action == "list":
        rows = comments()
        tasks = TaskStore(root=ROOT)
        todo = pending(rows, hours, tasks=tasks)
        total = len(parse(rows))
        done = sum(entry.get('status', 'done') == 'done' for entry in tasks.handled.values())
        scope = f"last {hours}h" if hours else "all time"
        print(f"{len(todo)} pending of {total} reported ({done} marked done, {scope})")
        for entry in todo:
            labels = f" [{entry['labels']}]" if entry["labels"] else ""
            print(f"{entry['key']:<45} {entry['posted'][:16]}{labels}  {entry['title'][:90]}")
            print(f"{'':<45} {entry['url']}")
        if todo:
            print("\ntriage each one, then: python tools/inbox.py done <key> --note <why>")
        return 0

    if action in {"done", "reopen"}:
        # Strip --note and its value before collecting keys: a note like
        # "author opened #4503" contains a '#', so scanning the raw argument
        # list for '#' silently records the prose as a second entry.
        rest = args[1:]
        note = ""
        if "--note" in rest:
            index = rest.index("--note")
            if index + 1 >= len(rest):
                raise SystemExit("--note needs text")
            note = rest[index + 1]
            rest = rest[:index] + rest[index + 2:]
        keys = [a for a in rest if not a.startswith("-") and "#" in a]
        if not keys:
            raise SystemExit(f"{action} needs at least one owner/repo#num")
        record_handled(ROOT / 'tools/inbox_handled.json', keys, note,
                       'done' if action == 'done' else 'open')
        for key in keys:
            print(f"{action} {key.lower()}  {note}")
        return 0

    if action == "stats":
        rows = comments()
        entries = parse(rows)
        tasks = TaskStore(root=ROOT)
        done = sum(entry.get("status", "done") == "done" for entry in tasks.handled.values())
        print(f"reported {len(entries)}  done {done}  pending {len(pending(rows, None, tasks=tasks))}")
        print(f"state file {ROOT / 'task_state.json'}")
        return 0

    print(__doc__.strip().splitlines()[0])
    print(f"unknown action: {action}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
