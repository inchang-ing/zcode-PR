# 项目长期记忆(规律为主 + 实例为注脚)

> 操作手册在 `work/PLAYBOOK.md`；质量、验证和对外沟通以根目录 RULES.md「当前重心：高质量贡献（2026-10-23）」为准。

## 2026-10-23 质量与证据校准
- 真人审阅不能由 agent 代为声明；没有用户对具体改动的实际审核依据，不写 human reviewed / I reviewed everything。
- 返工后验证最终提交；独立脚本、AST、stub 仅为局部证据。先核对失败确为目标缺陷，再跑正常/异常/插件/调用方相关用例。
- 首次提交与每次返工推送前执行 `tools/quality_check.py prepare/check`；命令和录入字段见 `contributions/README.md`。代码、正文或反馈改变后重验；通过仅表示登记证据一致，不是投稿授权或人工签字。
- 原日志中的账号 shadow-restrict 原因属推测，404/403 只能确认当次请求失败；不以换分支名/措辞/入口规避政策或反复创建探测。


## 元规则
- 只提共性规律(未来重复/改决策/去仓库名仍成立), 实例挂规律下 `例:仓#号`。流水: 单轮=`rounds-log.md`, 当日=`20YY-MM-DD.md`, 冷归档=`STATE-archive.md`; grep 历史只扫 `20*.md` 排除 `automations/`。Skill 保持英文只做增量。
- **本文件注入即截断, 超 ~13KB 必须压缩**(已压十二次; 长操作配方一律下沉 `work/PLAYBOOK.md`, 本文只留一行指针)。

## 一、不可违反的用户指令
- **方案/计划文档改动先审批后落盘**: 先给完整计划获批再写; 已落盘的摊开「改前→改后」供审。例: 未获批改 `work/plan-issue-first.md` 被纠正。
- **「找到就跑PR啊问我干什么」(2026-10-13)**: 干净候选自行实现+提 PR, 不回头问。例外: 法律协议/不可逆破坏先问。
- 权威仓 PR 监控 recurring automation 已授权(45 分钟一轮 `70b30a25`; 另有 2 小时扫描 `da3572ce`)。
- **无「一轮只跑一个 PR」约束; 纪律 = 同仓在飞 ≤1(硬上限 2)**。例: sqlalchemy 同 org 备 4 分支→整批 `createPullRequest` 被封。
- **权威池(4 门槛)**: ①Python 包 ②本机可跑测(重 GPU/C++/Rust 降级) ③收外部 bug-fix PR ④活跃 bug 流; 约 53 个, 受限池(sqlalchemy/httpx/pallets)只扫不投。
- **org 规范名**: starlette/uvicorn→`Kludex/*`; typer/fastapi→`fastapi/*`; ragas→`vibrantlabsai/ragas`; hydra→`hydra-ecosystem/hydra`; aiohttp=`aio-libs/aiohttp`。
- **CLA**: 已授权代签 OSS CLA; 标准 **CLAassistant**(litellm/deepchecks)须账号持有者网页 OAuth 点签, agent 评论只对 CLA Assistant Lite 生效。
- **AI 披露格式各异**: pytest 要 `Co-authored-by`+AUTHORS+人类担责; otel/pip「we don't police」披露即可; MS CLA bot 用 `@microsoft-github-policy-service agree`+大写 FIX:/FEAT:。

