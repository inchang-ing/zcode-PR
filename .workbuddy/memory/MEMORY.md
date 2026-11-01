# 项目长期记忆(规律为主 + 实例为注脚)

> 操作手册在 `work/PLAYBOOK.md`；质量、验证和对外沟通以根目录 RULES.md「当前重心：高质量贡献（2026-10-23）」为准。

## 2026-10-23 质量与证据校准
- 真人审阅不能由 agent 代为声明；没有用户对具体改动的实际审核依据，不写 human reviewed / I reviewed everything。
- 返工后验证最终提交；独立脚本、AST、stub 仅为局部证据。先核对失败确为目标缺陷，再跑正常/异常/插件/调用方相关用例。
- 首次提交与每次返工推送前执行 `tools/quality_check.py prepare/check`(见 `contributions/README.md`); 通过仅表示登记证据一致, 不是投稿授权或人工签字。不以换入口规避 404/403 政策。

## 元规则
- 只提共性规律(未来重复/改决策/去仓库名仍成立), 实例挂规律下 `例:仓#号`。流水: 单轮=`rounds-log.md`, 当日=`20YY-MM-DD.md`, 冷归档=`STATE-archive.md`; grep 历史只扫 `20*.md` 排除 `automations/`。Skill 保持英文只做增量。
- **本文件是注入层索引, 不是仓库; 超 ~13KB 就压缩**(已压十四次, 末次 2026-10-29: 三/四节详版下沉 PLAYBOOK)。**压缩=下沉+留指针, 不删本体**: 详版下沉 `work/PLAYBOOK.md` 本文留指针; 归档层全量保留。准入三判据(会重复/改决策/去名仍成立), 不达标进流水。
- **写进记忆的「实测」要能在 5 分钟内复测, 推测必须当场标注为推测**: 一次 403、一次超时都不构成「平台对该账号有限制」这类结论(2026-11-01 「连 2 次搜索即 403」被复测推翻, 顺次/并发全部 200)。错误规律比没有规律更贵 —— 它会长期改变后续决策(如无谓地回避 search API)。**给用户解释原因时, 证据清单和推测要分开说。**

## 路由表(高风险动作前强制检索)
**高风险动作**(解冲突/force push/同步、改共享写者/持久化/销毁、回 CI 红、开新 PR、压缩记忆/写日志)前必按本表读对应主题, **未检索不声称完成**; 漏召记 `work/recall-log.md`, 同一指针 30 天拉回 ≥3 次→升回。
- 解冲突/force push/merge commit → 三节 + PLAYBOOK「GitHub 解冲突」
- 共享配置/原子写/数据丢失/销毁清理 → 二·补 + PLAYBOOK「缺陷修复通用形态」
- CI 红/本地测试红/覆盖率/PR 标题 → 四节
- 开新 PR/撞车/认领/AI 政策/门禁 → 二节
- PR 巡检/合并状态/跟进催询 → 五节
- 压缩记忆/写日志/经验准入 → 元规则 + PLAYBOOK

