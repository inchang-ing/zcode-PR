#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对 auto_run 判定的 clean 候选做开 PR 前的 v4 终检:
强软认领正则 + "not ready for PR" 检测 + assignee/关联PR/state 复核。
输出 CLEAN / WARN / DROP / UNKNOWN，未知检查必须复核，不能视为通过。
"""
import argparse, json, os, subprocess, sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auto_run import load_candidates, is_clean, _is_real_bug, DispatchedStore  # noqa: E402
from gh_checks import issue_errors, linked_prs, comment_bodies  # noqa: E402

from claim_rules import SOFT as SOFT_EXT, NOT_READY
from repository_policy import policy_reason

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
    if isinstance(d, dict) and (not isinstance(d.get("title"), str) or not d["title"].strip()):
        errors.append("title 缺失或无效")
    if errors:
        return "UNKNOWN", "issue: " + "; ".join(errors)
    if d["state"] != "OPEN":
        return "DROP", f"issue 非 open({d['state']})"
    body = d["body"]
    labels = [l["name"] for l in d["labels"]]
    reason = policy_reason(c.repo, labels, [a["login"] for a in d["assignees"]])
    if reason:
        return "DROP", reason

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
    # Match monitor_round's label evidence; the snapshot's is_bug may be stale.
    live_candidate = replace(c, title=d["title"], labels=labels,
                             is_bug=any("bug" in label.lower() for label in labels))
    if not _is_real_bug(live_candidate):
        return "DROP", "实时标题/标签不再符合 bug 候选条件"
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
