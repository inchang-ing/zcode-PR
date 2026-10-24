# agent.md — 新会话/换软件入口文档

> 本文件是任何 agent 软件接手本项目的第一入口。细则分发到下游文档,此处只做导航与最小启动清单。

## 30 秒启动清单

1. 读 `RULES.md`(硬规则/AI 政策/身份红线/环境坑 §八)——动手前必读。
2. 看实时状态:`PR_STATUS.md`(只读展示)+ `pr_state.json`(机器可读);跟踪范围 = 根 `STATE.md`(两张 OPEN 表,**已合/已关行由 `tools/monitor_oss.py` 自动清理,勿手删**)。
3. 跑一轮同步:`python tools/monitor_oss.py`(需 gh CLI 已登录)。
4. 历史与复盘:`rounds-log.md`(逐轮日志)、`STATE-archive.md`(已离场 PR 记录)、`.workbuddy/memory/`(每日工作日志)。

## 架构一页图

- **监控(无人值守)**:子模块 `repo-monitor/`(GitHub Actions 每 30 分钟)轮询在飞 PR 与池内仓新 issue → 飞书推送(best-effort;飞书不可用时事件落入 `undelivered.jsonl` + 自仓 `monitor-digest` 标签 issue,GitHub 会发邮件)。改调度只动 `repo-monitor/.github/workflows/monitor.yml`。
- **扫描(按轮)**:`tools/scan_candidates.py`(精选池)→ `tools/filter_cands.py` → `tools/vet.py` 终检;维护者亲提 bug 用根目录 `maintainer_sweep.py`。撞车五查见 RULES §二。
- **跟踪表**:`tools/monitor_oss.py` 刷新 `pr_state.json` + `PR_STATUS.md`,并自动清理台账离场行。
- **通知**:飞书走 `tools/feishu_push.py`(凭证 `C:\Users\ROG\.Codex\feishu.json`,不入库);当前租户被平台 21001 政策封锁,通知兜底见 repo-monitor digest。

## 当前已知封锁(截至 2026-10-24,以 RULES.md 为准)

- **Textualize(rich/textual)**:API+网页对本账号双通道封锁 → handoff-only(修复推 fork,issue 留 compare 链接请维护者代开),禁重试创建。
- pallets/pre-commit/PyCQA/sqlalchemy 等见 `tools/repository_policy.py`(POLICY_EVIDENCE 有逐条证据与解除条件)。

## 换机恢复

装 git + GitHub CLI → `gh auth login` → SSH 走 443 → 子模块 `git submodule update --init --recursive` → 按需重建 workspaces venv(`import <pkg>.__file__` 必须指向克隆目录)。长期保留:规则/台账/`contributions/` 记录与证据;克隆与 venv 可重建。
