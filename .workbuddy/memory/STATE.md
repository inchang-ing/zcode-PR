# 在飞 PR 锚定(活跃才留, 合/关即删)

## 在飞(2026-10-14 同步)
- jupyter/nbconvert#2332 — fix/preserve-safe-subdirs-in-output-filenames — OPEN, MERGEABLE, UNSTABLE(**enforce-label 缺 bug 标签, 我无加标签权限, 已在 PR 留言求 maintainer 补**); 其余 CI 全绿。issue #2330
- BerriAI/litellm#46262 — litellm_fix_stream_delta_content_list — OPEN, MERGEABLE, BLOCKED(CI 全 pending + **CLA 待签: cla-assistant.io/BerriAI/litellm 须账号持有者网页签**)。issue #46209

- hydra-ecosystem/hydra#3543 — fix-missing-structured-config-root-override — OPEN, MERGEABLE, BLOCKED(等 CI/CLA: hydra 走 CLA Assistant); 已加 `news/3542.bugfix`。issue #3542

## 在飞(2026-10-13 同步)
- deepchecks#2826 — fix/sdp-condition-missing-class — OPEN, mergeable, review_required; **license/cla=SUCCESS(用户网页签完+recheck 翻绿)**, 全绿可合; 仅等 maintainer review/approve
- kedro#5816 — fix/snapshot-factory-pattern-parameters — OPEN, mergeable, review_required; DCO✓/RTD✓; 等 review
- microsoft/semantic-kernel#14586 — fix/prompt-template-config-default-execution-settings — OPEN, **MERGEABLE(无冲突)**; 已回复 `@microsoft-github-policy-service agree`(MS CLA); 等 CI/review。issue #14582(同仓在飞 1 个, 合规)

## 本 round 已关/已弃
- peft#3952 — fix/cpt-input-type-mask-mutation — **被 maintainer BenjaminBossan 关**(理由: #3928 已 assign 给本人且 OP 拟提 PR; 我漏查 assignee 的 v4 失误, 不申诉、不重开)

## 排队(同仓达在飞上限, 待上面关/合再开)
- peft#3929 ensure_weight_tying 静默停绑 LoRA 权重
- peft#3935 LoRA on nn.MultiheadAttention bias 永不被训练
- diffusers#15020 非 CLIP 文本编码器 LoRA 加载失败(回归风险高, 需真实 T5 端到端验证, 暂缓)

## 备注
- 另有 ~27 个历史 open PR 跨多仓(bottle/boltons/tornado/setuptools/dd-trace-py×多/aiohttp/repowise/tortoise/openinference×多/mala/crewAI/loguru/snowflake/statsmodels/instructor/weaviate/code-security-workbench 等), 见 `gh search prs --author inchang-ing --state open`; 本文件只锚定本轮监控相关, 不逐一追踪。
