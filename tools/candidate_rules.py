"""Candidate data and eligibility, shared by discovery, vetting and scheduling."""
import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from pipeline_state import atomic_write_json, file_lock, read_json_object
from repository_policy import policy_reason
from task_state import task_key

CANDIDATES = str(Path(__file__).resolve().parents[1] / 'round_candidates.json')
KINDS = {'bug', 'docs', 'small_fix', 'tooling'}
BLOCKING_LABELS = {'needs triage', 'needs investigation', 'status:blocked',
                   'blocked', 'needs discussion', 'wontfix', 'invalid'}


def contribution_kind(labels):
    return 'docs' if any(label.lower() in {'doc', 'docs', 'documentation', 'type: docs', 'type: documentation'} for label in labels) else 'bug'


def eligibility_reason(candidate):
    if not isinstance(candidate.kind, str) or candidate.kind not in KINDS:
        return '未知贡献类型'
    if candidate.kind == 'bug':
        return '' if _is_real_bug(candidate) else '非 bug(feature/perf/docs/rfc 等)'
    if any(label.lower() in {'enhancement', 'feature', 'feature request', 'proposal', 'rfc', 'api design'} for label in candidate.labels):
        return '新功能/设计提案不属于文档或低风险修正'
    return ''

# 人工裁定不投: 复核发现正文/评论已自占或维护者明示暂不接受 PR,
# 但扫描时的 SOFT 正则未覆盖到 → 在此固化判据, 避免每轮重复误判。
# (例: optuna#6898 正文 "I would like to implement it as Ra1nhy";
#      sklearn#35139 正文 "I will be pleased to help fix this bug, which will be my first commit"
#      + 官方 "not yet ready for a PR" 横幅)
MANUAL_DROP = {key.lower(): reason for key, reason in {
    "optuna/optuna#6898": "正文自占(I would like to implement it as Ra1nhy)",
    "scikit-learn/scikit-learn#35139": "正文自占 + 官方 not yet ready for a PR 横幅",
    "mlflow/mlflow#26605": "正文自占(已有 fix + 分支, 只等 triage)",
    "crewAIInc/crewAI#8111": "正文自占(I can submit a focused fix)",
    "stanfordnlp/dspy#10639": "timeline 有关联 PR #10642",
    "explosion/spaCy#14011": "站点/机器人故障, 非本仓代码 bug",
}.items()}

# 非 bug 标签: 命中即视为 feature/perf/docs/rfc, 不算"干净"候选
NON_BUG_LABELS = {
    "enhancement", "feature", "feature request", "new feature", "perf",
    "performance", "rfc", "doc", "document", "documentation", "question",
    "use case", "proposal", "roadmap", "maintenance", "need confirmation",
    "help wanted", "api design", "needs discussion", "fr",
}

# 标题 bug 信号(无 bug 标签时, 靠标题推断是否真 bug)
BUG_TITLE_RE = re.compile(
    r"\b(bug|regression|panic|error|fail|failed|incorrect|broken|crash|"
    r"wrong|unexpected|raise[sd]?|keyerror|valueerror|typeerror|"
    r"attributeerror|indexerror|overflow|timeout|leak)\b", re.I)


@dataclass
class Candidate:
    """候选对象: monitor_round.py 通过基础 v4 过滤后产出的 issue。"""
    repo: str
    number: int
    title: str
    url: str
    createdAt: str = ""
    is_bug: bool = False
    labels: list = field(default_factory=list)
    pr_unknown: bool = False      # timeline 验撞车是否失败(无法确定有无关联 PR)
    cmt_unknown: bool = False     # 评论软认领检测是否失败
    issue_unknown: bool = False   # issue 必需字段缺失或格式不完整
    check_errors: list = field(default_factory=list)
    clean: bool = False
    clean_reason: str = ""
    assignees: list = field(default_factory=list)  # login names; old snapshots have no evidence
    kind: str = "bug"  # bug / docs / small_fix / tooling
    checked_at: str = ""  # scan observation, not issue creation time
    source_version: str = ""  # immutable discovery identity, independent of scan flags

    @property
    def key(self) -> str:
        return f"{self.repo}#{self.number}"


def _has_non_bug_label(c: Candidate) -> bool:
    return any(lb.lower() in NON_BUG_LABELS for lb in c.labels)


def _is_real_bug(c: Candidate) -> bool:
    """真 bug 判定: is_bug 标签, 或(无 feature 类标签 + 标题含 bug 信号)。"""
    if c.is_bug:
        return True
    if _has_non_bug_label(c):
        return False
    return bool(BUG_TITLE_RE.search(c.title))


def is_clean(c: Candidate, store: "DispatchedStore", *, decision=None):
    """干净判定(全部满足才算 clean):
       ① 满足共享仓库限制 ② 属于允许的贡献类型
       ③ issue/timeline/评论检测均已确认 ④ 尚未派发(dedup)
       验证能力由队列核验与贡献证据另行确认。
    返回 (bool, reason)。
    """
    if c.key.lower() in MANUAL_DROP:
        return False, f"人工裁定不投: {MANUAL_DROP[c.key.lower()]}"
    reason = policy_reason(c.repo, c.labels, c.assignees, kind=c.kind)
    if reason:
        return False, reason
    reason = eligibility_reason(c)
    if reason:
        return False, reason
    if c.issue_unknown or c.pr_unknown or c.cmt_unknown:
        return False, "issue/撞车/认领检测不确定, 保守跳过"
    blocked = store.is_active(c.key) if decision is None else decision['blocked']
    if blocked:
        return False, decision['reason'] if decision is not None else f"已派发(dedup): {store.status_of(c.key)}"
    return True, "clean: 通过共享筛选 + 非受限 + 未派发（验证能力须另行确认）"


def load_candidates(path: str = CANDIDATES) -> list:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig") as f:
        return [Candidate(**c) for c in json.load(f)]


def enqueue_candidates(candidates, root):
    """Enqueue new evidence once; preserve receipts and explicit task decisions."""
    from discovery_state import discovery_version, is_consumed, load_consumed
    from task_state import TaskStore
    root = Path(root)
    path = root / 'tools/fresh_candidates.json'
    with file_lock(path):
        inbox = read_json_object(path)
        receipts = load_consumed(root)
        tasks = TaskStore(root=root)
        added = 0
        for candidate in candidates:
            key = task_key(candidate.key)
            item = asdict(candidate)
            if is_consumed(receipts, key, item, tasks.decision(key)):
                continue
            if key not in inbox or discovery_version(inbox[key]) != discovery_version(item):
                inbox[key] = item
                added += 1
        if added:
            atomic_write_json(path, inbox)
    return added
