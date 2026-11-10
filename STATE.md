# STATE.md — 跟踪范围 + 指针

> **权威源 = GitHub**。本文件只做一件事:声明监控的**跟踪范围**(下面两张 `OPEN(...)` 表)。
> `tools/monitor_scope.py` 与 `tools/monitor_oss.py` 按行解析本文件(`github.com/.../pull/N` 且含 `OPEN`)。
>
> | 你需要 | 去看 |
> | --- | --- |
> | 实时状态 / CI / 评审 | **`PR_STATUS.md`**(由 `tools/monitor_scope.py` 生成,勿手改) |
> | 机器可读状态 | **`pr_state.json`** |
> | 硬规则 / AI 政策 / 身份红线 | **`RULES.md`** |
> | 项目说明 / 目录 / 流程 / 飞书 / 换机 | **`README.md`** |
> | 历史轮次 / 已合并 PR 验证记录 | **`rounds-log.md`**、**`STATE-archive.md`** |

## OSS 贡献在飞（73）
> 2026-11-10 21:0x GMT+8 补记：litestar-org/litestar#5206 修复已推 fork 分支 `fix/accept-q0-wildcard-overrides-specific`（DCO 签署、测试全过），PR 创建被自动化 GitHub 凭证权限阻断（gh `CreatePullRequest` 错误 / REST 404 / MCP 403 `Resource not accessible by integration`，均无 PR 写权限）；待账号持有人代开或修复凭证后计入在飞。`session_claims` 保持认领防重复。

> 2026-11-10 21:5x GMT+8 第 159 轮：huggingface/huggingface_hub#5327 修复已推 fork 分支 `fix/inference-endpoints-token-propagation`（DCO 签署、`test_inference_endpoints.py` 2 个新回归测试 + 既有 15 测试全过；改前原始代码 401 / 改后通过证据齐）；PR 创建同受自动化 GitHub 凭证 PR 写权限阻断，待账号持有人代开或修复凭证。不计入权威 72（PR 未开）。

> 2026-11-10 20:5x GMT+8 第 158 轮对账：权威在飞 **72** / 台账 72，盲点 0 / 过期 0；本轮 3 条离场——`markdown-it-py#442`/`#443` 被维护者关闭（未合并，12:40Z）、`haystack#13633` 已合并（12:20Z，上轮 APPROVED 后落地，本次清理台账残留的过期行 1 条）。收件箱首拉 13 + 轮内新投 2 + 轮末二次复核 2 = **17 条全当轮 disposition**，终检 0 pending（2036 reported / 2120 done）；四刀降维：仓级门禁 2（pydantic-ai 禁投 / inspect_ai 缺 accepted）、reporter 自开或已有对应 PR 5（`deer-flow#8111`→`#8109`、`litellm#50903`→`#50904`、`litellm#50894`→`#50896`、`inspect_ai#6451`→`#6452`、`deer-flow#8112`→`#8113`）、他人认领或内部处理 3（`litellm#50893` dbdefault、`litellm#50890` keremburakyilmaz、`haystack#13659` handled internally）、需 Proxy/DB/Enterprise 不可本机验且 litellm 同仓在飞 2 达上限 6 （`litellm#50905`/`#50900`/`#50899`/`#50898`/`#50891`/`#50908`）、文档修正已有对应 PR 1（`pydantic-ai#13029`→`#13013`）、轮末 2 条仓级门禁（`agno#11561` 缺 ready / `livekit#8496` 须本人签 CLA 且已有 `#8244`）。全池 `--all` 350 仓 **0 NEW**（boltons 单仓 query incomplete，watermark 未推进，其余 349 仓正常），**0 干净候选**。14 条 ⚠CI 逐条回认失败 check 名，全为门禁族 / 平台性 / 继承 main / 自有实验仓，无一属我方引入。review_sweep 0 ACTION（3 PRs updated / 0 human activity）。rotator 39 奇数按规则跳过 maintainer_sweep，保持 39。**0 认领 / 0 新 PR / 0 评审回应 / 0 推送**，详见 rounds-log 本轮。
>
> 2026-11-10 19:2x GMT+8 第 157 轮对账：权威在飞 **75** / 台账 75，盲点 0 / 过期 0，本轮零变化（仅时间戳）；**`haystack#13633` REVIEW_REQUIRED → APPROVED**，CI 9✓/4✗ → 20✓/1✗（1✗ 为 `.github` 工作流噪声，与本改动无关，待维护者合入）。收件箱首拉 19 + 轮末二次复核 2（inspect_ai#6450/#6449 因 owner 长名 `ukgovernmentbeis` 与 `done` 短名 `ukgov` 不匹配，首轮未清，已用长名重标后终检 0 pending）= **21 条全部当轮 disposition**（2019 reported / 2103 done）；四刀降维：仓级门禁 13（trl AI policy×5 / fastmcp assign / pydantic-ai 禁投 / langchain assign / agno 缺 ready / inspect_ai 缺 accepted×2）、竞品 PR 1（litellm#50878→#50879）、已认领 1（litellm#50888）、前端 TS×2（litellm#50887/#50886）、proxy 不可本机验×2（litellm#50885/#50884）、feature 1（litellm#50877）、增强不可本机验 1（pipecat#6698）。全池 `--all` 350 仓 27 NEW 九查后 **0 干净候选**：sqlglot#8970 被 reporter 自开 PR #8971 占、pydantic#14267 已 CLOSED+PR#14268、sktime#11788 已被 RugvedBane 认领、twisted#12934 为干净 regex-DoS 但需克隆重框架 + 超时回归测试（本轮回退、留待专属会话）、dbt-core#17110/duckdb#28634/#28636/frappe×4 不可本机验或门禁、mlflow#27637 缺 ready 标签 + has-closing-pr。review_sweep 1 ACTION＝`accelerate#4504` Michael-RDev 仍报 `_gradient_key` BFloat16 TypeError + 两 `nn.Linear` 同名梯度串扰，本机无 torch 可验 → 回评索要精确 traceback 行 + torch 版本 + 两 Linear 复现形状（以审查者重测为验证门，未推未验代码）。rotator 38→39（偶数跑 slice 38，104 仓 / 41 候选全已处置）。**0 认领 / 0 新 PR / 1 评审回应 / 0 推送**，详见 rounds-log 本轮。

