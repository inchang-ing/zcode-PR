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
    python tools/inbox.py stats

State lives in tools/inbox_handled.json rather than work/, because work/ is
gitignored: a judgement that only exists on one disk gets re-made by the next
session. The inbox issue is the shared record; this file remembers what has
already been judged.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
    exe = shutil.which("gh") or r"C:\Program Files\GitHub CLI\gh.exe"
    proc = subprocess.run([exe, *args], capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise SystemExit(f"gh {' '.join(args[:3])} -> {proc.stderr.strip()[:300]}")
    return proc.stdout


def inbox_number() -> int:
    out = gh("api", f"repos/{REPO}/issues?labels={LABEL}&state=open&per_page=5")
    found = json.loads(out or "[]")
    if not found:
        raise SystemExit(f"no open issue labelled {LABEL} in {REPO}")
    return int(found[0]["number"])


def comments() -> list[dict]:
    number = inbox_number()
    out = gh(
        "api", "--paginate",
        f"repos/{REPO}/issues/{number}/comments?per_page=100",
        "--jq", ".[] | {body, created_at}",
    )
    rows = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def parse(rows: list[dict]) -> dict[str, dict]:
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


def load_state() -> dict:
    if not STATE.exists():
        return {}
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def pending(rows: list[dict], hours: int | None) -> list[dict]:
    done = load_state()
    cutoff = datetime.now(TZ) - timedelta(hours=hours) if hours else None
    out = []
    for key, entry in parse(rows).items():
        if key in done:
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

    if action == "list":
        rows = comments()
        todo = pending(rows, hours)
        total = len(parse(rows))
        done = len(load_state())
        scope = f"last {hours}h" if hours else "all time"
        print(f"{len(todo)} pending of {total} reported ({done} marked done, {scope})")
        for entry in todo:
            labels = f" [{entry['labels']}]" if entry["labels"] else ""
            print(f"{entry['key']:<45} {entry['posted'][:16]}{labels}  {entry['title'][:90]}")
            print(f"{'':<45} {entry['url']}")
        if todo:
            print("\ntriage each one, then: python tools/inbox.py done <key> --note <why>")
        return 0

    if action == "done":
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
            raise SystemExit("done needs at least one owner/repo#num")
        state = load_state()
        stamp = datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%SZ")
        for key in keys:
            state[key.lower()] = {"at": stamp, "note": note}
            print(f"done {key.lower()}  {note}")
        save_state(state)
        return 0

    if action == "stats":
        rows = comments()
        entries = parse(rows)
        state = load_state()
        print(f"reported {len(entries)}  done {len(state)}  pending {len(entries) - len(state & entries.keys())}")
        print(f"state file {STATE}")
        return 0

    print(__doc__.strip().splitlines()[0])
    print(f"unknown action: {action}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