## 一、不可违反的用户指令
- **方案/计划文档改动先审批后落盘**: 先给完整计划获批再写; 已落盘的摊开「改前→改后」供审。例: 未获批改 `work/plan-issue-first.md` 被纠正。
- **「找到就跑PR啊问我干什么」(2026-10-13)**: 干净候选自行实现+提 PR, 不回头问。例外: 法律协议/不可逆破坏先问。
- 自动化**已获授权**(2026-11-01 用户裁决「两个都建」, 实测合并为一个): `417db721` 开源贡献流水线每小时一轮, 第 0 步快扫 48h 新 issue+五项核查+认领, 之后维护/写码。**调度器上限 = 每小时一次**: 分钟级直接报错, `BYMINUTE` 能存但不生效(判据看 `nextRunAt` 是否真对齐, 别看 rrule 是否被接受), 锚点是创建时刻而非整点 → 多建任务只会同秒撞车并同写台账, 故合并为单任务。旧 `70b30a25`/`22508949`/`da3572ce`/`3997bee0` 均已删。**要亚小时频率就别在客户端调度器上使劲** —— 改走 GitHub Actions 快车道(见六节)。
- **无「一轮只跑一个 PR」约束; 纪律 = 同仓在飞 ≤1(硬上限 2)**。例: sqlalchemy 同 org 备 4 分支→整批 `createPullRequest` 被封。
- **权威池(4 门槛)**: ①Python 包 ②本机可跑测(重 GPU/C++/Rust 降级) ③收外部 bug-fix PR ④活跃 bug 流; 约 53 个, 受限池(sqlalchemy/httpx/pallets)只扫不投。
- **org 规范名**: starlette/uvicorn→`Kludex/*`; typer/fastapi→`fastapi/*`; ragas→`vibrantlabsai/ragas`; hydra→`hydra-ecosystem/hydra`; aiohttp=`aio-libs/aiohttp`。
- **CLA**: 已授权代签 OSS CLA; 标准 **CLAassistant**(litellm/deepchecks)须账号持有者网页 OAuth 点签, agent 评论只对 CLA Assistant Lite 生效。
- **AI 披露格式各异**: pytest 要 `Co-authored-by`+AUTHORS+人类担责; otel/pip「we don't police」披露即可; MS CLA bot 用 `@microsoft-github-policy-service agree`+大写 FIX:/FEAT:。

- **2026-11-01 贡献分层指令**: 不再要求「必须是有实质行为影响的 bug」——文档修正/简单 PR 可投;但**落点必须是高星库或有组织背书的大厂仓**(低星的公司官方仓合格,个人小库不因内容简单而下放)。验证门槛不降。详见 `RULES.md`「贡献分层」。

