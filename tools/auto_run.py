#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""候选(clean)检测 → 立即 run → 防重复触发。

设计目标(对应指令):
  1. 明确"候选"与"干净"的判定标准(见 is_clean / _is_real_bug)。
  2. 一旦某候选处于 clean 状态, 在遍历到的"瞬间"立即触发 run()。
  3. 用持久化 dispatched.json 去重, 同一候选绝不二次触发。

"run" 的语义 = 准备本地修复:
  clone/fetch → 复现(reproduce) → 应用补丁(FIXERS 钩子) → 等待最终提交与证据检查。
  quality_check.py 检查完成前停止；此入口不自动推送或创建 PR。
若无法本地复现, 或没有注册补丁, 一律不硬凑、不伪造 PR(标记 repro_failed / needs_fix 后停止)。

用法:
  python auto_run.py              # 真实运行: 对所有 clean 候选触发 run()
                                  # 无「一轮只能一个」的全局上限, 能跑几个跑几个
  python auto_run.py --dry-run    # 演练: 只打印判定与触发决策, 不克隆/不提 PR/不写 dispatched
  python auto_run.py --per-repo=1 # 默认: 同一仓库本轮最多触发 1 个(真实纪律=同仓在飞≤1, 硬上限2)
  python auto_run.py --max=N      # 可选全局上限(默认不设); 一般不设
