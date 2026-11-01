# 项目长期记忆(规律为主 + 实例为注脚)

> 操作手册 `work/PLAYBOOK.md`；质量、验证与对外沟通以根目录 RULES.md 为准。

## 元规则
- 只提共性规律(未来重复/改决策/去仓库名仍成立), 实例挂规律下 `例:仓#号`。流水: 单轮=`rounds-log.md`, 当日=`20YY-MM-DD.md`, 冷归档=`STATE-archive.md`; grep 历史只扫 `20*.md`。
- **本文件是注入层索引, 不是仓库; 超 ~12KB 就压缩**(已压十八次, 末次 2026-11-01, 13.2→12.9KB)。**压缩=下沉+留指针, 不删本体**; 归档层全量保留。
- **写进记忆的「实测」要能 5 分钟内复测, 推测必须当场标注**: 一次 403/超时不构成「平台限制该账号」(2026-11-01「连 2 次搜索即 403」被复测推翻)。错误规律比没规律更贵。**给用户解释时证据与推测分开说。**
- 不代声明真人审阅; 返工后验**最终提交**, 独立脚本/AST 只是局部证据。推送前跑 `tools/quality_check.py prepare/check`(通过≠投稿授权, 不换入口规避 404/403)。

## 路由表(高风险动作前强制检索)
**高风险动作**(解冲突/force push、改共享写者/销毁、回 CI 红、开新 PR、压缩记忆)前必读主题, **未检索不声称完成**; 漏召记 `work/recall-log.md`。映射: 解冲突→三; 销毁→二·补; CI 红/rst→四; 撞车/AI 政策→二; 巡检→五(细则均在 PLAYBOOK)。

## 一、不可违反的用户指令
- **方案/计划文档改动先审批后落盘**: 先给完整计划获批再写; 已落盘的摊开「改前→改后」供审(`work/plan-issue-first.md` 曾被纠正)。**「找到就跑PR啊问我干什么」(2026-10-13)**: 干净候选自行实现+提 PR, 不回头问; 例外=法律协议/不可逆破坏。
- 自动化**已获授权**(`417db721`): 每小时一轮, 第 0 步快扫+核查+认领, 之后维护/写码。**调度器硬上限=每小时一次**(minutely 被拒, `BYMINUTE` 能存不生效, 锚点=创建时刻), 判据看 `nextRunAt` 是否对齐。亚小时频率见六节。
- **无「一轮只跑一个 PR」约束; 纪律 = 同仓在飞 ≤1(硬上限 2)**。例: sqlalchemy 同 org 备 4 分支→整批被封; docling 满 2 个时让出 #5124, #4849 合后回捞。
- **权威池(4 门槛)**: ①Python 包 ②本机可跑测(重 GPU/C++/Rust 降级) ③收外部 bug-fix PR ④活跃 bug 流; 受限池(sqlalchemy/httpx/pallets)只扫不投。
- **提交侧**: 邮箱用 `197932532+inchang-ing@users.noreply.github.com`(CLA-bot 认人); 已授权代签 OSS CLA, 标准 CLAassistant 须账号持有者网页 OAuth; AI 披露格式各异(pytest 要 `Co-authored-by`+AUTHORS, MS 用 `/agree`); 其余见 PLAYBOOK。
- **贡献分层**: 文档修正/简单 PR 可投(不再要求实质行为影响), 但**落点必须是高星库或有组织背书的大厂仓**(低星公司官方仓合格, 个人小库不下放); 验证门槛不降。详见 `RULES.md`。

