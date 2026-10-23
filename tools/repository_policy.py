"""Local contribution restrictions from RULES.md; shared by every screening entry."""

ACCOUNT = "inchang-ing"
BLOCKED_OWNERS = {"pallets", "python-jsonschema", "textualize", "pre-commit", "pycqa", "sqlalchemy"}
BLOCKED_REPOS = {
    "sqlalchemy/sqlalchemy", "encode/httpx", "gradio-app/gradio", "psf/requests",
    "stanfordnlp/dspy", "camel-ai/camel", "matplotlib/matplotlib",
    "useblocks/sphinx-needs", "hypothesisworks/hypothesis",
    "ansible/ansible",
}
ASSIGN_OWNERS = {"langchain-ai"}
ASSIGN_REPOS = {"huggingface/peft", "pydantic/pydantic-ai", "modelcontextprotocol/python-sdk"}
REQUIRED_LABELS = {
    "mem0ai/mem0": "accepted",
    "ukgovernmentbeis/inspect_ai": "accepted",
    "mlflow/mlflow": "ready",
}
# Local operational evidence, not a claim that upstream policy was rechecked today.
POLICY_EVIDENCE = {
    "ansible/ansible": {"scope": "repo", "observed_at": "2026-10-23", "source": "https://github.com/ansible/ansible/pull/87712#issuecomment-6349441213", "review": "当前账号贡献被以自主投稿关闭；停止本项目自动投稿和跟进写入，待维护者明确允许后复核"},
    "python-markdown/markdown": {"scope": "repo", "observed_at": "2026-10-23", "source": "https://python-markdown.github.io/contributing/#ai-contributions", "review": "禁止 agent 自主提交 issue、PR、评论；只准备本地材料，作者须自行理解并参与"},
    "pycqa": {"scope": "owner", "observed_at": "2026-10-18", "source": ".workbuddy/memory/blocked-repos.md", "review": "重新确认账号投稿权限后解除"},
    "sqlalchemy": {"scope": "owner", "observed_at": "2026-10-18", "source": ".workbuddy/memory/blocked-repos.md", "review": "重新确认账号访问权限后解除"},
    "modelcontextprotocol/python-sdk": {"scope": "repo", "observed_at": "2026-10-18", "source": ".workbuddy/memory/blocked-repos.md", "review": "每次核验当前账号分配状态"},
    "frappe/frappe": {"scope": "repo", "observed_at": "2026-10-18", "source": ".workbuddy/memory/blocked-repos.md", "review": "须确认当前账号已获 vouched"},
    "geopandas/geopandas": {"scope": "repo", "observed_at": "2026-10-18", "source": ".workbuddy/memory/blocked-repos.md", "review": "须核验现有 issue 上的方案共识"},
}
MANUAL_GATES = {"frappe/frappe": "vouched 资格未核验", "geopandas/geopandas": "方案共识须专项核验",
                "python-markdown/markdown": "禁止 agent 自主提交/评论，须由作者本人理解并参与"}

# These are communication restrictions, not a ban on read-only observation.
INTERACTION_HOLDS = {
    "ansible/ansible": "该账号投稿已被明确拒绝；停止自动跟进写入，保留只读观察",
    "python-markdown/markdown": "只准备本地修复和答复材料；作者须按仓库政策亲自参与沟通",
}
NON_TESTABLE = {"apache/arrow", "vllm-project/vllm"}


def policy_reason(repo, labels=(), assignees=()):
    """Empty means eligible; missing assignment evidence never satisfies a gate."""
    repo = repo.lower()
    owner = repo.split("/", 1)[0]
    if owner in BLOCKED_OWNERS or repo in BLOCKED_REPOS:
        return f"受限/禁投仓库: {repo}"
    if repo in MANUAL_GATES:
        return "人工门禁: " + MANUAL_GATES[repo]
    if repo in NON_TESTABLE:
        return f"非可测仓(重构建/重依赖): {repo}"
    if not isinstance(assignees, (list, tuple)) or any(
            not isinstance(name, str) or not name for name in assignees):
        return "分配人数据无效，需重新核验"
    assigned = {name.lower() for name in assignees}
    if assigned - {ACCOUNT}:
        return "已被 assign 给其他贡献者"
    if (owner in ASSIGN_OWNERS or repo in ASSIGN_REPOS) and ACCOUNT not in assigned:
        return "assign 门禁仓: 须先分配给当前账号"
    required = REQUIRED_LABELS.get(repo)
    if required and (not isinstance(labels, (list, tuple)) or
                     required not in {label.lower() for label in labels if isinstance(label, str)}):
        return f"issue-readiness 门禁仓: 缺少 {required} 标签"
    return ""