## 二、做不做(质量红线 + 撞车九查 v5)
- **v5 门禁查**: `.github/workflows`(`require-issue-link`/`prgate`)、`.github/VOUCHED*`、CONTRIBUTING 正文(claim/assign/`open for pull requests`); 命中且未 assign→先求 assign。例: langgraph、pydantic#13959、sqlalchemy#13665、mem0#7618/#7642。
- **timeline 两查**: ①REST 全量 `repos/{r}/issues/{n}/timeline --paginate`(GraphQL 正序截断→假阴性; `gh search linked:pr` 漏 `fixes #N`), PR 判据 `source.issue.pull_request`; ②「正在发生」(占拒关 40%): 近 14 天 comments/同文件他人 open PR/assignee 更新。
- **自滤两类信号即弃**: ①自陈已修(`fixed by PR`/`resolved by #`)——cross-ref 抓不到正文裸链(llama_index#23613); ②软认领——正文+评论双查, 关键词跟得上真人措辞(「I have a focused fix ready」「please approve the issue and assign it to X」, langchain#41405/#41406)。工具 `tools/claim_rules.py`+`tools/scan_candidates.py` 只初筛, 每轮候选仍要人工读正文末尾(2026-10-23: 5 中 4 被认领)。
- **撞车竞态+预认领常态**: 他人 PR 早几十秒开出时 cross-ref 未生成→误报干净, 兜底=拉本仓近 60 个 open PR 正则比 `#N`。例: prefect#23492; dspy 30 天 8 个零评论 bug 全有 PR; 2026-10-17 六连栽(babel/uvicorn/pydantic×2/ipython/sklearn)。
- **同一门禁只许栽一次→命中即入台账**。例: langgraph 3 连栽; sqlglot 3 个(#8496/#8548/#8558); networkx 2 个。
- **语义/方言仓先证明输入本身合法**。例: sqlglot#8548 SQL Server 实测 `Msg 156`→整根 PR 失去讨论基础。
- **AI 政策见即弃**: 禁 agent 名单 pre-commit/matplotlib/hypothesis/scipy/sphinx-needs/pyparsing/requests/evidently/ibis/mem0/jax。**开 PR 前必读 `.github/AI_POLICY.md`+`AGENTS.md`+CONTRIBUTING 正文+PR 模板**(政策常在正文——geopandas#3896、jax#41846 栽在「只查文件是否存在」); VOUCHED 对仓做(frappe#44667)。三类: 禁 agent→弃 / 须披露 / 无条款(poetry/dd-trace/mypy)→可投。**ansible 已实质封闭**(账号被指 bot→sivel 以「autonomous contribution」关 #87712, 叠加禁评论)→一律跳过。
- **政策门禁**: openai-python 只收协作者; ibis 禁 agent 自提; mlflow 需 `ready`; jupyter 系 triage 标签门禁→留言求补。
- 内部 Jira 同步 issue 全 ASSIGNED 勿碰; v4 全清且**能复现**才投(glom#314/langdetect#102 弃); wontfix/设计如此见即弃。
- **留言按信息价值和仓库要求决定**: 必要的认领/方案问题、新复现证据才沟通, 不发占位留言; 需批准的仓库等批准。无新信息默认等待, 同一事项合并回复。
- **风险分级四类**: ①门禁→等 assign 才写; ②方案争议→等 maintainer 定方向; ③方言/解析器→先验证输入合法; ④撞车→读全部证据、存在认领即让, 不以试探留言争抢。
- **弃单下沉前先判「仓级 or issue 级」**: 去掉仓库名弃因仍成立 = issue 级, 只进弃单台账/按 `repo#N` 去重, **不可**下沉为仓级规则(误杀该仓未来干净候选); 弃因依赖该仓技术栈/门禁才可下沉。例: seatunnel(Java 栈)可下沉; huggingface_hub#5109(外部 CAS 401+间歇性)不可。
- **低门槛≠低竞争(2026-11-01 实测)**: 降低选题标准反而抬高撞车率——看懂文档错的人 ≫ 能定位 bug 的人,且修复成本更低。文档/小修候选 7/7 已被占(autogen#7749 有 **8 个**竞争 PR、llama_index#23673 有 5 个、sympy#29023 有 3 个)。简单改动的无竞争来源只有两类:维护者自批量开的 GFI(且落在低竞争仓)、必须跑起来才暴露的缺陷(示例输出过时/死链/docstring 与签名不符)。工具: `tools/scan_docs.py`、`tools/docstring_audit.py`、`tools/run_docs_doctest.py`。**竞争密度由「该仓有多少自动化在盯」决定, 与题目难度无关**: 拉 `pulls?state=open` 若分支名前缀高度同质(30+ 条 `fix/cli-*`/`fix/nested-*`)即 LLM 密集仓, 新 issue 1 小时内必被占, **前置跳过不必逐条核**。例: pydantic-settings#1121 开出 0.5h 已有多条同风格 PR, 对应 #1122 已占。
- **GFI 抢购窗口 ≤12h,与仓大小无关(2026-11-01)**: 维护者批量开出的 good-first-issue 会被数小时内瓜分——powertools 8 个(10-31 22:36 开出)12 小时内 8/8 被认领,3300★ 大厂仓也不例外。周期性扫描抢不过真人盯仓,GFI 路线只在「刚开出+立即响应」时有效。**认领前必须拉 `issues/{n}/comments` 全文**:认领留言不产生 cross-ref,timeline 干净只说明「没有 PR」不说明「没人认领」(powertools#8722 据此撤回,教训:只查 timeline 会假阴)。已认领即让,不留言争抢。
- **低星大厂仓是当前红利池**: 按**组织背书**判而非星数。先查 `archived`(googleapis/python-bigquery 796★、python-storage 502★ 已于 2026-03 归档)。例: aws-powertools(3303★) 维护者 10-31 批量开 8 个 GFI(#8721–#8728),一天后仍 0 cross-ref —— 同类 issue 在高星热门仓早被抢空。该类仓常内置「先认领等 assign 再开 PR」门禁,须按其流程走。
- **在飞规模是策略变量**: 外部在飞 ≳ 池子可消化量时, 产出 0 是结构性非随机, 先数在飞数再决定是否加频/扩池。例: 在飞 53 / 池 62 仓 → 5 轮 4 轮零产出。
- **先分「流程噪声 or 供给不足」再调参**: 同一已裁定单反复占满 CLEAN 集合 = 噪声, 用 `repository_policy.ISSUE_SUPPRESSIONS` 按 `repo#N` 抑制(**须带 `updated_at` 失效保护**: 上游有动静即 lapse, 否则会永久埋掉候选); 抑制后真实候选仍为 0 = 供给不足, 加频无增量。例: huggingface_hub#5109 连占 5 轮 → 抑制后 7/30 天窗口真实 CLEAN 均为 0。

## 二·补、缺陷修复通用形态(详版 `work/PLAYBOOK.md`「缺陷修复通用形态」)
五形态: ①读失败当空配置=多写者数据丢失(分「缺失=无可保留/读不懂=拒绝写盘」, fail-open 反噬必查调用方) ②修写者修全部+tmp+fsync+rename ③读路径宽容但不静默 ④销毁与失败清理联动 ⑤新值类型枚举全部原语。例: miloco#569/#602、ansible#87712 `_shred_file`、jax#41846 `LinVal`。

## 三、怎么交(2026-10-29 压缩; 全量详版见 `work/PLAYBOOK.md`「三、怎么交」)
- 提交邮箱 `197932532+inchang-ing@users.noreply.github.com`(否则 CLA-bot 认不出); DCO 仓手写 Signed-off-by; 浅克隆禁直接 amend。
- **有 AGENTS.md 即硬约束**(例 litellm: 分支名 `litellm_` 无 `/`、行宽 120、禁注释、conventional commits); 「预读」= AGENTS.md+CONTRIBUTING(releasenotes)+`.pre-commit-config` 全套。
- **本地 checkout 是 CRLF≠仓库是 CRLF**: API 推送前必须 LF 规范化; 判据: diff 整份文件被重写→先怀疑换行符, `git hash-object` 对齐 blob sha。例: repowise#3187、miloco#602、boltons#578。
- **`git merge-file` 干净 ≠ GitHub 接受合并**: 解法=merge commit 双父(`parents=[我的改动sha, main_sha]`)使 merge-base 后移。例: dd-trace#20877。沙箱代理/git https、Git Data API 兜底、解冲突取 upstream ref、pre-commit.ci 抢推 commit 等配方全部见 PLAYBOOK。

## 四、验证纪律(2026-10-29 压缩; 全量详版见 `work/PLAYBOOK.md`「四、验证纪律」)
- 判别力: **撤修复→fail, 恢复→pass**; 新增不可达防御分支会被覆盖率判失败(bokeh#15476); 跑源码非 site-packages 副本; 跨会话/API 重建的文件不能信"已验证"→推后必查 `gh pr checks`。
- **纯净基线对照用 `git restore --source=HEAD --staged --worktree`**; **git checkout 会丢本轮未提交改动**。
- **CI 红先判"是不是我的"**: ①同 workflow 在 main 是否天天红(dask `nightly`); ②同 commit 该 job 是否有更晚 success(statsmodels#10472); ③失败是否落在自己 diff 面。必拉日志定真因, 勿按作业名猜(tortoise#2307 实为 mypy arg-type)。
- **本地测试失败先判环境**: 缺 pytest-asyncio/fcntl(Windows)/POSIX 权限位/`/bin/sh` spawn 均非代码问题; 同环境对比基线与补丁失败集合, 同因才判环境。例: aiohttp 全红实为 multidict 缺 `_md`。
- **端到端对照要给「修复前/后不同数」**(repowise#3187「2 finding→0」; docling#4849「2 failed→13 passed」); 安装器/脚本无测试目录时, 用例放进已被 CI 覆盖的既有测试文件, 不为新目录改 workflow。PR 标题门禁、CI 日志另找出入口、Windows 跑 POSIX 库 stub、mypy 本地跑测见 PLAYBOOK。

## 五、监控/数据
- **跟进按阻塞和证据决定**: 有明确评审要求优先处理; 无新信息默认等待, 不因到期自动 ping 或关闭; 需催询时说明具体请求并核对既有消息。
- **处理真实阻塞**: 我方引入的失败优先修; 仅因真实冲突、必需检查、必要上游修复或维护者要求同步。behind 本身不触发同步; 修改 head 后重验受影响范围。
- 单一事实源=GitHub; 全量盘 PR 用 `gh api "search/issues?q=is:pr+author:inchang-ing+state:open&per_page=100&sort=updated"`(**`gh search prs` 静默返回 0, 不可信**); memory 只记规律不记清单。`mergeable_state`: blocked=待门禁/behind=落后/unstable=CI 未绿/unknown=重算。批量巡检 `work/triage_prs.py`→`work/pr_triage.json`。
- **批量工具坑**: `gh pr checks` 遇失败项 rc=1, 脚本必须忽略 returncode; GraphQL `statusCheckRollup` 是 `{state}` 而 REST 是 check runs; `gh api graphql` 偶发 502→必配 REST 兜底。
- 维护者先关 issue(not_planned)再关 PR=裁定不修; 大仓 reviewDecision null 数周常态; **fork PR 的 Actions 常停 `action_required`**=待维护者批准, 非推送失败。
- **扫「他人新动静」cutoff 用「上次扫描时间」不用自然日 0 点**; **codecov/patch·project 红未必阻塞**: 查 `gh api repos/{r}/rulesets` 有无 `required_status_checks`(rules:[] 空=非阻塞, aiohttp#14017 patch 89% 仍可合)。
- **AI review bot 的 🟡 项常是真回归线索**(miloco 两条 🟡 均成立), 逐条实现+回复+推 commit 是标准动作。

## 六、复盘/池状态
- **10-15 复盘**(`work/retro-2026-10-15.md`): 外部 100 个, 合 22/拒 30/在飞 48; 拒关率 9 月 32.1%→10 月 87.5%; **七成死因与代码质量无关**(重复/抢先 40%>门禁 30%>方案被否>AI 政策>自撤)。10-27: 外部合并 26、在飞 56(自有仓 67 另计)。
- **新 bug 流已饱和(10-19 起, 10-23 复核)**: 23 仓 × 30 天只扫出 3–5 个且多数已被软认领。**策略**: ①维护在飞 PR ②降星级 500–2000 中型仓 ③换贡献类型。
- **定时扫描机制**: `tools/quality_repos.json`+`tools/scan_candidates.py --days --max`→`work/ledger/candidates.json`; 现只有 automation `417db721`(每小时, 首步 `monitor_fresh.py --all`)。
- **发现层与决策层分开**: 发现新 issue 不需要模型 → 放 GitHub Actions(`tools/poll_fresh.py` + `.github/workflows/fresh-issue-poll.yml`, `cron */5`, 命中即往仓内收件箱 issue 追加评论并 `@inchang-ing`, **mention 才产生通知**); 认领/写码仍需模型 → 留每小时流水线。**私有仓按「每 job 最少 1 分钟」计费, 会把频率锁死在上限; 公开仓标准 runner 免费, 频率只受 cron 最小 5 分钟约束** —— `zcode-PR` 已于 2026-11-01 转公开。转公开前必扫: 跟踪文件+`git log -p --all` 的密钥模式、`.env`/`.pem` 类文件、提交作者邮箱。
- **轮询必须按仓拉增量, 不能用全局搜索**: `search/issues?q=created:>=X` 有 1000 条上限, 实测 5 小时窗口只拿到最新 200 条(全是热门仓), 池内命中 0; 改 `repos/{r}/issues?since=&state=all&sort=created` 并发 10 线程约 25 秒。池内含改名前后两个 slug(`embedchain/embedchain`+`mem0ai/mem0`)会重复播报, 按 `html_url` 去重。
- **triage bot 把关 issue 质量的仓, 快车道价值≈0**: langchain 的 `langchain-oss-automated-triage[bot]` 在 **12 秒**内以 `not_planned` 关闭「无 issue type」的 issue(同题 #36991/#41610 均被掐, 同题 open issue 数为 0)。这类仓报得再快也无法认领, 只剩「直接提 PR」一条路。**发现快 ≠ 可认领; 高速车道只对「愿收外部 issue 且不自动关」的仓有价值。**
- **search API 有独立配额(30/min) + secondary limit, 但「本账号连 2 次即 403」不成立**(2026-11-01 复测: 顺次 3/3 200、4 路并发 4/4 200、core 4771/5000)。遇 403 先分清: `X-RateLimit-Remaining` 为 0 = primary 额度耗尽; 否则是 secondary 短时突发, 对所有账号一样, 隔几秒重试即可。扫描优先用仓库 `issues` 端点的理由是它**没有 1000 条上限**, 不是「本账号被限」。**别把一次 403 升级成「账号被平台限制」的结论。**
