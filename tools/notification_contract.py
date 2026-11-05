"""Notification contract v1. Distributed unchanged to repo-monitor; stdlib only."""
import base64
import binascii
from datetime import datetime
import json
import re

MARKER = "zcode-events-v1"
BLOCK = re.compile(r"^<!-- zcode-events-v1\n([A-Za-z0-9+/=]+)\n-->$", re.MULTILINE)
HEADER = re.compile(r"^<!-- zcode-events-", re.MULTILINE)
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")


def code(text):
    """Keep foreign text inside one code span, never an active reference."""
    return "`" + str(text).replace("`", "'").replace("\r", " ").replace("\n", " ") + "`"


def _events(events):
    if not isinstance(events, list):
        raise ValueError("events must be a list")
    result = []
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("event must be an object")
        repo, number = event.get("repo"), event.get("number")
        if not isinstance(repo, str) or not REPO.fullmatch(repo) or type(number) is not int or number <= 0:
            raise ValueError("invalid event identity")
        if any(not isinstance(event.get(field), str) for field in ("title", "url", "created_at")):
            raise ValueError("event title, url and created_at must be strings")
        labels = event.get("labels")
        if not isinstance(labels, list) or any(not isinstance(label, str) for label in labels):
            raise ValueError("event labels must be strings")
        try:
            stamp = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("invalid event creation time") from exc
        if stamp.tzinfo is None:
            raise ValueError("event creation time needs a timezone")
        repo = repo.lower()
        result.append({"repo": repo, "number": number, "key": f"{repo}#{number}",
                       "title": event["title"], "labels": list(labels), "url": event["url"],
                       "created_at": event["created_at"]})
    return result


def encode_events(events):
    payload = json.dumps({"version": 1, "events": _events(events)},
                         ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return f"<!-- {MARKER}\n{base64.b64encode(payload).decode('ascii')}\n-->"


def decode_events(body):
    """None means legacy prose; a present but invalid block must never fall back."""
    body = body.replace("\r\n", "\n")
    matches = BLOCK.findall(body)
    headers = HEADER.findall(body)
    if not headers:
        return None
    if len(matches) != 1 or len(headers) != 1:
        raise ValueError("malformed or unsupported notification block")
    try:
        payload = json.loads(base64.b64decode(matches[0], validate=True).decode("utf-8"))
    except (binascii.Error, UnicodeError, ValueError) as exc:
        raise ValueError("invalid notification payload") from exc
    if not isinstance(payload, dict) or type(payload.get("version")) is not int or payload["version"] != 1:
        raise ValueError("unsupported notification version")
    return _events(payload.get("events"))


def digest_line(event):
    description = f"PR {event['kind']}" if "kind" in event else "new issue"
    if "delta" in event:
        description += f" (+{event['delta']})"
    return f"- **{description}** {code(event.get('key', '?'))} {code(event.get('title', '')[:200])}"
