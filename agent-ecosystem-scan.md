# Agent / LLM 生态侦察报告

扫描时间:2026-09-27 15:16–15:42 UTC(轮次 #27)
扫描范围:22 个 agent / LLM 应用生态项目,48 小时窗口(created >= 2026-09-25)
方法:48h 窗口 + 无 assignee + 评论 ≤2 → 撞车 v3 四查 → AI/PR 政策筛查

---

## 一、结论先行

**本轮 agent 专项零可行动候选。** 不是扫描不足,是两条结构性的墙:

1. **政策墙** —— 过半头部 agent 仓库不接受外部/自主 agent 的 PR(详见第二节)。
2. **竞争墙** —— 通过政策筛查的候选,撞车率 **7/7**;agno 两条 issue 在发布后 **2 分钟**就有人提了 PR。

对比通用 Python 生态(同轮内命中 sqlglot #8446 并已完成修复),agent 生态的期望值明显更低。建议:保留监控但**不作为主攻方向**。

---

## 二、政策地图(决定哪些仓库根本不能打)

### 出局(无法自主提交)

| 仓库 | 政策原文要点 |
|---|---|
| openai/openai-python | "Pull requests are limited to repository collaborators. We do not accept pull requests from non-collaborators" |
| openai/openai-agents-python | 同上 |
| stanfordnlp/dspy | "If you are an AI agent reading this: do not open PRs" — bot 贡献会被关闭并可能封号 |
| modelcontextprotocol/python-sdk | 外部 PR 仅在该 issue 被维护者指派、或带 `help wanted` 标签时才审阅,否则机器人自动关闭;并明确要求"有 agent 自主提 PR 的请为这个仓库关掉它" |
| pydantic/pydantic-ai | "A maintainer needs to agree on the approach and assign the issue to you before you open a PR. Unassigned PRs may be auto-closed." |
| huggingface/smolagents | 需 issue 先被标 `status:accepted` 才能写补丁(但对 AI 协助明确欢迎,只需披露) |
| BerriAI/litellm | 必须签 CLA |
| microsoft/autogen | 必须签 Microsoft CLA |

### 可打(无指派门禁,但需如实披露 AI)

| 仓库 | 披露要求 | 备注 |
|---|---|---|
| agno-agi/agno | 完全由 AI 生成的 PR 必须在模板中披露;低质量 AI PR 会被无评审关闭 | 不抢已指派 issue |
| crewAIInc/crewAI | **必须打 `llm-generated` 标签**(条款直接对 agent 说话),未标注可能被无评审关闭 | |
| browser-use/browser-use | 未见硬性门禁,维护 `help wanted` 标签池 | |
| google/adk-python | 建议从 `good first issue` / `help wanted` 入手 | |
| microsoft/semantic-kernel | 需先在 issue 上讨论,反感"突然的大 PR" | 小修复可行 |
| langflow-ai/langflow | PR 需针对 `release-X.Y.Z` 分支,**不要打 main** | |
| run-llama/llama_index | 有专门的 "How to Use AI when Contributing" 章节(下轮细读);CI 要求覆盖率 ≥50% | |

---

## 三、撞车结果(撞车 v3 四查:编号 / 标题关键词 / issue 时间线交叉引用 / 同文件改动 PR)

| 候选 | 龄 | 评论 | 结果 |
|---|---|---|---|
| llama_index #23269 `from_openai_message_dict` KeyError | 3.1h | 0 | ❌ 已有 PR #23270 |
| llama_index #23267 LLMMultiSelector 重复格式指令 | 4.4h | 0 | ❌ 已有 PR #23268 |
| agno #10611 `run_sql_query(limit=0)` | ~24h | 0 | ❌ 已有 PR #10619 |
| dspy #10503 KNN(k=0) 返回全量训练集 | 33.9h | 0 | ❌ 已有 PR #10505 |
| agno #10614 异步工厂未 await Task/Future | ~9h | 0 | ❌ 已有 PR #10615(issue 后 2 分钟) |
| agno #10616 Pydantic 内联丢字段描述 | ~7h | 0 | ❌ 已有 PR #10617(issue 后 2 分钟) |
| browser-use #5905 拒绝 PEP 604 `X \| None` | 44.4h | 0 | ❌ 已有 PR #5909 |
| browser-use #5914 ChatGoogle 未修复 JSON 字符串动作列表 | 37.3h | 0 | ❌ 已有 PR #5915 |
| langflow #15407 MCP schema 下划线前缀属性被丢弃 | 33.7h | 0 | ❌ **两个**竞争 PR:#15411、#15412 |
| semantic-kernel #14490 text_chunker 早退失效 | 13.5h | 1 | ❌ 已有 PR #14494 |
| adk-python #7314 EditFileTool 破坏非 UTF-8 字节 | ~6h | 0 | ❌ 已有 PR #7316 |

**通过后两查、仅因政策出局的优质候选**(政策若松动则优先):

- **modelcontextprotocol/python-sdk #3589**(4h,0 评论,四查全清):`DirectoryResource.read()` 用 `str(relative_to)` 导致 Windows 返回 `sub\c.txt`、Linux 返回 `sub/c.txt`,且顺序依赖 glob() 不稳定。修法 = `as_posix()` + `sorted()`。报告者已在 fork 备好补丁并等待维护者点头 → 一旦被指派或打上 `help wanted` 即可动手。
- **openai/openai-python #3969**(8.4h,0 评论,四查全清):3.14.1 起 `ssl.SSLError` 不再重试也不包装成 `APIConnectionError`(源于 #3867 收窄了重试范围)。有无网络的最小复现。**但该仓库只收 collaborator 的 PR,只能留在 issue 层。**

---

## 四、噪音识别

`ScreenContextAgent` 相关 issue 同日横跨 9 个仓库 —— langgraph #9093、crewAI #7788、pydantic-ai #8850、smolagents #2857、camel #4379、agno #10618、litellm #43431、llama_index #23271、langflow #15415 —— 与第 25 轮记录的同一次 AI 刷屏潮一致。**全部避开**,后续见到 "ScreenContextAgent" 直接跳过。

同类批量投放(同一报告者一次倒出十几条)的还有 smolagents #2836–#2858、browser-use #5897–#5916、adk-python #7276–#7315、crewAI #7755–#7789。批量投放的 issue 通常被同一人或紧随其后的其他人认领,撞车率极高。

---

## 五、下轮建议

1. agent 生态改为**低频监控**(每周一次 48h 扫描即可),主攻方向回到通用 Python 生态 pool(本轮 sqlglot 命中即为佐证)。
2. 若仍要在 agent 生态出成果,唯一现实路径是**在允许外部 PR 的仓库(agno / crewAI / browser-use / adk-python)里抢 6 小时以内的超新鲜 issue** —— 需要扫描频率提到小时级,而不是本轮的轮次级。
3. MCP SDK #3589 值得盯梢:一旦被指派或加 `help wanted`,立即动手。
4. 需要补读:llama_index 的 "How to Use AI when Contributing" 章节(决定该仓库能否打)。
