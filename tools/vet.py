#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对 auto_run 判定的 clean 候选做开 PR 前的 v4 终检:
强软认领正则 + "not ready for PR" 检测 + assignee/关联PR/state 复核。
输出 CLEAN / WARN / DROP / UNKNOWN，未知检查必须复核，不能视为通过。
"""
import argparse, json, os, re, subprocess, sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auto_run import load_candidates, is_clean, DispatchedStore  # noqa: E402
from gh_checks import issue_errors, linked_prs, comment_bodies  # noqa: E402

# 强版软认领正则(补 2026-10-13 两个漏判实例:
#   optuna#6898 "I would like to implement it as Ra1nhy / I will wait for the preferred scope"
#   sklearn#35139 "I will be pleased to help fix this bug, which will be my first commit")
SOFT_EXT = re.compile(
    r"(i'?d\s*like\s*to\s*(take|implement|fix|work|submit)|"
    r"happy\s*to\s*(open|prepare|submit|work|help)|"
    r"i'?m\s*(planning|going)\s*to\s*(contribute|fix|implement)|"
    r"would\s*love\s*to\s*(work|fix|implement)|"
    r"can\s*i\s*take\s*this|i'?ll\s*submit\s*a\s*pr|i\s*will\s*submit\s*a\s*pr|"
    r"working\s*on\s*(a|this)\s*(fix|pr)|i'?m\s*on\s*it|taking\s*this|claiming\s*this|"
    r"i\s*can\s*take\s*(this|it)|assign\s*(this|it)\s*to\s*me|already\s*(on\s*it|working)|"
    r"i\s*have\s*a\s*(fix|pr)\s*ready|local\s*fix\s*ready|"
    r"would\s*like\s*to\s*implement|i\s*would\s*like\s*to\s*(implement|fix|work|take)|"
    r"i\s*will\s*wait\s*for|waiting\s*for\s*(the\s*)?(preferred|maintainer|green)|"
    r"(be\s*)?pleased\s*to\s*help\s*(to\s*)?(fix)?|help\s*(to\s*)?fix\s*this\s*bug|"
    r"my\s*first\s*(commit|contribution|pr)|interest\s*in\s*fixing|"
    r"i\s*would\s*(be\s*)?(happy|glad)\s*to|let\s*me\s*(take|fix|try)\s*(this|it)?)", re.I)

NOT_READY = re.compile(
    r"not\s*yet\s*ready\s*for\s*a\s*pr|do\s*not\s*(open|submit)\s*a\s*pr|"
    r"wait\s*(for|until)\s*(triage|maintainer)", re.I)

BLOCKING_LABELS = {"needs triage", "needs investigation", "status:blocked",
                   "blocked", "needs discussion", "wontfix", "invalid"}


def gh(args):
    try:
        p = subprocess.run(["gh"] + args, capture_output=True, text=True,
                           encoding="utf-8", timeout=60)
    except (OSError, subprocess.TimeoutExpired, UnicodeError):
        return None
    return p.stdout if p.returncode == 0 else None


def vet(c):
    out = gh(["issue", "view", str(c.number), "--repo", c.repo,
              "--json", "number,title,state,assignees,labels,body"])
    if not out:
        return "UNKNOWN", "issue 请求失败或超时"
    try:
        d = json.loads(out)
    except (ValueError, TypeError):
        return "UNKNOWN", "issue 返回无效 JSON"
    errors = issue_errors(d)
    if errors:
        return "UNKNOWN", "issue: " + "; ".join(errors)
    if d["state"] != "OPEN":
        return "DROP", f"issue 非 open({d['state']})"
    if d["assignees"]:
        return "DROP", "已被 assign"
    body = d["body"]
    labels = [l["name"] for l in d["labels"]]

    tl = gh(["api", f"repos/{c.repo}/issues/{c.number}/timeline?per_page=100",
             "--paginate", "--slurp"])
    try:
        prs = linked_prs(tl)
        if prs:
            return "DROP", f"timeline 有关联 PR {prs}"
    except ValueError as exc:
        errors.append(f"timeline: {exc}")

    cm = gh(["api", f"repos/{c.repo}/issues/{c.number}/comments?per_page=100",
             "--paginate", "--slurp"])
    comments = []
    try:
        comments = comment_bodies(cm)
    except ValueError as exc:
        errors.append(f"comments: {exc}")
    if SOFT_EXT.search(body):
        return "DROP", "正文软认领/自占"
    if any(SOFT_EXT.search(x or "") for x in comments):
        return "DROP", "评论软认领"
    if NOT_READY.search(body) or any(NOT_READY.search(comment) for comment in comments):
        return "DROP", "仓内标注 not ready for PR"
    if errors:
        return "UNKNOWN", "; ".join(errors)
    hit = [l for l in labels if l.lower() in BLOCKING_LABELS]
    if hit:
        return "WARN", f"标签提示未 triage/受阻: {hit}"
    return "CLEAN", ""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", help="候选 JSON 路径，默认 round_candidates.json")
    args = parser.parse_args(argv)
    cands = load_candidates(args.candidates) if args.candidates else load_candidates()
    store = DispatchedStore()
    clean = []
    res = {"CLEAN": [], "WARN": [], "DROP": [], "UNKNOWN": []}
    for c in cands:
        unknown = c.issue_unknown or c.pr_unknown or c.cmt_unknown
        # Evaluate policy and dedup separately; the original unknown flags still block vet.
        policy_candidate = replace(c, issue_unknown=False, pr_unknown=False,
                                   cmt_unknown=False) if unknown else c
        accepted, reason = is_clean(policy_candidate, store)
        if not accepted:
            print(f"  SKIP  {c.key}: {reason}", flush=True)
        elif unknown:
            why = "快照检查未完成，需重扫: " + "; ".join(
                c.check_errors or [name for name in ("issue_unknown", "pr_unknown", "cmt_unknown")
                                   if getattr(c, name)])
            res["UNKNOWN"].append((c, why))
            print(f"  UNKNOWN {c.key}: {why}", flush=True)
        else:
            clean.append(c)
    print(f"is_clean 通过: {len(clean)}", flush=True)
    for c in clean:
        st, why = vet(c)
        res[st].append((c, why))
        print(f"  {st:5} {c.key}: {why}", flush=True)
    print("--- " + " ".join(f"{status}={len(items)}" for status, items in res.items()))
    for c, _ in res["CLEAN"]:
        print(f"CLEAN_CAND|{c.key}|{c.title[:90]}")
    return 1 if res["UNKNOWN"] else 0


if __name__ == "__main__":
    sys.exit(main())
