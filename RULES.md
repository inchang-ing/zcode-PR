# RULES.md — 硬规则 / AI 政策 / 身份红线

> 违反任何一条 = 劣质轮次。动手前必读。实时状态见 `PR_STATUS.md`,跟踪范围见 `STATE.md`。

## 一、身份与并发红线

- GitHub 账号:`inchang-ing`;git 提交身份用**仓库级** `user.name=inchang-ing` + `user.email=197932532+inchang-ing@users.noreply.github.com`(CLA-bot 依赖此邮箱)。
- 并发上限:**全局 open PR ≤ 5**;**同仓库 ≤ 2 且不同子系统**;**每轮最多 1 个新 PR**。
- 质量红线:**宁可空手,不交勉强补丁**;不削弱检查器;不碰安全敏感面与维护者分歧未决的设计问题。
- 用户说"继续"= 执行下一轮;说"停止"= 停止轮次(在飞 PR 的评审动静仍需在手动轮次里跟进)。

## 二、撞车查证 v4(动手前 + push 前各查一次)

五查:**编号搜索 / 标题关键词 / issue 时间线交叉引用 / 同文件 open PR / 崩溃签名**。

- `gh search` 404 的仓库(agentscope 等)用 `gh pr list` 全量手工比对。
- agentscope 的 `/assign` 评论 = bot 正式认领,**必须读 issue 评论**。
- 软认领与暂不接受 PR 的规则统一在 `tools/claim_rules.py`；扫描和终检共用，正文及全部评论命中即让。
- 候选终检用 `tools/vet.py`,输出 `CLEAN / WARN / DROP / UNKNOWN`;**`UNKNOWN` 必须复核,不等于无人认领**。

## 三、礼让

报告者正文/评论含以下意图一律让:`I will / I can open a PR / I will add tests / I have a patch / I would like to implement / my first contribution / Codex is assisting` 等。

## 四、AI 披露(如实,绝不作假)

仓库禁投、分配人和必需标签的可执行配置统一在 `tools/repository_policy.py`，扫描、本地过滤、联网终检共用。修改下列限制时同步更新该配置和回归测试；DCO 等提交步骤仍按本文执行。
分配门禁要求当前账号 `inchang-ing` 已被分配，且没有其他分配人；旧候选快照没有分配人字段时须重扫。终检重新读取 GitHub 的标签和分配人，不能仅凭旧快照放行。

- 如实披露 AI 协助(工具名以当前实际使用的为准),**绝不写 "No AI use" 虚假声明**。
- 仓库级政策(提 PR 前必读 devel/contributing 的 AI 段):
  - **pallets**(jinja2/click/flask/werkzeug):禁 AI。
  - **camel**:关闭 LLM PR;`inspect_ai` 需 `accepted` 标签;`langchain-ai` 需先被 assign;`dspy` 禁 agent;`mem0` 需 `accepted` issue(有自动重开机制);`docling` 需 DCO(`git commit -s`)。

### AI 政策「见即弃」名单

- **matplotlib/matplotlib**:devdocs 明文禁止外部 AI 工具直接交互(建 issue/PR/评论),且把"同时给多项目贡献"列为 unacceptable。→ 见即弃。
- **useblocks/sphinx-needs**:从 issue 自动生成、讨论数小时内提交的 PR 一律无审关闭。→ 见即弃。
- **HypothesisWorks/hypothesis**:禁维护者团队外的 unreviewed / 全自主贡献。→ 见即弃。
- **pre-commit(asottile)**:维护者拒收 AI 投稿。→ 见即弃。

## 五、工程规范

- **分支卫生**:新分支必须 `git checkout -b <name> origin/main`(曾因切自旧分支混入旧提交,须 rebase --onto 修正)。
- **推送**:token 直推 `git -c credential.helper= push "https://x-access-token:$(gh auth token)@github.com/inchang-ing/<repo>.git" <branch>:<branch>`;`gh` 全路径 `/c/Program Files/GitHub CLI/gh.exe`。
- **质量门禁**:修复必须带**修复前失败的回归测试**;推送前本地跑覆盖率,每个新增分支都要有用例。
- **DCO 仓**用 `git commit -s`。

## 六、删除安全

- 只动本流水线(在 `E:\zcode-PR` 内)创建的文件;删除/覆盖前先预览。
- 本地状态写入统一走 `tools/pipeline_state.py` 的 `file_lock` + 原子替换;`.lock` 文件保留是正常现象,勿删正在使用的锁。

## 七、org 开 PR 权限实测(2026-10-08 `tools/probe_perm.py`)

- **BLOCKED**(CreatePullRequest 拒):Textualize(rich/textual)、psf(requests)、pallets(jinja2/click/flask/werkzeug)、python-jsonschema、encode/httpx。
- **ALLOWED**:dd-trace-py、openinference、snowflake、statsmodels、langchain、docling、sqlglot、pydantic、fastapi、typer、celery、networkx、attrs、anyio、pluggy、keyring、psycopg、alembic、poetry、redis-py、aiohttp、urllib3、graphene、strawberry、mypy、PyGithub、build。
