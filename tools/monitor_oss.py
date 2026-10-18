# -*- coding: utf-8 -*-
"""OSS PR 体检: 只扫 STATE.md 的 OSS 段, 拉 state/mergeable/reviewDecision/CI 检查, 报 diff."""
import re, subprocess, json, pathlib, time, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pipeline_state import file_lock
from pr_state import (PR_STATE_PATH, PR_STATUS_PATH, LEGACY_PATHS,
                      load_pr_state, save_observations, utc_now)

GH = "C:/Program Files/GitHub CLI/gh.exe"
STATE = str(pathlib.Path(__file__).resolve().parents[1] / "STATE.md")
CANONICAL = PR_STATE_PATH
REPORT = PR_STATUS_PATH
CWD = "C:/Users/ROG"


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
            keys[f"{owner}/{repo}#{num}"] = {"repo": f"{owner}/{repo}", "num": int(num)}
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
    return any(int(n) > 0 for n in re.findall(r"(\d+)(?:✗|ERR|UNKNOWN)", ci))


def fetch(key):
    repo, num = key.split("#")
    for _ in range(2):
        try:
            d = json.loads(gh(["pr", "view", str(num), "--repo", repo, "--json",
                                "state,mergedAt,mergeable,reviewDecision,statusCheckRollup,title"]))
            if d.get("state") not in {"OPEN", "CLOSED", "MERGED"}:
                raise ValueError("PR response has no valid state")
            st = "MERGED" if d.get("mergedAt") else d["state"]
            return {"state": st, "mergeable": d.get("mergeable") or "-",
                    "reviewDecision": d.get("reviewDecision") or "-",
                    "ci": ci_summary(d.get("statusCheckRollup")),
                    "title": d.get("title", ""), "checked_at": utc_now()}
        except Exception as e:
            time.sleep(2); last = str(e)
    return {"state": "QUERY_ERROR", "mergeable": "-", "reviewDecision": "-", "ci": "-", "title": "", "_err": last, "checked_at": utc_now()}


def run_round():
    keys = load_keys()
    if not keys:
        print("ERROR: STATE.md 未解析到在飞行,保留上次 baseline")
        return
    base = load_pr_state(CANONICAL, LEGACY_PATHS)
    cur = {k: fetch(k) for k in sorted(keys)}

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
                if v["mergeable"] != b.get("mergeable"):
                    ch.append(f"[mergeable] {k}: {b.get('mergeable','-')} -> {v['mergeable']}")
                if v["ci"] != b.get("ci"):
                    ch.append(f"[CI] {k}: {b.get('ci')} -> {v['ci']}")
        print("-" * 90)
        print("本轮变化:" + ("\n  ".join([""] + ch) if ch else " 无(仅时间戳)"))
    else:
        print("-" * 90)
        print("首次查询，成功结果将写入 pr_state.json")

    if not save_observations(CANONICAL, base, cur, REPORT):
        print("本轮无成功查询，未初始化 pr_state.json；旧基线保留")


def main():
    with file_lock(CANONICAL):
        run_round()


if __name__ == "__main__":
    main()
