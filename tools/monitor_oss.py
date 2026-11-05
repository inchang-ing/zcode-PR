# -*- coding: utf-8 -*-
"""OSS PR 体检: 只扫 STATE.md 的 OSS 段, 拉 state/mergeable/reviewDecision/CI 检查, 报 diff."""
import re, subprocess, pathlib, sys

import github_read
import pr_monitor
from pr_monitor import ci_summary, ci_failed, ci_fingerprint
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pipeline_state import atomic_write_text, file_lock
from pr_state import (PR_STATE_PATH, PR_STATUS_PATH, LEGACY_PATHS,
                      load_pr_state, save_observations)

STATE = str(pathlib.Path(__file__).resolve().parents[1] / "STATE.md")
CANONICAL = PR_STATE_PATH
REPORT = PR_STATUS_PATH

_ROW_RE = pr_monitor.PR_URL


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


def audit_scope():
    """Compare the complete authored OPEN set with registered ledger rows."""
    try:
        items = github_read.api(
            "search/issues?q=author%3Ainchang-ing+type%3Apr+state%3Aopen&per_page=100",
            paginate=True, item_key="items", search=True)
        open_now = set()
        for item in items:
            repo_url, number = item.get("repository_url"), item.get("number")
            if (not isinstance(repo_url, str)
                    or not re.fullmatch(r"https://api.github.com/repos/[^/\s]+/[^/\s]+", repo_url)
                    or type(number) is not int or number <= 0):
                raise ValueError("Invalid search PR identity")
            repo = repo_url.removeprefix("https://api.github.com/repos/").lower()
            if not repo.startswith("inchang-ing/"):
                open_now.add(f"{repo}#{number}")
        tracked = set()
        with open(STATE, encoding="utf-8") as fh:
            for line in fh:
                key = _row_key(line)
                if key and not key.startswith("inchang-ing/"):
                    tracked.add(key)
        blind = sorted(open_now - tracked)
        stale = sorted(tracked - open_now)
        print(f"范围自检: 盲点 {len(blind)}, 过期行 {len(stale)} "
              f"(权威 OPEN {len(open_now)} / 台账 {len(tracked)})")
        for key in blind:
            print(f"  BLIND: {key} —— 同轮补录 STATE.md")
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, KeyError, TypeError) as exc:
        print(f"范围自检: UNKNOWN ({exc})")


def gh(args):
    return github_read.output(args)


def load_keys():
    return pr_monitor.load_keys(STATE)


def fetch(key):
    return pr_monitor.fetch(key, gh, ci_summary=ci_summary, ci_fingerprint=ci_fingerprint)


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
        ch = pr_monitor.change_lines(base, cur, include_ci=True)
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

    audit_scope()
    return 1 if any(v["state"] == "QUERY_ERROR" for v in cur.values()) else 0


def main():
    with file_lock(CANONICAL):
        return run_round()


if __name__ == "__main__":
    sys.exit(main())
