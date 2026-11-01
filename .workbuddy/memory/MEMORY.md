# 项目长期记忆(规律为主 + 实例为注脚)

> 操作手册 `work/PLAYBOOK.md`；质量、验证与对外沟通以根目录 RULES.md 为准。

## 元规则
- 只提共性规律(未来重复/改决策/去仓库名仍成立), 实例挂规律下 `例:仓#号`。流水: 单轮=`rounds-log.md`, 当日=`20YY-MM-DD.md`, 冷归档=`STATE-archive.md`; grep 历史只扫 `20*.md`。
- **本文件是注入层索引, 不是仓库; 超 ~12KB 就压缩**(已压十七次, 末次 2026-11-01)。**压缩=下沉+留指针, 不删本体**; 归档层全量保留。
- **写进记忆的「实测」要能 5 分钟内复测, 推测必须当场标注**: 一次 403/超时不构成「平台限制该账号」(2026-11-01「连 2 次搜索即 403」被复测推翻)。错误规律比没规律更贵。**给用户解释时证据与推测分开说。**
- 不代声明真人审阅; 返工后验最终提交, 独立脚本/AST/stub 只是局部证据(先核对失败确为目标缺陷, 再跑正常/异常/插件/调用方用例)。首次提交与每次返工推送前跑 `tools/quality_check.py prepare/check`(通过≠投稿授权, 也不借换入口规避 404/403)。

## 路由表(高风险动作前强制检索)
**高风险动作**(解冲突/force push/同步、改共享写者/持久化/销毁、回 CI 红、开新 PR、压缩记忆/写日志)前必读对应主题, **未检索不声称完成**; 漏召记 `work/recall-log.md`, 同一指针 30 天拉回 ≥3 次→升回。映射: 解冲突→三+PLAYBOOK「GitHub 解冲突」; 数据丢失/销毁→二·补; CI 红/rst→四+PLAYBOOK「推送通道」; 撞车/AI 政策→二+PLAYBOOK「撞车核查 v5」; 巡检/跟进→五。

## 一、不可违反的用户指令
- **方案/计划文档改动先审批后落盘**: 先给完整计划获批再写; 已落盘的摊开「改前→改后」供审(`work/plan-issue-first.md` 曾被纠正)。**「找到就跑PR啊问我干什么」(2026-10-13)**: 干净候选自行实现+提 PR, 不回头问; 例外=法律协议/不可逆破坏。
- 自动化**已获授权**(`417db721`): 每小时一轮, 第 0 步快扫 48h 新 issue+核查+认领, 之后维护/写码。**客户端调度器硬上限=每小时一次**(minutely 被校验拒绝, `BYMINUTE` 能存但不生效, 锚点=创建时刻), 判据看 `nextRunAt` 是否真对齐。亚小时频率见六节。
- **无「一轮只跑一个 PR」约束; 纪律 = 同仓在飞 ≤1(硬上限 2)**。例: sqlalchemy 同 org 备 4 分支→整批被封; docling 满 2 个时让出 #5124, #4849 合后回捞。
- **权威池(4 门槛)**: ①Python 包 ②本机可跑测(重 GPU/C++/Rust 降级) ③收外部 bug-fix PR ④活跃 bug 流; 约 53 个, 受限池(sqlalchemy/httpx/pallets)只扫不投。
- **提交侧**: 邮箱用 `197932532+inchang-ing@users.noreply.github.com`(CLA-bot 认人); 已授权代签 OSS CLA, 标准 CLAassistant 须账号持有者网页 OAuth; AI 披露格式各异(pytest 要 `Co-authored-by`+AUTHORS, MS 用 `/agree` bot); org 规范名与其余渠道细则见 PLAYBOOK。
- **2026-11-01 贡献分层**: 不再要求「必须是有实质行为影响的 bug」——文档修正/简单 PR 可投; 但**落点必须是高星库或有组织背书的大厂仓**(低星的公司官方仓合格, 个人小库不因内容简单而下放)。验证门槛不降。详见 `RULES.md`。

