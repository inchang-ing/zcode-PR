# 在飞 PR 锚定(活跃才留, 合/关即删)

## 2026-10-18「10 个新 PR」产出(全部当日新建)
- zarr-developers/zarr-python#4526 — ShardingCodec.validate 不再因 default_scalar 不可编码而失败 — OPEN, 40 检查全绿。issue #4511
- zauberzeug/nicegui#6400 — sub_pages 只认领 root_path 下路径 — OPEN, CI Gate 等 maintainer 批(fork 首PR常态)。issue #6385
- dbt-labs/dbt#16798 — Jinja sum/min/max 恢复 Jinja2 语义(attribute=/case_sensitive=/start=) — OPEN, 代码绿; 待 CLA 网页签 + `ci:approve-public-fork-ci` 标签。issue #16786+#16783(一个 PR)
- flet-dev/flet#6982 — GestureDetector on_tap_move 事件接入 TapGestureRecognizer(Dart 侧) — OPEN, CI 待批; 待 CLA。issue #6961
- python-poetry/poetry-core#987 — OR 约束生成合法 PEP 508 metadata(折叠预发布门, 不可表示则报错) — OPEN, CI 运行中; **同 issue 有竞品 PR #984**。poetry#11101
- ansible/ansible#87712 — ansible-vault 临时文件+原子替换防数据丢失 — OPEN, CI 运行中。issue #87679
- **bandit#1478 — 修复已完成+分支已推 fork, PyCQA org 禁 createPullRequest → 需账号持有人网页开**: https://github.com/PyCQA/bandit/compare/main...inchang-ing:bandit:fix/pyproject-per-check-skips
- 当日已关 2: geopandas#3896(CONTRIBUTING 正文 AI 政策), frappe#44667(VOUCHED.td) — 均入 blocked-repos.md
- 在途实现(子代理): mypy#22220 / litestar#5131 / xarray#11689 / sphinx#14745

## 在飞(2026-10-14 同步)
- jupyter/nbconvert#2332 — fix/preserve-safe-subdirs-in-output-filenames — OPEN, MERGEABLE, UNSTABLE(**enforce-label 缺 bug 标签, 我无加标签权限, 已在 PR 留言求 maintainer 补**); 其余 CI 全绿。issue #2330
- BerriAI/litellm#46262 — litellm_fix_stream_delta_content_list — OPEN, MERGEABLE(2026-10-17: rebase 到 main ef1cb19 后压回单干净提交 `b19363b7`); **五大门禁全过**(type-discipline/test-quality/ruff format+lint+strict/basedpyright/循环 import/import safety), 82 项检查全绿(仅 mcp-elicitation pending); PR body 已按模板重写, 已回复 VANDRANKI。issue #46209


## 2026-10-24 移植合并
- hydra#3543 → 维护者 omry 验证后自开 #3548 取代,已 MERGED → 按移植合并计(第 29 个成果)。

## 在飞(2026-10-13 同步)
- deepchecks#2826 — fix/sdp-condition-missing-class — OPEN, mergeable, review_required; **license/cla=SUCCESS(用户网页签完+recheck 翻绿)**, 全绿可合; 仅等 maintainer review/approve
- kedro#5816 — fix/snapshot-factory-pattern-parameters — OPEN, mergeable, review_required; DCO✓/RTD✓; 等 review
- microsoft/semantic-kernel#14586 — fix/prompt-template-config-default-execution-settings — OPEN, **MERGEABLE(无冲突)**; 已回复 `@microsoft-github-policy-service agree`(MS CLA); 等 CI/review。issue #14582(同仓在飞 1 个, 合规)

## 在飞(2026-10-18 同步 — 本轮十个目标 PR, 全部 MERGEABLE)
- open-telemetry/opentelemetry-python#5717 — OPEN, MERGEABLE, CI 绿; 等 review(herin049 已审, 3 新测试 335 passed)
- traceloop/openllmetry#4633 — OPEN, REVIEW_REQUIRED, MERGEABLE; 刚开 10-18, 等 review
- bashtage/linearmodels#850 — OPEN, MERGEABLE, CI 绿(3 pass); 等 review
- bashtage/linearmodels#849 — OPEN, MERGEABLE, CI 绿(3 pass); 等 review
- BerriAI/litellm#46262 — litellm_fix_stream_delta_content_list — OPEN, MERGEABLE, **82 检查全绿**(含 LIT/ruff/pyright); 修复已迁进 `_accumulate_streamed_delta`(VANDRANKI 建议); BLOCKED=待 review 门禁非冲突; 等 maintainer approve。issue #46209
- huggingface/smolagents#2993 — OPEN, REVIEW_REQUIRED, MERGEABLE; ducanhnguyen223 反馈已 address(c1ebe98 链式作用域); 等 re-review
- aio-libs/aiohttp#14017 — OPEN, MERGEABLE; codecov/patch·project·Backport-label **非阻塞**(rulesets rules:[]); 49 项真实测试/lint 全绿; 等 review。issue #14000
- docling-project/docling#4849 — OPEN, CHANGES_REQUESTED, MERGEABLE; BOM/UTF-8 抽公共 utility 已在 78b105f 完成; 10-18 评论求 re-review; 等 re-review
- crewAIInc/crewAI#7981 — OPEN, MERGEABLE, CI 绿(3 pass); 等 review
- Arize-ai/openinference#3982 — OPEN, REVIEW_REQUIRED, MERGEABLE, CI 绿(1 pass); 等 review。issue #3904

## 本 round 已关/已弃
- peft#3952 — fix/cpt-input-type-mask-mutation — **被 maintainer BenjaminBossan 关**(理由: #3928 已 assign 给本人且 OP 拟提 PR; 我漏查 assignee 的 v4 失误, 不申诉、不重开)

## 排队(同仓达在飞上限, 待上面关/合再开)
- peft#3929 ensure_weight_tying 静默停绑 LoRA 权重
- peft#3935 LoRA on nn.MultiheadAttention bias 永不被训练
- diffusers#15020 非 CLIP 文本编码器 LoRA 加载失败(回归风险高, 需真实 T5 端到端验证, 暂缓)

## 备注
- 另有 ~27 个历史 open PR 跨多仓(bottle/boltons/tornado/setuptools/dd-trace-py×多/aiohttp/repowise/tortoise/openinference×多/mala/crewAI/loguru/snowflake/statsmodels/instructor/weaviate/code-security-workbench 等), 见 `gh search prs --author inchang-ing --state open`; 本文件只锚定本轮监控相关, 不逐一追踪。

## 在飞(2026-10-24 新增)
- Textualize/rich#4233 — ANSI 注入(NUL 夹在 ESC 与 [ 间绕过 re_ansi, 控制序列直达终端) — 修复已推 fork 分支 `fix-4233-ansi-nul`(78922ef7, +27: strip NUL/ESC + 3 回归测试); **10-24 终局: API+网页双通道封锁(2FA 后仍封;外部账号同期可开,账号特定) → handoff-only,由维护者从链接代开,禁重试创建**: https://github.com/Textualize/rich/compare/main...inchang-ing:rich:fix-4233-ansi-nul ; 已在 issue 留言给分支链接并礼让 BepuSun(19 天无 PR)。策略: strip 而非正则容忍(混淆序列应中和不应执行)。
