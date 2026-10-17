#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""权威仓库池 单轮扫描器 (v4 纪律: timeline 验撞车 + assignee + 软认领)。
用法: python monitor_round.py [--out PATH] [repo ...]   不传仓库=全量池。
输出: round_candidates.json (通过 v4 基础过滤的候选), 并打印摘要。
"""
import argparse, subprocess, json, re, sys, time, os

from gh_checks import issue_errors, linked_prs, comment_bodies
from pipeline_state import atomic_write_json, file_lock

CORE = [
    "BerriAI/litellm","chroma-core/chroma","mem0ai/mem0","sentence-transformers/sentence-transformers",
    "langchain-ai/langchain","pydantic/pydantic-ai","langflow-ai/langflow","microsoft/autogen",
    "huggingface/transformers","huggingface/diffusers","haystack-ai/haystack","stanfordnlp/dspy",
    "optuna/optuna","mlflow/mlflow","gradio-app/gradio","langchain-ai/langgraph","dask/dask",
    "explosion/spaCy","cleanlab/cleanlab","huggingface/peft",
]
DATA = ["numpy/numpy","pandas-dev/pandas","scikit-learn/scikit-learn","pola-rs/polars","apache/arrow","sympy/sympy","networkx/networkx"]
WEB  = ["fastapi/fastapi","pydantic/pydantic","Kludex/starlette","pallets/flask","django/django"]
NET  = ["aio-libs/aiohttp","tornadoweb/tornado","encode/httpx","Kludex/uvicorn"]
ORM  = ["sqlalchemy/sqlalchemy","tortoise/tortoise-orm"]
AGENT= ["vllm-project/vllm","run-llama/llama_index","guidance-ai/guidance","crewAIInc/crewAI","microsoft/semantic-kernel"]
VEC  = ["qdrant/qdrant-client","weaviate/weaviate-python-client","vibrantlabsai/ragas","langfuse/langfuse","Arize-ai/phoenix"]
NB   = ["jupyter/notebook","jupyter/nbconvert","pallets/click","fastapi/typer","hydra-ecosystem/hydra"]
POOL = CORE+DATA+WEB+NET+ORM+AGENT+VEC+NB

SOFT = re.compile(
    r"(i'?d\s*like\s*to\s*take|happy\s*to\s*(open|prepare|submit|work)|i'?m\s*(planning|going)\s*to\s*contribute|"
    r"would\s*love\s*to\s*work|can\s*i\s*take\s*this|i'?ll\s*submit\s*a\s*pr|i\s*will\s*submit\s*a\s*pr|"
    r"working\s*on\s*(a|this)\s*(fix|pr)|i'?m\s*on\s*it|taking\s*this|claiming\s*this|"
    r"i\s*can\s*take\s*(this|it)|assign\s*(this|it)\s*to\s*me|already\s*(on\s*it|working)|"
    r"i\s*have\s*a\s*(fix|pr)\s*ready|local\s*fix\s*ready|"
    # 2026-10-13 补: optuna#6898 正文写 "I would like to implement it as Ra1nhy /
    # I will wait for the preferred scope" 属明确自占, 旧正则只覆盖 would like to take → 漏判
    r"would\s*like\s*to\s*implement|i\s*would\s*like\s*to\s*(implement|fix|work|take)|"
    r"i\s*will\s*wait\s*for|waiting\s*for\s*(the\s*)?(preferred|maintainer|green))", re.I)

LIMIT = 10  # 每仓每轮上限

def gh(args, retries=4):
    for i in range(retries):
        try:
            p = subprocess.run(["gh"]+args, capture_output=True, text=True,
                               encoding="utf-8", timeout=90)
            if p.returncode == 0:
                return p.stdout
            err = (p.stderr or "").lower()
            if "rate limit" in err or "abuse" in err or "secondary" in err or p.returncode == 62:
                wait = min(60, 15*(i+1))
                print(f"  [rate-limit backoff {wait}s]", file=sys.stderr); time.sleep(wait); continue
            return None
        except subprocess.TimeoutExpired:
            print("  [timeout]", file=sys.stderr); time.sleep(10)
        except (OSError, UnicodeError):
            return None
    return None

def get_issues(repo):
    out = gh(["issue","list","--repo",repo,"--state","open","--limit",str(LIMIT),
              "--json","number,title,createdAt,state,labels,assignees,body"])
    if not out:
        return None
    try:
        issues = json.loads(out)
        if not isinstance(issues, list) or any(
            not isinstance(issue, dict)
            or type(issue.get("number")) is not int or issue["number"] <= 0
            or not isinstance(issue.get("title"), str)
            for issue in issues
        ):
            return None
        return issues
    except (ValueError, TypeError):
        return None

def has_linked_pr(repo, n):
    out = gh(["api", f"repos/{repo}/issues/{n}/timeline?per_page=100",
              "--paginate", "--slurp"])
    try:
        return bool(linked_prs(out))
    except ValueError as exc:
        print(f"  UNKNOWN {repo}#{n} timeline: {exc}", file=sys.stderr)
        return None

def get_comments(repo, n):
    out = gh(["api", f"repos/{repo}/issues/{n}/comments?per_page=100",
              "--paginate", "--slurp"])
    try:
        return comment_bodies(out)
    except ValueError as exc:
        print(f"  UNKNOWN {repo}#{n} comments: {exc}", file=sys.stderr)
        return None

def scan(repos, out_path):
    print(f"POOL size = {len(repos)} (全量 {len(POOL)})", flush=True)
    shortlist = []
    scanned = 0
    successful_repos = 0
    for repo in repos:
        issues = get_issues(repo)
        if issues is None:
            print(f"  SKIP {repo} (issue list 失败/无权限)", flush=True); continue
        successful_repos += 1
        scanned += len(issues)
        for it in issues:
            errors = issue_errors(it)
            assignees = it.get("assignees")
            if isinstance(assignees, list) and assignees:
                continue  # v4: 已 assign -> 在处理 -> 弃
            if it.get("state") == "CLOSED":
                continue
            body = it.get("body") if isinstance(it.get("body"), str) else ""
            if SOFT.search(body):
                continue  # 软认领(正文) -> 弃
            n = it["number"]
            pr = has_linked_pr(repo, n)
            if pr is True:
                continue  # timeline 有关联 PR -> 撞车 -> 弃
            pr_unknown = (pr is None)
            cmts = get_comments(repo, n)
            if cmts and any(SOFT.search(c) for c in cmts):
                continue  # 软认领(评论) -> 弃
            raw_labels = it.get("labels")
            labels = [label["name"].lower() for label in raw_labels
                      if isinstance(label, dict) and isinstance(label.get("name"), str)] \
                if isinstance(raw_labels, list) else []
            check_errors = list(errors)
            if pr_unknown:
                check_errors.append("timeline 请求或响应校验失败")
            if cmts is None:
                check_errors.append("comments 请求或响应校验失败")
            shortlist.append({
                "repo": repo, "number": n, "title": it["title"],
                "createdAt": it.get("createdAt"),
                "is_bug": any("bug" in l for l in labels),
                "labels": labels,
                "pr_unknown": pr_unknown,
                "cmt_unknown": (cmts is None),
                "issue_unknown": bool(errors),
                "check_errors": check_errors,
                "url": f"https://github.com/{repo}/issues/{n}",
            })
        time.sleep(0.3)
    if not successful_repos:
        print("FAILED. 所有仓库扫描失败，保留已有候选快照", file=sys.stderr)
        return 1
    atomic_write_json(out_path, shortlist)
    print(f"DONE. scanned_issues={scanned}, shortlist={len(shortlist)} -> {out_path}", flush=True)
    if successful_repos < len(repos):
        print(f"PARTIAL. 成功仓库={successful_repos}/{len(repos)}，失败仓库需重新扫描",
              file=sys.stderr)
        return 1
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "round_candidates.json"))
    parser.add_argument("repos", nargs="*")
    args = parser.parse_args(argv)
    with file_lock(args.out):
        return scan(args.repos or POOL, args.out)

if __name__ == "__main__":
    sys.exit(main())