## 二、做不做(质量红线 + 撞车九查 v5)
- **v5 门禁查**: `.github/workflows`(`require-issue-link`/`prgate`)、`.github/VOUCHED*`、CONTRIBUTING 正文(claim/assign/`open for pull requests`); 命中且未 assign→先求 assign。例: langgraph、pydantic#13959、sqlalchemy#13665、mem0#7618/#7642。
- **timeline 两查**: ①REST 全量 `repos/{r}/issues/{n}/timeline --paginate`(GraphQL 正序截断→假阴性; `gh search linked:pr` 漏 `fixes #N`), PR 判据 `source.issue.pull_request`; ②「正在发生」(占拒关 40%): 近 14 天 comments/同文件他人 open PR/assignee 更新。
- **自滤两类信号即弃**: ①自陈已修(`fixed by PR`/`resolved by #`)——cross-ref 抓不到正文裸链(llama_index#23613); ②软认领。**软认领必须正文+评论双查, 且关键词跟得上真人措辞**: 评论里「I have a focused fix ready」(langchain#41406)、正文末「please approve the issue and assign it to X / so I can open a focused PR」(langchain#41405/#41406)。已统一到 `tools/claim_rules.py` 与 `tools/scan_candidates.py`; **扫描器只做初筛, 每轮候选仍要人工读一遍正文末尾**(2026-10-23 扫出 5 个, 人工看后 4 个被认领)。
- **撞车竞态+预认领常态**: 他人 PR 早几十秒开出时 cross-ref 未生成→误报干净, 兜底=拉本仓近 60 个 open PR 正则比 `#N`。例: prefect#23492; dspy 30 天 8 个零评论 bug 全有 PR; 2026-10-17 六连栽(babel/uvicorn/pydantic×2/ipython/sklearn)。
- **同一门禁只许栽一次→命中即入台账**。例: langgraph 3 连栽; sqlglot 3 个(#8496/#8548/#8558); networkx 2 个。
- **语义/方言仓先证明输入本身合法**。例: sqlglot#8548 SQL Server 实测 `Msg 156`→整根 PR 失去讨论基础。
- **AI 政策见即弃**: 禁 agent 名单 pre-commit/matplotlib/hypothesis/scipy/sphinx-needs/pyparsing/requests/evidently/ibis/mem0/jax。**开 PR 前必读 `.github/AI_POLICY.md`+`AGENTS.md`+CONTRIBUTING 正文+PR 模板**(政策常在正文——geopandas#3896、jax#41846 都栽在「只查文件是否存在」); **VOUCHED 对仓做**(frappe#44667)。三类: 禁 agent→弃 / 须披露 / 无条款(poetry/dd-trace/mypy)→可投。**ansible 已实质封闭**: DevashishX 公开指账号为 bot → sivel 以「autonomous contribution」关闭 #87712(返工 5d58e77 + shellcheck 8bc9317 均已推送；关闭明确理由是自主投稿，但同期存在真实代码缺陷和沟通问题，不能据此宣称质量无关); 叠加已被禁评论, **ansible 仓后续一律跳过(不投新·不维护)**。
- **政策门禁**: openai-python 只收协作者; ibis 禁 agent 自提; mlflow 需 `ready`(只 `triage: reproduced` 不行); jupyter 系 triage 标签门禁外部无权限→留言求补。
- 内部 Jira 同步 issue 全 ASSIGNED 勿碰; v4 全清且**能复现**才投(glom#314/langdetect#102 弃); 维护者定性 wontfix/设计如此见即弃。
- **留言按信息价值和仓库要求决定**：必要的认领/方案问题、新复现证据才沟通，不自动发占位留言；需批准的仓库必须等批准。无新信息默认等待，同一事项合并回复。
- **风险分级四类**: ①门禁→等 assign 才写; ②方案争议→等 maintainer 定方向; ③方言/解析器→先验证输入合法; ④撞车→读全部证据、存在认领即让，不以试探性留言争抢。

## 二·补、缺陷修复通用形态
- **「读失败按空配置处理」是共享配置多写者的高频数据丢失形态**: 写入方把解析失败当空基底→deep_merge 退化成整体覆盖; 须区分「文件缺失=无可保留」与「读不懂=拒绝写盘」。例: miloco#569 四写入方同款 fail-open, PR#602 两轮修完; 损坏源=原子写没 fsync 掉电留空文件。
- **把严格化修复反噬的兜底路径一并枚举**: fail-open 改 fail-closed 时必查调用方异常分支——fallback 自身 fail-open 会让损坏场景**必然**落进兜底整体覆盖。例: miloco PR#602 r2: CLI 严格拒绝后 install.py `_fallback_write_config` 反噬, 第二 commit 才补。
- **修共享文件写者要修全部写者+持久化**: 只堵运行时写者不闭环——插件写者无 fsync, 掉电落在 rename 窗口的**空文件**会被读取器按「首启初始化」静默重建; 每个写者都要 tmp+fsync+rename。
- **rename 后目录项 fsync 失败必须降级 warning**: 数据已落盘, 异常穿到外层会让调用方看到「写失败」; 目录 fsync 只是掉电保险。测试用假目录 fd(patch `os.open`+忽略 `os.close`)让 Windows 也走到该分支; Windows 下 `os.open(dir, O_RDONLY)` 直接 PermissionError→目录 fsync 必须 best-effort(miloco CLI `atomic_write`, PR#602 一并修)。
- **读路径宽容但不能静默**: 各读取器可观测性要一致(CLI 非严格分支向 stderr 打 warning, stdout 是 JSON 协议不能污染), 否则默认值被误判成「配置真丢了」; 注释承诺的降级要先验证下层读取器不会先崩(settings 层对非对象 config.json 抛 ValueError)。
- **销毁步骤一旦会删掉旧数据, 失败路径的清理必须与它联动**: 「写新→销毁旧→rename」里销毁成功而 rename 失败时再删临时文件=新旧皆丢。用「销毁是否已执行」标志决定临时文件去留并在错误里给出路径。例: ansible#87712 `_shred_file()` 结尾 `os.remove()`(commit `1e9d140`); 同一标志还修正了我自己的单测(默认 `shred=True` 先把待断言「仍完好」的原文件 shred 了)。
- **解释器/求值器引入新值类型时, 枚举它流经的全部原语**: traceback 只暴露第一个炸点, 同值类型还会流进其他读写/生命周期原语。例: jax discharge 对 pinned ref 的 `LinVal` 只处理了 freeze/free, get/swap/addupdate 漏修→泄给 `add`(#41846, jax 已因 AI 政策弃)。

## 三、怎么交(详版 `work/PLAYBOOK.md`)
- **沙箱代理 git https 时好时坏**(偶发 CONNECT 502→重试或绕代理直连); Git Data API(blob→tree→commit→ref)兜底; `gh pr create` 报 "Head sha blank"=分支没推上; 改名仓 POST 遇 307→用 `repositories/{id}`; **clone 被墙时** `curl .../tarball/{ref}` 下源码+Git Data API 推分支(miloco PR#600/#602)。
- 提交邮箱 `197932532+inchang-ing@users.noreply.github.com`(否则 CLA-bot 认不出); DCO 仓手写 Signed-off-by; 浅克隆禁直接 amend。
- **pre-commit.ci / 机器人会往 PR 分支推 commit**, push 被 non-fast-forward 拒时先 `git fetch` 再 rebase(重复补丁会被自动 drop)。例: xarray#11759、aiohttp#14017。
- **无本地克隆也能同步/合并分支**; **Windows 建 CHANGES 符号链接要用 `git update-index --cacheinfo 120000`**(`ln -s` 会退化成普通文件)。配方见 `work/PLAYBOOK.md`; 例: openinference#3981(落后 55 提交)、aiohttp#14017。
- **本地 checkout 是 CRLF≠仓库是 CRLF**: API 推送前必须 LF 规范化; 校验 `tr -cd '\r' | wc -c`=0 且 `git hash-object` 与 API blob sha 对齐; Edit 工具会保留/放大 CRLF。例: repowise#3187 三文件 CR→0; miloco#602 二轮 CR=179/671→0; boltons#578(2026-10-23, `git diff` 显示整文件重写)。**判据: diff 里整份文件被重写→先怀疑换行符, 不是内容**; 修法=`open(p,'rb')` 读+替换 `\r\n` 写回。
- **有 AGENTS.md 即硬约束**(例 litellm: 分支名 `litellm_` 无 `/`、行宽 120、禁注释、conventional commits、lint 比 merge-base 违规不增长); **「预读」=全套**: AGENTS.md+CONTRIBUTING(releasenotes)+`.pre-commit-config`。

## 四、验证纪律(详版 `work/PLAYBOOK.md`)
- 判别力: **撤修复→fail, 恢复→pass**; 新增不可达防御分支会被覆盖率判失败(bokeh#15476); 跑源码非 site-packages 副本; 跨会话/API 重建的文件都不能信"已验证"; **本地补的抑制注释可能在 API 推送时丢**(litellm#46262)→推后必查 `gh pr checks`。
- **PR 标题也受门禁**: `amannn/action-semantic-pull-request` 要求 conventional commit 前缀, `Fix #3803: ...` 会红→改标题即绿(无需 push)。例: openinference#3981/#3982(2026-10-23)。
- **纯净基线对照用 `git restore --source=HEAD --staged --worktree <files>`**(索引有 staged 改动时 `git checkout --` 恢复的是改动版); **git checkout 会丢本轮未提交改动**——判别力实验后用脚本反向替换恢复(miloco#602 二轮踩过)。
- CI 失败必拉日志定真因, 勿按作业名猜(tortoise#2307 实为 mypy arg-type 非 pre-commit); **CI 红先判"是不是我的"**: ①同 workflow 在 main 是否天天红(dask `nightly`); ②同 commit 该 job 是否有更晚 success(statsmodels#10472); ③失败项是否落在自己 diff 面。
- **本地测试失败先判环境**: 缺 pytest-asyncio(异步用例全红)/fcntl(Windows)/POSIX 权限位/`/bin/sh` spawn——都不是代码问题, 用 tarball 原件对照确认基准(在相同环境与命令下对比干净基线和补丁的失败集合，定位同一原因才判环境；无关用例也红不足以下结论)。例: miloco venv 补装 pytest-asyncio 后 26 个 token 用例全过; aiohttp 本地全红实为 **Windows 版 multidict C 扩展缺 `_md`**, `MULTIDICT_NO_EXTENSIONS=1` 走纯 Python 即恢复(`test_keepalive_expires_on_time` 也红→判定为环境)。
- **CI 日志读不到时另找出入口(详见 `work/PLAYBOOK.md`)**: ①Azure DevOps(ansible)用公共 REST `timeline`→`log.id`→`/logs/{id}`, 注意同名 job 有多个要按 `parentId` 定位(ansible#87712 因此定位到是我的单测红, 不是 SSH/容器镜像的基础设施失败); ②pre-commit.ci 用 WebFetch 取结果页。
- **Windows 跑 POSIX 库代码: 逐层 stub 后可 import 真实模块跑生产代码**, 比 `ast` 抽函数保真得多(ansible#87712: stub 链 fcntl→termios→tty→register_at_fork→chown→multiprocessing.context→ctypes libc; harness `work/ansible_write_harness.py`)。Windows 观测不到 `chmod` 细粒度模式→模式断言放进 POSIX 集成测试。配方见 `work/PLAYBOOK.md`。
- **端到端对照要给「修复前/后不同数」**: repowise#3187「main resolver=2 finding→本分支 0」; docling#4849「旧规则 2 failed→13 passed」; **安装器/脚本无测试目录时, 用例放进已被 CI 覆盖的既有测试文件**(miloco `test_install_runtime.py` 用 importlib 加载 install.py), 不为新目录改 workflow。

## 五、监控/数据
- **跟进按阻塞和证据决定**：有明确评审要求优先处理；无新信息默认等待，不因到期自动 ping 或关闭。需催询时说明具体请求并核对既有消息，避免重复。
- **处理真实阻塞**：我方引入的失败优先修；仅因真实冲突、必需检查、必要上游修复或维护者要求同步。behind 本身不触发同步；修改 head 后重验受影响范围，遵守仓库增量提交规则。
- 单一事实源=GitHub; 全量盘 PR 用 `gh api "search/issues?q=is:pr+author:inchang-ing+state:open&per_page=100&sort=updated"`(**`gh search prs` 会静默返回 0, 不可信**)。memory 只记规律不记清单。`mergeable_state`: blocked=待门禁/behind=落后/unstable=CI 未绿/unknown=重算。批量巡检用 `work/triage_prs.py`(并发拉 mergeStateStatus+checks, 输出 `work/pr_triage.json`)。
- **批量工具坑**: `gh pr checks` 遇失败项 rc=1, 脚本必须忽略 returncode; GraphQL `statusCheckRollup` 是 `{state}` 而 REST 是 check runs 列表, `gh api graphql` 偶发 502→必配 REST 兜底。
- 维护者先关 issue(not_planned)再关 PR=裁定不修; 大仓 review 队列长(reviewDecision null 数周常态); **fork PR 的 Actions 常停 `action_required`**(待 maintainer 批准)=常态门禁, 非推送失败。
- **扫「他人新动静」cutoff 用「上次扫描时间」不用自然日 0 点**; **codecov/patch·project 红未必阻塞**: 先查 `gh api repos/{r}/rulesets` 有无 `required_status_checks`, rulesets `rules:[]` 为空即非阻塞(aiohttp#14017 patch 89% 仍可合)。
- **AI review bot 的 🟡 项常是真回归线索**: miloco pr-review 两条 🟡(兜底写者反噬/插件无 fsync)都成立, 逐条实现+回复+推 commit 是标准动作。

## 六、复盘/池状态
- **10-15 复盘**(全文 `work/retro-2026-10-15.md`): 外部 PR 100 个, 合 22/拒 30/在飞 48; 拒关率 9 月 32.1%→10 月 87.5%。归因: 重复/抢先 40%>门禁 30%>方案被否>AI 政策>自撤——**七成死因与代码质量无关**。
- **新 bug 流已饱和(10-19 起, 10-23 复核)**: 23 仓 × 30 天只扫出 3–5 个, 且多数已被软认领。**策略**: ①维护在飞 PR(回 review/修 CI/rebase)②降星级到 500–2000 中型仓 ③换贡献类型。
- **定时扫描机制**: `tools/quality_repos.json`(仓库池+blocked+heavy/rust)+`tools/scan_candidates.py --days --max`（旧 work 入口兼容）→`work/ledger/candidates.json`; automation `da3572ce`(HOURLY/INTERVAL=2)。
- **search API 对本账号容忍度极低**(连 2 次即 403): 扫描用仓库 issues 端点并保留间隔; 单次调用别拆成查 total+取 items。
