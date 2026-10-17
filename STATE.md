# STATE.md — 在飞 PR 紧凑台账(2026-10-07 重建自 GitHub 权威源)

> 本文件只保留**当前 OPEN 的 PR 权威列表**(监控脚本解析用),每行含 `pull/<N>` + `OPEN(`。
>
> 历史轮次叙事、已合并/关闭 PR 的详细验证记录 → **STATE-archive.md**(全量归档,勿删)。
>
> 单一事实源 = GitHub;本台账每周/每轮开新 PR 时据此 `+N` 行重建,不无限增长。

## OSS 贡献在飞(19)

| PR                                                                           | 仓库                                     | 状态                                                                                                                                         | 修复内容                                      |
| ---------------------------------------------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------- |
| [#2717](https://github.com/567-labs/instructor/pull/2717)                    | 567-labs/instructor                    | OPEN(2026-10-07 重建)                                                                                                                        | gemini MD_JSON 不复用/污染调用方 messages         |
| [#2736](https://github.com/567-labs/instructor/pull/2736)                    | 567-labs/instructor                    | OPEN(2026-10-07 重建)                                                                                                                        | gpt-3.5-turbo 弃用→默认 gpt-4.1-mini          |
| [#20769](https://github.com/DataDog/dd-trace-py/pull/20769)                  | DataDog/dd-trace-py                    | OPEN(2026-10-07 重建)                                                                                                                        | vLLM>=0.20 移除 num_cached_tokens 守卫        |
| [#682](https://github.com/OpenBMB/ChatDev/pull/682)                          | OpenBMB/ChatDev                        | OPEN(2026-10-07 重建)                                                                                                                        | 动态工具模块 exec 前注册 sys.modules               |
| [#986](https://github.com/QwenLM/Qwen-Agent/pull/986)                        | QwenLM/Qwen-Agent                      | OPEN(2026-10-07 重建)                                                                                                                        | 同秒历史文件名碰撞跨会话泄漏→uuid4 后缀                   |
| [#15476](https://github.com/bokeh/bokeh/pull/15476)                          | bokeh/bokeh                            | OPEN(2026-10-08 bryevdv 两点已修 head=3a94209)                                                                                                 | legend_group 含 None 字符串列崩溃                |
| [#7795](https://github.com/crewAIInc/crewAI/pull/7795)                       | crewAIInc/crewAI                       | OPEN(2026-10-07 重建)                                                                                                                        | GPT-6 Astra 多媒体文件输入                       |
| [#13094](https://github.com/deepset-ai/haystack/pull/13094)                  | deepset-ai/haystack                    | OPEN(2026-10-07 重建)                                                                                                                        | \_deepcopy_with_exceptions 保留 dict 子类     |
| [#4439](https://github.com/docling-project/docling/pull/4439)                | docling-project/docling                | OPEN(2026-10-10 ai-pr-triage blocker 已修:force-add 缺失实例+docstring路径+改 doc.key_value_items 断言+getattr注释,head=6490911b,DCO 已签,4条triage已回Done) | typed dimension 误解引用 memberQname          |
| [#442](https://github.com/executablebooks/markdown-it-py/pull/442)           | executablebooks/markdown-it-py         | OPEN(2026-10-07 重建)                                                                                                                        | 列表项外 HTML 块起始关列表                          |
| [#443](https://github.com/executablebooks/markdown-it-py/pull/443)           | executablebooks/markdown-it-py         | OPEN(2026-10-07 重建)                                                                                                                        | 规则不推进 state 死循环守卫                         |
| [#5717](https://github.com/open-telemetry/opentelemetry-python/pull/5717)    | open-telemetry/opentelemetry-python    | OPEN(2026-10-10 lzchen两点review已回Done head=1a6912a; EasyCLA 通过)                                                                             | DELTA 聚合 collect 重置 exponent mapping      |
| [#2385](https://github.com/pydicom/pydicom/pull/2385)                        | pydicom/pydicom                        | OPEN(**2026-10-14 rebase 解冲突**: head=503b13a, mergeable=MERGEABLE, 原 CONFLICTING;APPROVED, 待维护者合)                                                      | ISO 2022 IR 58 GB2312 转义序列(GH#2383)       |
| [#5337](https://github.com/pypa/setuptools/pull/5337)                        | pypa/setuptools                        | OPEN(2026-10-07 重建)                                                                                                                        | tar 解包过 tarfile data filter(jaraco #5328) |
| [#431](https://github.com/pytest-dev/execnet/pull/431)                       | pytest-dev/execnet                     | MERGED(2026-10-09 维护者合并,此前 CHANGES_REQUESTED 陈旧,两点已满足)                                                                                     | safe_terminate 后 join + 返回 waitall 结果     |
| [#3046](https://github.com/snowflakedb/snowflake-connector-python/pull/3046) | snowflakedb/snowflake-connector-python | OPEN(2026-10-07 重建)                                                                                                                        | externalbrowser 流超时约束                     |
| [#2180](https://github.com/weaviate/weaviate-python-client/pull/2180)        | weaviate/weaviate-python-client        | OPEN(2026-10-10 CLA 已回同意 comment 6095057639;2026-10-10 监控=MERGEABLE+CI全绿+reviewDecision空待review)                                           | batch 重加错误按 uuid 过滤 + 弃用 all_responses    |
| [#967](https://github.com/yaml/pyyaml/pull/967)                              | yaml/pyyaml                            | OPEN(2026-10-07 重建)                                                                                                                        | 前导零数字串 dump 加引号                           |

## 2026-10-08 新增 OSS PR(10,目标达成)

| PR                                                                           | 仓库                                     | 状态                                                                  | 修复内容                                                                |
| ---------------------------------------------------------------------------- | -------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------- |
| [#20873](https://github.com/DataDog/dd-trace-py/pull/20873)                  | DataDog/dd-trace-py                    | OPEN                                                                | Anthropic 流式 1h cache 写入误记 5m → 正确 TTL 分解                           |
| [#20874](https://github.com/DataDog/dd-trace-py/pull/20874)                  | DataDog/dd-trace-py                    | CLOSED(2026-10-09 被 upstream #20820 等价修复取代,已关)                      | 生成 dd tracestate 超 256 字符 → upstream #20820 已合入等价修复,冗余关闭            |
| [#20877](https://github.com/DataDog/dd-trace-py/pull/20877)                  | DataDog/dd-trace-py                    | OPEN(2026-10-09 rebase 到 main, 冲突已解, head=492fd0648, mergeable 重算中) | ASGI keep-alive 跨请求链到上请求 context → nearest_active_context           |
| [#20883](https://github.com/DataDog/dd-trace-py/pull/20883)                  | DataDog/dd-trace-py                    | OPEN                                                                | google_genai 漏 tool_use_prompt_token_count → input+output==total    |
| [#20886](https://github.com/DataDog/dd-trace-py/pull/20886)                  | DataDog/dd-trace-py                    | OPEN                                                                | gevent 下 warnings 被卸载致 captureWarnings 失效 → KEEP_MODULES 加 warnings |
| [#3981](https://github.com/Arize-ai/openinference/pull/3981)                 | Arize-ai/openinference                 | OPEN                                                                | tuple/不支持 content part 无属性 → 记录 type                                |
| [#3982](https://github.com/Arize-ai/openinference/pull/3982)                 | Arize-ai/openinference                 | OPEN                                                                | 流提前退出把占位 {} 当最终 tool args → 省略占位                                    |
| [#3050](https://github.com/snowflakedb/snowflake-connector-python/pull/3050) | snowflakedb/snowflake-connector-python | OPEN                                                                | force_microsecond_precision 对 NTZ/LTZ(7) 未截断为微秒                     |
| [#10472](https://github.com/statsmodels/statsmodels/pull/10472)              | statsmodels/statsmodels                | OPEN                                                                | SARIMAX start_params 裸 squeeze 致 0 维 endog IndexError               |
| [#1526](https://github.com/Delgan/loguru/pull/1526)                          | Delgan/loguru                          | OPEN                                                                | opt-in sanitize 中和 C0/C1 控制字符(转义注入)                                 |

> 当日弃置(确认撞车/已修/设计,按纪律不强提):dd-trace#20871(已有在飞 #20872)、langchain#41141(报告者认领)、langchain#40895(认领)、langchain#41146(认领)、poetry#11101(认领+贡献者倾向弃用)、otel#5743(认领+维护者定聚合语义)、otel#5700(维护者裁定 nothing to fix)、PyGithub#3261(上游 #3432 已修)、bokeh#15278(上游 #15374 已修)、alembic#1121(PR#1393 已修)、alembic#1341(PR#1665 已修)。

## 2026-10-09 新增 OSS PR(目标 10,进行中)

| PR                                                           | 仓库                     | 状态                                                        | 修复内容                                                |
| ------------------------------------------------------------ | ---------------------- | --------------------------------------------------------- | --------------------------------------------------- |
| [#3995](https://github.com/Arize-ai/openinference/pull/3995) | Arize-ai/openinference | OPEN(2026-10-09 CLA pass,REVIEW_REQUIRED)                 | google-genai contents 传 tuple 未记录为 input_messages   |
| [#3053](https://github.com/microsoft/PyRIT/pull/3053)        | microsoft/PyRIT        | OPEN(2026-10-09 Microsoft CLA 已签 SUCCESS,REVIEW_REQUIRED) | PlagiarismScorer \_tokenize 不归一化且剥离 combining mark  |
| [#7981](https://github.com/crewAIInc/crewAI/pull/7981)       | crewAIInc/crewAI       | OPEN(2026-10-09 MERGEABLE,REVIEW_REQUIRED,AI 披露已写正文)      | MDXLoader 破坏 fenced/inline code 内容                  |
| [#3166](https://github.com/repowise-dev/repowise/pull/3166)  | repowise-dev/repowise  | MERGED(2026-10-10 维护者合并, closes issue#3163)               | repowise mcp 在未初始化目录创建 stray .repowise/ + 空 wiki.db |


## 2026-10-10 监控补录(6,台账外新发现 OPEN)

| PR                                                           | 仓库                     | 状态                                                                                                                                                                                                                                  | 修复内容                                                                        |
| ------------------------------------------------------------ | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| [#3998](https://github.com/Arize-ai/openinference/pull/3998) | Arize-ai/openinference | OPEN(2026-10-10 监控发现 mergeable 重算中,REVIEW_REQUIRED,CLAAssistant SUCCESS)                                                                                                                                                            | fix(agno): don't resolve an async tools factory in run attributes           |
| [#682](https://github.com/mala-project/mala/pull/682)        | mala-project/mala      | OPEN(2026-10-10 监控发现 MERGEABLE,reviewDecision 空(待 review);2026-10-10 二轮监控 CI 全绿 build/test/lint, 仍待 review)                                                                                                                         | Return a scalar float from Density.get_number_of_electrons                  |
| [#3170](https://github.com/repowise-dev/repowise/pull/3170)  | repowise-dev/repowise  | OPEN(2026-10-10 监控发现 mergeable 重算中,REVIEW_REQUIRED,CI 全绿 py3.11/3.12/3.13+tree-sitter)                                                                                                                                              | fix(claude_cli): parse the verbose event array from claude -p               |
| [#3187](https://github.com/repowise-dev/repowise/pull/3187)  | repowise-dev/repowise  | OPEN(2026-10-10 监控发现 mergeable 重算中,REVIEW_REQUIRED,Repowise/code health NEUTRAL)                                                                                                                                                    | fix(doc_drift): treat agent/editor config paths as uncheckable, not missing |
| [#3188](https://github.com/repowise-dev/repowise/pull/3188)  | repowise-dev/repowise  | OPEN(2026-10-10 监控发现 mergeable 重算中,REVIEW_REQUIRED,Repowise/code health NEUTRAL)                                                                                                                                                    | fix(ingestion): emit size-skip notices as notice, not warning (#3185)       |
| [#2307](https://github.com/tortoise/tortoise-orm/pull/2307)  | tortoise/tortoise-orm  | OPEN(2026-10-10 CI 根因=mypy arg-type 误判为 pre-commit;已改 test_migration_graph 用真实 Migration + add_dependency 首参传 child key;判别力验证撤修复复现3错/恢复0错,311 passed;amend 成 a30b980 带 Signed-off 推 fork;CI=action_required 待维护者批准,REVIEW_REQUIRED) | fix(migrations): scope leaf/root nodes to same-app edges                    |

## 2026-10-10 开新 PR 主线(langgraph#9272)

| PR                                                           | 仓库                     | 状态                                                                                                                                                     | 修复内容                                                                                                                 |
| ------------------------------------------------------------ | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| [#9272](https://github.com/langchain-ai/langgraph/pull/9272) | langchain-ai/langgraph | CLOSED(2026-10-10 建 PR 后被 require_issue_link 自动关,标签 external+missing-issue-link;#9271 已请求 assign,待维护者 assign 后 reopen_on_assignment 自动重开;head=58a38b0) | fix(checkpoint): get_tuple 按 checkpoint_id 寻址时 config 原样返回缺 checkpoint_ns → put/update_state 抛 KeyError,已构造完整 config |

## org 开 PR 权限实测(2026-10-08 probe_perm.py)

- **BLOCKED**(CreatePullRequest 拒):Textualize(rich/textual)、psf(requests)、pallets(jinja2/click/flask/werkzeug)、python-jsonschema、encode/httpx。
- **ALLOWED**(20+):dd-trace-py、openinference、snowflake、statsmodels、langchain、docling、sqlglot、pydantic、fastapi、typer、celery、networkx、attrs、anyio、pluggy、keyring、psycopg、alembic、poetry、redis-py、aiohttp、urllib3、graphene、strawberry、mypy、PyGithub、build。

## AI 政策「见即弃」名单(提 PR 前必查 devel/contributing 的 AI 段)

- **matplotlib/matplotlib**:官方 devdocs `use-of-generative-ai` **明文禁止「外部 AI 工具(bots/agents)直接与本项目交互,包括创建 issue/PR 或评论」**,且把「同时给多个项目贡献」列为 unacceptable。→ 外部 agent 开 PR 直接违规,见即弃(例: 2026-10-09 弃 #32454 Qt 弃用枚举行)。
- **useblocks/sphinx-needs**:CONTRIBUTING 明文——AI 协助本人工作可以,但「**从 issue 自动生成、由未参与讨论的账号在 issue 提交后数小时内提交的 PR 一律无审关闭**」,且外部 PR 需维护者批准才跑 CI。→ 命中此模式,见即弃(例: 2026-10-09 弃 #2165 parts 非 mapping 崩溃,尽管根因/既有修复模式 #2163 都很清晰)。
- **HypothesisWorks/hypothesis**:禁「unreviewed or fully-autonomous contributions from anyone outside the maintainers team」(例: 弃 #4897)。
- **pre-commit(asottile)**:维护者留言拒收 AI 投稿(例: #2530)。

## 个人 fork 在飞(21)

| PR                                                                      | 仓库                                  | 状态                  | 内容                                    |
| ----------------------------------------------------------------------- | ----------------------------------- | ------------------- | ------------------------------------- |
| [#153](https://github.com/inchang-ing/code-security-workbench/pull/153) | inchang-ing/code-security-workbench | OPEN(2026-10-07 重建) | D6-11 SQL/YAML 资格基线                   |
| [#161](https://github.com/inchang-ing/code-security-workbench/pull/161) | inchang-ing/code-security-workbench | OPEN(2026-10-07 重建) | D6-25 公网 HTTPS 评审入口                   |
| [#162](https://github.com/inchang-ing/code-security-workbench/pull/162) | inchang-ing/code-security-workbench | OPEN(2026-10-07 重建) | fix(ui) 读取静态检查失败记录                    |
| [#1](https://github.com/inchang-ing/commerce-ops-xianyu/pull/1)         | inchang-ing/commerce-ops-xianyu     | OPEN(2026-10-07 重建) | 商品素材优化中心 v0.8.1                       |
| [#2](https://github.com/inchang-ing/commerce-ops-xianyu/pull/2)         | inchang-ing/commerce-ops-xianyu     | OPEN(2026-10-07 重建) | 多SKU每周阻塞审计 docs                       |
| [#3](https://github.com/inchang-ing/commerce-ops-xianyu/pull/3)         | inchang-ing/commerce-ops-xianyu     | OPEN(2026-10-07 重建) | 仅改标题正文保留原图                            |
| [#4](https://github.com/inchang-ing/commerce-ops-xianyu/pull/4)         | inchang-ing/commerce-ops-xianyu     | OPEN(2026-10-07 重建) | 单规格文案保护+本机审核提交修复                      |
| [#5](https://github.com/inchang-ing/commerce-ops-xianyu/pull/5)         | inchang-ing/commerce-ops-xianyu     | OPEN(2026-10-07 重建) | isolate quality tools + reuse catalog |
| [#6](https://github.com/inchang-ing/commerce-ops-xianyu/pull/6)         | inchang-ing/commerce-ops-xianyu     | OPEN(2026-10-07 重建) | Chrome 只读长连接 MVP v0.10.0              |
| [#7](https://github.com/inchang-ing/commerce-ops-xianyu/pull/7)         | inchang-ing/commerce-ops-xianyu     | OPEN(2026-10-07 重建) | uv 管理 + Trafilatura 离线试验 v0.11.0      |
| [#8](https://github.com/inchang-ing/commerce-ops-xianyu/pull/8)         | inchang-ing/commerce-ops-xianyu     | OPEN(2026-10-07 重建) | Trafilatura 边界验证 docs                 |
| [#9](https://github.com/inchang-ing/commerce-ops-xianyu/pull/9)         | inchang-ing/commerce-ops-xianyu     | OPEN(2026-10-07 重建) | 详情图片 OCR 实验 docs                      |
| [#10](https://github.com/inchang-ing/commerce-ops-xianyu/pull/10)       | inchang-ing/commerce-ops-xianyu     | OPEN(2026-10-07 重建) | Paddle OCR 对照与模型登记 docs               |
| [#11](https://github.com/inchang-ing/commerce-ops-xianyu/pull/11)       | inchang-ing/commerce-ops-xianyu     | OPEN(2026-10-07 重建) | v6 medium OCR 精度实测 docs               |
| [#12](https://github.com/inchang-ing/commerce-ops-xianyu/pull/12)       | inchang-ing/commerce-ops-xianyu     | OPEN(2026-10-07 重建) | 详情 OCR 增强 + 人工核验 v0.12.0              |
| [#13](https://github.com/inchang-ing/commerce-ops-xianyu/pull/13)       | inchang-ing/commerce-ops-xianyu     | OPEN(2026-10-07 重建) | multi-shop readiness(partial)         |
| [#14](https://github.com/inchang-ing/commerce-ops-xianyu/pull/14)       | inchang-ing/commerce-ops-xianyu     | OPEN(2026-10-07 重建) | 多账号上架检查 v0.14.0                       |
| [#15](https://github.com/inchang-ing/commerce-ops-xianyu/pull/15)       | inchang-ing/commerce-ops-xianyu     | OPEN(2026-10-07 重建) | 反馈读取+可靠回执恢复                           |
| [#16](https://github.com/inchang-ing/commerce-ops-xianyu/pull/16)       | inchang-ing/commerce-ops-xianyu     | OPEN(2026-10-07 重建) | Edge 任推邦持久只读会话 v0.15.0                |
| [#17](https://github.com/inchang-ing/commerce-ops-xianyu/pull/17)       | inchang-ing/commerce-ops-xianyu     | OPEN(2026-10-07 重建) | AI 任务工作台 G0 验证                        |
| [#18](https://github.com/inchang-ing/commerce-ops-xianyu/pull/18)       | inchang-ing/commerce-ops-xianyu     | OPEN(2026-10-07 重建) | 多 SKU 周审计受阻记录 docs                    |

> 待办/下一步等动态状态以 GitHub 为准,监控脚本 `monitor_scope.py` 逐 PR `gh pr view` 取 state/reviewDecision/mergeable 与 baseline diff。

## 2026-10-14 新增 OSS PR(本轮)

| PR | 仓库 | 状态 | 修复内容 |
| --- | --- | --- | --- |
| [#12636](https://github.com/dask/dask/pull/12636) | dask/dask | OPEN(2026-10-14 建, head=8f744d03) | shuffle 索引/argsort 位置范围=轴长→uint8 溢出越界;dtype 改 `np.min_scalar_type(sum(chunks[axis]))` |
| [#46262](https://github.com/BerriAI/litellm/pull/46262) | BerriAI/litellm | OPEN(2026-10-14 重推 head=0ad8164; type-discipline+lint PASS; osv-scan 预存 fail 非我引入) | streaming_handler `_delta_content_as_str` 注解 list→Sequence[Mapping];4 调用点加 cast+#cast-ok+Final 过 LIT001/LIT006/LIT010 |
| [#15023](https://github.com/huggingface/diffusers/pull/15023) | huggingface/diffusers | OPEN(2026-10-14 建, head=18b1fca, MERGEABLE) | add_noise 在 set_timesteps 前用错噪声级(取 sigmas[999-t]);按 timestep 值索引 sigmas / flow 线性 sigma;回归测试 added |
| [#29928](https://github.com/pola-rs/polars/pull/29928) | pola-rs/polars | OPEN(2026-10-14 建, head=75198b4, MERGEABLE/BLOCKED review gate) | scan_delta 过滤 struct 列时 Delta stats 仅覆盖部分字段→严格 struct cast `struct[1]→struct[5]` 崩溃;新增 `_align_struct` 按名重建并缺字段填 null;回归测试 added |

### 本轮 v4 复查弃置(撞车/非 bug/已合)
- transformers#49540: **弃**(issue 评论 akasakariko "I'd like to work on this"+"i'm going to fix it" 且提及在途 PR → 软认领 TAKEN)。
- notebook#8065: **弃**(5 评论为 krassowski 排障对话,根因在 OS/浏览器配置 + jupyter_server,非 jupyter/notebook 仓库可复现代码缺陷 → 违反判别力硬门槛)。
- phoenix#16934: **弃**(issue 仅指向 PR #16926,该 PR 已于 2026-10-12 MERGED,已修复)。

### 本轮延迟→已投
- polars#29919(pola-rs/polars): **干净**(无 assignee/0 评论/无关联 PR)。原判根因在 Rust,实测根因为 **Python**(`py-polars/src/polars/io/delta/_utils.py` 的 `_extract_table_statistics_from_delta_add_actions` 对部分覆盖 stats 的 struct 做严格 cast 失败)→ 用预编译 wheel+deltalake 验证(撤修复复现崩溃/恢复全过,26–33 前导列全绿),已投 **PR #29928**(head=75198b4)。同仓在飞≤1 不冲突。
