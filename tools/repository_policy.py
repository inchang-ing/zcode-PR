"""Local contribution restrictions from RULES.md; shared by every screening entry."""

ACCOUNT = "inchang-ing"
BLOCKED_OWNERS = {"pallets", "python-jsonschema", "textualize", "pre-commit", "pycqa", "sqlalchemy"}
BLOCKED_REPOS = {
    "sqlalchemy/sqlalchemy", "encode/httpx", "gradio-app/gradio", "psf/requests",
    "stanfordnlp/dspy", "camel-ai/camel", "matplotlib/matplotlib",
    "useblocks/sphinx-needs", "hypothesisworks/hypothesis",
    "ansible/ansible", "pypa/packaging", "google/jax", "jax-ml/jax",
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
    "pypa/packaging": {"scope": "repo", "observed_at": "2026-10-19", "source": "tools/quality_repos.json", "review": "blocked.reasons 记录 #934 维护者要求勿再开 PR；本地补充见 .workbuddy/memory/2026-10-19.md；待明确允许后复核，未重新调查上游政策"},
    "google/jax": {"scope": "repo", "observed_at": "2026-10-22", "source": "tools/quality_repos.json", "review": "blocked.reasons 记录 CONTRIBUTING 禁止 agent 自主开 PR，#41846/#41847 已弃；本地补充见 .workbuddy/memory/2026-10-22.md；其他写入范围待复核"},
    "jax-ml/jax": {"scope": "repo", "observed_at": "2026-10-22", "source": "tools/quality_repos.json", "review": "与 blocked.reasons.google/jax 使用同一禁投记录（本地补充 .workbuddy/memory/2026-10-22.md）；规范名称及重定向依据 .workbuddy/memory/2026-09-30.md；未重新调查上游政策"},
    "pycqa": {"scope": "owner", "observed_at": "2026-10-18", "source": ".workbuddy/memory/blocked-repos.md", "review": "重新确认账号投稿权限后解除"},
    "modelcontextprotocol/servers": {"scope": "repo", "observed_at": "2026-10-24", "source": ".workbuddy/memory/2026-10-24.md", "review": "POST /pulls 对本账号 404（两次复现；issue 评论仍可发）；handoff-only：修复推 fork + issue 留 compare 链接请维护者代开（time 服务器 LOCAL_TIMEZONE 修复先例，分支 fix/time-docker-env-entrypoint）。python-sdk 的 assign 门禁独立存在"},
    "textualize": {"scope": "owner", "observed_at": "2026-10-24", "source": ".workbuddy/memory/2026-10-24.md", "review": "PR 创建对本账号双通道封锁（API CreatePullRequest FORBIDDEN + 网页 compare 表单不渲染，2FA 配置后仍如此）；外部账号 2026-05 仍可正常开 PR，判定为账号特定限制；残余测试仅剩 GitHub 完全重登。handoff-only：修复推 fork 后在 issue 留 compare 链接请维护者代开（rich#4233 先例）；禁止重试 API 创建以免加固封锁标记"},
    "sqlalchemy": {"scope": "owner", "observed_at": "2026-10-18", "source": ".workbuddy/memory/blocked-repos.md", "review": "重新确认账号访问权限后解除"},
    "modelcontextprotocol/python-sdk": {"scope": "repo", "observed_at": "2026-10-18", "source": ".workbuddy/memory/blocked-repos.md", "review": "每次核验当前账号分配状态"},
    "frappe/frappe": {"scope": "repo", "observed_at": "2026-10-18", "source": ".workbuddy/memory/blocked-repos.md", "review": "须确认当前账号已获 vouched"},
    "geopandas/geopandas": {"scope": "repo", "observed_at": "2026-10-18", "source": ".workbuddy/memory/blocked-repos.md", "review": "须核验现有 issue 上的方案共识"},
    "arize-ai/phoenix": {"scope": "repo", "observed_at": "2026-10-29", "source": "https://raw.githubusercontent.com/Arize-ai/phoenix/main/CONTRIBUTING.md", "review": "「Issues First」节明写 open issue 不等于邀请提 PR，须等 maintainer 明确确认；未确认的 PR 大概率直接关闭。另：仓库自带 claude-implement-issue / factory-* 工作流，issue 多由内部自动化承接"},
    "apache/seatunnel": {"scope": "repo", "observed_at": "2026-10-29", "source": ".workbuddy/memory/2026-10-29.md", "review": "主仓为 Java/Scala（Connector-V2 = Java），本机不具备构建与测试条件；已合 PR 的经验不足以抵消可测性门槛"},
    "python/mypy": {"scope": "repo", "observed_at": "2026-10-26", "source": ".workbuddy/memory/2026-10-26.md", "review": "本地降级（非上游封锁）：外部修复 PR 三连无声离场（#22288、#22291 未合并关闭且零人工互动，#22056 被维护者自有 PR 取代；唯一合并 #22058 为文档区）。停止投递新的 mypy 修复 PR，纯文档类可例外；在飞为零，已关闭项不申诉"},
    "langfuse/langfuse": {"scope": "repo", "observed_at": "2026-10-29", "source": "https://raw.githubusercontent.com/langfuse/langfuse/main/CONTRIBUTING.md", "review": "仓级不可测（TypeScript 全栈 monorepo，非 Python 包，不满足权威池准入门槛①）：CONTRIBUTING 列明构建需 Node+pnpm+Rust(rustup，worker 的 napi-rs 原生插件 + AI gateway)+native linker，运行时需 PostgreSQL/ClickHouse/Redis/S3 全套服务；本机实测无 rustc/cargo、Docker daemon 未运行、无 psql。另注：该仓自带 AGENTS.md 且明确面向外部贡献者与 agent（无 AI 禁投条款），登记 NON_TESTABLE 仅为可测性门槛，非封禁"},
    "OpenHands/enterprise": {"scope": "repo", "observed_at": "2026-10-29", "source": ".workbuddy/memory/2026-10-26.md", "review": "POST /pulls 对本账号 404（两次复现；GET /pulls 正常，仓内 30 个开放 PR）——handoff-only：修复推 fork 后在 OpenHands/OpenHands（原 All-Hands-AI/OpenHands，307 迁移）的 issue 留 compare 链接请维护者代开（bootstrap 可选脚本修复先例，分支 fix/bootstrap-optional-scripts）"},
}
MANUAL_GATES = {"frappe/frappe": "vouched 资格未核验", "geopandas/geopandas": "方案共识须专项核验",
                "modelcontextprotocol/servers": "handoff-only：修复推 fork 后请维护者代开 PR",
                "python-markdown/markdown": "禁止 agent 自主提交/评论，须由作者本人理解并参与",
                "arize-ai/phoenix": "CONTRIBUTING 明写「An open issue is not an invitation to submit a PR」，须 maintainer 明确确认后才可开工"}

