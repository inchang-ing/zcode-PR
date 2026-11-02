# 项目长期记忆(规律为主 + 实例为注脚)

> 操作手册 `work/PLAYBOOK.md`；质量、验证与对外沟通以根目录 RULES.md 为准。

## 元规则
- 只提共性规律(未来重复/改决策/去仓库名仍成立), 实例挂规律下 `例:仓#号`。流水: 单轮`rounds-log.md`/当日`20YY-MM-DD.md`/冷归档`STATE-archive.md`。
- **本文件是注入层索引, 超 ~12KB 压缩**(已压廿五次)。**压缩=机制下沉 PLAYBOOK+留指针, 规律与实例留本层**; 微调措辞无效, 有效=整节搬走。
- **写进记忆的「实测」要能 5 分钟内复测, 推测必须当场标注**: 一次 403/超时不构成「平台限制该账号」(2026-11-01「连 2 次搜索即 403」被复测推翻)。错误规律比没规律更贵。**给用户解释时证据与推测分开说。**
- 不代声明真人审阅; 返工后验**最终提交**, 独立脚本/AST 只是局部证据。推送前跑 `tools/quality_check.py prepare/check`(通过≠投稿授权, 不换入口规避 403)。

## 路由表(高风险动作前强制检索)
**高风险动作**(解冲突/force push、销毁、回 CI 红、开新 PR、压缩记忆)前必读对应主题, **未检索不声称完成**; 漏召记 `work/recall-log.md`。映射: 解冲突→三; 销毁→二·补; CI 红/rst→四; 撞车/AI 政策→二; 巡检→五; 机制→PLAYBOOK。

## 一、不可违反的用户指令
- **方案/计划文档改动先审批后落盘**: 先给完整计划获批再写; 已落盘的摊开「改前→改后」供审。**「找到就跑PR啊问我干什么」(2026-10-13)**: 干净候选自行实现+提 PR, 不回头问; 例外=法律协议/不可逆破坏。
- 自动化**已获授权**(`417db721`): 每小时一轮, 第 0 步消费收件箱后维护/写码。**调度器硬上限=每小时一次**, 判据看 `nextRunAt` 是否对齐; 细节见 PLAYBOOK「调度器机制」。
- **无「一轮只跑一个 PR」约束; 纪律 = 同仓在飞 ≤1(硬上限 2)**。例: sqlalchemy 同 org 备 4 分支→整批被封; docling 满 2 个时让出 #5124, #4849 合后回捞。
- **权威池(4 门槛)**: ①Python 包 ②本机可跑测(重 GPU/C++/Rust 降级) ③收外部 bug-fix PR ④活跃 bug 流; 受限池(sqlalchemy/httpx/pallets)只扫不投。
- **提交侧**: 邮箱用 `197932532+inchang-ing@users.noreply.github.com`(CLA-bot 认人); 已授权代签 OSS CLA, 标准 CLAassistant 须账号持有者网页 OAuth; AI 披露格式各异(pytest 要 `Co-authored-by`+AUTHORS, MS 用 `/agree`); 其余见 PLAYBOOK。
- **贡献分层**: 文档修正/简单 PR 可投(不再要求实质行为影响), 但**落点必须是高星库或有组织背书的大厂仓**(低星公司官方仓合格, 个人小库不下放); 验证门槛不降。详见 `RULES.md`。

