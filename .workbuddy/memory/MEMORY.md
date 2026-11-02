# 项目长期记忆(规律为主 + 实例为注脚)

> 操作手册 `work/PLAYBOOK.md`；质量、验证与对外沟通以根目录 RULES.md 为准。

## 元规则
- 只提共性规律(未来重复/改决策/去仓库名仍成立), 实例挂规律下 `例:仓#号`。流水: 单轮=`rounds-log.md`, 当日=`20YY-MM-DD.md`, 冷归档=`STATE-archive.md`; grep 历史只扫 `20*.md`。
- **本文件是注入层索引, 不是仓库; 超 ~12KB 就压缩**(已压十九次, 末次 2026-11-02, 15.2→12.9KB)。**压缩=机制段落下沉 PLAYBOOK+留指针, 规律与实例留本层**; 归档层全量保留。
- **写进记忆的「实测」要能 5 分钟内复测, 推测必须当场标注**: 一次 403/超时不构成「平台限制该账号」(2026-11-01「连 2 次搜索即 403」被复测推翻)。错误规律比没规律更贵。**给用户解释时证据与推测分开说。**
- 不代声明真人审阅; 返工后验**最终提交**, 独立脚本/AST 只是局部证据。推送前跑 `tools/quality_check.py prepare/check`(通过≠投稿授权, 不换入口规避 404/403)。

## 路由表(高风险动作前强制检索)
**高风险动作**(解冲突/force push、改共享写者/销毁、回 CI 红、开新 PR、压缩记忆)前必读对应主题, **未检索不声称完成**; 漏召记 `work/recall-log.md`。映射: 解冲突→三; 销毁→二·补; CI 红/rst→四; 撞车/AI 政策→二; 巡检→五; 机制细节→PLAYBOOK。

## 一、不可违反的用户指令
- **方案/计划文档改动先审批后落盘**: 先给完整计划获批再写; 已落盘的摊开「改前→改后」供审(`work/plan-issue-first.md` 曾被纠正)。**「找到就跑PR啊问我干什么」(2026-10-13)**: 干净候选自行实现+提 PR, 不回头问; 例外=法律协议/不可逆破坏。
- 自动化**已获授权**(`417db721`): 每小时一轮, 第 0 步消费收件箱+快扫+核查+认领, 之后维护/写码。**调度器硬上限=每小时一次**(minutely 被拒, `BYMINUTE` 能存不生效, 锚点=创建时刻), 判据看 `nextRunAt` 是否对齐。亚小时频率见六节。
- **无「一轮只跑一个 PR」约束; 纪律 = 同仓在飞 ≤1(硬上限 2)**。例: sqlalchemy 同 org 备 4 分支→整批被封; docling 满 2 个时让出 #5124, #4849 合后回捞。
- **权威池(4 门槛)**: ①Python 包 ②本机可跑测(重 GPU/C++/Rust 降级) ③收外部 bug-fix PR ④活跃 bug 流; 受限池(sqlalchemy/httpx/pallets)只扫不投。
- **提交侧**: 邮箱用 `197932532+inchang-ing@users.noreply.github.com`(CLA-bot 认人); 已授权代签 OSS CLA, 标准 CLAassistant 须账号持有者网页 OAuth; AI 披露格式各异(pytest 要 `Co-authored-by`+AUTHORS, MS 用 `/agree`); 其余见 PLAYBOOK。
- **贡献分层**: 文档修正/简单 PR 可投(不再要求实质行为影响), 但**落点必须是高星库或有组织背书的大厂仓**(低星公司官方仓合格, 个人小库不下放); 验证门槛不降。详见 `RULES.md`。