## 二、做不做(质量红线 + 撞车九查 v5; 细则见 PLAYBOOK「撞车核查 v5 细则」)
- **核查顺序**: 候选出现 → ①先数本仓我方 open PR(硬上限 2) → ②再核 timeline/评论/PR/assignee/标签。反了会把时间花在只能让出的候选上。
- **cross-referenced 必须核 `source.issue.repository.full_name`**: 只有同仓才算撞车, 他仓引用是正信号。**改名仓的 full_name 与入口 slug 不同**, 判同仓看对象身份不看字符串(否则把自家竞品 PR 当"他仓正信号"放过); 旧 slug 打 search 会 422。兜底: 拉本仓近 60 open PR 正则比 `#N` 与分支名。例: nvitop#238 ← psutil#3092 差点误判。
- **自滤两类即弃**: ①自陈已修(`fixed by PR`/`resolved by #`, 裸链 cross-ref 抓不到) ②软认领(正文+评论双查, 关键词要跟得上真人措辞)。工具只初筛, 每轮仍要人工读正文末尾。例: lm-eval#4502 正文质量很高, 但作者 19 分钟后自己开了 #4503。
- **同一门禁只许栽一次** → 命中即入台账。例: langgraph 3 连栽; sqlglot 3 个; networkx 2 个。
- **准入再前移一条**: issue 描述的文件**是否还在默认分支**(重写会让 bug 流失效; 一次 `contents/<path>` 即判)。例: dbt-core#16990 根因齐全但 main 已 Rust 重写、该 py 404。
- **AI 政策三类**: 禁 agent 名单(pre-commit/matplotlib/hypothesis/scipy/pyparsing/requests/evidently/ibis/mem0/jax/**transformers**)见即弃 —— 后者禁令含「autonomous agents 不得开 PR」, 质量高不算例外; **开 PR 前必读 AI_POLICY+AGENTS+CONTRIBUTING 正文+PR 模板**(政策常写在正文, geopandas#3896、jax#41846 栽在「只查文件存在」); 须披露→如实披露; 无条款(poetry/dd-trace/mypy/psutil)可投。**ansible 已实质封闭**(#87712)。
- **留言按信息价值决定**: 必要的认领/方案问题、新复现证据才沟通; 不发占位留言, 同一事项合并一次回复。仓库允许直接提 PR 的不发认领评论(psutil 属此类)。
- **风险分级四类**: ①门禁→等 assign ②方案争议→等 maintainer 定方向 ③方言/解析器→先证明输入本身合法 ④撞车→存在认领即让, 不留言争抢。
- **弃单下沉前判「仓级 or issue 级」**: 去掉仓库名弃因仍成立 = issue 级, 只进弃单台账, **不可**下沉为仓级规则(会误杀该仓未来干净候选)。
- **低门槛≠低竞争 / GFI 窗口 ≤12h / 低星大厂池是红利 / 在飞规模是策略变量 / 供给不足时加频无增量**: 五条均实测成立, 详见 PLAYBOOK。要点: 竞争密度＝该仓有多少自动化在盯(open PR 分支名同质即 LLM 密集仓, 前置跳过)。

## 二·补、缺陷修复通用形态(详版 PLAYBOOK「缺陷修复通用形态」)
五形态: ①读失败当空配置=多写者数据丢失(fail-open 必查调用方) ②修写者修全部+tmp+fsync+rename ③读路径宽容但不静默 ④销毁与失败清理联动 ⑤新值类型枚举全部原语。**⑥弱签名探测器(只看魔数的)要用带校验和的 stdlib 解析器确认**, 拒绝后回落 `_mime_from_extension(ext)` 而非 None。例: ansible#87712、jax#41846、docling#5124 tar。

## 三、怎么交(详版 PLAYBOOK「三、怎么交」)
- DCO 仓手写 Signed-off-by; 浅克隆禁直接 amend; **动手前 `git fetch <fork> <branch>` 比远端 head**(status 干净≠没做过)。例: docling#5007 改码验完后才发现远端 10-29 已做完同一修复, 整轮 reset 丢弃。
- **有 AGENTS.md 即硬约束**(例 litellm: 分支名 `litellm_` 无 `/`、行宽 120、禁注释、conventional commits); 「预读」= AGENTS.md+CONTRIBUTING+`.pre-commit-config` 全套; **改 rst 必跑 `rstwrap <file>`**(手写断行会被 CI `Lint rst` 判失败)。
- **本地 checkout 是 CRLF≠仓库是 CRLF**: API 推送前必须 LF 规范化; 判据: diff 整份文件被重写→先怀疑换行符, `git hash-object` 对齐 blob sha。本地 lint 报错同理(基线也报=换行符问题, 用 LF 副本 + `diff --strip-trailing-cr` 分辨)。
- **`git merge-file` 干净 ≠ GitHub 接受合并**: 解法=merge commit 双父使 merge-base 后移。**git 出网被封时不降级**, 走 `blobs→trees→commits(双父)→PATCH refs`, 天然双父且 diff 不掺上游。**Contents API 只能用账号主邮箱(泄漏真实邮箱), 本地 commit 才走 noreply。** 手法详见 PLAYBOOK。例: zarr#4526。

## 四、验证纪律(详版 PLAYBOOK「四、验证纪律」)
- 判别力: **撤修复→fail, 恢复→pass**; 新增不可达防御分支会被覆盖率判失败(bokeh#15476); 跑源码非 site-packages 副本; 跨会话/API 重建的文件不能信"已验证"→推后必查 `gh pr checks`。**纯净基线用 `git restore --source=HEAD --staged --worktree`**, `git checkout` 会丢本轮未提交改动。
- **CI 红先判"是不是我的", 逐 job 判**: 一轮里可能既有仓库既有红(psutil `linters` clang-format 漂移)也有我造成的红(同仓 `Lint rst`)。判据: 同 workflow 在 main 是否天天红 / 同 commit 该 job 是否有更晚 success / 失败是否落在自己 diff 面; 必拉日志定真因, 勿按作业名猜。**判红用 `gh pr checks --json state` 统计, 别用文本 grep —— `CANCELLED`(fail-fast 连带)≠`FAILURE`**(coveragepy#2350 文本 12 fail → 实为 1 FAILURE + 11 CANCELLED, 真因 `CreateArtifact: ETIMEDOUT`)。fork PR 的 `rerun --failed` 需 admin rights, 只能推空提交重触发。**mergify/devflow 类失败项常是评审门禁而非测试红**。
- **本地测试失败先判环境**: 缺 pytest-asyncio/fcntl(Windows)/POSIX 权限位/`/bin/sh` spawn 均非代码问题; 同环境对比基线与补丁失败集合, 同因才判环境。例: aiohttp 全红实为 multidict 缺 `_md`; psutil 需先 `build_ext --inplace`。
- **端到端对照要给「修复前/后不同数」**(repowise#3187「2→0」; docling#4849「2 failed→13 passed」); **判「失败是不是我造成的」比失败集合不比数量**(`grep '^FAILED'|sort` 后 `comm -13`; markdown#1666 master 13 vs 分支 15, 差 2 才是真回归); **基准文件的「删除行」多半是 EOF 换行规范化**(追加后原末行不再位于 EOF 被重写; 判据=被删内容是否在 `+` 侧原样出现; docling#5007 md/itxt 的 `\ No newline at end of file`); 下游扩展套件是兼容性唯一探针但须先跑 baseline; 插件缺失可走 backend 旁路但须在未修改 fixture 上证明与基准全等; 改完 `.py` 提交前跑 `ast.parse`(lm-eval#4459 `\n` 落盘成真换行→整文件 SyntaxError); 用例放进已被 CI 覆盖的既有测试文件。

## 五、监控/数据
- **跟进按阻塞和证据决定**: 有明确评审要求优先处理; 无新信息默认等待, 不因到期自动 ping 或关闭。我方引入的失败优先修; behind 本身不触发同步。**但「具体化催询」例外且有效**: 点名谁已批/何时批/卡在哪一条 → docling#4849 挂了 16 天的 CHANGES_REQUESTED 当天解开并合并; 空催无效。
- 单一事实源=GitHub; 全量盘 PR 用 `gh api "search/issues?q=is:pr+author:inchang-ing+state:open&per_page=100&sort=updated"`(**`gh search prs` 静默返回 0, 不可信**); memory 只记规律不记清单。`mergeable_state`: blocked=待门禁/behind=落后/unstable=CI 未绿。
- GraphQL `statusCheckRollup` 是 `{state}` 而 REST 是 check runs; `gh api graphql` 偶发 502→配 REST 兜底; `gh pr checks` 遇失败项 rc=1(脚本须忽略 returncode)。
- 维护者先关 issue(not_planned)再关 PR=裁定不修; 大仓 reviewDecision null 数周常态; **fork PR 的 Actions 常停 `action_required`**=待批准, 非推送失败; **rulesets 才是必需检查的唯一事实源**(空=该红不阻塞)。
- **扫「他人新动静」cutoff 用「上次扫描时间」不用自然日 0 点**。
- **AI review bot 的 🟡 项常是真回归线索**(miloco 两条均成立), 逐条实现+回复+推 commit。

## 六、复盘/池状态(运维细则见 PLAYBOOK「发现层/池状态运维」)
- **10-15 复盘**: 合 22/拒 30; 拒关率 32%→87.5%; **七成死因与代码质量无关**(重复/抢先 40%>门禁 30%>方案被否>AI 政策>自撤)。
- **新 bug 流已饱和**: 23 仓 × 30 天只扫出 3–5 个且多数已被软认领; 策略=维护在飞 + 降星级 500–2000 仓 + 换贡献类型。**唯一稳定收益: 只有跑起来才暴露的缺陷**(无人立 issue 也无人抢)。
- **维护期的产出上限由评审吞吐决定, 不由写入速度决定**: 2026-11-01 实测 85 在飞 = 29 CLEAN(只等合) + 38 BLOCKED(只等评审) + 15 UNSTABLE(逐条查完多为仓库既有红) + 2 BEHIND。此时正确动作是清红、具体化催询、补自己欠下的承诺, **不是开新单**。
- **发现层与决策层分开**: 发现不需模型 → 按仓拉增量并 `@inchang-ing`(mention 才通知); 认领/写码留每小时流水线(`417db721`, 首步 `--all`)。轮询禁用全局 search(1000 条上限), 按仓 `issues?since=` 并按 `html_url` 去重(改名仓重复播报)。
- **本仓 Actions schedule 从未触发**(3 次复核、70+ 应触发时点全 0, 纯 echo 探针同样 0; 文件在 main、语法正确、平台/配置均排除, **不编因果**; 快车道靠 `work/poll_5min.cmd`+schtasks, 须用户本人注册)。
- **triage bot 把关仓的快车道价值≈0**(12 秒 `not_planned` 关单): 发现快≠可认领。
- **search API 有独立配额(30/min)+secondary limit**: 遇 403 先看 `X-RateLimit-Remaining`, 为 0 才是 primary 耗尽; 其余隔几秒重试即可。用 issues 端点的理由是没有 1000 条上限, 不是 search 不可用。