> 2026-11-10 18:0x GMT+8 第 156 轮对账：权威在飞 **75** / 台账 75，盲点 0 / 过期 0，本轮零变化（仅时间戳）； `haystack#13633` CI 9✓/4✗（`reno` check 因单反引号失败，已推双反引号修正至在飞分支、待重跑转绿；余 `format`/`detect`/Vercel 为 `.github` 工作流噪声、与本改动无关）。 收件箱首拉 14 + 轮末二次复核 2 = **16 条全部当轮 disposition**，终检 0 pending（2000 reported / 2082 done）； 全池 `--all` 350 仓 33 NEW 九查后 **0 干净候选**（crewai×5 被 Kiko0301 占 / pipecat#6694 / dagster#34420/#34423 竞品 PR、 agno×2/peft/trl/adk-python/inspect_ai/mlflow/phoenix 门禁、openinference#4269 软认领、litellm×3/superset/duckdb 不可本机验、 darts#3352 需 `ok` 标签、pydantic#14266 维护者明言非官方支持、streamlit/mlflow feature、mlflow#27636 spam）。 dispositions 1165 未增（rotator 37 强制跑 slice 37 落账旧 DISPOSITIONED）。 review_sweep 2 ACTION：`haystack#13633` reno 单反引号改双反引号已推 + 回评； `accelerate#4504` `_gradient_key` BFloat16 + Linear 同名梯度串扰仍本机不可验 → 维持推迟不占位。 rotator 37→38（强制跑 slice 37，106 仓 / 20 候选全已处置）。 **0 认领 / 0 新 PR / 1 评审回应 / 1 推送（renocal）**，详见 rounds-log 本轮。

> 2026-11-10 15:51–16:2x GMT+8 第 154 轮对账：权威在飞 **75** / 台账 75，盲点 0 / 过期 0，本轮零变化（仅时间戳）；`haystack#13633` CI 2✓/1✗ → 9✓/4✗（我方在飞 PR，4 失败待查）。收件箱首拉 66（01:00–07:52Z 全为当日新投）= **66 条全部当轮 disposition**，二次复核 0 pending（1972 reported / 2054 done）；本地 `policy_reason` 批查砍 28 条（禁投/人工门禁/缺标签/assign 门禁），余 38 条 ALLOW 仓逐条 timeline + 同仓 open PR 号段 + `claim_check` 后全弃（竞品/自开 PR 25、已 assign 2、RFC 1、feature 3、不可本机验 7）。全池 `--all` 350 仓 NEW 含 21 条 inbox 之外新面孔，九查后 **0 干净候选**（竞品/自开 PR 6、CLOSED 1、feature 2、C/Rust/前端/重依赖不可本机验 12）；dispositions 1144→1165。review_sweep 2 ACTION：`haystack#13633` 维护者 `sjrl` 要求 `hatch run release-note` → 推送 reno 发布说明至在飞分支并回复确认（`format`/`detect` 失败指向 `.github` 工作流、与改动无关）；`accelerate#4504` 审查者在**我方当前 head** 复核仍报 `_gradient_key` 的 BFloat16 TypeError + 两 `nn.Linear` 同名梯度串扰，真实未解决、需源码级调试且本机不可验 → 推迟、不占位。rotator 36→37（偶数跑 slice 36，106 仓 / 20 候选全已处置）。**0 认领 / 0 新 PR / 1 评审回应 / 1 推送（发布说明至在飞分支）**，详见 rounds-log 本轮。

