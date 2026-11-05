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
import pathlib, sys

import github_read
import pr_monitor
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pipeline_state import file_lock
from pr_state import (PR_STATE_PATH, PR_STATUS_PATH, LEGACY_PATHS,
                      load_pr_state, save_observations)

STATE = str(pathlib.Path(__file__).resolve().parents[1] / "STATE.md")
CANONICAL = PR_STATE_PATH
REPORT = PR_STATUS_PATH


def gh(args):
    return github_read.output(args)


def load_state_keys():
    """Read the shared OPEN ledger scope, normalized by repository and number."""
    return pr_monitor.load_keys(STATE)


def fetch(key):
    return pr_monitor.fetch(key, gh)


def run_round():
    keys = load_state_keys()
    if not keys:
        print("ERROR: STATE.md 未解析到任何 OPEN 在飞行,检查台账格式")
        return 1

    base = load_pr_state(CANONICAL, LEGACY_PATHS)
    keys = sorted({key.lower() for key in keys})
    with ThreadPoolExecutor(max_workers=4) as executor:
        cur = dict(zip(keys, executor.map(fetch, keys)))

    open_n = len([k for k, v in cur.items() if v["state"] == "OPEN"])
    qerr_n = len([k for k, v in cur.items() if v["state"] == "QUERY_ERROR"])
    # 始终打印当前 scope 快照(20 行结构化状态表,非长篇 prose)
    print(f"当前在飞 scope = {open_n} OPEN / 解析到 {len(cur)} 个 ledger key"
          + (f" (⚠️ {qerr_n} 个查询失败,见下)" if qerr_n else ""))
    print(f"{'key':52} {'state':9} {'review':16} {'merge'}")
    print("-" * 92)
    for key in sorted(cur):
        v = cur[key]
        print(f"{key:52} {v['state']:9} {v['reviewDecision']:16} {v['mergeable']}")

    # diff 报告(仅变化时提示)
    if not base:
        print("-" * 92)
        print(f"首次查询({len(cur)} 个 key)，成功结果将写入 pr_state.json")
    else:
        changes = pr_monitor.change_lines(base, cur)
        print("-" * 92)
        if changes:
            print("本轮变化:")
            for c in changes:
                print("  " + c)
        else:
            print("无变化(仅 GitHub 时间戳可能更新)")

    if not save_observations(CANONICAL, base, cur, REPORT):
        print("本轮无成功查询，未初始化 pr_state.json；旧基线保留")

    return 1 if qerr_n else 0


def main():
    with file_lock(CANONICAL):
        return run_round()


if __name__ == "__main__":
    sys.exit(main())
