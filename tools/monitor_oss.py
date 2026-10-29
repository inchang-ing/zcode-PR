# -*- coding: utf-8 -*-
"""OSS PR 体检: 只扫 STATE.md 的 OSS 段, 拉 state/mergeable/reviewDecision/CI 检查, 报 diff."""
import re, subprocess, json, pathlib, time, sys
import hashlib
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pipeline_state import atomic_write_text, file_lock
from pr_state import (PR_STATE_PATH, PR_STATUS_PATH, LEGACY_PATHS,
                      load_pr_state, save_observations, utc_now)

GH = "C:/Program Files/GitHub CLI/gh.exe"
STATE = str(pathlib.Path(__file__).resolve().parents[1] / "STATE.md")
CANONICAL = PR_STATE_PATH
REPORT = PR_STATUS_PATH
CWD = "C:/Users/ROG"

_ROW_RE = re.compile(r"github\.com/([^/\s]+)/([^/\s)]+)/pull/(\d+)")


def _row_key(line):
    m = _ROW_RE.search(line)
    return f"{m.group(1)}/{m.group(2)}#{int(m.group(3))}".lower() if (m and "| [" in line) else None


def _fix_row_count(line, kept, header):
    if not line.startswith(header):
        return line
    n = sum(1 for l in kept if _row_key(l))
    return re.sub(r"（\d+）", f"（{n}）", line, count=1)


def reconcile_state_ledger(cur, state_path=STATE):
    """Drop ledger rows whose PR is definitively MERGED/CLOSED and fix the counts.

    Departures used to linger in STATE.md until someone removed them by hand
    (execnet#431 sat merged for 15 days). Query errors and OPEN rows are never
    touched; the file's line endings are preserved as-is.
    Returns the removed ledger lines (stripped), [] when nothing to remove.
    """
    gone = {k.lower() for k, v in cur.items() if v.get("state") in ("MERGED", "CLOSED")}
    if not gone or not pathlib.Path(state_path).exists():
        return []
    with file_lock(state_path):
        try:
            raw = pathlib.Path(state_path).read_bytes()
        except FileNotFoundError:
            return []
        newline = "\r\n" if b"\r\n" in raw else "\n"
        text = raw.decode("utf-8")
        head, sep, tail = text.partition("## 个人 fork")
        removed, rebuilt = [], []
        for section, header in ((head, "## OSS 贡献在飞"), (sep + tail, "## 个人 fork 在飞")):
            lines = section.split(newline)
            kept = [l for l in lines if not (_row_key(l) and _row_key(l) in gone)]
            removed.extend(l.strip() for l in lines
                           if _row_key(l) and _row_key(l) in gone)
            if removed:
                kept = [_fix_row_count(l, kept, header) for l in kept]
            rebuilt.append(newline.join(kept))
        if not removed:
            return []
        atomic_write_text(state_path, rebuilt[0] + rebuilt[1])
        return removed


def gh(args):
    r = subprocess.run([GH] + args, capture_output=True, text=True, timeout=60, cwd=CWD)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} -> {r.stderr.strip()[:120]}")
    return r.stdout.strip()


def load_keys():
    txt = pathlib.Path(STATE).read_text(encoding="utf-8", errors="ignore")
    keys = {}
    for line in txt.splitlines():
        if "github.com" not in line or "/pull/" not in line:
            continue
        if not re.search(r"\bOPEN\b", line):   # 仅含 OPEN/OPEN( 状态的台账行
            continue
        if "原 OPEN(" in line:                # 历史备注,非当前在飞
            continue
        for m in re.finditer(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)", line):
            owner, repo, num = m.group(1), m.group(2), m.group(3)
            keys[f"{owner}/{repo}#{num}".lower()] = {"repo": f"{owner}/{repo}", "num": int(num)}
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


