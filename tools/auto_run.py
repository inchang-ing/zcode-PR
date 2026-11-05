#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""候选(clean)检测 → 立即 run → 防重复触发。

设计目标(对应指令):
  1. 明确"候选"与"干净"的判定标准(见 is_clean / _is_real_bug)。
  2. 一旦某候选处于 clean 状态, 在遍历到的"瞬间"立即触发 run()。
  3. 用统一 task_state.json 记录派发与处理结论，防止重复执行。

"run" 的语义 = 准备本地修复:
  clone/fetch → 复现(reproduce) → 应用补丁(FIXERS 钩子) → 等待最终提交与证据检查。
  quality_check.py 检查完成前停止；此入口不自动推送或创建 PR。
本地准备不强制占位留言；讨论和分配要求按目标仓库政策执行。
若无法本地复现, 或没有注册补丁, 一律不硬凑、不伪造 PR(标记 repro_failed / needs_fix 后停止)。

用法:
  python auto_run.py              # 真实运行: 对所有 clean 候选触发 run()
                                  # 无「一轮只能一个」的全局上限, 能跑几个跑几个
  python auto_run.py --dry-run    # 演练: 只打印判定与触发决策, 不克隆/不提 PR/不写 dispatched
  python auto_run.py --per-repo=1 # 默认: 同仓本轮准备 1 项；PR 名额另按 2 + 等待 7 天例外 1 个核验
  python auto_run.py --max=N      # 可选全局上限(默认不设); 一般不设
