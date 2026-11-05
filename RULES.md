# RULES.md — 硬规则 / AI 政策 / 身份红线

> 违反任何一条 = 劣质轮次。动手前必读。实时状态见 `PR_STATUS.md`,跟踪范围见 `STATE.md`。

## 当前重心：高质量贡献（2026-10-23）

成功合并仍是结果目标；执行时先降低无效返工和维护者审查成本，不把每日开 PR 数作为任务完成条件。以下规范适用于首次提交和每次评审返工；与旧操作手册冲突时以本节为准。

- **选题与方案**：先说明实际用户受影响的行为、期望结果及依据。涉及语义、容错、安全边界、公共接口的改动，先确认方案，不以“让一个复现通过”替代正确性。只接能验证、能持续回应评审的工作；有我方引入的失败或尚未理解的评审时，先处理再接新任务。
- **测试与真实代码一致**：从真实入口、真实依赖运行回归，确认修复前失败原因确实是目标缺陷，修复后相同用例通过。记录基线与最终提交 SHA、命令、环境、日志；代码更新后重跑受影响测试，不能沿用旧提交结果。AST 抽取、stub、独立脚本只算局部证据；目标平台的行为须在该平台或等价 CI 验证，无法验证则明确标待验证，不宣称完整通过。
- **检查影响范围**：列出主要调用方、数据类型/形状、共享状态写入方及异常清理路径；按改动涉及的风险补正常输入、边界、插件/扩展组合、错误恢复验证。独立审查需能指出反例与遗漏，而非只确认新增测试通过；不堆无关测试或要求每次全仓测试。
- **回复评审也先验证**：将维护者建议还原成行为要求，检查原代码承担的职责，再实现和测试。不得机械替换 API 后先推送、等 CI 找错误。CI 的环境/上游归因需要同平台、同工作流的基线证据；一个无关用例失败不足以免责。
- **提交前执行证据检查**：首次提交和每次返工推送都运行 `tools/quality_check.py check <记录ID> --checkout <目标仓库> --body <实际正文>`，具体录入见 `contributions/README.md`。它校验当前提交与登记证据的一致性；不能替代源码审阅、实时终检、AI 政策或并发限制，也不证明真人审阅。修改代码、正文或收到新反馈后重新准备检查材料。
- **降低沟通负担**：按仓库需要讨论或申请分配；不为占位发“我来做”，不把留言当成对其他贡献者的试探。回复默认只含已改内容、提交、相关验证和一个未决点（如有），长度服从内容，不机械套模板。没有新证据、具体请求或仓库规定时不催促、不重复解释同一 CI；behind 本身不触发同步，只因真实冲突、必需检查或维护者要求同步，遵守仓库的增量提交/强推规则。
- **真实披露与责任**：披露实际使用的工具和参与范围。未经真实人工审阅，不写“human reviewed”“I reviewed everything”等声明，也不代人勾选无法证明的检查项。仓库禁止自主 agent 发 PR/评论时，只准备本地材料，由理解改动并承担责任的人按政策参与；不能把换入口或粘贴生成文本当成合规。出现权限限制先停止该写入，记录错误并通过官方支持或维护者确认，避免反复试创建。
- **复盘按证据归因**：分别记录关闭的明确理由、代码缺陷和流程失误；政策关闭不证明补丁无问题，404/403 不证明账号被反垃圾限制。有效贡献被维护者接手时记录接手链接和提交归属，待上游实际合并后计入贡献结果，不重复计作本账号 PR 合并。

