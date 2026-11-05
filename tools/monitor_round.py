#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""权威仓库池 单轮扫描器 (v4 纪律: timeline 验撞车 + assignee + 软认领)。
用法: python monitor_round.py [--out PATH] [repo ...]   不传仓库=全量池。
输出: round_candidates.json (通过 v4 基础过滤的候选), 并打印摘要。
"""
import argparse, subprocess, json, sys, time
from pathlib import Path
from datetime import datetime, timezone

from gh_checks import issue_errors, linked_prs, comment_bodies
from pipeline_state import atomic_write_json, file_lock, read_json_object
from task_state import TaskStore
from discovery_state import is_consumed, load_consumed, record_consumed
from claim_rules import SOFT, NOT_READY
from repository_policy import policy_reason
from pr_state import utc_now
from candidate_rules import contribution_kind

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

LIMIT = 10  # 每仓新候选发现上限；已有候选另做精确复核

def gh(args, retries=4):
    for i in range(retries):
        try:
            p = subprocess.run(["gh"]+args, capture_output=True, text=True,
                               encoding="utf-8", timeout=90)
            if p.returncode == 0:
                return p.stdout
            err = (p.stderr or "").lower()
            if "rate limit" in err or "abuse" in err or "secondary" in err or p.returncode == 62:
                if i + 1 < retries:
                    wait = min(60, 15*(i+1))
                    print(f"  [rate-limit backoff {wait}s]", file=sys.stderr)
                    time.sleep(wait)
                continue
            return None
        except subprocess.TimeoutExpired:
            print("  [timeout]", file=sys.stderr)
            if i + 1 < retries:
                time.sleep(10)
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

def get_issue(repo, number):
    raw = gh(["issue", "view", str(number), "--repo", repo,
              "--json", "number,title,createdAt,state,labels,assignees,body"])
    try:
        issue = json.loads(raw)
        if (not isinstance(issue, dict) or issue_errors(issue)
                or type(issue.get("number")) is not int or issue["number"] != number
                or not isinstance(issue.get("title"), str)):
            return None
        return issue
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

def scan(repos, out_path, issue_lists=None, failed_issues=()):
    print(f"POOL size = {len(repos)} (全量 {len(POOL)})", flush=True)
    shortlist = []
    scanned = 0
    successful_repos = 0
    checked = set()
    failed = set()
    failed_issues = set(failed_issues)
    previous = json.loads(Path(out_path).read_text(encoding="utf-8-sig")) if Path(out_path).exists() else []
    if not isinstance(previous, list):
        raise ValueError("Invalid candidate snapshot")
    previous_kinds = {(c["repo"].lower(), c["number"]): c.get("kind", "bug") for c in previous}
    for repo in repos:
        issues = issue_lists.get(repo) if issue_lists is not None else get_issues(repo)
        if issues is None:
            failed.add(repo.lower())
            print(f"  SKIP {repo} (issue list 失败/无权限)", flush=True); continue
        successful_repos += 1
        issues = list(issues)
        if issue_lists is None:
            # A limited list cannot establish that an older candidate was closed.
            listed = {issue["number"] for issue in issues}
            for old in previous:
                if old["repo"].lower() != repo.lower() or old["number"] in listed:
                    continue
                listed.add(old["number"])
                issue = get_issue(repo, old["number"])
                if issue is None:
                    failed_issues.add((repo.lower(), old["number"]))
                else:
                    issues.append(issue)
        checked.update((repo.lower(), issue["number"]) for issue in issues)
        scanned += len(issues)
        for it in issues:
            errors = issue_errors(it)
            assignees = it.get("assignees")
            if it.get("state") == "CLOSED":
                continue
            body = it.get("body") if isinstance(it.get("body"), str) else ""
            if SOFT.search(body) or NOT_READY.search(body):
                continue  # 软认领(正文) -> 弃
            raw_labels = it.get("labels")
            labels = [label["name"].lower() for label in raw_labels
                      if isinstance(label, dict) and isinstance(label.get("name"), str)] \
                if isinstance(raw_labels, list) else []
            names = [a["login"] for a in assignees] if not errors else []
            kind = it.get('_kind') or previous_kinds.get((repo.lower(), it['number'])) or contribution_kind(labels)
            if not errors and policy_reason(repo, labels, names, kind=kind):
                continue
            n = it["number"]
            pr = has_linked_pr(repo, n)
            if pr is True:
                continue  # timeline 有关联 PR -> 撞车 -> 弃
            pr_unknown = (pr is None)
            cmts = get_comments(repo, n)
            if cmts and any(SOFT.search(c) or NOT_READY.search(c) for c in cmts):
                continue  # 软认领(评论) -> 弃
            check_errors = list(errors)
            if pr_unknown:
                check_errors.append("timeline 请求或响应校验失败")
            if cmts is None:
                check_errors.append("comments 请求或响应校验失败")
            shortlist.append({
                "repo": repo, "number": n, "title": it["title"],
                "kind": kind,
                "checked_at": utc_now(),
                "createdAt": it.get("createdAt"),
                "is_bug": any("bug" in l for l in labels),
                "labels": labels,
                "assignees": names,
                "pr_unknown": pr_unknown,
                "cmt_unknown": (cmts is None),
                "issue_unknown": bool(errors),
                "check_errors": check_errors,
                "url": f"https://github.com/{repo}/issues/{n}",
            })
        time.sleep(0.3)
    for old in previous:
        if (old["repo"].lower(), old["number"]) not in checked:
            if (old["repo"].lower(), old["number"]) in failed_issues:
                old = dict(old, checked_at="", issue_unknown=True, check_errors=["本轮 issue 读取失败，须重新核验"])
            elif old["repo"].lower() in failed:
                old = dict(old, checked_at="", issue_unknown=True, check_errors=["本轮仓库扫描失败，须重新核验"])
            shortlist.append(old)
    if not successful_repos:
        print("FAILED. 所有仓库扫描失败，保留已有候选快照", file=sys.stderr)
        if previous:
            atomic_write_json(out_path, shortlist)
        return 1
    atomic_write_json(out_path, shortlist)
    print(f"DONE. scanned_issues={scanned}, shortlist={len(shortlist)} -> {out_path}", flush=True)
    if successful_repos < len(repos):
        print(f"PARTIAL. 成功仓库={successful_repos}/{len(repos)}，失败仓库需重新扫描",
              file=sys.stderr)
        return 1
    if failed_issues:
        print(f"PARTIAL. {len(failed_issues)} 个 issue 精确核验失败，已保留为待核验", file=sys.stderr)
        return 1
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    default = Path(__file__).resolve().parents[1] / "round_candidates.json"
    parser.add_argument("--out", default=str(default),
                        help="候选快照路径；--pending 使用自定义路径时保留待核验收件箱")
    parser.add_argument("repos", nargs="*")
    parser.add_argument("--pending", action="store_true", help="核验增量监控发现的精确 issue")
    args = parser.parse_args(argv)
    canonical_output = Path(args.out).resolve() == default
    if args.pending:
        root = default.parent
        inbox_path = root / "tools/fresh_candidates.json"
        result = 0
        # Serialize scans before any API work; discovery needs only the short inbox lock.
        with file_lock(args.out):
            with file_lock(inbox_path):
                inbox = read_json_object(inbox_path)
            now = datetime.now(timezone.utc)
            tasks = TaskStore(root=root)
            receipts = load_consumed(root)
            consumed_keys, newly_checked = set(), {}
            groups, failed_issues = {}, set()
            skipped = 0
            for key, item in inbox.items():
                decision = tasks.decision(key, now)
                if decision['blocked']:
                    skipped += 1
                    continue
                if is_consumed(receipts, key, item, decision):
                    consumed_keys.add(key)
                    continue
                repo = item['repo']
                groups.setdefault(repo, [])
                issue = get_issue(repo, item['number'])
                if issue is None:
                    failed_issues.add((repo.lower(), item['number']))
                    continue
                issue['_kind'] = item.get('kind')
                groups[repo].append(issue)
            if skipped:
                print(f"SKIP {skipped} 个已处理/延期任务，保留记录，等待显式重开或到期")
            if groups:
                # Include existing candidates so targeted checks cannot remove siblings.
                result = scan(list(groups), args.out, groups, failed_issues)
                snapshot = json.loads(Path(args.out).read_text(encoding='utf-8-sig'))
                unknown = {(item['repo'].lower(), item['number']) for item in snapshot
                           if any(item.get(flag) for flag in
                                  ('pr_unknown', 'cmt_unknown', 'issue_unknown', 'check_errors'))}
                checked = {(repo.lower(), item['number']) for repo, items in groups.items()
                           for item in items}
                resolved = checked - unknown
                newly_checked = {key: item for key, item in inbox.items()
                                 if (item['repo'].lower(), item['number']) in resolved}
                if failed_issues or checked & unknown:
                    print("PARTIAL. 未完成核验的 issue 已保留，可再次运行 --pending", file=sys.stderr)
                    result = 1
            if canonical_output and (newly_checked or consumed_keys):
                with file_lock(inbox_path):
                    current = read_json_object(inbox_path)
                    removable = {key for key in newly_checked.keys() | consumed_keys
                                 if current.get(key) == inbox[key]}
                    # Receipt first: a failed deletion can be retried without network.
                    record_consumed(root, {key: newly_checked[key] for key in removable
                                           if key in newly_checked}, checked_at=now.isoformat())
                    remaining = {key: item for key, item in current.items() if key not in removable}
                    if remaining != current:
                        atomic_write_json(inbox_path, remaining)
    else:
        with file_lock(args.out):
            result = scan(args.repos or POOL, args.out)
    if canonical_output:
        from work_queue import refresh
        try:
            refresh()
        except (ValueError, OSError, RuntimeError) as exc:
            print(f'候选扫描已保存，队列视图刷新失败；运行 work_queue.py refresh 重试: {exc}', file=sys.stderr)
            return result or 2
    return result

if __name__ == "__main__":
    sys.exit(main())