# Local pauses on automated follow-up; read-only observation remains allowed.
INTERACTION_HOLDS = {
    "ansible/ansible": "该账号投稿已被明确拒绝；停止自动跟进写入，保留只读观察",
    "python-markdown/markdown": "只准备本地修复和答复材料；作者须按仓库政策亲自参与沟通",
    "pypa/packaging": "维护者已要求勿再开 PR；本地暂缓自动跟进写入，沟通范围待复核，保留只读观察",
    "google/jax": "本地记录禁止 agent 自主开 PR；只准备本地材料，其他写入范围待复核，保留只读观察",
    "jax-ml/jax": "本地记录禁止 agent 自主开 PR；只准备本地材料，其他写入范围待复核，保留只读观察",
}
NON_TESTABLE = {"apache/arrow", "vllm-project/vllm", "apache/seatunnel", "langfuse/langfuse"}

# Issue-level suppressions for adjudications that survive dropping the repo name.
# Never put a repo-wide trait here; those belong in NON_TESTABLE / MANUAL_GATES.
# `updated_at` is the upstream state the decision was made against: when upstream
# moves (new comment, label, assignee), the suppression lapses so it cannot
# silently bury a candidate forever.
ISSUE_SUPPRESSIONS = {
    "huggingface/huggingface_hub#5109": {
        "observed_at": "2026-10-29",
        "updated_at": "2026-10-08T17:25:56Z",
        "reason": "不可复现(issue 级)：根因在第三方 CAS 返回 401 + 镜像站 + 间歇性失败，maintainer 已按环境问题排查，完整复现需约 47GB 下载",
    },
}


def issue_suppression(repo, number, updated_at=None):
    """Reuse an already-adjudicated issue-level rejection; empty means re-screen."""
    entry = ISSUE_SUPPRESSIONS.get(f"{repo}#{number}".lower())
    if not entry:
        return ""
    if not isinstance(updated_at, str) or not updated_at:
        return ""  # Missing state evidence never suppresses: re-screen instead.
    recorded = entry.get("updated_at")
    if not isinstance(recorded, str) or not recorded or updated_at != recorded:
        return ""  # Upstream moved since the decision; re-adjudicate.
    return f"issue 级已裁定({entry.get('observed_at', '?')}): {entry['reason']}"


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
