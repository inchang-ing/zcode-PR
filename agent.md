# agent.md — 新会话/换软件入口文档

> 本文件是任何 agent 软件接手本项目的第一入口。细则分发到下游文档,此处只做导航与最小启动清单。

## 30 秒启动清单

1. 读 `RULES.md`(硬规则/AI 政策/身份红线/环境坑 §八)——动手前必读。
2. 看实时状态:`PR_STATUS.md`(只读展示)+ `pr_state.json`(机器可读);跟踪范围 = 根 `STATE.md`(两张 OPEN 表,**已合/已关行由 `tools/monitor_oss.py` 自动清理,勿手删**)。
3. 跑一轮同步:`python tools/monitor_oss.py`(需 gh CLI 已登录)。
4. 历史与复盘:`rounds-log.md`(逐轮日志)、`STATE-archive.md`(已离场 PR 记录)、`.workbuddy/memory/`(每日工作日志)。

## 架构一页图

- **云端扫描**：主仓 `.github/workflows/fresh-issue-poll.yml` 扫描新 issue 并通知到自己的收件箱，实际任务始终在本机执行。私有子模块 `repo-monitor/` 保留监控代码和独立测试，但定时监控工作流已于 2026-11-02 删除，当前不自动运行。
- **扫描(按轮)**：`tools/monitor_fresh.py`、`tools/scan_candidates.py`、`tools/scan_docs.py` 或 `tools/inbox.py import` → `tools/fresh_candidates.json` → `tools/monitor_round.py --pending` → `round_candidates.json` → `tools/filter_cands.py` / `tools/vet.py`。常规全池扫描直接运行 `tools/monitor_round.py`；维护者亲提问题用 `tools/maintainer_sweep.py`。撞车五查见 RULES §二。
- **调度与证据**：`tools/work_queue.py refresh` 展示前 50 项，完整 JSON 保留全部任务；收件箱 done/reopen 和队列阶段共享处理结论。候选规则在 `candidate_rules.py`，所有入口通过 `task_state.TaskStore` 读写根目录 `task_state.json`；迁移命令为 `python -S tools/task_state.py migrate`，备份与回退见 `QUEUE_GUIDE.md`。旧三份文件保留原样，迁移后不得继续写入。发现消费记录在 `discovery_state.py`，文件锁与原子写入在 `pipeline_state.py`。会话认领需保存 token，释放和续期携带同一 token。提交前运行 `quality_check.py`，文档与代码的证据方式见 `contributions/README.md`。
- **快轮询与开关**：主仓 Actions 的逐仓游标保存在收件箱正文。`tools/pipeline_switch.py off` 同时更新开关并取消运行；查询 UNKNOWN 不等于开启。
- **跟踪表**:`tools/monitor_oss.py` 刷新 `pr_state.json` + `PR_STATUS.md`,并自动清理台账离场行。
- **通知**:飞书走 `tools/feishu_push.py`(凭证 `C:\Users\ROG\.Codex\feishu.json`,不入库)；历史记录显示租户曾被平台 21001 政策封锁。主仓快轮询使用自己的 GitHub 收件箱；停用的 `repo-monitor` 不提供自动 digest 兜底。

## 当前已知封锁(截至 2026-10-24,以 RULES.md 为准)

- **Textualize(rich/textual)**:API+网页对本账号双通道封锁 → handoff-only(修复推 fork,issue 留 compare 链接请维护者代开),禁重试创建。
- pallets/pre-commit/PyCQA/sqlalchemy 等见 `tools/repository_policy.py`(POLICY_EVIDENCE 有逐条证据与解除条件)。

## 换机恢复

同仓投递采用 **常规 2 个、确认等待维护者满 7 天额外 1 个、实际 OPEN 最多 3 个**。提交前运行 `python -S tools/repo_capacity.py check owner/repo`；等待登记与失效条件见 `QUEUE_GUIDE.md`。缓存预筛、任务认领、`auto_run --per-repo` 都不等于 PR 名额许可。

装 git + GitHub CLI → `gh auth login` → SSH 走 443 → 子模块 `git submodule update --init --recursive` → 按需重建 workspaces venv(`import <pkg>.__file__` 必须指向克隆目录)。长期保留:规则/台账/`contributions/` 记录与证据;克隆与 venv 可重建。