## 二、做不做(全文细则见 PLAYBOOK「2026-11-02 下沉: 做不做」, 原九查 v5 一字未删)
- **核查顺序**: 候选出现 → ①先数本仓我方 open PR(硬上限 2) → ②再核 timeline/评论/PR/assignee/标签。反了会把时间花在只能让出的候选上。
- **先试「PR 号 = issue 号 +1/+2/+3」再跑 timeline**: 竞品 PR 常在 issue 开出十几分钟内出现; timeline 的 cross-referenced 留作兜底。例: 2026-11-02 轮 29 条收件箱 15 条如此。
- **cross-referenced 必须核 `source.issue.repository.full_name`**: 只有同仓才算撞车, 他仓引用是正信号(含作者自有 fork 备 PR = 对方已在做); 改名仓看对象身份不看 slug。例: nvitop#238; sympy#30921→csp256/sympy#26。
- **自滤两类即弃**: 自陈已修/自陈愿提 PR(`fixed by PR`、裸链 cross-ref 抓不到), 与软认领(正文+评论双查)。每轮仍要人工读正文末尾; **尾巴句式「happy to send a PR」已蔓延到高质量 issue, 且新变体=正文 `<details>` 里贴出改好的代码与 `fix OK` 输出**(有则按已有补丁弃, 不必细读)。例: lm-eval#4502; inspect_ai#6230; lighteval#1466; huggingface_hub#5293。
- **准入三条**: ①issue 描述的文件**是否还在默认分支**(dbt-core#16990 main 已 Rust 重写) ②仓级 PR 门禁三形态 assign / **`ready`、`ready-for-dev` 标签**(同族, 见到即弃, 不必再读正文)(agno#11422; openhands#19210) / AI 政策禁投, 读 CONTRIBUTING 专找 close-draft-ready-label-assign 动词 ③政策名单以 `tools/repository_policy.py` 为准, **探测名须含 `AGENTS.md`**(pandas 只有 contributing.rst)。
- **同一门禁只许栽一次** → 命中即入台账(langgraph 3 连栽)。**留言按信息价值决定**: 不发占位留言, 允许直提 PR 的仓不问(psutil/vcrpy); **弃单下沉前判「仓级 or issue 级」**: 去掉仓库名弃因仍成立就只进 `tools/dispositions.json`, 误下沉会误杀该仓未来干净候选。
- **低门槛≠低竞争 / GFI 窗口 ≤12h / 低星大厂池是红利 / 在飞规模是策略变量 / 供给不足时加频无增量**: 五条均实测成立, 详见 PLAYBOOK。要点: 竞争密度＝该仓有多少自动化在盯(open PR 分支名同质即 LLM 密集仓, 前置跳过)。

## 二·补、缺陷修复通用形态(七形态详见 PLAYBOOK「缺陷修复通用形态」)
①读失败当空配置=多写者数据丢失(fail-open 必查调用方) ②修写者修全部+tmp+fsync+rename ③读路径宽容但不静默 ④销毁与失败清理联动 ⑤新值类型枚举全部原语 ⑥弱签名探测器要用带校验和的 stdlib 解析器确认 ⑦**兼容层按「对方公开面的最小版本」写**: 新版才有的符号用 `try/except ImportError` 回落私有路径, 不把对方提成硬依赖(会连累被 pin 在老版本的用户)。例: docling#5124 tar; vcrpy#1092 的 `HTTPHeaderDict` 仅 2.0+ 在顶层导出。

## 三、怎么交(机制细节见 PLAYBOOK「三、怎么交」+「2026-11-01 下沉」)
- DCO 仓手写 Signed-off-by; 浅克隆禁直接 amend; **动手前 `git fetch <fork> <branch>` 比远端 head**(status 干净≠没做过)。例: docling#5007 远端 10-29 已做完同一修复, 整轮丢弃。
- **判「分叉」只认 `git merge-base --is-ancestor <remote> HEAD`**; 拿 `git log -3` 两边并列比必然误判。**push 打印 `old..new`(无 `+`)才是 fast-forward 实证**。例: zcode-PR 误报分叉, 实际本地领先 5 个。
- **推送顺序: 先试直推 fork 再降级** —— git https 时通时不通(2026-11-02 vcrpy 全通 / 11-01 封), 不通且 api 通才走 Git Data API(`work/push_via_api.py`); **API 提交默认取主邮箱(泄漏), 须显式传 noreply**; `hash-object -w` 复现不了远端 sha, 故 API 分支本地与远端内容同而 sha 并行。**`git merge-file` 干净 ≠ GitHub 接受合并**(解法=merge commit 双父)。例: zarr#4526。
- **有 AGENTS.md 即硬约束**(litellm: 分支名无 `/`、行宽 120、禁注释); 「预读」= AGENTS+CONTRIBUTING+`.pre-commit-config` 全套; **改 rst 必跑 `rstwrap <file>`**; **本地 checkout 是 CRLF≠仓库是 CRLF**, diff 整份重写先怀疑换行符。

## 四、验证纪律(全文细则见 PLAYBOOK「2026-11-02 下沉: 验证纪律」)
- 判别力: **撤修复→fail, 恢复→pass**; 竞态类撤代码不便时, 同进程把守卫 monkeypatch 成空上下文管理器做对照组(**先存原方法引用再还原**, 否则假阴性); 不可达防御分支会被覆盖率判失败(bokeh#15476); 跑源码非 site-packages 副本; 跨会话/API 重建的文件不能信"已验证"。**纯净基线用 `git restore --source=HEAD --staged --worktree`**。**本地 lint/format 版本必须对齐仓库 pin(读 `setup.py`/`.pre-commit-config.yaml`), 否则「本地已格式化」是假绿**; 判 CI 红是否属我方可比「同一句报错」而非只比失败集合。例: sqlglot#8869 本地 ruff 0.17.3 报绿、pin 的 0.15.6 判红, main 同 commit 同一句 "2 files reformatted" 证其为我方之外遗留。
- **兼容性类修复在双版本各跑一遍**(旧版=复现环境, 新版=回归环境), 正文写「两环境改前改后失败集合逐条同名」。例: vcrpy#1092 用 urllib3 1.26.18 / 2.8.0, 67 failed→6 failed。
- **判「失败是不是我造成的」比集合不比数量**(`grep '^FAILED'|sort` 后 `comm -13`; markdown#1666 13 vs 15); **端到端要给「修复前/后不同数」**(docling#4849「2 failed→13 passed」); **基准的「删除行」多半是 EOF 换行规范化**; 用例放进已被 CI 覆盖的既有文件; 改完 `.py` 前跑 `ast.parse`。
- **CI 红先判"是不是我的", 逐 job 判**; **用 `gh pr checks --json state` 统计而非文本 grep —— `CANCELLED`(fail-fast 连带)≠`FAILURE`**(coveragepy#2350 文本 12 fail 实为 1 FAILURE + 11 CANCELLED, 真因 `CreateArtifact: ETIMEDOUT`)。fork PR 无法 `rerun --failed`; **mergify/devflow 类失败常是评审门禁**。
- **本地失败先判环境**: 缺 pytest-asyncio/fcntl(Windows)/POSIX 权限位/`/bin/sh` spawn 均非代码问题; 同环境对比基线与补丁失败集合, 同因才判环境。例: aiohttp 缺 multidict `_md`; psutil 需 `build_ext --inplace`; vcrpy 6 条是 Windows 路径分隔符。

## 五、监控/数据(机制细节见 PLAYBOOK「调度器机制」「发现层/池状态运维」)
- **本仓 Actions schedule 极不可靠**(`*/5` 在 166 分钟内只响 1 次=2.9%, 平台与配置逐项排除, 不编因果)。根治=**`GITHUB_TOKEN` 能自链 `workflow_dispatch`**: 一次触发跑长班(≤6h)+班末自触发下一班, cron 退化成重启按钮。坑: permissions 须 `actions: write`; 守卫=实跑不足一半不链; **schedule 只跑默认分支**; 回看窗口以「上次成功运行的 `created_at`」为下界。
- **时间戳先对时区再下结论**: `inbox.py list`、Actions `created_at`、API 全是 **UTC**; 判「积压/停摆/多久没动」前先 `date -u` 与条目时间并排打印。例: 2026-11-02 轮把 28 分钟前的投递读成「8 小时积压, 发现层没在投递」, 差点写成假规律 —— 与「整份巡检全 `QUERY_ERROR` ≠ 无变化」同类: 把观测工具的表示形式当成被测对象的状态。
- **跟进按阻塞和证据决定**: 无新信息默认等待, 不因到期 ping; 我方引入的失败优先修; behind 不触发同步。**「具体化催询」有效**: 点名谁已批/卡在哪一条 → docling#4849 挂了 16 天的 CHANGES_REQUESTED 当天解开; 空催无效; 维护者回「还没想好/等有空看」= 无请求, 不催。
- **关得掉才叫开关**(老班不会因推新配置就停): 三层读同一变量 job `if` + poller 退出码 42 + chain step 末尾重读; **只关发现层不关执行层 = 只堆 backlog**。例: `PIPELINE_ENABLED`。
- **发现层与执行层之间要有队列状态**: 「这条判过了」不在评论流里 → 每轮重判同一批(实测 28 条 0 标记)。台账两级: done=判过了(弃单也记+原因), PR 号=做完了; **每轮必须清零**, 轮内新到的一起处置。例: `tools/inbox.py list/done/stats`; 2026-11-02 轮 41/41/0。
- **轮询间隔由 token 配额定**: 88 仓 × 4 次/h = 352, 占 1000/h 的三分之一; 6 分钟一轮是 880 几乎顶满。放宽回看窗口不花钱, 缩短间隔才花钱。
- 单一事实源=GitHub; 全量盘 PR 用 `gh api "search/issues?q=is:pr+author:inchang-ing+state:open&per_page=100"`(**`gh search prs` 静默返回 0**); memory 只记规律不记清单。`mergeable_state`: blocked=待门禁/behind=落后/unstable=CI 未绿。
- 维护者先关 issue(not_planned)再关 PR=裁定不修; **fork PR 的 Actions 常停 `action_required`**=待批准, 非推送失败 —— `gh pr checks` 此时只报 "no checks reported", 判据拉 `actions/runs?head_sha=<sha>`; **rulesets 才是必需检查的唯一事实源**(空=该红不阻塞)。
- **扫「他人新动静」cutoff 用「上次扫描时间」不用自然日 0 点**; 单仓 `query incomplete` 不必补救(watermark 未推进, 下轮 `--all` 补扫)。**整份巡检全 `QUERY_ERROR` 不是「无变化」**: 先看 `rate_limit`, 充足即重跑。临时文件统一 `work/tmp/`。
- **AI review bot 的 🟡 项常是真回归线索**(miloco 两条均成立), 逐条实现+回复+推 commit。
- **拿 GitHub issue 当日志会外溢到别人仓库**: issue 正文/评论里的**裸 URL 或 `owner/repo#num`** 都会生成 cross-reference 并通知目标 issue 的全部 watcher; **编辑评论、删评论都不回收**, 只有删掉**评论所在的整个 issue** 才让 timeline 清零(删后**全量复查 1269 个 issue 全部为 0**, 不是抽样)。所以内部日志只写反引号包裹的 `repo#num`(code span 不链接化), 绝不贴外链。例: 2026-11-02 `repo-monitor#1` 43 条评论 → **1269 个 issue / 108 个仓**, biopython#5396 维护者公开投诉 spam; 同源问题在自家 `zcode-PR#1`(28 个引用), 两处都已删 issue + 改格式 + 停 workflow。代价是**已发出的通知邮件收不回**, 且一次 cross-reference 推给该 issue 的全部 watcher, 实际触达远大于 issue 数; 补救只能靠删源, 不能靠逐个道歉(那是第二轮骚扰)。

## 六、复盘/池状态(运维细节见 PLAYBOOK「发现层/池状态运维」)
- **七成弃单死因与代码质量无关**(重复/抢先 40% > 门禁 30% > 方案被否 > AI 政策 > 自撤); 10-15 复盘 合 22/拒 30。
- **新 bug 流已饱和**: 23 仓 × 30 天只扫出 3–5 个且多数被软认领; 策略=维护在飞 + 降星级 500–2000 仓 + 换贡献类型。**唯一稳定收益: 只有跑起来才暴露的缺陷**(无人立 issue 也就无人抢)。连续四轮全池 0 认领, 印证「加频率无增量」。
- **维护期产出上限由评审吞吐决定**: 62 在飞时正确动作是清红、具体化催询、补欠承诺, **不是开新单**; 新单只在「无竞品 PR + 无自陈补丁」时开。
- **发现层与决策层分开**, 两层频率差是硬上限(发现 15 分钟 / 执行最快 1 小时, 最多 45 分钟时差): 想缩短只能让执行层自己盯盘, 不能靠加自动化。轮询禁用全局 search(1000 条上限), 按仓 `issues?since=` 并用 `html_url` 去重(改名仓重复播报)。
- **search API 有独立配额(30/min)+secondary limit**: 遇 403 先看 `X-RateLimit-Remaining`, 为 0 才是 primary 耗尽, 否则隔几秒重试。