> 2026-11-10 16:52 GMT+8 第 155 轮对账：权威在飞 **75** / 台账 75，盲点 0 / 过期 0，本轮零变化（仅时间戳）；`haystack#13633` CI 9✓/4✗ → 2✓/1✗/6…（重跑中，非我方引入）。收件箱首拉 10 + 轮末二次复核 2 = **12 条全部当轮 disposition**，终检 0 pending（1984 reported / 2066 done）；本地 `policy_reason` 批查砍 4（`fastmcp` 须 assign 人工门禁、`trl` AI policy×3），余 8 条逐条 timeline + 同仓 open PR 号段 + `claim_check` 全弃（竞品/自开 PR 3：`deer-flow#8097`→`#8098`/`docling#5273`→`#5274`/`smolagents#3143`→`#3144`；`crewai#9314` 已被 `its-amann` 认领；`haystack#13657` 标 `handled internally`；`semantic-kernel#14773` 为 feature；`crewai#9315` 同仓在飞 2 达上限 HOLD；`deer-flow#8099` 五查全清但需完整 backend 栈本机不可跑验）。全池 `--all` 350 仓 NEW 含 12 条 inbox 已判 + 7 新面孔（frappe#46841-47/lancedb#4937/polars#30695/pillow#10482/mypy#22427/reflex#7785/inspect_ai#6448），九查后 **0 干净候选**（仓级政策砍 inspect_ai 缺 accepted/frappe vouched/mypy 贡献类别 3；polars#30695 标 accepted、mypy feature、reflex 前端 TS、lancedb Java/CI、pillow CI flaky、frappe 分阶段设计跟踪单均不可本机验/非缺陷）。dispositions 1165 未增（rotator 37 奇数跳过 maintainer_sweep，新面孔下轮偶数/强制跑落账）。review_sweep 1 ACTION＝`accelerate#4504` 审查者 `Michael-RDev` 最新 head 仍报 `_gradient_key` BFloat16 TypeError + 两 `nn.Linear` 同名梯度串扰，需 DDP 多进程 CPU 测试方可验证、本机不可验 → 维持第 154 轮「推迟、不占位」。**0 认领 / 0 新 PR / 0 评审回应 / 0 推送**，详见 rounds-log 本轮。

> 2026-11-10 00:52–01:0x UTC / 08:52 GMT+8 第 153 轮对账：权威在飞 **75** / 台账 75，盲点 0 / 过期 0，本轮零变化（仅时间戳）；15 条 ⚠CI 逐条回认（backport/codecov/Vercel 部署授权/Mergify/devflow/enforce-label/skill-sync 等门禁族与 status context、coveragepy macOS 3.13–3.15 与 dask nightly 平台性失败、dagster buildkite 继承 main、我方自有实验仓、any-agent 旧重跑残留）**无一属我方引入**，无 ACTION。收件箱首拉 43 + 轮内新投 1 = **44 条全部当轮 disposition**，二次复核 0 pending（1906 reported / 1988 done）；全池 `--all` 350 仓 34 NEW 九查后 **0 干净候选**（boltons 单仓 query incomplete，与上轮相同，未改代码）。review_sweep 1 ACTION（`markdown#1688` 两条维护者间对话「等 facelessuser 审」/「在我清单上」，无具体请求）→ 判过不回复；rotator 35→36（奇数强制跑 slice 35 防停摆，105 仓 / 28 候选全已处置）；dispositions 1095→1144。**0 认领 / 0 PR / 0 回复 / 0 推送**，详见 rounds-log 本轮。

> 2026-11-09 23:1xZ 第 152 轮对账：权威在飞 **75** / 台账 75，盲点 0 / 过期 0；本轮 2 条合并离场（`tobymao/sqlglot#8959`、`bytedance/deer-flow#8057`），台账自动清理。收件箱首拉 17 + 轮末 2 = 19 条全部当轮 disposition、终检 0 pending（1862 / 1944）；全池 350 仓 30 NEW 九查后 **0 干净候选**（`--all` 因 boltons 单仓 query incomplete 退出码 1、watermark 未推进，其余 349 仓正常）。review_sweep 2 ACTION：`markdown#1688` 维护者间对话判过不回复；`factory_boy#1161` 维护者以 `#1164` 重构取代我方实现 → **1 条实质评审回应**（认同设计异议 + 让出 + 暂不关闭理由），因替代方案 CI 6 平台真红未落地、本机缺 Django 无法完成结案判据，故**不关闭**。rotator 34→35（slice 34：104 仓 / 35 候选全已处置）；dispositions 1081→1095。**0 认领 / 0 PR / 0 推送 / 1 评审回应**，详见 rounds-log 本轮。

> 2026-11-09 21:4xZ 第 151 轮对账：权威在飞 **77** / 台账 77，盲点 0 / 过期 0，零变化（仅时间戳）；15 条 ⚠CI 逐条回认（head sha + 失败 check 名）无一属我方（门禁族 / macOS 平台 / Vercel status context / 旧重跑残留）。收件箱首拉 14 + 轮末新投 7 + 写日志后第三次投递 4 = 25 条全部当轮 disposition、连续两次终检 0 pending（1843 / 1925）；全池 350 仓 22 NEW 九查后 **0 干净候选**（仓级政策 11、竞品号段 6、软认领+bot 已贴完整修复 1、CTracer C 层不可本机验 3、设计提案/功能模板/前端 若干）。review_sweep 1 ACTION（`markdown#1688` 维护者间对话、无具体请求）→ 判过不回复；rotator 33→34（强制跑 slice 33，27 候选全已处置）；dispositions 1063→1081。**0 认领 / 0 PR / 0 回复 / 0 推送**，详见 rounds-log 本轮。

