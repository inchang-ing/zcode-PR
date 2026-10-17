#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
差异驱动监控入口(修正版 v_final)。

设计要点(来自 2026-10-01 用户指令 + 纠错):
- 唯一真相源 = GitHub,不是飞书。飞书只是 Actions 镜像的通知输出,脆弱不可解析。
- scope 由 STATE.md 台账锚定,不扫全账号(全账号 open PR 含大量历史噪声 PR)。
- 解析必须覆盖两种在飞格式:
    * 表格行  `| [#N](url) | owner/repo | OPEN(...) | notes |`
    * bullet 行 `- **[#N](url)** OPEN(...)`
  注意:pyyaml #967 曾因"只在 prose 枚举、没有 OPEN( 行"而被任何行扫描逻辑漏掉 -> 已补真实台账行。
- 每轮只报 diff(新增在飞 / 离场合并 / 评审变化 / mergeable 变化),不重灌全景。

gh 调用统一用 `--repo owner/repo NUM`,避免 `repo#num` 形式触发的 git 仓库解析错误。
"""
import subprocess, json, re, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pipeline_state import file_lock
from pr_state import (PR_STATE_PATH, PR_STATUS_PATH, LEGACY_PATHS,
                      load_pr_state, save_observations, utc_now)

GH = "C:/Program Files/GitHub CLI/gh.exe"
STATE = "E:/zcode-PR/STATE.md"
CANONICAL = PR_STATE_PATH
REPORT = PR_STATUS_PATH
CWD = "C:/Users/ROG"  # 避免 gh 在 zcode-PR 下找 .git 报错


def gh(args):
    r = subprocess.run([GH] + args, capture_output=True, text=True, timeout=60, cwd=CWD)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} -> {r.stderr.strip()[:120]}")
    return r.stdout.strip()


def load_state_keys():
    """返回 {'owner/repo#num': {'repo':..., 'num':...}} —— 仅含状态列含 OPEN( 的行。

    排除 MERGED/CLOSED 行内历史文字"原 OPEN(...)"(如 agno #10654 / deer-flow #6048
    的备注"原 OPEN(09-28..."),否则会被宽松的 OPEN( 匹配误抓。
    """
    txt = pathlib.Path(STATE).read_text(encoding="utf-8", errors="ignore")
    keys = {}
    row_re = re.compile(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)")
    for line in txt.splitlines():
        if "OPEN(" not in line:
            continue
        if "原 OPEN(" in line:   # 历史备注,非当前在飞状态
            continue
        for m in row_re.finditer(line):
            owner, repo, num = m.group(1), m.group(2), m.group(3)
            keys[f"{owner}/{repo}#{num}"] = {"repo": f"{owner}/{repo}", "num": int(num)}
    return keys


def fetch(key):
    repo, num = key.split("#")
    last_err = ""
    for attempt in range(2):  # 单次重试,规避 gh 瞬时限流抖动
        try:
            out = gh(["pr", "view", str(num), "--repo", repo,
                      "--json", "state,reviewDecision,mergeable,updatedAt,url"])
            d = json.loads(out)
            if d.get("state") not in {"OPEN", "CLOSED", "MERGED"}:
                raise ValueError("PR response has no valid state")
            return {
                "state": (d.get("state") or "?").upper(),
                "reviewDecision": d.get("reviewDecision") or "-",
                "mergeable": d.get("mergeable") or "-",
                "updatedAt": d.get("updatedAt") or "-",
                "url": d.get("url") or "-",
                "checked_at": utc_now(),
            }
        except Exception as e:
            last_err = str(e)
            import time
            time.sleep(2)
    return {"state": "QUERY_ERROR", "reviewDecision": "-", "mergeable": "-",
            "updatedAt": "-", "url": "-", "_err": last_err, "checked_at": utc_now()}


def run_round():
    keys = load_state_keys()
    if not keys:
        print("ERROR: STATE.md 未解析到任何 OPEN( 在飞行,检查台账格式")
        return

    base = load_pr_state(CANONICAL, LEGACY_PATHS)
    cur = {}
    for key in sorted(keys):
        cur[key] = fetch(key)

    open_n = len([k for k, v in cur.items() if v["state"] == "OPEN"])
    qerr_n = len([k for k, v in cur.items() if v["state"] == "QUERY_ERROR"])
    # 始终打印当前 scope 快照(20 行结构化状态表,非长篇 prose)
    print(f"当前在飞 scope = {open_n} OPEN / 解析到 {len(cur)} 个 ledger key"
          + (f" (⚠️ {qerr_n} 个查询失败,见下)" if qerr_n else ""))
    print(f"{'key':52} {'state':9} {'review':16} {'merge'}")
    print("-" * 92)
    for key in sorted(cur):
        v = cur[key]
        flag = ""
        if key in base and v["state"] != "QUERY_ERROR":
            b = base[key]
            if b.get("state") == "OPEN" and v["state"] != "OPEN":
                flag = "  << 离场/合并"
            elif b.get("reviewDecision") != v["reviewDecision"] and v["state"] == "OPEN":
                flag = f"  << 评审 {b.get('reviewDecision','-')}->{v['reviewDecision']}"
            elif b.get("mergeable") != v["mergeable"] and v["state"] == "OPEN":
                flag = f"  << mergeable {b.get('mergeable','-')}->{v['mergeable']}"
        print(f"{key:52} {v['state']:9} {v['reviewDecision']:16} {v['mergeable']}{flag}")

    # diff 报告(仅变化时提示)
    if not base:
        print("-" * 92)
        print(f"首次查询({len(cur)} 个 key)，成功结果将写入 pr_state.json")
    else:
        changes = []
        for key in sorted(cur):
            v, b = cur[key], base.get(key, {})
            if v["state"] == "QUERY_ERROR":
                continue  # 瞬时限流/抖动,不误报离场
            if b.get("state") is None and v["state"] == "OPEN":
                changes.append(f"[新增在飞] {key}")
            elif v["state"] != "OPEN" and b.get("state") == "OPEN":
                changes.append(f"[离场/合并] {key}: {b.get('state')} -> {v['state']}")
            elif v["state"] == "OPEN" and b.get("state") == "OPEN":
                if v["reviewDecision"] != b.get("reviewDecision"):
                    changes.append(f"[评审变化] {key}: {b.get('reviewDecision','-')} -> {v['reviewDecision']}")
                if v["mergeable"] != b.get("mergeable"):
                    changes.append(f"[mergeable] {key}: {b.get('mergeable','-')} -> {v['mergeable']}")
        print("-" * 92)
        if changes:
            print("本轮变化:")
            for c in changes:
                print("  " + c)
        else:
            print("无变化(仅 GitHub 时间戳可能更新)")

    if not save_observations(CANONICAL, base, cur, REPORT):
        print("本轮无成功查询，未初始化 pr_state.json；旧基线保留")


def main():
    with file_lock(CANONICAL):
        run_round()


if __name__ == "__main__":
    main()
