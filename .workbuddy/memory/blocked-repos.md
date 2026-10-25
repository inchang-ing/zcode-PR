# 门禁/封锁台账(同一门禁只许栽一次, 命中即入本表)

> 用法: 投递前对照本表 + MEMORY.md 二·v5。命中以下任何一条的仓/组织, 默认跳过。

## org 级 createPullRequest 封锁(实测)
- Textualize / psf / pallets / jsonschema / httpx (2026-10-08 probe_perm.py 实测)
- **PyCQA**(2026-10-18, bandit#1478: 评论可发, POST /pulls 404 + GraphQL CreatePullRequest 拒绝) → PyCQA 全系(pydocstyle/pyflakes)连带跳过
- **sqlalchemy org**(2026-10-18, alembic#1879: 连 addComment 都 403 "Blocked")

## 仓级门禁
- modelcontextprotocol/python-sdk — PR 未关联「assign 给作者」的 issue 会被自动关闭(AGENTS.md 明文, 2026-10-18 弃 2 候选)
- frappe — `.github/VOUCHED.td`, 非 vouched 用户 PR 被 frappe-pr-bot 自动关闭(2026-10-18 实测 PR#44667 当天关)
- geopandas — AI 政策写在 **CONTRIBUTING.md 正文**: "AI generated PRs will not be accepted unless they resolve an existing issue where there is consensus on the solution to implement"(2026-10-18 实测 PR#3896 被 martinfleis 当天关)
- dbt — fork PR 需 `ci:approve-public-fork-ci` 标签 + CLAassistant 网页签(2026-10-18 PR#16798)
- langgraph(3 连栽); sqlglot 3 个; networkx 2 个; pydantic#13959; mem0#7618/#7642; agno#11022 — 历史门禁

## 已改名仓(POST 遇 307/Moved Permanently → 改用 repositories/{id})
- dbt-labs/dbt-core → **dbt-labs/dbt**(2026-10-18 实测)