## 二、做不做(质量红线 + 撞车九查 v5; 细则见 PLAYBOOK「撞车核查 v5 细则」)
- **核查顺序**: 候选出现 → ①先数本仓我方 open PR(硬上限 2) → ②再核 timeline/评论/PR/assignee/标签。反了会把时间花在只能让出的候选上。
- **cross-referenced 必须核 `source.issue.repository.full_name`**: 只有同仓才算撞车, 他仓引用是正信号。**改名仓的 full_name 与入口 slug 不同**, 判同仓看对象身份不看字符串; 旧 slug 打 search 会 422。兜底: 拉本仓近 60 open PR 正则比 `#N` 与分支名。例: nvitop#238 ← psutil#3092 差点误判。
- **自滤两类即弃**: ①自陈已修(`fixed by PR`/`resolved by #`, 裸链 cross-ref 抓不到) ②软认领(正文+评论双查, 关键词要跟得上真人措辞)。工具只初筛, 每轮仍要人工读正文末尾。例: lm-eval#4502 正文质量很高, 但作者 19 分钟后自己开了 #4503。
- **同一门禁只许栽一次** → 命中即入台账。例: langgraph 3 连栽; sqlglot 3 个; networkx 2 个。
- **准入再前移一条**: issue 描述的文件**是否还在默认分支**(重写会让 bug 流失效; 一次 `contents/<path>` 即判)。例: dbt-core#16990 根因齐全但 main 已 Rust 重写、该 py 404。
- **仓级 PR 门禁有三形态, 准入阶段就要读出**: assign 门禁 / **`ready` 标签门禁**(未标 `ready` 的外部 PR 被机器人自动关闭, 只有维护者能重开; 质量再高也白写) / AI 政策禁投。读 CONTRIBUTING 专找 close-draft-ready-label-assign 动词, 不只扫 AI 关键词。例: agno#11422 安全类高质量候选栽在 `ready`。
- **AI 政策三类**: 禁 agent 名单(pre-commit/matplotlib/hypothesis/scipy/pyparsing/requests/evidently/ibis/mem0/jax/**transformers**/**pandas**/**home-assistant**)见即弃(后三条禁「autonomous agents 代开 PR/评论」, 质量高不是例外); **开 PR 前必读 AGENTS+AI_POLICY+CONTRIBUTING 正文+PR 模板**, **探测名须含 `AGENTS.md`**(pandas 只有 `contributing.rst`, 政策写在 `AGENTS.md`; 逐文件探 404 会把禁投仓当干净仓); 无条款(poetry/dd-trace/mypy/psutil)可投。**ansible 已实质封闭**(#87712)。
- **留言按信息价值决定**: 必要的认领/方案问题、新复现证据才沟通; 不发占位留言, 同一事项合并一次回复; 允许直接提 PR 的仓不发认领评论(psutil 属此类)。**风险分级四类**: ①门禁→等 assign ②方案争议→等 maintainer 定向 ③方言/解析器→先证明输入合法 ④撞车→有认领即让, 不争抢。**弃单下沉前判「仓级 or issue 级」**: 去掉仓库名弃因仍成立 = issue 级, 只进弃单台账, **不可**下沉为仓级规则(会误杀该仓未来干净候选)。
- **低门槛≠低竞争 / GFI 窗口 ≤12h / 低星大厂池是红利 / 在飞规模是策略变量 / 供给不足时加频无增量**: 五条均实测成立, 详见 PLAYBOOK。要点: 竞争密度＝该仓有多少自动化在盯(open PR 分支名同质即 LLM 密集仓, 前置跳过)。

## 二·补、缺陷修复通用形态(详版 PLAYBOOK「缺陷修复通用形态」)
六形态: ①读失败当空配置=多写者数据丢失(fail-open 必查调用方) ②修写者修全部+tmp+fsync+rename ③读路径宽容但不静默 ④销毁与失败清理联动 ⑤新值类型枚举全部原语 ⑥弱签名探测器要用带校验和的 stdlib 解析器确认, 拒绝后回落 `_mime_from_extension` 而非 None。例: docling#5124 tar。

## 三、怎么交(详版 PLAYBOOK「三、怎么交」)
- DCO 仓手写 Signed-off-by; 浅克隆禁直接 amend; **动手前 `git fetch <fork> <branch>` 比远端 head**(status 干净≠没做过)。例: docling#5007 验完后才发现远端 10-29 已做完同一修复, 整轮丢弃。
- **判「分叉」只认 `git merge-base --is-ancestor <remote> HEAD`**: 拿 `git log -3` 两边并列比必然误判 —— 远端 head 的提交是更早的历史, 当然不在「本地最近 3 个」里。**push 打印 `old..new`(无 `+`)才是 fast-forward 实证**。例: zcode-PR 2026-11-01 误报分叉, 实际本地领先 5 个提交。
- **有 AGENTS.md 即硬约束**(例 litellm: 分支名 `litellm_` 无 `/`、行宽 120、禁注释、conventional commits); 「预读」= AGENTS+CONTRIBUTING+`.pre-commit-config` 全套; **改 rst 必跑 `rstwrap <file>`**(手写断行会被 `Lint rst` 判失败)。
- **本地 checkout 是 CRLF≠仓库是 CRLF**: API 推送前必须 LF 规范化; 判据: diff 整份文件被重写→先怀疑换行符, `git hash-object` 对齐 blob sha。本地 lint 报错同理(基线也报=换行符问题, 用 LF 副本 + `diff --strip-trailing-cr` 分辨)。
- **`git merge-file` 干净 ≠ GitHub 接受合并**: 解法=merge commit 双父使 merge-base 后移。**git 出网被封但 `api` 通时不降级**, 走 `blobs→trees→commits(双父)→PATCH refs`, 配 `work/push_via_api.py`; **`hash-object -w` 复现不了远端 sha**(message 逐字节相同也不行), 所以 API 推过的分支本地与远端内容同而 sha 并行, 脚本每次以远端 head 作 parent 续推即可。**API 提交默认取主邮箱(泄漏), 须显式传 author+committer 的 noreply**; 它另起一条历史, 同文件双写必 add/add 冲突(取分支版)。例: zarr#4526、zcode-PR 2026-11-01。

## 四、验证纪律(详版 PLAYBOOK「四、验证纪律」)
- 判别力: **撤修复→fail, 恢复→pass**; 竞态类修复撤代码不便时, 可在同进程把守卫 monkeypatch 成空上下文管理器做对照组(**先存原方法引用再还原**, 否则第二组仍是坏的→假阴性); 新增不可达防御分支会被覆盖率判失败(bokeh#15476); 跑源码非 site-packages 副本; 跨会话/API 重建的文件不能信"已验证"→推后必查 `gh pr checks`。**纯净基线用 `git restore --source=HEAD --staged --worktree`**, `git checkout` 会丢本轮未提交改动。
- **CI 红先判"是不是我的", 逐 job 判**: 判据=同 workflow 在 main 是否天天红 / 同 commit 该 job 是否有更晚 success / 失败是否落在自己 diff 面; 必拉日志定真因。**用 `gh pr checks --json state` 统计而非文本 grep —— `CANCELLED`(fail-fast 连带)≠`FAILURE`**(coveragepy#2350 文本 12 fail 实为 1 FAILURE + 11 CANCELLED, 真因 `CreateArtifact: ETIMEDOUT`)。fork PR 无法 `rerun --failed`(需 admin), 只能推空提交; **mergify/devflow 类失败常是评审门禁**。
- **本地测试失败先判环境**: 缺 pytest-asyncio/fcntl(Windows)/POSIX 权限位/`/bin/sh` spawn 均非代码问题; 同环境对比基线与补丁失败集合, 同因才判环境。例: aiohttp 全红实为 multidict 缺 `_md`; psutil 需先 `build_ext --inplace`。
- **端到端对照要给「修复前/后不同数」**(docling#4849「2 failed→13 passed」); **判「失败是不是我造成的」比失败集合不比数量**(`grep '^FAILED'|sort` 后 `comm -13`; markdown#1666 13 vs 15, 差 2 才是真回归); **基准文件的「删除行」多半是 EOF 换行规范化**(判据=被删内容是否在 `+` 侧原样出现); 下游扩展套件须先跑 baseline; 插件缺失可走 backend 旁路但须证明与基准全等; 改完 `.py` 前跑 `ast.parse`; 用例放进已被 CI 覆盖的既有测试文件。

## 五、监控/数据
- **本仓 Actions schedule 极不可靠**(`*/5` 在 166 分钟内 34 个时点只响 1 次 = 2.9%; 平台与配置已逐项排除, 不编因果)。两条对策, 后者是根治: ①窗口不能固定, 以「上一次成功运行的 `created_at`」为下界(`clamp(gap+2min, 20m, 6h)`), 否则 20 分钟窗 + 145 分钟间隔会丢掉期间全部内容; ②**`GITHUB_TOKEN` 能自链 `workflow_dispatch`**(「GITHUB_TOKEN 事件不产生新 run」的唯一豁免, 实测 204 + 5 秒后新 run), 所以**一次触发跑长班(≤6h) + 班末自触发下一班**, cron 退化为重启按钮。**坑: permissions 必须 `actions: write`, 写 read 会 403 `Resource not accessible by integration`**; 守卫=实际时长不足一半不链(防挂掉的环变成秒级循环), 留 `chain=false` 让链条可测。**只改分支没用, schedule 只跑默认分支。**
- **跟进按阻塞和证据决定**: 有明确评审要求优先处理; 无新信息默认等待, 不因到期自动 ping 或关闭。我方引入的失败优先修; behind 本身不触发同步。**但「具体化催询」例外且有效**: 点名谁已批/何时批/卡在哪一条 → docling#4849 挂了 16 天的 CHANGES_REQUESTED 当天解开并合并; 空催无效。
- 单一事实源=GitHub; 全量盘 PR 用 `gh api "search/issues?q=is:pr+author:inchang-ing+state:open&per_page=100&sort=updated"`(**`gh search prs` 静默返回 0, 不可信**); memory 只记规律不记清单。`mergeable_state`: blocked=待门禁/behind=落后/unstable=CI 未绿。
- 维护者先关 issue(not_planned)再关 PR=裁定不修; 大仓 reviewDecision null 数周常态; **fork PR 的 Actions 常停 `action_required`**=待批准, 非推送失败 —— `gh pr checks` 此时只报 "no checks reported", 判据要拉 `actions/runs?head_sha=<sha>` 看 `conclusion`; **rulesets 才是必需检查的唯一事实源**(空=该红不阻塞)。
- **扫「他人新动静」cutoff 用「上次扫描时间」不用自然日 0 点**; 单仓 `query incomplete` 不必补救(watermark 未推进, 下轮 `--all` 补扫)。**但整份巡检全 `QUERY_ERROR` 不是「无变化」**: 先看 `gh api rate_limit`, 充足即判瞬时抖动重跑, 别把查询失败当状态未变。临时文件统一 `work/tmp/`(Windows 上 Python 的 `/tmp` 落 `E:\tmp`, 与 bash 的 `%TEMP%` 不同目录)。
- **AI review bot 的 🟡 项常是真回归线索**(miloco 两条均成立), 逐条实现+回复+推 commit。

## 六、复盘/池状态(运维细则见 PLAYBOOK「发现层/池状态运维」)
- **七成弃单死因与代码质量无关**(重复/抢先 40%>门禁 30%>方案被否>AI 政策>自撤); 10-15 复盘 合 22/拒 30。
- **新 bug 流已饱和**: 23 仓 × 30 天只扫出 3–5 个且多数被软认领; 策略=维护在飞 + 降星级 500–2000 仓 + 换贡献类型。**唯一稳定收益: 只有跑起来才暴露的缺陷**(无人立 issue 也就无人抢)。连续四轮全池 0 认领, 印证「加频率无增量」。
- **维护期产出上限由评审吞吐决定, 不由写入速度决定**: 85 在飞 = 29 CLEAN + 38 BLOCKED + 15 UNSTABLE(多为既有红) + 2 BEHIND。此时正确动作是清红、具体化催询、补欠承诺, **不是开新单**。
- **发现层与决策层分开**: 发现不需模型 → 按仓拉增量并 `@inchang-ing`(mention 才通知); 认领/写码留每小时流水线(`417db721`)。轮询禁用全局 search(1000 条上限), 按仓 `issues?since=` 并用 `html_url` 去重(改名仓重复播报)。
- **search API 有独立配额(30/min)+secondary limit**: 遇 403 先看 `X-RateLimit-Remaining`, 为 0 才是 primary 耗尽, 否则隔几秒重试。用 issues 端点是因为它没有 1000 条上限。