def fetch(key):
    repo, num = key.split("#")
    for attempt in range(2):
        try:
            d = json.loads(gh(["pr", "view", str(num), "--repo", repo, "--json",
                                "state,createdAt,closedAt,mergedAt,updatedAt,mergeable,reviewDecision,statusCheckRollup,title,headRefOid"]))
            if d.get("state") not in {"OPEN", "CLOSED", "MERGED"}:
                raise ValueError("PR response has no valid state")
            st = "MERGED" if d.get("mergedAt") else d["state"]
            return {"state": st, "mergeable": d.get("mergeable") or "-",
                    "reviewDecision": d.get("reviewDecision") or "-",
                    "headRefOid": d.get("headRefOid"),
                    "updatedAt": d.get("updatedAt"),
                    "ci": ci_summary(d.get("statusCheckRollup")),
                    "ci_head_oid": d.get("headRefOid"),
                    "ci_fingerprint": ci_fingerprint(d.get("statusCheckRollup")),
                    "ci_checked_at": utc_now(),
                    "createdAt": d.get("createdAt"), "mergedAt": d.get("mergedAt"),
                    "closedAt": d.get("closedAt"),
                    "title": d.get("title", ""), "checked_at": utc_now()}
        except FileNotFoundError as e:
            last = str(e)
            break
        except Exception as e:
            last = str(e)
            if attempt == 0:
                time.sleep(2)
    return {"state": "QUERY_ERROR", "mergeable": "-", "reviewDecision": "-", "ci": "-", "title": "", "_err": last, "checked_at": utc_now()}


def run_round():
    keys = load_keys()
    if not keys:
        print("ERROR: STATE.md 未解析到在飞行,保留上次 baseline")
        return 1
    base = load_pr_state(CANONICAL, LEGACY_PATHS)
    keys = sorted({key.lower() for key in keys})
    with ThreadPoolExecutor(max_workers=4) as executor:
        cur = dict(zip(keys, executor.map(fetch, keys)))

    open_n = sum(1 for v in cur.values() if v["state"] == "OPEN")
    bad_ci = [(k, v["ci"]) for k, v in cur.items() if v["state"] == "OPEN" and ci_failed(v["ci"])]
    print(f"在飞 scope: {len(cur)} 个 key, {open_n} OPEN"
          + (f" | ⚠️ {len(bad_ci)} 个 OPEN 的 CI 有失败/需处理/未知结果" if bad_ci else ""))
    order = {"CLOSED": 0, "MERGED": 1, "OPEN": 2, "QUERY_ERROR": 3}
    for k in sorted(cur, key=lambda x: (order.get(cur[x]["state"], 9), x)):
        v = cur[k]
        flag = "" if v["state"] == "OPEN" else f"  <<< {v['state']}"
        nc = "  ⚠CI" if (v["state"] == "OPEN" and ci_failed(v["ci"])) else ""
        print(f"{k:46} {v['state']:7} mg={str(v['mergeable']):8} rev={str(v['reviewDecision']):13} CI[{v['ci']}]{flag}{nc}")
        print(f"        {v['title'][:88]}")

    # diff
    if base:
        ch = []
        for k in sorted(cur):
            v, b = cur[k], base.get(k, {})
            if v["state"] == "QUERY_ERROR":
                continue
            if b.get("state") is None and v["state"] == "OPEN":
                ch.append(f"[新增在飞] {k}")
            elif v["state"] != "OPEN" and b.get("state") == "OPEN":
                ch.append(f"[离场] {k}: {b.get('state')} -> {v['state']}")
            elif v["state"] == "OPEN" and b.get("state") == "OPEN":
                if v["reviewDecision"] != b.get("reviewDecision"):
                    ch.append(f"[评审] {k}: {b.get('reviewDecision','-')} -> {v['reviewDecision']}")
                # UNKNOWN is GitHub's transient mergeability computation; only
                # definitive transitions are worth a change line.
                if (v["mergeable"] != b.get("mergeable")
                        and "UNKNOWN" not in (v["mergeable"], b.get("mergeable"))):
                    ch.append(f"[mergeable] {k}: {b.get('mergeable','-')} -> {v['mergeable']}")
                if v["ci"] != b.get("ci") or v.get("ci_fingerprint") != b.get("ci_fingerprint"):
                    detail = "（检查或运行已变化）" if v["ci"] == b.get("ci") else ""
                    ch.append(f"[CI] {k}: {b.get('ci')} -> {v['ci']}{detail}")
        print("-" * 90)
        print("本轮变化:" + ("\n  ".join([""] + ch) if ch else " 无(仅时间戳)"))
    else:
        print("-" * 90)
        print("首次查询，成功结果将写入 pr_state.json")

    if not save_observations(CANONICAL, base, cur, REPORT):
        print("本轮无成功查询，未初始化 pr_state.json；旧基线保留")

    removed = reconcile_state_ledger(cur, state_path=STATE)
    if removed:
        print(f"台账自动清理: 从 STATE.md 移除 {len(removed)} 条已合/已关行")
        for line in removed:
            print(f"  - {line[:100]}")

    return 1 if any(v["state"] == "QUERY_ERROR" for v in cur.values()) else 0


def main():
    with file_lock(CANONICAL):
        return run_round()


if __name__ == "__main__":
    sys.exit(main())