> 2026-11-09 20:2xZ 第 150 轮对账：权威在飞 **77** / 台账 77，盲点 0 / 过期 0，零变化（仅时间戳）；15 条 ⚠CI 逐条回认无一属我方（门禁族 / macOS 平台 / Vercel status context）。收件箱首拉 5 + 轮末二次复核新投 5 = 10 条全部当轮 disposition、连续两次终检 0 pending（1818 / 1900）；全池 350 仓 30 NEW 九查后 **0 干净候选**（`tobymao/sqlglot#8963` 五项全清但属 DATEDIFF 语义设计演进区 + AI 协同成对发单者，需方案共识判弃）。review_sweep 1 ACTION（`markdown#1688` 维护者间对话、无具体请求）→ 判过不回复；rotator 32→33（slice 32，27 候选全已处置）；反向自查 4 疑似全为误报不编码；dispositions 1031→1063。**0 认领 / 0 PR / 0 回复 / 0 推送**，详见 rounds-log 本轮。

> 2026-11-09 19:0xZ 第 149 轮对账：权威在飞 **77** / 台账 77，盲点 0 / 过期 0，零变化（仅 `markdown#1688` 的 CI 运行刷新）；15 条 ⚠CI 逐条回认无一属我方。收件箱 12 + 轮末 5 = 17 条全部当轮 disposition、连续两次终检 0 pending（1808 / 1890）；全池 350 仓 44 NEW 九查后 **0 干净候选**。实质产出＝`apache/iceberg-python` 仓级漏编码：默认分支 `AGENTS.md`「GitHub Write Approval」要求任何 GitHub 写动作须本会话逐动作明确批准（会话内批准型人工门禁），已补 `manual_gate` + `INTERACTION_HOLDS` 双通道与回归断言（29 passed / 168 subtests；全套 469 passed）。review_sweep 1 ACTION（`markdown#1688` 维护者对第三方的评审提醒，无具体请求）→ 判过不回复；rotator 31→32（强制跑 slice 31，28 候选全已处置）；dispositions 1011→1031。**0 认领 / 0 PR / 0 回复 / 0 推送**，详见 rounds-log 本轮。
>
> 2026-11-09 17:4xZ 第 148 轮对账：权威在飞 **77** / 台账 77，盲点 1 = 本轮新 PR `sqlglot#8959`，已同轮补录上表。收件箱首拉 7 条 + 轮末新投 15 条 = **22 条全部当轮 disposition，0 pending**（1782 reported / 1864 done）。全池 350 仓 26 NEW，收件箱之外 20 条九查后 **1 个干净候选 → 投出 `tobymao/sqlglot#8959`**（嵌套 INITCAP 转 DuckDB 抛 ParseError；根因 `exp.case().when()` 用默认方言重解析已生成的 DuckDB SQL；修法改用生成方言解析并保留规范化输出形式）。改前 9 subTest 全 ParseError → 改后 9/9 通过；177 方言测试 / 1599 全量单测 / ruff 均通过；quality_check prepare+check EVIDENCE_OK。review_sweep 3 更新 / 0 人类活动 / 0 ACTION；rotator 31（奇数按规则跳过，保持 31）。**1 PR / 0 认领 / 0 回复**，详见 rounds-log 本轮。
>
> 2026-11-09 16:1xZ 第 147 轮对账：权威在飞 **76** / 台账 76，盲点 0 / 过期 0，无合并、关闭或新增，零变化（仅时间戳）；15 条 ⚠CI 全量回认无一属我方（`haystack#13633` 的 1✗ 为 `Vercel` 部署授权 status context、`any-agent#969` 为旧重跑残留，其余门禁族/继承 main）。收件箱 9 + 轮末 1 + 写日志前 5 = 15 条全当轮 disposition、连续两次 stats 0 pending（1760 / 1841）；全池 350 仓 `seen` 新增 721 条，openhands 约 680 条整类撞仓级人工门禁，余 31 条非 openhands 九查后 **0 干净候选**（dispositions 985→1010）。review_sweep 0 ACTION；rotator 30→31（slice 30 全已处置）。**0 认领 / 0 PR / 0 回复 / 0 推送**，详见 rounds-log 本轮。
>
> 上一轮（第 146 轮，14:4xZ）：权威 76 / 台账 76，25 条收件箱清零、全池 36 NEW 0 干净候选；唯一五项全清候选 `pydicom/pydicom#2425` 因 PR 模板「We do not accept AI-only PRs」人工门禁弃投（本地修复与验证完备但未开 PR，patch 存档），门禁已补编码 `policy_reason`。

