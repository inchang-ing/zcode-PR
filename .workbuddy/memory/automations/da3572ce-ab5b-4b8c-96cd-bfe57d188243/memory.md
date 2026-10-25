# automation da3572ce (高质量仓新 bug 扫描 + 自动实现 PR, HOURLY/INTERVAL=2)

## 机制
- `work/scan_candidates.py --days 4 --max 5` 读 `work/quality_repos.json`(31 仓 + blocked + heavy/rust)，动态排除在飞仓(同仓≤1)，REST timeline 判 linked PR + 软认领关键词 → 输出 `work/ledger/candidates.json`。
- 0 候选 = 只在当日 memory 追加一行日志后静默退出；有候选走复核→意向评论→实现→开 PR。

## 执行记录
- 2026-10-21 02:05 — 扫 24 仓，0 干净候选，静默退出(未写码、未发评论)。
  - 唯一候选 `run-llama/llama_index#23613` 复核否决：正文自陈 "fixed by PR #23287"(该 PR 由报告者本人提交，仍 open)。
  - 同一候选上一轮(01:45)已否决过 → 说明扫描器漏了"正文裸链"这类已修声明。
  - **改进**：给 `scan_candidates.py` 加了正文级过滤(`fixed by pr`/`resolved by #`/`fix reference` 等)，避免每轮重复报同一死候选。改进后重跑确认 0。
- 附带：MEMORY.md 超 15KB 注入截断，已压缩 18.5KB→13.8KB(第四次压缩)。

- 2026-10-21 03:48 — 扫 24 仓，0 干净候选，静默退出（未写码、未发评论）。正文级已修过滤生效，未再复报 llama_index#23613。

- 2026-10-21 05:50 — 扫 24 仓，初筛 3 候选，复核后 0 可投，静默退出（未写码、未发评论）。
  - prefect#23492/#23491：各已被 devin-ai-integration[bot] 的 PR #23493/#23494 closes（扫描前 ~30 秒开出，timeline 事件竞态）。
  - langchain#41348：报告者 fork 内已备补丁并留言求 maintainer assign。
  - **改进**：扫描器加两道过滤——①正文软认领（`i plan a fix`/`i have a focused fix`/`assign this issue to` 等）②本仓最近 60 个 open PR 引用号兜底比对（修 timeline 竞态）。改后重扫确认 0 候选。

- 2026-10-21 07:59 — 扫 24 仓，0 干净候选，静默退出（未写码、未发评论）。上一轮新增的两道过滤（正文软认领 + 本仓 open PR 引用号兜底）持续生效，无重复死候选复报。
- 2026-10-21 10:02 — 扫 24 仓，0 干净候选，静默退出（未写码、未发评论）。三道过滤全部生效，无复报。连续 5 轮 0 候选，池枯竭属预期。
- 2026-10-21 12:10 — 扫 24 仓（skipped 8：在飞/blocked/heavy），0 干净候选，静默退出（未写码、未发评论）。连续 6 轮 0 候选，无复报，参数未动。

- 2026-10-21 14:12 — 扫 24 仓，0 干净候选，静默退出（未写码、未发评论）。连续 7 轮 0 候选，无复报，参数未动。

## 注意
- 池已枯竭：知名 Python 仓未认领 bug 近乎为零，连续多轮 0 候选属预期，不必改参数硬找。
- scanner 全量扫 24 仓约 2 分钟；search API 易 403，保持只走仓库 issues 端点。
