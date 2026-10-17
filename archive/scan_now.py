import subprocess, json, sys

REPOS = [
    "BerriAI/litellm",
    "chroma-core/chroma",
    "sentence-transformers/sentence-transformers",
    "mem0ai/mem0",
]

def gh(args):
    r = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=30)
    return r.stdout

for repo in REPOS:
    out = gh(["issue", "list", "-R", repo, "--state", "open", "--limit", "8",
              "--json", "number,title,createdAt,comments,labels"])
    try:
        issues = json.loads(out)
    except Exception:
        print(f"{repo}: issue list failed"); sys.stdout.flush(); continue
    if not issues:
        print(f"{repo}: 0 recent open issues"); sys.stdout.flush(); continue
    total = claimed = 0
    open_examples = []
    for it in issues:
        total += 1
        n = it["number"]
        tl = gh(["api", f"repos/{repo}/issues/{n}/timeline", "--paginate"])
        try:
            evs = json.loads(tl)
        except Exception:
            continue
        has_pr = False
        for ev in evs:
            if ev.get("event") == "cross-referenced":
                src = ev.get("source") or {}
                iss = src.get("issue") or {}
                if iss.get("pull_request"):
                    has_pr = True
                    break
        if has_pr:
            claimed += 1
        else:
            open_examples.append((n, (it.get("title") or "")[:46]))
    pct = (claimed / total * 100) if total else 0
    print(f"\n=== {repo} === 抽查{total} | 被占(有PR){claimed}({pct:.0f}%) | 无PR{total-claimed}")
    for n, t in open_examples[:6]:
        print(f"   无PR #{n}: {t}")
    sys.stdout.flush()
