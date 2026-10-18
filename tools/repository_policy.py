"""Local contribution restrictions from RULES.md; shared by every screening entry."""

ACCOUNT = "inchang-ing"
BLOCKED_OWNERS = {"pallets", "python-jsonschema", "textualize", "pre-commit"}
BLOCKED_REPOS = {
    "sqlalchemy/sqlalchemy", "encode/httpx", "gradio-app/gradio", "psf/requests",
    "stanfordnlp/dspy", "camel-ai/camel", "matplotlib/matplotlib",
    "useblocks/sphinx-needs", "hypothesisworks/hypothesis",
}
ASSIGN_OWNERS = {"langchain-ai"}
ASSIGN_REPOS = {"huggingface/peft", "pydantic/pydantic-ai"}
REQUIRED_LABELS = {
    "mem0ai/mem0": "accepted",
    "ukgovernmentbeis/inspect_ai": "accepted",
    "mlflow/mlflow": "ready",
}
NON_TESTABLE = {"apache/arrow", "vllm-project/vllm"}


def policy_reason(repo, labels=(), assignees=()):
    """Empty means eligible; missing assignment evidence never satisfies a gate."""
    repo = repo.lower()
    owner = repo.split("/", 1)[0]
    if owner in BLOCKED_OWNERS or repo in BLOCKED_REPOS:
        return f"受限/禁投仓库: {repo}"
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