"""
import argparse
import os, re, subprocess
import hashlib, tarfile, io, tempfile
from pipeline_state import file_lock
from task_state import DispatchedStore
import session_claims

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 仓库根(本文件在 tools/)
CANDIDATES = os.path.join(BASE, "round_candidates.json")   # monitor_round.py 的产物
WORKDIR = os.path.join(BASE, "work")                        # 仓库克隆目录

# ──────────────────────────────────────────────────────────────
# 1) 候选 / 干净的判定标准
# ──────────────────────────────────────────────────────────────

# Compatibility exports for existing imports; shared rules live independently.
from candidate_rules import (Candidate, is_clean, load_candidates, _is_real_bug,
                             _has_non_bug_label, MANUAL_DROP, NON_BUG_LABELS, BUG_TITLE_RE)

# ──────────────────────────────────────────────────────────────
# 2) 去重状态库(防重复触发)
# ──────────────────────────────────────────────────────────────

# DispatchedStore remains exported here for existing callers.


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


# ── 本地源码准备与快照 ──

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
    """拉取 main 源码到 WORKDIR/{name}，保留既有路径；仅清理本次 staging。"""
    if (not isinstance(repo, str)
            or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)
            or any(part in {".", ".."} for part in repo.split("/"))):
        raise ValueError("无效 GitHub owner/repo")
    name = repo.split("/")[1]
    dest = os.path.join(WORKDIR, name)
    with file_lock(dest):
        if os.path.lexists(dest):
            raise FileExistsError(f"源码目标已存在，拒绝覆盖: {dest}")
        url = f"https://github.com/{repo}/archive/refs/heads/main.tar.gz"
        p = subprocess.run(["curl", "-sL", "--max-time", "240", url],
                           capture_output=True)
        if p.returncode != 0 or len(p.stdout) < 1000:
            raise RuntimeError(f"tarball 下载失败 {url} rc={p.returncode} len={len(p.stdout)}")
        with tempfile.TemporaryDirectory(dir=WORKDIR) as tmp:
            with tarfile.open(fileobj=io.BytesIO(p.stdout), mode="r:gz") as tf:
                tf.extractall(tmp, filter=tarfile.data_filter)
            subs = os.listdir(tmp)
            if len(subs) != 1 or subs[0].lower() != f"{name}-main".lower():
                raise RuntimeError("tarball 必须只有一个对应仓库的 main 源码根目录")
            srcdir = os.path.join(tmp, subs[0])
            if not os.path.isdir(srcdir) or os.path.islink(srcdir):
                raise RuntimeError("tarball 源码根必须是实际目录")
            root = os.path.realpath(srcdir)
            final_root = os.path.realpath(dest)
            for directory, dirs, files in os.walk(srcdir):
                for entry in dirs + files:
                    path = os.path.join(directory, entry)
                    if os.path.islink(path):
                        target = os.readlink(path)
                        prefix, crossed_link = directory, False
                        for part in re.split(r"[\\/]", target):
                            if part == ".." and crossed_link:
                                raise RuntimeError("tarball 链接越出源码根目录: 链接之后包含 '..'")
                            prefix = os.path.join(prefix, part)
                            crossed_link = crossed_link or os.path.islink(prefix)
                        relocated = os.path.abspath(os.path.join(
                            final_root, os.path.relpath(directory, srcdir), target))
                        if (os.path.commonpath([root, os.path.realpath(path)]) != root
                                or os.path.commonpath([final_root, relocated]) != final_root):
                            raise RuntimeError("tarball 链接越出源码根目录")
            # Reserve the target atomically so a late directory cannot become a move container.
            os.mkdir(dest)
            for entry in os.listdir(srcdir):
                os.rename(os.path.join(srcdir, entry), os.path.join(dest, entry))
    return dest


def run(c: Candidate, store: DispatchedStore, dry_run: bool = False):
    """触发运行。dry_run 仅打印决策, 不克隆/不提 PR/不写 dispatched。
    真实运行先原子领取；后续写入只接受本次领取未被他人更新的记录。"""
    if dry_run:
        if store.is_active(c.key):
            print(f"  [dedup] SKIP {c.key} 已派发({store.status_of(c.key)})")
        else:
            print(f"  [dry-run] WOULD RUN {c.key}: {c.title}")
        return

    lease_path = store.root / 'work/ledger/session_claims.json'
    token = session_claims.claim(c.key, 'auto_run', path=lease_path)
    if token is None:
        print(f"  [claimed] SKIP {c.key} 已由其他会话认领")
        return
    try:
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

        def require_lease():
            if not session_claims.renew(c.key, token, path=lease_path):
                raise RuntimeError('任务认领已失效，停止准备')

        def finish(status, **fields):
            if not session_claims.renew(c.key, token, path=lease_path):
                print(f"  [run] {c.key} 认领已失效，保留现有状态")
                return False
            if store.mark(c.key, status, expected=claimed, **fields):
                return True
            print(f"  [run] {c.key} 状态已被其他操作更新，保留最新记录")
            return False

        print(f"  [run] >> {c.key}: {c.title}")
        repo_path = os.path.join(WORKDIR, c.repo.split("/")[1])

        try:
            # (a) 拉取 main 源码，拒绝覆盖既有工作目录。
            repo_path = _clone_via_tarball(c.repo)

            require_lease()

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

            require_lease()
            before = _snapshot_hashes(repo_path)
            fixer(c, repo_path)
            after = _snapshot_hashes(repo_path)
            changed = [p for p in sorted(before.keys() | after.keys()) if before.get(p) != after.get(p)]
            if not changed:
                if finish("needs_fix", reason="fixer 未改动任何文件, 不提 PR"):
                    print(f"  [run] {c.key} fixer 无改动 → needs_fix")
                return

            # A changed tarball is not a tested final Git commit or submission evidence.
            if finish("needs_verification", changed=changed,
                      reason="将补丁落入目标 Git checkout，完成回归及 quality_check.py 后按规则提交"):
                print(f"  [run] {c.key} → needs_verification：完成最终提交与证据检查后再提交")
        except BaseException as e:  # 任何步骤失败都不留半成品 PR
            if finish("repro_failed", reason=f"run 异常: {e}"):
                print(f"  [run] {c.key} 异常 → {e}")
            if not isinstance(e, Exception):
                raise

    finally:
        session_claims.release(c.key, token, path=lease_path)


# ──────────────────────────────────────────────────────────────
# 4) 主循环: 遍历候选, clean 的瞬间触发 run()
# ──────────────────────────────────────────────────────────────

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max", type=int)
    parser.add_argument("--per-repo", type=int, default=1)
    args = parser.parse_args(argv)
    if (args.max is not None and args.max < 0) or args.per_repo < 0:
        parser.error("--max and --per-repo must be non-negative")
    dry, max_n, per_repo = args.dry_run, args.max, args.per_repo
    cands = load_candidates()
    store = DispatchedStore()
    clean_n = 0
    repo_n: dict = {}
    for c in cands:
        ok, why = is_clean(c, store)
        c.clean, c.clean_reason = ok, why
        if ok:
            # 本地修复准备的并发限制独立于 GitHub PR 投递名额。
            repo_key = c.repo.lower()
            if store.repo_inflight(c.repo) or repo_n.get(repo_key, 0) >= per_repo:
                print(f"  [per-repo] {c.key} 同仓已达上限 {per_repo}（{c.repo}）→ 留待下轮")
                continue
            if max_n is not None and clean_n >= max_n:
                print(f"  [max] 已达全局上限 {max_n}, 余下留待下轮")
                continue
            if dry or c.key in REPROS or c.key in FIXERS:
                clean_n += 1
                repo_n[repo_key] = repo_n.get(repo_key, 0) + 1
            run(c, store, dry_run=dry)      # ← 满足条件的瞬间立即触发
        else:
            print(f"  skip {c.key}: {why}")
    print(f"DONE. candidates={len(cands)}, clean_triggered={clean_n}, "
          f"repos={len(repo_n)}{' (dry-run)' if dry else ''}")


if __name__ == "__main__":
    main()
