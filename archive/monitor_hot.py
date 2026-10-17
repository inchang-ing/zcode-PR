import subprocess, json, sys, re, time

# 热门/高活跃仓库（python 可贡献 bug-fix 为主）。deepchecks/kedro 已达在飞上限(各1)，本轮不新开。
REPOS = [
    "BerriAI/litellm",
    "chroma-core/chroma",
    "mem0ai/mem0",
    "sentence-transformers/sentence-transformers",
    "langchain-ai/langchain",
    "pydantic/pydantic-ai",
    "langflow-ai/langflow",
    "microsoft/autogen",
    "huggingface/transformers",
    "huggingface/diffusers",
    "haystack-ai/haystack",
    "stanfordnlp/dspy",
    "optuna/optuna",
    "mlflow/mlflow",
    "gradio-app/gradio",
    "langchain-ai/langgraph",
    "dask/dask",
    "explosion/spaCy",
    "cleanlab/cleanlab",
    "huggingface/peft",
]

CLAIM = re.compile(
    r"(i('d| would) like to (take|work on|handle|claim)|"
    r"i('m| am) (happy to|planning to|going to|working on|on it|taking)|"
    r"happy to (open|submit|create|prepare) (a |the )?pr|"
    r"i can (take|work on|handle)|"
    r"i('ve| have) (started|opened|submitted|created)|"
    r"taking this|claiming this|i will (work on|handle|fix)|"
    r"let me (take|work on|handle)|"
    r"i('m| am) (on it|interested in))", re.I)

def gh(args, timeout=30):
    try:
        r = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=timeout)
        return r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT"

def has_collision(repo, num):
    out, err = gh(["api", f"repos/{repo}/issues/{num}/timeline", "--paginate"])
    if not out:
        return None
    try:
        evs = json.loads(out)
    except Exception:
        return None
    for ev in evs:
        if ev.get("event") == "cross-referenced":
            src = ev.get("source") or {}
            iss = src.get("issue") or {}
            if iss.get("pull_request"):
                return True
    return False

def soft_claimed(repo, num):
    body, _ = gh(["issue", "view", "-R", repo, str(num), "--json", "body,comments"])
    try:
        d = json.loads(body)
    except Exception:
        return False
    text = (d.get("body") or "")
    for c in d.get("comments", []):
        text += "\n" + (c.get("body") or "")
    return bool(CLAIM.search(text))

candidates = []
checked = 0
for repo in REPOS:
    out, err = gh(["issue", "list", "-R", repo, "--state", "open",
                   "--limit", "18",
                   "--json", "number,title,createdAt,comments,url"])
    if not out:
        print(f"[skip] {repo}: issue list empty -> {err[:100]}", file=sys.stderr)
        sys.stdout.flush()
        continue
    try:
        issues = json.loads(out)
    except Exception:
        print(f"[skip] {repo}: issue list failed -> {err[:100]}", file=sys.stderr)
        sys.stdout.flush()
        continue
    # 按创建时间倒序（新版在前），弥补去掉 --sort 后的排序
    issues.sort(key=lambda x: x.get("createdAt") or "", reverse=True)
    if not issues:
        print(f"[empty] {repo}", file=sys.stderr)
        sys.stdout.flush()
        continue
    for it in issues:
        n = it["number"]
        checked += 1
        col = has_collision(repo, n)
        if col is True:
            continue  # 已有关联 PR -> 撞车
        if col is None:
            continue  # 时间线拉取失败 -> 保守跳过
        # 无撞车，查软认领
        if soft_claimed(repo, n):
            continue
        candidates.append({
            "repo": repo, "number": n, "title": it["title"],
            "comments": it.get("comments"), "createdAt": it.get("createdAt"),
            "url": it.get("url"),
        })
        print(f"[CANDIDATE] {repo} #{n}: {it['title'][:70]}", file=sys.stderr)
        sys.stdout.flush()

print("\n===== CANDIDATES (no collision, no soft-claim) =====")
print(json.dumps(candidates, indent=2, ensure_ascii=False))
with open("candidates.json", "w", encoding="utf-8") as f:
    json.dump(candidates, f, ensure_ascii=False, indent=2)
print(f"\nchecked issues={checked}, candidates={len(candidates)}", file=sys.stderr)