"""
import json, os, re, subprocess, sys, time
import base64, shutil, hashlib, tarfile, io, tempfile
import math
from dataclasses import dataclass, field
from datetime import datetime
from pipeline_state import atomic_write_json, file_lock, read_json_object
from repository_policy import policy_reason

# 提交作者邮箱(须绑 GitHub, 否则 CLA-bot 认不出)
EMAIL = "197932532+inchang-ing@users.noreply.github.com"

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 仓库根(本文件在 tools/)
CANDIDATES = os.path.join(BASE, "round_candidates.json")   # monitor_round.py 的产物
DISPATCHED = os.path.join(BASE, "dispatched.json")          # 去重状态库
WORKDIR = os.path.join(BASE, "work")                        # 仓库克隆目录
CLAIM_QUEUE = os.path.join(WORKDIR, "claim-queue.md")       # 「先领再写」台账(留言证据)

# ──────────────────────────────────────────────────────────────
# 1) 候选 / 干净的判定标准
# ──────────────────────────────────────────────────────────────

# 人工裁定不投: 复核发现正文/评论已自占或维护者明示暂不接受 PR,
# 但扫描时的 SOFT 正则未覆盖到 → 在此固化判据, 避免每轮重复误判。
# (例: optuna#6898 正文 "I would like to implement it as Ra1nhy";
#      sklearn#35139 正文 "I will be pleased to help fix this bug, which will be my first commit"
#      + 官方 "not yet ready for a PR" 横幅)
MANUAL_DROP = {
    "optuna/optuna#6898": "正文自占(I would like to implement it as Ra1nhy)",
    "scikit-learn/scikit-learn#35139": "正文自占 + 官方 not yet ready for a PR 横幅",
    "mlflow/mlflow#26605": "正文自占(已有 fix + 分支, 只等 triage)",
    "crewAIInc/crewAI#8111": "正文自占(I can submit a focused fix)",
    "stanfordnlp/dspy#10639": "timeline 有关联 PR #10642",
    "explosion/spaCy#14011": "站点/机器人故障, 非本仓代码 bug",
}

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
    checked_at: str = ""  # scan observation, not issue creation time

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


def is_clean(c: Candidate, store: "DispatchedStore"):
    """干净判定(全部满足才算 clean):
       ① 满足共享仓库限制      ② 可本地测试
       ③ 真 bug(非 feature 等) ④ timeline/评论检测均已确认(pr_unknown/cmt_unknown 均为 False)
       ⑤ 尚未派发(dedup)
    返回 (bool, reason)。
    """
    if c.key in MANUAL_DROP:
        return False, f"人工裁定不投: {MANUAL_DROP[c.key]}"
    reason = policy_reason(c.repo, c.labels, c.assignees)
    if reason:
        return False, reason
    if not _is_real_bug(c):
        return False, "非 bug(feature/perf/docs/rfc 等)"
    if c.issue_unknown or c.pr_unknown or c.cmt_unknown:
        return False, "issue/撞车/认领检测不确定, 保守跳过"
    if store.is_active(c.key):
        return False, f"已派发(dedup): {store.status_of(c.key)}"
    return True, "clean: 通过 v4 + 非受限 + 可测 + 真 bug + 未派发"


# ──────────────────────────────────────────────────────────────
# 2) 去重状态库(防重复触发)
# ──────────────────────────────────────────────────────────────

class DispatchedStore:
    """持久化记录每个候选的派发状态, 跨 45 分钟多轮去重。
    进行中/已提交/已排除不再派发；待复现、复现失败可重试。
    deferred 通过 retry_after (UTC ISO 时间或 Unix 秒) 指定复查时间。
    """

    # needs_repro 不在此集合: 只是"还没人写复现", 非终态, 下轮可重试
    ACTIVE = {"running", "pr_opened", "needs_fix", "needs_verification"}
    TERMINAL = {"dropped", "merged", "closed"}
    RETRYABLE = {"pending", "needs_repro", "repro_failed", "dry_run"}

    def __init__(self, path: str = DISPATCHED):
        self.path = path
        self.data = self._normalize(read_json_object(path))

    @staticmethod
    def _validate(data):
        if any(not isinstance(value, dict) for value in data.values()):
            raise ValueError("Invalid dispatched state: each candidate must be an object")

    @classmethod
    def _normalize(cls, data):
        cls._validate(data)
        normalized, priorities = {}, {}
        for key, entry in data.items():
            key = key.lower()
            status = entry.get("status")
            # Legacy aliases must not revive finished work or hide an in-flight PR.
            rank = (3 if status in cls.ACTIVE else
                    2 if status not in cls.RETRYABLE | {"deferred"} else
                    int(cls._entry_active(entry)))
            stamp = entry.get("ts", 0)
            if not isinstance(stamp, (int, float)) or not math.isfinite(stamp):
                stamp = 0
            priority = (rank, stamp)
            if key not in normalized or priority > priorities[key]:
                normalized[key], priorities[key] = entry, priority
        return normalized

    @classmethod
    def _entry_active(cls, entry) -> bool:
        if entry is None:
            return False
        status = entry.get("status")
        if status in cls.ACTIVE or status in cls.TERMINAL:
            return True
        if status not in cls.RETRYABLE | {"deferred"}:
            return True
        retry_after = entry.get("retry_after")
        if retry_after is not None:
            try:
                if isinstance(retry_after, str):
                    date = datetime.fromisoformat(retry_after.replace("Z", "+00:00"))
                    if date.tzinfo is None:
                        return True
                    retry_after = date.timestamp()
                retry_after = float(retry_after)
                return not math.isfinite(retry_after) or retry_after > time.time()
            except (TypeError, ValueError, OverflowError):
                return True
        return status not in cls.RETRYABLE

    def is_active(self, key: str) -> bool:
        return self._entry_active(self.data.get(key.lower()))

    def status_of(self, key: str) -> str:
        return self.data.get(key.lower(), {}).get("status", "none")

    def repo_inflight(self, repo: str) -> bool:
        """该仓是否已有在飞(跨轮累计)。用于落实真实纪律「同仓在飞 ≤1」,
        而不是「一轮只能跑一个」——后者并无此硬约束。"""
        pre = f"{repo.lower()}#"
        return any(k.startswith(pre) and v.get("status") in self.ACTIVE
                   for k, v in self.data.items())

    def mark(self, key: str, status: str, *, only_if_inactive=False, expected=None, **extra):
        """Write under lock; dispatch and completion can guard the latest record."""
        if status not in self.ACTIVE | self.TERMINAL | self.RETRYABLE | {"deferred"}:
            raise ValueError(f"Unknown candidate status: {status}")
        with file_lock(self.path):
            data = self._normalize(read_json_object(self.path))
            current = data.get(key.lower())
            if ((only_if_inactive and self._entry_active(current))
                    or (expected is not None and current != expected)):
                self.data = data
                return False
            entry = {**(current or {}), "status": status, "ts": time.time(), **extra}
            if "retry_after" not in extra:
                entry.pop("retry_after", None)
            data[key.lower()] = entry
            atomic_write_json(self.path, data)
            self.data = data
            return True


# ──────────────────────────────────────────────────────────────
# 3) run(): 干净候选的 PR 落地管线(可被立即触发)
# ──────────────────────────────────────────────────────────────

# 每个候选的具体修复补丁在此注册: key -> fn(candidate, repo_path) -> None
# 未注册 → run() 复现成功后标记 needs_fix, 绝不编造补丁。
FIXERS: dict = {}
# 可选的复现函数注册: key -> fn(candidate, repo_path) -> bool
REPROS: dict = {}


def _reproduce(c: Candidate, repo_path: str) -> bool:
    fn = REPROS.get(c.key)
    if fn is not None:
        return bool(fn(c, repo_path))
    # 无注册复现 → 无法断言可复现, 返回 False(不硬凑)
    return False


# ── 代理安全 I/O(本沙箱 git https 被代理拦 502, 故 clone/push 走 tarball+gh api) ──

def _sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _snapshot_hashes(root: str) -> dict:
    snap = {}
    for dp, _, fns in os.walk(root):
        if ".git" in dp.split(os.sep):
            continue
        for fn in fns:
            p = os.path.join(dp, fn)
            snap[p] = _sha256_file(p)
    return snap


def _clone_via_tarball(repo: str) -> str:
    """代理安全拉取 main 源码(tarball, 无 .git)。解压到 WORKDIR/{name},
    与旧 git clone 路径约定一致, 故既有 FIXER 路径假设不变。"""
    name = repo.split("/")[1]
    dest = os.path.join(WORKDIR, name)
    url = f"https://github.com/{repo}/archive/refs/heads/main.tar.gz"
    p = subprocess.run(["curl", "-sL", "--max-time", "240", url],
                       capture_output=True)
    if p.returncode != 0 or len(p.stdout) < 1000:
        raise RuntimeError(f"tarball 下载失败 {url} rc={p.returncode} len={len(p.stdout)}")
    tmp = tempfile.mkdtemp(dir=WORKDIR)
    with tarfile.open(fileobj=io.BytesIO(p.stdout), mode="r:gz") as tf:
        tf.extractall(tmp)
    subs = [d for d in os.listdir(tmp) if d.startswith(name + "-")]
    if not subs:
        raise RuntimeError("tarball 解压后无源码子目录")
    srcdir = os.path.join(tmp, subs[0])
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    shutil.move(srcdir, dest)
    shutil.rmtree(tmp, ignore_errors=True)
    return dest


def _push_via_api(repo: str, branch: str, base_commit: str, base_tree: str,
                  changed_abs: list, commit_msg: str) -> str:
    """代理安全推送: 建 blob→tree(overlay)→commit→ref 到 fork(inchang-ing/{name})。
    仅 overlay 改动文件, 不截断仓库。返回 commit sha。"""
    owner = "inchang-ing"
    name = repo.split("/")[1]
    if subprocess.run(["gh", "api", f"repos/{owner}/{name}"],
                       capture_output=True, text=True).returncode != 0:
        subprocess.run(["gh", "api", "-X", "POST", f"repos/{repo}/forks"],
                       capture_output=True, text=True)
    root = os.path.join(WORKDIR, name)
    tree_items = []
    for ap in changed_abs:
        content = open(ap, "rb").read()
        b = subprocess.run(
            ["gh", "api", "-X", "POST", f"repos/{owner}/{name}/git/blobs", "--input", "-"],
            input=json.dumps({"content": base64.b64encode(content).decode(),
                              "encoding": "base64"}),
            capture_output=True, text=True)
        blob_sha = json.loads(b.stdout)["sha"]
        rel = os.path.relpath(ap, root).replace(os.sep, "/")
        tree_items.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob_sha})
    t = subprocess.run(
        ["gh", "api", "-X", "POST", f"repos/{owner}/{name}/git/trees", "--input", "-"],
        input=json.dumps({"base_tree": base_tree, "tree": tree_items}),
        capture_output=True, text=True)
    tree_sha = json.loads(t.stdout)["sha"]
    c = subprocess.run(
        ["gh", "api", "-X", "POST", f"repos/{owner}/{name}/git/commits", "--input", "-"],
        input=json.dumps({"message": commit_msg, "tree": tree_sha, "parents": [base_commit]}),
        capture_output=True, text=True)
    commit_sha = json.loads(c.stdout)["sha"]
    ref = f"heads/{branch}"
    if subprocess.run(["gh", "api", f"repos/{owner}/{name}/git/ref/{ref}"],
                      capture_output=True, text=True).returncode == 0:
        subprocess.run(["gh", "api", "-X", "PATCH", f"repos/{owner}/{name}/git/ref/{ref}",
                        "--input", "-"], input=json.dumps({"sha": commit_sha}),
                       capture_output=True, text=True)
    else:
        subprocess.run(["gh", "api", "-X", "POST", f"repos/{owner}/{name}/git/refs",
                        "--input", "-"], input=json.dumps({"ref": ref, "sha": commit_sha}),
                       capture_output=True, text=True)
    return commit_sha


def run(c: Candidate, store: DispatchedStore, dry_run: bool = False):
    """触发运行。dry_run 仅打印决策, 不克隆/不提 PR/不写 dispatched。
    真实运行先原子领取；后续写入只接受本次领取未被他人更新的记录。"""
    if dry_run:
        if store.is_active(c.key):
            print(f"  [dedup] SKIP {c.key} 已派发({store.status_of(c.key)})")
        else:
            print(f"  [dry-run] WOULD RUN {c.key}: {c.title}")
        return

    no_hooks = c.key not in REPROS and c.key not in FIXERS
    initial = "needs_repro" if no_hooks else "running"
    extra = {"reason": "无注册 REPRO/FIXER, 待 agent 提供; 不克隆不消耗名额"} if no_hooks else {}
    if not store.mark(c.key, initial, only_if_inactive=True, **extra):
        print(f"  [dedup] SKIP {c.key} 已派发({store.status_of(c.key)})")
        return
    if no_hooks:
        print(f"  [run] {c.key} 无注册 REPRO/FIXER → needs_repro(不克隆, 下轮可重试)")
        return

    claimed = dict(store.data[c.key.lower()])

    def finish(status, **fields):
        if store.mark(c.key, status, expected=claimed, **fields):
            return True
        print(f"  [run] {c.key} 状态已被其他操作更新，保留最新记录")
        return False

    print(f"  [run] >> {c.key}: {c.title}")
    repo_path = os.path.join(WORKDIR, c.repo.split("/")[1])

    try:
        # (a) 代理安全拉源码(tarball, 覆盖式刷新到 main)
        repo_path = _clone_via_tarball(c.repo)

        # (b) 复现(判别力硬门槛: 撤修复→fail / 恢复→pass; 这里先要有 fail)
        if not _reproduce(c, repo_path):
            if finish("repro_failed", reason="无法本地复现, 不硬凑"):
                print(f"  [run] {c.key} 复现失败 → repro_failed(不提 PR)")
            return

        # (c) 应用补丁(钩子)
        fixer = FIXERS.get(c.key)
        if fixer is None:
            if finish("needs_fix", reason="已复现但无注册修复逻辑, 待 agent 实现补丁"):
                print(f"  [run] {c.key} 已复现但无 FIXER → needs_fix(不伪造 PR)")
            return

        before = _snapshot_hashes(repo_path)
        fixer(c, repo_path)
        after = _snapshot_hashes(repo_path)
        changed = [p for p in after if before.get(p) != after.get(p)]
        if not changed:
            if finish("needs_fix", reason="fixer 未改动任何文件, 不提 PR"):
                print(f"  [run] {c.key} fixer 无改动 → needs_fix")
            return

        # A changed tarball is not a tested final Git commit or submission evidence.
        if finish("needs_verification", changed=changed,
                  reason="将补丁落入目标 Git checkout，完成回归及 quality_check.py 后按规则提交"):
            print(f"  [run] {c.key} → needs_verification：完成最终提交与证据检查后再提交")
    except Exception as e:  # 任何步骤失败都不留半成品 PR
        if finish("repro_failed", reason=f"run 异常: {e}"):
            print(f"  [run] {c.key} 异常 → {e}")


# ──────────────────────────────────────────────────────────────
# 4) 主循环: 遍历候选, clean 的瞬间触发 run()
# ──────────────────────────────────────────────────────────────

def _claimed(repo: str, issue: int, queue: str = CLAIM_QUEUE) -> bool:
    """「先领再写」硬检查: 该 issue 必须在 claim-queue.md 里有「写码前留言」记录。

    台账是 markdown 表格, 行首形如 '| owner/name | 123 | ...'。
    历史教训: 91 个关联 issue 里只有 16 个留过言, 82% 是 drive-by PR,
    而 pytest CONTRIBUTING 明确把 'drive-by PR against an issue the author
    never engaged with' 列为封号签名。故此处做兜底拦截。
    """
    if not os.path.exists(queue):
        return False
    pat = re.compile(r"^\|\s*" + re.escape(repo) + r"\s*\|\s*" + str(issue) + r"\s*\|", re.M)
    try:
        with open(queue, encoding="utf-8") as f:
            return bool(pat.search(f.read()))
    except OSError:
        return False


def load_candidates(path: str = CANDIDATES) -> list:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [Candidate(**c) for c in json.load(f)]


def main():
    dry = "--dry-run" in sys.argv
    max_n = None          # 可选全局上限, 默认不设(能跑几个跑几个)
    per_repo = 1          # 真实纪律: 同仓在飞 ≤1(硬上限 2)
    for a in sys.argv[1:]:
        if a.startswith("--max="):
            try:
                max_n = int(a.split("=", 1)[1])
            except ValueError:
                pass
        elif a.startswith("--per-repo="):
            try:
                per_repo = int(a.split("=", 1)[1])
            except ValueError:
                pass
    cands = load_candidates()
    store = DispatchedStore()
    clean_n = 0
    repo_n: dict = {}
    for c in cands:
        ok, why = is_clean(c, store)
        c.clean, c.clean_reason = ok, why
        if ok:
            # 「先领再写」兜底: 台账里没有留言记录的候选一律不投, 防止旧逻辑绕过留言直接出 PR
            if not _claimed(c.repo, c.number):
                print(f"  [claim-first] {c.key} 未在 issue 留言(work/claim-queue.md 无记录) → 跳过, 请先留言再跑")
                continue
            # 同仓限流(跨轮在飞 or 本轮已触发)——不是"一轮只能一个"的全局限制
            repo_key = c.repo.lower()
            if store.repo_inflight(c.repo) or repo_n.get(repo_key, 0) >= per_repo:
                print(f"  [per-repo] {c.key} 同仓已达上限 {per_repo}（{c.repo}）→ 留待下轮")
                continue
            if max_n is not None and clean_n >= max_n:
                print(f"  [max] 已达全局上限 {max_n}, 余下留待下轮")
                continue
            clean_n += 1
            repo_n[repo_key] = repo_n.get(repo_key, 0) + 1
            run(c, store, dry_run=dry)      # ← 满足条件的瞬间立即触发
        else:
            print(f"  skip {c.key}: {why}")
    print(f"DONE. candidates={len(cands)}, clean_triggered={clean_n}, "
          f"repos={len(repo_n)}{' (dry-run)' if dry else ''}")


if __name__ == "__main__":
    main()