## 二、做不做(全文细则见 PLAYBOOK「2026-11-02 下沉: 做不做」, 原九查 v5 一字未删)
- **核查顺序**: 候选出现 → ①先数本仓我方 open PR(硬上限 2) → ②再核 timeline/评论/PR/assignee/标签。反了会把时间花在只能让出的候选上。
- **先试「PR 号 = issue 号 +1/+2/+3」再跑 timeline**: 竞品 PR 常在 issue 开出十几分钟内出现; timeline 的 cross-referenced 留作兜底。例: 2026-11-02 轮 29 条中 15 条。
- **cross-referenced 必须核 `source.issue.repository.full_name`**: 只有同仓才算撞车, 他仓引用是正信号(含作者自有 fork 备 PR = 对方已在做); 改名仓看对象身份不看 slug。例: nvitop#238; sympy#30921→csp256/sympy#26。
- **自滤两类即弃**: 自陈已修/自陈愿提 PR(`fixed by PR`、裸链 cross-ref 抓不到), 与软认领(正文+评论双查)。每轮仍要读正文末尾; 尾巴句式「happy to send a PR」已蔓延到高质量 issue, 新变体=正文 `<details>` 里贴修好的代码与 `fix OK` 输出。例: lighteval#1466; huggingface_hub#5293。
- **准入三条**: ①issue 描述的文件**是否还在默认分支**(dbt-core#16990 main 已 Rust 重写) ②仓级门禁三形态 assign / **`ready`、`ready-for-dev` 标签**(同族, 见到即弃)(agno#11422) / AI 政策禁投 ③政策名单以 `tools/repository_policy.py` 为准, **探测名须含 `AGENTS.md`**(pandas 只有 contributing.rst)。
- **同一门禁只许栽一次** → 命中即入台账(langgraph 3 连栽)。**不发占位留言**, 允许直提 PR 的仓不问(psutil/vcrpy); **弃单下沉前判「仓级 or issue 级」**: 去掉仓库名弃因仍成立就只进 `tools/dispositions.json`, 误下沉会误杀该仓未来干净候选。
- **低门槛≠低竞争 / GFI 窗口 ≤12h / 低星大厂池是红利 / 在飞规模是策略变量 / 加频无增量**: 五条均实测成立, 详见 PLAYBOOK。竞争密度＝该仓有多少自动化在盯(open PR 分支名同质即 LLM 密集仓, 前置跳过)。

## 二·补、缺陷修复通用形态(七形态详见 PLAYBOOK「缺陷修复通用形态」)
①读失败当空配置=多写者数据丢失(fail-open 必查调用方) ②修写者修全部+tmp+fsync+rename ③读路径宽容但不静默 ④销毁与失败清理联动 ⑤新值类型枚举全部原语 ⑥弱签名探测器要用带校验和的 stdlib 解析器确认 ⑦**兼容层按「对方公开面的最小版本」写**: 新版符号用 `try/except ImportError` 回落私有路径, 不把对方提成硬依赖。例: vcrpy#1092 的 `HTTPHeaderDict` 仅 2.0+ 在顶层导出。

## 三、怎么交(机制细节见 PLAYBOOK「三、怎么交」+「2026-11-01 下沉」)
- DCO 仓手写 Signed-off-by; 浅克隆禁直接 amend; **动手前 `git fetch <fork> <branch>` 比远端 head**(status 干净≠没做过)。例: docling#5007 远端 10-29 已做完同一修复, 整轮丢弃。
- **判「分叉」只认 `git merge-base --is-ancestor <remote> HEAD`**; 拿 `git log -3` 两边并列比必然误判。**push 打印 `old..new`(无 `+`)才是 fast-forward 实证**。例: zcode-PR 误报分叉, 实际本地领先 5 个。
- **推送顺序: 先试直推 fork 再降级** —— git https 时通时不通, 不通且 api 通才走 Git Data API; **API 默认取主邮箱须显式传 noreply**; 之后 `reset --hard fork/<branch>` 对齐。**`git merge-file` 干净 ≠ GitHub 接受合并**(要双父 commit)。例: zarr#4526。见 PLAYBOOK「推送通道」。
- **有 AGENTS.md 即硬约束**(litellm: 分支名无 `/`、行宽 120、禁注释); 「预读」= AGENTS+CONTRIBUTING+`.pre-commit-config` 全套; **改 rst 必跑 `rstwrap <file>`**; **本地 checkout 是 CRLF≠仓库是 CRLF**, diff 整份重写先怀疑换行符。

## 四、验证纪律(全文细则见 PLAYBOOK「2026-11-02 下沉: 验证纪律」)
- 判别力: **撤修复→fail, 恢复→pass**; 竞态类撤代码不便时用同进程撤守卫的对照组(**先存原方法引用再还原**); 不可达防御分支会被覆盖率判失败(bokeh#15476); 跑源码非 site-packages 副本; 跨会话/API 重建的文件不能信"已验证"。**纯净基线 `git restore --source=HEAD --staged --worktree`**。**本地 lint 版本必须对齐仓库 pin**, 否则「本地已格式化」是假绿; 判红属谁比「同一句报错」。例: sqlglot#8869 ruff 0.17.3 绿 / pin 0.15.6 红。
- **兼容性类修复在双版本各跑一遍**(旧=复现/新=回归), 正文写「两环境失败集合逐条同名」。例: vcrpy#1092 urllib3 1.26/2.8, 67→6 failed。
- **判「失败是不是我造成的」比集合不比数量**(`grep '^FAILED'|sort` 后 `comm -13`; markdown#1666 13 vs 15); **端到端要给「修复前/后不同数」**(docling#4849); **基准的「删除行」多半是 EOF 换行规范化**; 用例放进已被 CI 覆盖的既有文件; 改完 `.py` 前跑 `ast.parse`。
- **CI 红先判"是不是我的", 逐 job 判**; **用 `gh pr checks --json state` 统计而非文本 grep —— `CANCELLED`(fail-fast 连带)≠`FAILURE`**(coveragepy#2350 文本 12 fail 实为 1 FAILURE + 11 CANCELLED)。fork PR 无法 `rerun --failed`; **mergify 类失败常是评审门禁**; **同一 sha 同名检查会并存多次重跑, 取 `started_at` 最新者**(any-agent#969 旧 failure 仍在列却已 4 次 success, 按条计数会误判「结论反转」)。**零变化轮的重复回认=比「head sha + 该时间戳」, 两者都没变即免取证**。
- **本地失败先判环境**: 缺 pytest-asyncio/fcntl(Windows)/POSIX 权限位/`/bin/sh` spawn 均非代码问题; 同环境对比基线与补丁失败集合, 同因才判环境。例: psutil 需 `build_ext --inplace`; vcrpy 6 条是 Windows 路径分隔符。

## 五、监控/数据(机制细节见 PLAYBOOK「三次下沉」「调度器机制」「发现层运维」)
- **Actions schedule 极不可靠**(2.9% 命中), 根治=自链 `workflow_dispatch`(班末自触发, cron 退化成重启按钮); 坑与守卫见 PLAYBOOK「Actions 自链」。
- **时间戳先对时区再下结论**: `inbox.py list`、Actions `created_at`、API 全是 **UTC**; 判「积压/停摆」前先 `date -u` 并排打印。例: 把 28 分钟前的投递读成「8 小时积压」= 把观测工具的表示形式当成被测对象状态; 同族=「整份 `QUERY_ERROR` ≠ 无变化」。**计数一律 `grep -c` 全量, 不取 `tail -N` 尾部**(报 3 条 vs 全量 12 条, 且下轮还读同一段尾部→自我复现, 改结论不改取数入口无用)。**同一「0 产出」须分因**: OFF 停摆 vs 池子没货, 处置相反。**OFF 同时停住发现层**(→ 恢复时无积压可清; 机制见 PLAYBOOK)。「零变化」轮仍逐条回认带红项, 记「列几条/核几条」分开写。
- **跟进按阻塞和证据决定**: 无新信息默认等待, 不因到期 ping; 我方引入的失败优先修; behind 不触发同步。**「具体化催询」有效**: 点名谁已批/卡在哪一条 → docling#4849 挂 16 天的 CHANGES_REQUESTED 当天解开; 空催无效; 维护者回「还没想好/等有空看」= 无请求, 不催。
- **关得掉才叫开关**: 判「关没关」只看 `pipeline_switch.py status` 的 `effective`, 不看配置文件写了什么; **只关一层 = 半边开着**。机制见 PLAYBOOK。**开关必须覆盖「写」而不只是「跑」**: 关闭态里留一个「回复评审」等于还开着——回复照样在别人仓库产生通知。例: 2026-11-02 流水线 prompt 原写「OFF 时只做同步和评审响应」, 已改为 OFF 时除 GET 外一律不写。
- **「判过了」不在评论流里 → 必须有台账**(done=判过了含弃因/PR 号=做完了, 每轮清零), 否则每轮重判同一批。详见 PLAYBOOK「三次下沉」。
- 单一事实源=GitHub; 全量盘 PR 用 `gh api "search/issues?q=is:pr+author:inchang-ing+state:open&per_page=100"`(**`gh search prs` 静默返回 0**)。`mergeable_state`: blocked=待门禁/behind=落后/unstable=CI 未绿。
- 维护者先关 issue 再关 PR=裁定不修; **fork PR 的 Actions 常停 `action_required`**=待批准, 非推送失败 —— `gh pr checks` 此时只报 "no checks reported", 判据拉 `actions/runs?head_sha=<sha>`; **rulesets 才是必需检查的唯一事实源**(空=该红不阻塞)。
- **扫「他人新动静」cutoff 用「上次扫描时间」不用自然日 0 点**; 单仓 `query incomplete`、临时文件位置等取数前提见 PLAYBOOK「巡检取数的两个小前提」。
- **AI review bot 的 🟡 项常是真回归**(miloco 两条均成立): 逐条实现+回复+推 commit。
- **拿 GitHub issue 当日志会外溢到别人仓库**: 裸 URL 或裸 `owner/repo#num` 会 cross-reference 并通知全部 watcher, **删评论不回收**。内部日志一律反引号包裹。例: 2026-11-02 43 条评论波及 1269 issue / 108 仓。全文 PLAYBOOK「日志外溢」。
- **外溢面要按字段封闭, 不能只堵 URL**: 一条上报里凡是「别人写的文本」都是入口——URL → **issue 标题** → **labels** 依次被漏过(标题带 `@某人` 真通知到人, 带别仓编号生成引用)。判据: 渲染外部文本时**逐字段**过一遍 `code()`(剥反引号再包, 防提前闭 span), 而不是记得哪个字段有链接就修哪个。同理 commit message 里写别仓 `owner/repo#num` 也外溢(实测 190 个提交里 4 处命中, 3 处指向不存在的 slug 或 code span 内, 1 处指向自有 PR)。**只有 code span 是可靠隔离**; 事后编辑/删除都撤销不了(已删评论仍留 1 条)。
- **上报条目里夹带上游文本会污染去重**: 用「整行搜 `owner/repo#num`」解析自己的台账, 会把标题里出现的编号也记成「已报过」, 之后静默跳过另一条真实 issue。解析必须**锚定行首 + 限定本工具自己的格式**。例: 2026-11-03 `poll_fresh.py`/`inbox.py` 的 `KEY_RE`。

## 六、复盘/池状态(运维细节见 PLAYBOOK「发现层/池状态运维」)
- **七成弃单死因与代码质量无关**(重复/抢先 > 门禁 > 方案被否 > AI 政策 > 自撤)。
- **新 bug 流已饱和**: 23 仓 × 30 天只 3–5 个, 多数被软认领; 策略=维护在飞 + 降星级 500–2000 仓 + 换贡献类型。**唯一稳定收益: 只有跑起来才暴露的缺陷**(无人立 issue 也就无人抢)。
- **维护期产出上限由评审吞吐决定**: 在飞大时正确动作是清红+具体化催询, **不是开新单**(须无竞品 PR 且无自陈补丁)。
- **发现层与决策层分开**, 两层频率差是硬上限(发现 15min / 执行 1h)。轮询禁用全局 search, 按仓 `issues?since=` + `html_url` 去重(细则 PLAYBOOK)。
- **search API 有独立配额(30/min)**: 遇 403 先看 `X-RateLimit-Remaining`, 为 0 才是配额耗尽, 否则隔几秒重试。
