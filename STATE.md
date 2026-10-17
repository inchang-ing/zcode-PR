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

## OSS 贡献在飞（30）

| PR | 仓库 | 状态 | 摘要 |
| --- | --- | --- | --- |
| [#2717](https://github.com/567-labs/instructor/pull/2717) | 567-labs/instructor | OPEN(2026-10-17) | fix(gemini): do not mutate caller-owned messages in MD_JSON mode |
| [#3981](https://github.com/Arize-ai/openinference/pull/3981) | Arize-ai/openinference | OPEN(2026-10-17) | Fix #3803: record attributes for tuple-valued and unsupported message content parts |
| [#3982](https://github.com/Arize-ai/openinference/pull/3982) | Arize-ai/openinference | OPEN(2026-10-17) | Fix #3904: do not record the SDK placeholder tool arguments on early stream exit |
| [#3995](https://github.com/Arize-ai/openinference/pull/3995) | Arize-ai/openinference | OPEN(2026-10-17) |  |
| [#3998](https://github.com/Arize-ai/openinference/pull/3998) | Arize-ai/openinference | OPEN(2026-10-17) |  |
| [#46262](https://github.com/BerriAI/litellm/pull/46262) | BerriAI/litellm | OPEN(2026-10-17) |  |
| [#7795](https://github.com/crewAIInc/crewAI/pull/7795) | crewAIInc/crewAI | OPEN(2026-10-17) | fix(openai): allow multimodal file inputs for GPT-6 Astra |
| [#7981](https://github.com/crewAIInc/crewAI/pull/7981) | crewAIInc/crewAI | OPEN(2026-10-17) |  |
| [#12636](https://github.com/dask/dask/pull/12636) | dask/dask | OPEN(2026-10-17) |  |
| [#20873](https://github.com/DataDog/dd-trace-py/pull/20873) | DataDog/dd-trace-py | OPEN(2026-10-17) | Fix #20782: map Anthropic 1h cache creation tokens to the correct span attribute |
| [#20877](https://github.com/DataDog/dd-trace-py/pull/20877) | DataDog/dd-trace-py | OPEN(2026-10-17) | Fix #20858: reset ASGI ExecutionContext between keep-alive requests |
| [#20883](https://github.com/DataDog/dd-trace-py/pull/20883) | DataDog/dd-trace-py | OPEN(2026-10-17) | Fix #20783: include tool_use_prompt_token_count in google_genai LLM span tokens |
| [#20886](https://github.com/DataDog/dd-trace-py/pull/20886) | DataDog/dd-trace-py | OPEN(2026-10-17) | fix(bootstrap): keep logging.captureWarnings working under ddtrace-run with gevent |
| [#1526](https://github.com/Delgan/loguru/pull/1526) | Delgan/loguru | OPEN(2026-10-17) | Fix #1525: neutralise C0/C1 control characters in log messages |
| [#4439](https://github.com/docling-project/docling/pull/4439) | docling-project/docling | OPEN(2026-10-17) | fix(xb): don't dereference memberQname on typed dimensions |
| [#442](https://github.com/executablebooks/markdown-it-py/pull/442) | executablebooks/markdown-it-py | OPEN(2026-10-17) | fix(block): HTML block start outside a list item closes the list |
| [#443](https://github.com/executablebooks/markdown-it-py/pull/443) | executablebooks/markdown-it-py | OPEN(2026-10-17) | fix(parser): fail fast on rules that don't advance state (infinite loop guard) |
| [#15023](https://github.com/huggingface/diffusers/pull/15023) | huggingface/diffusers | OPEN(2026-10-17) |  |
| [#682](https://github.com/mala-project/mala/pull/682) | mala-project/mala | OPEN(2026-10-17) |  |
| [#5717](https://github.com/open-telemetry/opentelemetry-python/pull/5717) | open-telemetry/opentelemetry-python | OPEN(2026-10-17) | fix(metrics): reset the exponent mapping between DELTA collections |
| [#29928](https://github.com/pola-rs/polars/pull/29928) | pola-rs/polars | OPEN(2026-10-17) |  |
| [#5337](https://github.com/pypa/setuptools/pull/5337) | pypa/setuptools | OPEN(2026-10-17) | Extract tar members through the tarfile data filter |
| [#431](https://github.com/pytest-dev/execnet/pull/431) | pytest-dev/execnet | OPEN(2026-10-17) | fix: observe terminated workers and report safe_terminate outcome |
| [#986](https://github.com/QwenLM/Qwen-Agent/pull/986) | QwenLM/Qwen-Agent | OPEN(2026-10-17) | fix(agents): uniquify dialogue history filenames per run |
| [#3187](https://github.com/repowise-dev/repowise/pull/3187) | repowise-dev/repowise | OPEN(2026-10-17) |  |
| [#3046](https://github.com/snowflakedb/snowflake-connector-python/pull/3046) | snowflakedb/snowflake-connector-python | OPEN(2026-10-17) | fix: honor external_browser_timeout in the externalbrowser flow |
| [#3050](https://github.com/snowflakedb/snowflake-connector-python/pull/3050) | snowflakedb/snowflake-connector-python | OPEN(2026-10-17) | Fix #3049: apply force_microsecond_precision to TIMESTAMP_NTZ/LTZ(7) |
| [#10472](https://github.com/statsmodels/statsmodels/pull/10472) | statsmodels/statsmodels | OPEN(2026-10-17) | Fix #9237: index 0-d array as a scalar |
| [#2307](https://github.com/tortoise/tortoise-orm/pull/2307) | tortoise/tortoise-orm | OPEN(2026-10-17) |  |
| [#2180](https://github.com/weaviate/weaviate-python-client/pull/2180) | weaviate/weaviate-python-client | OPEN(2026-10-17) | fix(batch): filter re-added errors by uuid and avoid the deprecated all_responses read |

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
