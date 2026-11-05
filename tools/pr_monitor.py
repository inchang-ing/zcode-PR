"""Shared PR scope, observation and change rules; command entry points own output."""
import hashlib
import json
from pathlib import Path
import re
import time

from pr_state import utc_now

PR_URL = re.compile(r"github\.com/([^/\s]+)/([^/\s)]+)/pull/(\d+)")
FIELDS = "state,reviewDecision,mergeable,updatedAt,url,createdAt,mergedAt,closedAt,headRefOid"


def load_keys(path):
    keys = {}
    for line in Path(path).read_text(encoding="utf-8", errors="ignore").splitlines():
        if not re.search(r"\bOPEN\b", line) or "原 OPEN(" in line:
            continue
        for match in PR_URL.finditer(line):
            repo, number = f"{match[1]}/{match[2]}".lower(), int(match[3])
            keys[f"{repo}#{number}"] = {"repo": repo, "num": number}
    return keys


def ci_summary(roll):
    if roll == []:
        return "no-checks"
    if not isinstance(roll, list):
        return "1UNKNOWN"
    counts = dict(ok=0, fail=0, pending=0, error=0, skip=0, unknown=0)
    for check in roll:
        value = None
        if isinstance(check, dict):
            if "status" in check:
                value = check.get("conclusion") if check["status"] == "COMPLETED" else check["status"]
            else:
                value = check.get("state")  # Legacy StatusContext, not CheckRun.
        if value == "SUCCESS":
            kind = "ok"
        elif value == "FAILURE":
            kind = "fail"
        elif value in ("ERROR", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE", "STALE"):
            kind = "error"
        elif value in ("IN_PROGRESS", "QUEUED", "PENDING", "EXPECTED", "WAITING", "REQUESTED"):
            kind = "pending"
        elif value in ("SKIPPED", "NEUTRAL"):
            kind = "skip"
        else:
            kind = "unknown"
        counts[kind] += 1
    return (f"{counts['ok']}✓/{counts['fail']}✗/{counts['pending']}…/{counts['error']}ERR"
            f"/{counts['skip']}SKIP/{counts['unknown']}UNKNOWN")


def ci_failed(ci):
    # Unknown results need attention too; never silently count them as healthy.
    return not isinstance(ci, str) or any(int(n) > 0 for n in re.findall(r"(\d+)(?:✗|ERR|UNKNOWN)", ci))


def ci_fingerprint(roll):
    """Identify the actual check observations, independent of API result order.

    Counts cannot distinguish swapped failures or reruns. Unknown/malformed check
    data has no acknowledgeable fingerprint, even when its summary looks healthy.
    """
    if not isinstance(roll, list):
        return None
    checks = []
    for check in roll:
        if not isinstance(check, dict) or "1UNKNOWN" in ci_summary([check]):
            return None
        if "status" in check:
            if check.get("status") not in {"COMPLETED", "IN_PROGRESS", "QUEUED", "PENDING", "WAITING", "REQUESTED"}:
                return None
            kind, name = "CheckRun", check.get("name")
            identity = (check.get("id"), check.get("detailsUrl"), check.get("startedAt"))
            fields = ("id", "name", "workflowName", "detailsUrl", "status", "conclusion", "startedAt", "completedAt")
        else:
            if check.get("state") not in {"SUCCESS", "FAILURE", "ERROR", "PENDING", "EXPECTED"}:
                return None
            kind, name = "StatusContext", check.get("context")
            identity = (check.get("id"), check.get("targetUrl"), check.get("createdAt"), check.get("startedAt"))
            fields = ("id", "context", "targetUrl", "state", "createdAt", "startedAt")
        if (not isinstance(name, str) or not name.strip()
                or check.get("__typename", kind) != kind
                or not any(isinstance(value, str) and value.strip() for value in identity)
                or any(check.get(field) is not None and not isinstance(check[field], str) for field in fields)):
            return None
        checks.append({"type": kind, **{field: check.get(field) for field in fields}})
    serialized = sorted(json.dumps(check, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
                        for check in checks)
    return hashlib.sha256(json.dumps(serialized, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def fetch(key, query, *, ci_summary=None, ci_fingerprint=None):
    repo, number = key.rsplit("#", 1)
    fields = FIELDS + (",statusCheckRollup,title" if ci_summary is not None else "")
    error = ""
    for attempt in range(2):
        try:
            data = json.loads(query(["pr", "view", number, "--repo", repo, "--json", fields]))
            if data.get("state") not in {"OPEN", "CLOSED", "MERGED"}:
                raise ValueError("PR response has no valid state")
            observed = {"state": "MERGED" if data.get("mergedAt") else data["state"],
                        "reviewDecision": data.get("reviewDecision") or "-",
                        "mergeable": data.get("mergeable") or "-",
                        "updatedAt": data.get("updatedAt") or "-", "url": data.get("url") or "-",
                        "headRefOid": data.get("headRefOid"), "createdAt": data.get("createdAt"),
                        "mergedAt": data.get("mergedAt"), "closedAt": data.get("closedAt"),
                        "checked_at": utc_now()}
            if ci_summary is not None:
                observed.update(ci=ci_summary(data.get("statusCheckRollup")),
                                ci_head_oid=data.get("headRefOid"),
                                ci_fingerprint=ci_fingerprint(data.get("statusCheckRollup")),
                                ci_checked_at=observed["checked_at"], title=data.get("title", ""))
            return observed
        except FileNotFoundError as exc:
            error = str(exc)
            break
        except Exception as exc:
            error = str(exc)
            if isinstance(exc.__cause__, FileNotFoundError):
                break  # The shared reader preserves the missing executable cause.
            if attempt == 0:
                time.sleep(2)
    return {"state": "QUERY_ERROR", "reviewDecision": "-", "mergeable": "-",
            "updatedAt": "-", "url": "-", "ci": "-", "title": "",
            "_err": error, "checked_at": utc_now()}


def changes(previous, current, *, include_ci=False):
    """Return stable semantic changes; UNKNOWN mergeability is transient."""
    result = []
    for key in sorted(current):
        value, old = current[key], previous.get(key, {})
        if value["state"] == "QUERY_ERROR":
            continue
        if old.get("state") is None and value["state"] == "OPEN":
            result.append((key, "新增在飞", None, None))
        elif old.get("state") == "OPEN" and value["state"] != "OPEN":
            result.append((key, "离场/合并", old["state"], value["state"]))
        elif old.get("state") == "OPEN" and value["state"] == "OPEN":
            for field, kind in (("reviewDecision", "评审"), ("mergeable", "mergeable")):
                before, after = old.get(field, "-"), value.get(field, "-")
                if before != after and (field != "mergeable" or "UNKNOWN" not in (before, after)):
                    result.append((key, kind, before, after))
            if include_ci and (value.get("ci") != old.get("ci")
                               or value.get("ci_fingerprint") != old.get("ci_fingerprint")):
                detail = "（检查或运行已变化）" if value.get("ci") == old.get("ci") else ""
                result.append((key, "CI", old.get("ci"), str(value.get("ci")) + detail))
    return result


def change_lines(previous, current, *, include_ci=False):
    return [f"[{kind}] {key}" + (f": {before} -> {after}" if before is not None else "")
            for key, kind, before, after in changes(previous, current, include_ci=include_ci)]