依据：近期日志 `.workbuddy/memory/2026-10-20.md`（statsmodels 返工未验证）、`2026-10-21.md`（miloco 实际依赖与遗漏路径）、`2026-10-23.md`（aiohttp 失败原因不匹配）；已读取的原始反馈：[Ansible 回复过长](https://github.com/ansible/ansible/pull/87712#issuecomment-6345076952)、[Markdown 测试范围](https://github.com/Python-Markdown/markdown/pull/1666#issuecomment-6291788805)、[Markdown 贡献指南](https://github.com/Python-Markdown/markdown/pull/1666#issuecomment-6348291341)。

## 贡献分层（2026-11-01 用户指令，与上一节并行生效）

不再把「必须挑有实质行为影响的 bug」当作开 PR 的前置条件。**选题门槛下调，验证门槛不下调**。

- **仓库准入不变且更严**：内容可以是文档/小修，但**落点必须是高星库或有明确大厂/公司背书的仓库**。判定按组织而非单仓星数——AWS/azure/google/阿里/腾讯/字节/DataDog/Cloudflare/Twilio/PostHog/ModelScope 等公司官方 Python 仓即使只有一两百星也算合格，因为它们有 CI、有维护者轮值、有稳定的评审流程；个人小库即使几千星、只要没有组织化维护，也不因「内容简单」而下放标准。反例：低星个人玩具仓、无 CI 的仓、单人维护且长期不响应评审的仓，一律不投，无论改动多小。
- **可投类别**：①文档修正——错误示例、失效/错误链接、参数名/默认值/返回值描述与实现不符、缺失的迁移或配置步骤、明显过时的版本说明；②低风险小修——docstring 与实现不符、错误消息/日志文案错字导致误导、裸 `except` 后空 `pass` 造成的静默吞异常、类型标注与签名不一致；③测试与工具链自身缺陷——测试写错了断言、CI 脚本明显 bug、fixture 失效；④既有 API 的明显边界遗漏（不改变语义、不新增公共接口）。
- **仍不投**：纯个人偏好重排、mass typo 批量提交（一次几十文件）、无 issue 支撑的行为变更、需要设计共识的问题。
- **验证要求不变**：文档类也要实际跑通改动后的示例/渲染/链接有效性；小修仍要带能证明改动前后差异的证据（修复前失败的用例、修复前的错误输出对比）。文档 PR 允许不带回归测试，但必须在正文写清「怎么确认现在是对的」。
- **撞车策略调整**：文档/小修同样走五查，但**不与被认领的 bug 抢**——一旦发现有人在做同一处，立即换目标，不在评论区试探争抢。
- **收益定位**：这类 PR 的价值是维持活跃贡献者状态与仓库熟悉度，不是主结果指标。合并率高但单点影响小，复盘时与 bug 类分开统计。

**低门槛 ≠ 低竞争（2026-11-01 实测）**：刻意降低选题标准并不能提高产出，反而撞车更严重——能看懂文档问题的人远多于能定位 bug 的人，且修复成本更低，于是每个 issue 吸引的提交者更多。实测：autogen#7749（补 `encoding="utf-8"`）有 8 个竞争 PR、llama_index#23673 有 5 个、sympy#29023 有 3 个、sympy#24244 有 2 个、python-fire#238 有 1 个，7 个文档/小修候选**全部已被占**。因此简单改动的可行来源只有两类：①维护者自己批量开出的 good-first-issue（且落在低竞争仓，如低星大厂仓）；②自己跑代码/文档才能暴露、无人立 issue 的缺陷（示例输出过时、死链、docstring 与签名不符）。例：cattrs#815 是别人 4 天前已合入的 `cache_result` docstring 修正，同一处再动手即为重复。

## 一、身份与并发红线

- GitHub 账号:`inchang-ing`;git 提交身份用**仓库级** `user.name=inchang-ing` + `user.email=197932532+inchang-ing@users.noreply.github.com`(CLA-bot 依赖此邮箱)。
- 并发上限:**全局 open PR 数不设硬顶(用户 2026-09-28 指令"无限制PR";2026-10-18 单日 10 个新 PR 实际执行)**;**同仓库 ≤ 2 且不同子系统**继续生效。**每轮新建 PR 数服从「当前重心」的质量门禁**——选题、验证和评审响应优先,不以 PR 数量为目标;`tools/repository_policy.py` 的封锁/门禁仓一律不投。
- 质量红线:**宁可空手,不交勉强补丁**;不削弱检查器;不碰安全敏感面与维护者分歧未决的设计问题。
- 用户说"继续"= 执行下一轮;说"停止"= 停止轮次(在飞 PR 的评审动静仍需在手动轮次里跟进)。

## 二、撞车查证 v4(动手前 + push 前各查一次)

五查:**编号搜索 / 标题关键词 / issue 时间线交叉引用 / 同文件 open PR / 崩溃签名**。

- `gh search` 404 的仓库(agentscope 等)用 `gh pr list` 全量手工比对。
- agentscope 的 `/assign` 评论 = bot 正式认领,**必须读 issue 评论**。
- 软认领与暂不接受 PR 的规则统一在 `tools/claim_rules.py`；扫描和终检共用，正文及全部评论命中即让。
- 候选终检用 `tools/vet.py`,输出 `CLEAN / WARN / DROP / UNKNOWN`;**`UNKNOWN` 必须复核,不等于无人认领**。
- **多会话认领登记(2026-10-30 增补,本周 docling#5007/psutil#3061 两次撞车的制度化)**:并行会话共享工作区,任何会话在 issue/PR 上开工(写码、推分支、发认领评论)前,执行 `python -S tools/session_claims.py --claim <owner/repo>#N`，仅在返回成功后开工；`--check` 只是查询，不能替代原子认领。遇到占用、锁竞争或损坏状态均不得开工，成功后保存返回的 token，完工/放弃用 `--release <key> --token <token>`，需要续期时用 `--renew <key> --token <token>`；不持有凭证不能释放。活的认领 48h 自动过期，旧格式认领保留至原到期时间。开工前另必查:`git fetch` 后对目标分支核对**远端 head sha 与本地是否一致**——不一致即有并行会话或维护者推过,以远端为准,禁止 force-push。

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
- **质量门禁**：代码、小修和工具链修复必须带**修复前失败的回归测试**；推送前本地跑覆盖率，每个新增分支都要有用例。纯文档按上文贡献分层执行真实示例/渲染/链接验证，使用 `contributions/README.md` 的 documentation 证据方式，仍绑定基线、当前提交及日志。
- **DCO 仓**用 `git commit -s`。

## 六、删除安全

- 只动本流水线(在 `E:\zcode-PR` 内)创建的文件;删除/覆盖前先预览。
- 本地状态写入统一走 `tools/pipeline_state.py` 的 `file_lock` + 原子替换;`.lock` 文件保留是正常现象,勿删正在使用的锁。

## 七、org 开 PR 权限实测(2026-10-08 `tools/probe_perm.py`)

- **BLOCKED**(CreatePullRequest 拒):Textualize(rich/textual)、psf(requests)、pallets(jinja2/click/flask/werkzeug)、python-jsonschema、encode/httpx。**Textualize 2026-10-24 终局判定**:API 与网页双通道封锁(2FA 配置后仍未解;外部账号同期可正常开 PR,属账号特定限制)→ **handoff-only**:修复推 fork + issue 留 compare 链接请维护者代开,禁止重试创建。
- **ALLOWED**:dd-trace-py、openinference、snowflake、statsmodels、langchain、docling、sqlglot、pydantic、fastapi、typer、celery、networkx、attrs、anyio、pluggy、keyring、psycopg、alembic、poetry、redis-py、aiohttp、urllib3、graphene、strawberry、mypy、PyGithub、build。

## 本地门禁补充（2026-10-21 同步）

依据 2026-10-18 本地门禁台账，PyCQA、sqlalchemy 组织暂缓；modelcontextprotocol/python-sdk 要求分配给当前账号；frappe/frappe 的 vouched 资格及 geopandas/geopandas 的方案共识需专项核验。执行配置、来源及解除条件见 tools/repository_policy.py。以上是本地操作限制，本次未重新核实远端政策；不能把短期权限失败解释为永久政策。

2026-10-23 补齐已有禁投记录：`pypa/packaging` 的维护者在 #934 要求勿再开 PR（本地记录 `.workbuddy/memory/2026-10-19.md`）；`google/jax` 的贡献指南被记录为禁止 agent 自主开 PR（`.workbuddy/memory/2026-10-22.md`），同样适用于规范名称 `jax-ml/jax`（名称依据 `.workbuddy/memory/2026-09-30.md`）。共享门禁阻止这些仓库的新候选；现有 PR 保留只读观察，自动跟进写入在复核允许的沟通范围前暂缓。这是本地保守限制，已有记录仅明确禁止开 PR，本次未联网核实，也不据此宣称上游禁止所有评论。专用仓库池的其他排除项仍按各自依据处理。

## 台账登记门（2026-10-26 增补）

**开 PR 当轮必须登记 STATE.md**（2026-10-26 第五十轮实证）：monitor_oss 的监控范围与 review_sweep 的增量基线都派生自 STATE.md/pr_state.json——新 PR 只写 rounds-log 不进 STATE.md 时两者对它双双失明（曾致 8 个在飞 PR 整体脱离自动评审扫描）。流程：PR 创建成功后同轮在 STATE.md「OSS 贡献在飞」表追加一行（`| [#N](url) | owner/repo | OPEN(日期) | 摘要 |`，计数同步更新），下一轮 monitor_oss 自动把观测写入 pr_state.json。全量核对基准：`search/issues?q=author:inchang-ing+type:pr+state:open`（1 调用得权威清单）。

2026-10-23 补齐已有禁投记录：`pypa/packaging` 的维护者在 #934 要求勿再开 PR（本地记录 `.workbuddy/memory/2026-10-19.md`）；`google/jax` 的贡献指南被记录为禁止 agent 自主开 PR（`.workbuddy/memory/2026-10-22.md`），同样适用于规范名称 `jax-ml/jax`（名称依据 `.workbuddy/memory/2026-09-30.md`）。共享门禁阻止这些仓库的新候选；现有 PR 保留只读观察，自动跟进写入在复核允许的沟通范围前暂缓。这是本地保守限制，已有记录仅明确禁止开 PR，本次未联网核实，也不据此宣称上游禁止所有评论。专用仓库池的其他排除项仍按各自依据处理。

## 八、Windows/Git Bash 环境坑（2026-10-24 实测汇总,动手前过一遍）

1. **MSYS 路径转换**：Git Bash 里 `gh api --jq` 的表达式含 `/`（如 `.state+"/"+.mergeable_state`）会被转换成 Git 安装路径,查询静默变空 → jq 表达式一律避免 `/` 字面量（用空格连接）,或整个查询走 Python 脚本。
2. **Python 写文件 CRLF**：Windows 下 `Path.write_text()` 把 LF 仓文件整体转 CRLF → `git diff` 整文件级别假变化。修冲突/改仓库文件必须 `write_bytes()` 并保持原行尾；克隆工作树本身可能已是 CRLF（autocrlf=false 也不保证），**提交前必查 `git diff --stat`**。
3. **bash heredoc**：`<< EOF`（未加引号）会执行 `$()`/反引号,`<< 'EOF'` 也可能吃掉一层反斜杠（含转义断言的测试文件被写坏过）→ 含转义/插值的内容一律走 Edit/Write 工具,不经 heredoc。
4. **`git checkout -- <file>` 会清掉未提交修复**（本次 mypy 修好被误清重做一次）→ 有未提交修复时先 `git stash push <file>` 或确认 diff 里没有它；探针调试后清场用精确 replace,清完 `grep` 验证。
5. **git HTTPS 被代理选择性掐断**：github.com:443 连接失败而 api.github.com/ssh.github.com 正常时,推送改走 SSH:`git push git@github.com:<owner>/<repo>.git <branch>`(~/.ssh/config 已配 ssh.github.com:443);克隆同理。重试 3 次×30 秒仍失败即切换,不干等。
6. **pytest 参数冲突**：mypy 等仓库 pyproject 里 `addopts=-nauto` 时,`-p no:xdist` 会报 unrecognized arguments → 用 `-n0` 关并发;`--update-data` 必须与 `-n0` 同用才真正生效。
7. **数据驱动测试表达不了的环境语义**：PYTHONPATH/PEP420 命名空间包等宿主环境行为,`.test` 数据文件造不出等价触发器（base 上同样绿）→ 及时止损,PR 描述附 repro 步骤替代,不硬凑。
8. **提交只 add 显式路径,禁 `git add -A`/`commit -a`**（2026-10-26 coveragepy#2350 首推实证）：工作区装依赖/pip-compile/pre-commit 会静默改写 requirements 与 pin 文件,一把梭会把无关 bump 扫进修复提交稀释 diff → 只 `git add <修复文件>`;推前断言 `git diff --name-only <base> HEAD` 与预期文件集一致,多余文件按 §九 4 amend+force-push 清除。

## 九、git 合并/推送事故规程（2026-10-25 tortoise 事故补录）

1. **冲突标记尾是合并源的对象名**（commit SHA 或分支名），不是字面 "FETCH_HEAD"——正则按 `>>>>>>> [0-9a-f]{40}|<分支名>` 兜底匹配。
2. **python 失败后，换行分隔的后续语句照跑**——`&&` 只保护同一行的链。处理冲突的多步脚本（解冲突→add→commit→push）必须**整体 && 串联**或分多次调用，每次校验上一步结果。
3. **推前验证**：任何 union/自动解决后，push 前必须 `grep -c "<<<<<<<"` 断言零残留；推完抽查远端文件内容（gh api contents）。
4. amend+force-push 是修复错推提交的既定通道（solo fork 分支安全）；推完用 gh api 复核远端内容与本地一致。