| PR | 仓库 | 状态 | 摘要 |
| --- | --- | --- | --- |
| [#16718](https://github.com/Significant-Gravitas/AutoGPT/pull/16718) | Significant-Gravitas/AutoGPT | OPEN(2026-11-11) | fix(backend): don't apply library agent PATCH fields when the version update is refused |
| [#13336](https://github.com/wandb/wandb/pull/13336) | wandb/wandb | OPEN(2026-11-08) | fix(cli): materialize projects paginator before the length check |
| [#2727](https://github.com/paramiko/paramiko/pull/2727) | paramiko/paramiko | OPEN(2026-11-08) | fix: strip OpenSSH-style inline comments from SSHConfig values |
| [#8437](https://github.com/microsoft/autogen/pull/8437) | microsoft/autogen | OPEN(2026-11-06) | fix: serialize state and history writes in the agentchat FastAPI sample |
| [#5952](https://github.com/Aider-AI/aider/pull/5952) | Aider-AI/aider | OPEN(2026-11-06) | fix: give assistant_output the same ASCII fallback as _tool_message |
| [#866](https://github.com/run-llama/llama-agents/pull/866) | run-llama/llama-agents | OPEN(2026-11-06) | fix: count StepFailedEvent handlers as top-level producers in multi-slot validation |
| [#24020](https://github.com/run-llama/llama_index/pull/24020) | run-llama/llama_index | OPEN(2026-11-07) | fix: count generated tool calls in the token-counting usage-less fallback |
| [#4507](https://github.com/huggingface/accelerate/pull/4507) | huggingface/accelerate | OPEN(2026-11-07) | fix: stop BatchSamplerShard padding from mutating sampler-owned batches |
| [#4504](https://github.com/huggingface/accelerate/pull/4504) | huggingface/accelerate | OPEN(2026-11-07) | fix: persist partial gradients in save_state for mid-accumulation checkpoints |
| [分支](https://github.com/inchang-ing/huggingface_hub/pull/new/fix/inference-endpoints-token-propagation) | huggingface/huggingface_hub | 分支已推(2026-11-10) · PR 待代开 | fix: propagate token and api in Inference Endpoints listing (fixes #5327) |
| [#34406](https://github.com/dagster-io/dagster/pull/34406) | dagster-io/dagster | OPEN(2026-11-05) | Fix Helm command flow sequence indentation in daemon and webserver deployments |
| [#11784](https://github.com/pylint-dev/pylint/pull/11784) | pylint-dev/pylint | OPEN(2026-11-05) | Fix false positive for too-many-statements on empty function bodies |
| [#3770](https://github.com/agentscope-ai/agentscope/pull/3770) | agentscope-ai/agentscope | OPEN(2026-11-05) | fix(app): re-establish the wakeup signal subscription when it ends |
| [#3467](https://github.com/pygments/pygments/pull/3467) | pygments/pygments | OPEN(2026-11-05) | Fill in version_added for five lexers whose version line never rendered |
| [#6310](https://github.com/browser-use/browser-use/pull/6310) | browser-use/browser-use | OPEN(2026-11-05) | fix: accept the advertised doctor flags instead of rejecting them |
| [#5945](https://github.com/Aider-AI/aider/pull/5945) | Aider-AI/aider | OPEN(2026-11-04) | fix: don't crash startup when litellm ships a new exception type |
| [#6300](https://github.com/browser-use/browser-use/pull/6300) | browser-use/browser-use | OPEN(2026-11-04) | fix(cli): report the browser-use package version for --version |
| [#3052](https://github.com/truera/trulens/pull/3052) | truera/trulens | OPEN(2026-11-03) | fix(dataset): keep parquet list columns as their elements when curating |
| [#3057](https://github.com/truera/trulens/pull/3057) | truera/trulens | OPEN(2026-11-05) | fix(huggingface): score an empty statement as ungrounded, not nan |
| [#2359](https://github.com/coveragepy/coveragepy/pull/2359) | coveragepy/coveragepy | OPEN(2026-11-04) | fix: don't treat a touched file as a conflicting tracer claim |
| [#3981](https://github.com/Arize-ai/openinference/pull/3981) | Arize-ai/openinference | OPEN(2026-10-17) | Fix #3803: record attributes for tuple-valued and unsupported message content parts |
| [#4633](https://github.com/traceloop/openllmetry/pull/4633) | traceloop/openllmetry | OPEN(2026-10-18) | fix(sdk): keep local dataset state when a delete request fails |
| [#46262](https://github.com/BerriAI/litellm/pull/46262) | BerriAI/litellm | OPEN(2026-10-17) |  |
| [#7795](https://github.com/crewAIInc/crewAI/pull/7795) | crewAIInc/crewAI | OPEN(2026-10-17) | fix(openai): allow multimodal file inputs for GPT-6 Astra |
| [#7981](https://github.com/crewAIInc/crewAI/pull/7981) | crewAIInc/crewAI | OPEN(2026-10-17) |  |
| [#12636](https://github.com/dask/dask/pull/12636) | dask/dask | OPEN(2026-10-17) |  |
| [#20873](https://github.com/DataDog/dd-trace-py/pull/20873) | DataDog/dd-trace-py | OPEN(2026-10-17) | Fix #20782: map Anthropic 1h cache creation tokens to the correct span attribute |
| [#20877](https://github.com/DataDog/dd-trace-py/pull/20877) | DataDog/dd-trace-py | OPEN(2026-10-17) | Fix #20858: reset ASGI ExecutionContext between keep-alive requests |
| [#20935](https://github.com/DataDog/dd-trace-py/pull/20935) | DataDog/dd-trace-py | OPEN(2026-10-24 入账) | fix(tracing): keep dd= member within W3C 256-char limit; emmettbutler 已 APPROVED(10-12), 待 apm-idm-python spec 审查 |
| [#1526](https://github.com/Delgan/loguru/pull/1526) | Delgan/loguru | OPEN(2026-10-17) | Fix #1525: neutralise C0/C1 control characters in log messages |
| [#4439](https://github.com/docling-project/docling/pull/4439) | docling-project/docling | OPEN(2026-10-17) | fix(xb): don't dereference memberQname on typed dimensions |
| [#15023](https://github.com/huggingface/diffusers/pull/15023) | huggingface/diffusers | OPEN(2026-10-17) |  |
| [#682](https://github.com/mala-project/mala/pull/682) | mala-project/mala | OPEN(2026-10-17) |  |
| [#5337](https://github.com/pypa/setuptools/pull/5337) | pypa/setuptools | OPEN(2026-10-17) | Extract tar members through the tarfile data filter |
| [#986](https://github.com/QwenLM/Qwen-Agent/pull/986) | QwenLM/Qwen-Agent | OPEN(2026-10-17) | fix(agents): uniquify dialogue history filenames per run |
| [#3187](https://github.com/repowise-dev/repowise/pull/3187) | repowise-dev/repowise | OPEN(2026-10-17) |  |
| [#23876](https://github.com/run-llama/llama_index/pull/23876) | run-llama/llama_index | OPEN(2026-11-01) | fix(core): let Memory.reset() win over writes that are still in flight |
| [#23998](https://github.com/run-llama/llama_index/pull/23998) | run-llama/llama_index | OPEN(2026-11-06) | fix(core): ignore non-query brackets in the FLARE output parser |
| [#3046](https://github.com/snowflakedb/snowflake-connector-python/pull/3046) | snowflakedb/snowflake-connector-python | OPEN(2026-10-17) | fix: honor external_browser_timeout in the externalbrowser flow |
| [#3050](https://github.com/snowflakedb/snowflake-connector-python/pull/3050) | snowflakedb/snowflake-connector-python | OPEN(2026-10-17) | Fix #3049: apply force_microsecond_precision to TIMESTAMP_NTZ/LTZ(7) |
| [#2307](https://github.com/tortoise/tortoise-orm/pull/2307) | tortoise/tortoise-orm | OPEN(2026-10-17) |  |
| [#2392](https://github.com/tortoise/tortoise-orm/pull/2392) | tortoise/tortoise-orm | OPEN(2026-11-02) | fix(transactions): return the pool connection when entering a transaction is cancelled |
| [#2180](https://github.com/weaviate/weaviate-python-client/pull/2180) | weaviate/weaviate-python-client | OPEN(2026-10-17) | fix(batch): filter re-added errors by uuid and avoid the deprecated all_responses read |
| [#5349](https://github.com/pypa/setuptools/pull/5349) | pypa/setuptools | OPEN(2026-10-12) | Restore hashability of Extension via eq=False (fix #5303) |
| [#1546](https://github.com/bottlepy/bottle/pull/1546) | bottlepy/bottle | OPEN(2026-10-12) | Fix mounted apps using the parent error handlers (#1205) |
| [#3791](https://github.com/tornadoweb/tornado/pull/3791) | tornadoweb/tornado | OPEN(2026-10-12) | Fix Subprocess.wait_for_exit hanging when child already ran |
| [#2826](https://github.com/deepchecks/deepchecks/pull/2826) | deepchecks/deepchecks | OPEN(2026-10-12) | Fix single dataset performance conditions for metrics with a |
| [#14017](https://github.com/aio-libs/aiohttp/pull/14017) | aio-libs/aiohttp | OPEN(2026-10-12) | Fix RequestHandler crash after connection_lost() during keep |
| [#2332](https://github.com/jupyter/nbconvert/pull/2332) | jupyter/nbconvert | OPEN(2026-10-13) | Preserve safe subdirectories in extracted output filenames |
| [#2993](https://github.com/huggingface/smolagents/pull/2993) | huggingface/smolagents | OPEN(2026-10-15) | Fix comprehension scoping to match CPython closure capture |
| [#987](https://github.com/python-poetry/poetry-core/pull/987) | python-poetry/poetry-core | OPEN(2026-10-18) | fix: generate valid PEP 508 metadata for OR version constrai |
| [#4526](https://github.com/zarr-developers/zarr-python/pull/4526) | zarr-developers/zarr-python | OPEN(2026-10-18) | fix: tolerate unencodable default_scalar in ShardingCodec.validate（11-01 冲突已解，merge 双父 9f7cea0，MERGEABLE 待 d-v-b 复评） |
| [#11759](https://github.com/pydata/xarray/pull/11759) | pydata/xarray | OPEN(2026-10-19) | Fix rolling(center=True) splitting the rolling dimension int |
| [#14752](https://github.com/sphinx-doc/sphinx/pull/14752) | sphinx-doc/sphinx | OPEN(2026-10-19) | autodoc: register alias targets for type aliases so runtime- |
| [#1688](https://github.com/Python-Markdown/markdown/pull/1688) | Python-Markdown/markdown | OPEN(2026-11-04) | Fix HTML blocks nested in indented blocks (#1096)，改容器方案，基于 facelessuser 原型分支 |
| [#2814](https://github.com/mhammond/pywin32/pull/2814) | mhammond/pywin32 | OPEN(2026-10-20) | Detect namespace packages in gencache._GetModule |
| [#1161](https://github.com/FactoryBoy/factory_boy/pull/1161) | FactoryBoy/factory_boy | OPEN(2026-10-20) | Fix django_get_or_create for factories built through SubFact |
| [#4023](https://github.com/mwaskom/seaborn/pull/4023) | mwaskom/seaborn | OPEN(2026-10-21) | Fix catplot crash when plotting an empty DataFrame |
| [#600](https://github.com/XiaoMi/xiaomi-miloco/pull/600) | XiaoMi/xiaomi-miloco | OPEN(2026-10-21) | fix video mp4 container duration using capture window instea |
| [#602](https://github.com/XiaoMi/xiaomi-miloco/pull/602) | XiaoMi/xiaomi-miloco | OPEN(2026-10-21) | fix(config): refuse to clobber unreadable config.json on mer |
| [#48309](https://github.com/BerriAI/litellm/pull/48309) | BerriAI/litellm | OPEN(2026-10-25) | fix(docker): bump UI_BUILD_IMAGE to node 24.22.1 (Oct 2026 s |
| [#4459](https://github.com/EleutherAI/lm-evaluation-harness/pull/4459) | EleutherAI/lm-evaluation-harness | OPEN(2026-10-25) | fix: only strip the thinking prefix when the token is presen |
| [#56](https://github.com/explosion/preshed/pull/56) | explosion/preshed | OPEN(2026-10-25) | Fix OverflowError for keys above 2**63 after the Cython 3 re |
| [#3529](https://github.com/confident-ai/deepeval/pull/3529) | confident-ai/deepeval | OPEN(2026-10-25) | fix(benchmarks): score EquityMedQA without inverting BiasMet |
| [#17429](https://github.com/Arize-ai/phoenix/pull/17429) | Arize-ai/phoenix | OPEN(2026-10-31) | fix(phoenix-otel): treat empty process env values as unset |
| [#8588](https://github.com/pymc-devs/pymc/pull/8588) | pymc-devs/pymc | OPEN(2026-10-31) | fix(timeseries): scope the support_shape_offset to the steps dimension |
| [#11770](https://github.com/pylint-dev/pylint/pull/11770) | pylint-dev/pylint | OPEN(2026-10-31) | Fix false-positive used-before-assignment for walrus in nested dict values |
| [#2350](https://github.com/coveragepy/coveragepy/pull/2350) | coveragepy/coveragepy | OPEN(2026-10-25) | fix: hold the data lock only to snapshot, and make it re-ent |
| [#3074](https://github.com/vibrantlabsai/ragas/pull/3074) | vibrantlabsai/ragas | OPEN(2026-10-31) | docs: use Answer Relevancy consistently for the answer_relevance metric |
| [#969](https://github.com/mozilla-ai/any-agent/pull/969) | mozilla-ai/any-agent | OPEN(2026-11-01) | fix(vendor): keep reasoning_content and extra_content through the LangChain tool loop |
| [#817](https://github.com/python-attrs/cattrs/pull/817) | python-attrs/cattrs | OPEN(2026-11-01) | docs: fix structure() output for Sequence[str] in why.md |
| [#5125](https://github.com/docling-project/docling/pull/5125) | docling-project/docling | OPEN(2026-11-01) | fix(datamodel): only accept a tar guess that the header confirms |
| [#1473](https://github.com/huggingface/lighteval/pull/1473) | huggingface/lighteval | OPEN(2026-11-03) | Fill in the translation literals for Latvian, Lithuanian, Maltese and Slovenian |
| [#5843](https://github.com/robotframework/robotframework/pull/5843) | robotframework/robotframework | OPEN(2026-11-02) | Handle cyclic exception chains when removing Robot traces |

## 个人 fork 在飞（21）

| PR | 仓库 | 状态 | 摘要 |
| --- | --- | --- | --- |
| [#153](https://github.com/inchang-ing/code-security-workbench/pull/153) | inchang-ing/code-security-workbench | OPEN(2026-10-17) | D6-11：SQL/YAML 真实资格基线与未完成网页验收 |
| [#161](https://github.com/inchang-ing/code-security-workbench/pull/161) | inchang-ing/code-security-workbench | OPEN(2026-10-17) | D6-25：公网 HTTPS 评审入口与实际代理边界验证 |
| [#162](https://github.com/inchang-ing/code-security-workbench/pull/162) | inchang-ing/code-security-workbench | OPEN(2026-10-17) | fix(ui): 正常读取通用静态检查失败记录 |
| [#1](https://github.com/inchang-ing/commerce-ops-xianyu/pull/1) | inchang-ing/commerce-ops-xianyu | OPEN(2026-10-17) | feat: 商品素材优化中心与项目整理 v0.8.1（含此前未合并升级） |
| [#2](https://github.com/inchang-ing/commerce-ops-xianyu/pull/2) | inchang-ing/commerce-ops-xianyu | OPEN(2026-10-17) | docs: 2026-09-07 多SKU每周阻塞审计 |
| [#3](https://github.com/inchang-ing/commerce-ops-xianyu/pull/3) | inchang-ing/commerce-ops-xianyu | OPEN(2026-10-17) | fix: 仅修改标题正文并保留原图 |
| [#4](https://github.com/inchang-ing/commerce-ops-xianyu/pull/4) | inchang-ing/commerce-ops-xianyu | OPEN(2026-10-17) | fix: 单规格文案保护、编号排版及本机审核提交修复 |
| [#5](https://github.com/inchang-ing/commerce-ops-xianyu/pull/5) | inchang-ing/commerce-ops-xianyu | OPEN(2026-10-17) | feat: isolate quality tools and establish tool reuse catalog |
| [#6](https://github.com/inchang-ing/commerce-ops-xianyu/pull/6) | inchang-ing/commerce-ops-xianyu | OPEN(2026-10-17) | feat: Chrome 只读长连接 MVP v0.10.0 |
| [#7](https://github.com/inchang-ing/commerce-ops-xianyu/pull/7) | inchang-ing/commerce-ops-xianyu | OPEN(2026-10-17) | feat: 第二轮 uv 管理与 Trafilatura 离线试验 v0.11.0 |
| [#8](https://github.com/inchang-ing/commerce-ops-xianyu/pull/8) | inchang-ing/commerce-ops-xianyu | OPEN(2026-10-17) | docs: Trafilatura 边界验证与真实对照阻塞 |
| [#9](https://github.com/inchang-ing/commerce-ops-xianyu/pull/9) | inchang-ing/commerce-ops-xianyu | OPEN(2026-10-17) | docs: 详情图片 OCR 实验与核验缺口 |
| [#10](https://github.com/inchang-ing/commerce-ops-xianyu/pull/10) | inchang-ing/commerce-ops-xianyu | OPEN(2026-10-17) | docs: Paddle OCR 同样本对照与模型登记 |
| [#11](https://github.com/inchang-ing/commerce-ops-xianyu/pull/11) | inchang-ing/commerce-ops-xianyu | OPEN(2026-10-17) | docs: v6 medium OCR 精度与资源实测 |
| [#12](https://github.com/inchang-ing/commerce-ops-xianyu/pull/12) | inchang-ing/commerce-ops-xianyu | OPEN(2026-10-17) | feat: 详情 OCR 受限增强与人工核验接入 v0.12.0 |
| [#13](https://github.com/inchang-ing/commerce-ops-xianyu/pull/13) | inchang-ing/commerce-ops-xianyu | OPEN(2026-10-17) | feat: multi-shop readiness and source error classification (partial workflow) |
| [#14](https://github.com/inchang-ing/commerce-ops-xianyu/pull/14) | inchang-ing/commerce-ops-xianyu | OPEN(2026-10-17) | feat: 多账号上架准备检查接入控制台 v0.14.0 |
| [#15](https://github.com/inchang-ing/commerce-ops-xianyu/pull/15) | inchang-ing/commerce-ops-xianyu | OPEN(2026-10-17) | fix: 读取中心反馈、店铺确认与可靠回执恢复 |
| [#16](https://github.com/inchang-ing/commerce-ops-xianyu/pull/16) | inchang-ing/commerce-ops-xianyu | OPEN(2026-10-17) | feat: Edge 任推邦持久只读会话 v0.15.0 |
| [#17](https://github.com/inchang-ing/commerce-ops-xianyu/pull/17) | inchang-ing/commerce-ops-xianyu | OPEN(2026-10-17) | feat: AI 任务工作台 G0 验证与 Cloudflare Pages 入口 |
| [#18](https://github.com/inchang-ing/commerce-ops-xianyu/pull/18) | inchang-ing/commerce-ops-xianyu | OPEN(2026-10-17) | docs: 9月21日多 SKU 周审计受阻记录 |
