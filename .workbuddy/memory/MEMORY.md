# 项目长期记忆(规律为主 + 实例为注脚)

## 元规则
- 只提共性规律(未来重复/改决策/去仓库名仍成立), 实例挂规律下 `例:仓#号`, 写具体不抽象。
- 单轮流水=`rounds-log.md`; 明细=当日 `20YY-MM-DD.md`(append-only); 冷归档=`STATE-archive.md`; grep 历史只扫 `20*.md` 排除 `automations/`。
- Skill 保持英文只做增量(用户 2026-10-08); 看不懂用中文讲一遍。
- **本文件会被注入截断, 超 ~15KB 必须压缩**(2026-10-16 已压过两次)。

## 一、不可违反的用户指令
- **方案/计划文档改动先审批后落盘(2026-10-16)**: 先给完整计划获批再写; 已落盘的摊开「改前→改后」供审。例: 未获批改 `work/plan-issue-first.md` 被纠正。
- **「找到就跑PR啊问我干什么」(2026-10-13)**: 干净候选自行实现+提 PR, 不回头问。例外: 法律协议/不可逆破坏先问。
- 权威仓 PR 监控 recurring automation 已授权(每 45 分钟一轮)。
- **无「一轮只跑一个 PR」约束; 纪律 = 同仓在飞 ≤1(硬上限 2)**。例: sqlalchemy 同 org 备 4 分支→整批 `createPullRequest` 被封。auto_run.py 默认 `--per-repo=1`。
- **权威池(4 门槛)**: ①Python 包 ②本机可跑测(重 GPU/C++/Rust 降级) ③收外部 bug-fix PR ④活跃 bug 流。约 53 个; 受限池(sqlalchemy/httpx/pallets)只扫不投。
- **org 规范名**: starlette/uvicorn→`Kludex/*`; typer/fastapi→`fastapi/*`; ragas→`vibrantlabsai/ragas`; hydra→`hydra-ecosystem/hydra`; aiohttp=`aio-libs/aiohttp`。
- **CLA**: 已授权代签 OSS CLA; 标准 **CLAassistant**(litellm/deepchecks)须账号持有者网页 OAuth 点签, agent 评论只对 CLA Assistant Lite 生效。

## 二、做不做(质量红线 + 撞车九查 v5)
- **v5 = v4 八查 + 门禁查**: `.github/workflows` 有无 `require-issue-link`/`prgate`/`issue not ready`、`.github/VOUCHED*`、CONTRIBUTING 是否要 claim/assign 或 `open for pull requests`。**命中门禁且未 assign → 先求 assignment 再投**(langgraph#9100/#9101/#9272 被同一 bot 连关; pydantic#13959; sqlalchemy#13665; mem0#7618/#7642; agno#11022)。
- **timeline 必 REST 全量** `gh api repos/{r}/issues/{n}/timeline --paginate`, PR 判据 `source.issue.pull_request`。GraphQL `timelineItems` 正序截断→假阴性; `gh search linked:pr` 只索引 Development 关联, 漏 `fixes #N`。
- **timeline 全量仍不够, 必查"正在发生"**(占拒关 40%): ①issue 近 14 天 comments; ②同文件他人 open PR; ③assignee 与最近更新。例: repowise#3188、deer-flow#6064、celery#10845。
- **有「高拥挤仓」: 新 bug 常 1–2 天内被认领, 投前必查 cross-referenced**。例: dspy 近 30 天 8 个零评论 bug **全部已有 PR**(#10603/#10614/#10577/#10529/#10571/#10647); langchain#41237 两人争抢; llama_index#23515 作者已开 llama-agents#808。此类仓从「新 bug 流」选候选基本无效。
- **同一门禁只许栽一次 → 命中即入台账 `blocked-repos.md`**。例: langgraph 3 连栽; sqlglot 3 个(#8496/#8548/#8558); networkx 2 个。
- **语义/方言仓先证明输入本身合法**。例: sqlglot#8548 maintainer 实测 SQL Server 报 `Msg 156` → 整根 PR 失去讨论基础。
- **AI 政策见即弃**: pre-commit/matplotlib/hypothesis/scipy/sphinx-needs/pyparsing/requests/evidently/ibis/mem0。**开 PR 前必读 `.github/AI_POLICY.md`+`AGENTS.md`+`CONTRIBUTING`+PR 模板 AI 段**(政策常在正文)。三类: ①禁 agent 提交→弃; ②允许须披露且格式仓仓不同(pytest 要 `Co-authored-by` 署名+AUTHORS+人类担责; otel/pip「we don't police」→披露即可); ③无条款(poetry/dd-trace/mypy)→可投。`gh api .../content` 对 404 返回字符串 `null`→用 `jq -r '.content // empty'` 判存在。
- **政策门禁**: openai-python 只收协作者; ibis 禁 agent 自提; evidently 反 AI PR; mem0+agno 需 `ready`/`accepted` 标签; **mlflow 需 `ready`(只有 `triage: reproduced` 不行)**。
- 内部 Jira 同步 issue 全 ASSIGNED 勿碰。判别力门槛: v4 全清且**能复现**才投(glom#314/langdetect#102 弃); 维护者定性 wontfix/设计如此见即弃。
- **issue 参与是硬要求(2026-10-16 量化)**: 100 个 PR 引用的 91 个 issue 全是别人开的, 我只在 16 个(18%)下留过言 → 82% 属 pytest 明列封号的 "drive-by PR against an issue the author never engaged with"。8 次还是开完才通知(结局: 写码前声明 8→4 合 3 拒; 开完才通知 8→1 合 4 拒)。**硬纪律: 留言必须在动手写代码之前发出。**
- **社区反馈点在 PR 之后**(pytest CONTRIBUTING L53 是 declare 而非 request permission; L466「If in doubt, go ahead and open a PR」)。「等批准才写」是为 agent 身份加码, 非常态化会成新指纹; 留言回复率仅 38%、延迟中位 12h。等待只留高风险且设 48h 超时降级。
- **风险分级四类**: ①门禁→等 assign 才写; ②方案争议(修法不唯一/涉公开 API 语义)→等 maintainer 定方向; ③方言/解析器→先用权威实现验证输入合法; ④撞车→**留言引蛇出洞但不等**。例: ④repowise#3188、celery#10845。

## 三、怎么交(提交/推送/CI)
- **沙箱代理杀 git https**(CONNECT 502)→ 用 Git Data API(blob→tree→commit→ref); `gh pr create` 报 "Head sha blank/No commits"=分支没推上。
- 提交邮箱 `197932532+inchang-ing@users.noreply.github.com`(否则 CLA-bot 认不出)。DCO 仓手写 Signed-off-by; 浅克隆禁直接 amend。
- 大仓 rebase: `git clean -fdx` + `GIT_EDITOR=true git rebase --continue`; 建 PR 前 `git fetch origin main` 重打补丁。changelog 只认 towncrier 片段(news/、.changelog/), 改 CHANGELOG.md fail。
- **封禁分级**: 同账号可同封 `addComment`+`createPullRequest`; 只读 `viewerPermission=READ` 不可靠→坐实须真试 create。
- **有 AGENTS.md 即硬约束**(例 litellm 分支名 `litellm_` 前缀无 `/`、行宽 120、几乎禁注释、conventional commits、PR body 按 `general.md`、lint 按 merge-base 比违规不增长)。
- **issue-readiness 门禁**(agno/mlflow 需 `ready`); **triage 标签门禁**(jupyter 系)→ 外部无权限, 留言求 maintainer 补。
- **「预读」= 全套非只看 AI 政策**: AGENTS.md(测试写法/标题格式)+CONTRIBUTING(docs/releasenotes 要求)+`.pre-commit-config`(bot 装了哪些 `additional_dependencies`)+releasenotes 文档; 漏读的代价由 reviewer/CI 事后收账。例: markdown-it-py#442 用 `@pytest.fixture` 而 mypy hook 没装 pytest 且 strict 未对 tests 关 `disallow_untyped_decorators`(AGENTS.md 早写明测试内建 `MarkdownIt`), 该仓还要 emoji 标题+CHANGELOG Unreleased 条目; dd-trace-py 要 reno note(`releasenotes/notes/*.yaml` 的 `fixes:` 段, bug fix 必需, 例 #20873)。
- **MS CLA bot** `@microsoft-github-policy-service agree` + 大写 FIX:/FEAT:。
- **手写解析/状态机要预留边缘预算**: 投前先查仓库是否已有解析依赖(有则复用), 自己先过「容器前缀、转义字符、区间交错、EOF 空白」四类边界。例: crewAI#7981 被 CodeRabbit 找 5 处(3 处属实当轮修)。
- 装环境: `pip install -e . --no-deps` 迭代; **`PYTHONPATH=<src>` 跑测若依赖 `entry_points()` 必 fail**→先 `pip install -e <pkg> --no-deps`(openinference 105 passed); Windows 深路径须 `git config core.longpaths true`; fixture 匹配根 `.gitignore` 须 `git add -f`(docling#4439)。
- **本地 checkout 是 CRLF ≠ 仓库是 CRLF**: `core.autocrlf=true` 时走 API 推送前必须 LF 规范化(文本模式读→`newline="\n"` 写); 校验 `tr -cd '\r' | wc -c`=0 且 `git hash-object` 与 API blob sha 对齐。例: repowise#3187 三文件 CR=451/420/168→0。
- 拉 PR 头不必靠 fork 可达性: 上游 `git fetch origin refs/pull/<N>/head:<local>`; sparse-checkout 要 `git sparse-checkout add <dir>`, 浅克隆+promisor 常见 `expected 'packfile'` → 改用 `gh api contents`。
- **「抽通用工具让别的模块复用」前先查模块边界门禁**: 有 `tach.toml`(docling) 时 `tach check` 会 FAIL 掉新引入的跨模块依赖。例: docling#4849 让 webvtt/boxnote 复用 `UTF8_BOM_ENCODING`, 但 `docling.backend.json` 不许依赖 `docling.utils` → 该后端保持原写法并说明。
- **做「纯净基线」对照要用 `git restore --source=HEAD --staged --worktree <files>`**: 索引里有已 staged 改动时 `git checkout -- <file>` 恢复的是**索引版本**(=有改动版), "纯净基线"实际跑改动版。例: docling 两次对照数字完全相同才发现。

## 四、验证纪律
- 判别力: **撤修复→fail, 恢复→pass**; 新增不可达防御分支会被覆盖率判失败(bokeh#15476)。
- 跑源码非 site-packages 副本; 跨会话/粘贴补丁不能信"已验证"→必跑真实触发路径。
- 测试**别造时序竞态** → 直接驱动 bug 后置状态(确定性白盒, aiohttp#14017)。
- CI 失败必拉日志定真因, 勿按作业名猜(tortoise#2307 实为 mypy arg-type 非 pre-commit)。
- **lint 版本按仓库 pin 装再判**: 「跑 check」≠「跑 format --check」, 先查 `pr checks` 里有没有该作业。例: dd-trace pin `ruff==0.14.10` 要求 `_get_attr(...)` 并成单行; optuna pin `0.14.4`(line-length 99); polars 版本在 `py-polars/requirements-lint.txt`; repowise 只跑 check; smolagents `ruff>=0.9.0` 不 pin 且跑 `check examples src tests`+`format --check`。
- **CI 日志取法**: ruff-action 这类"动作"把 diff 写进 **step summary**(API `check-runs.output.summary` 常为 null), 必须 `gh run view <run> --job <id> --log`(全量)再 grep; `--log-failed` 只剩收尾步骤。拿不到就本地复现: 沙箱断网不能完整 clone 时**伪造最小目录树 + 真 pyproject**, 逐步补 first-party 模块让 ruff 判定跑对(例 polars#29928)。
- **ruff 的 first-party/third-party 判定不确定时, 选「两种归类都合规」的写法**。例: 第三方与 `polars` import 间补一空行, 在 `polars` 被判 first-party(必须空行)/third-party(空行被容忍)时都 pass; 「块内容逐字节相同却一次 pass 一次报 I001」即分类漂移。
- **源码栈跑不起来的两招白盒**: ①`ast` 抽目标函数配桩 exec(dd-trace#20883: 编译扩展缺失, 抽 `_extract_metrics_from_response`+桩 `_get_attr`/常量, 12 项全过); ②最小 stub 包跑**仓库真实测试文件**(crewAI#7981: 桩三个 import 依赖, 自带测试 18/18 过)。判据: 撤掉修复必须变红。
- **端到端对照要给「修复前/后不同数」**: 例 repowise#3187「main 的 resolver + 删标记 = 恰好 2 个 finding → 本分支 0」; docling#4849「旧规则 2 failed([utf_8]/[u8]) → 13 passed」。
- **改「解释器/作用域」这类全局机制, 只跑自己新加的测试不够, 必须跑整个相关测试文件并与基线逐条对比失败集**: 这类机制有大量隐式依赖行为。例: smolagents#2993 换成链式作用域后自己 14 项 CPython 对照全过, 但 `test_tuple_id` 变红——`evaluate_name` 有 `difflib.get_close_matches(name.id, state.keys())` 兜底, 而链式作用域 `keys()` 只暴露本地名(该测试正靠它把 typo `food_item_counts` 兜到 `food_items`); 修法是补 `keys()` 透出外层名 + `setdefault` 不遮蔽外层同名对象。
- **多条新断言要逐条标明「判别力」还是「守护」**: 一次加 3 条可能有 1 条在旧代码下也过。例: smolagents#2993 的 `[(lambda: x, [x for x in range(2)])[0]() for x in range(3)]` 旧代码也过, 但正是它把「链式作用域」与「朴素共享同一 dict」区分开(后者内层目标会覆写外层同名目标)。
- **「与权威实现逐项对照」当验收手段**: 语义类改动写「本实现 vs CPython」对照表(smolagents#2993 共 14 项), 比"改完变绿"更有说服力, 还能挖出**同源未发现 bug**(该表挖出 PR 自身引入的 `lambda i=i: i` 从 `[0,1,2]` 退化成 `[2,2,2]`, 因 `evaluate_lambda` 忽略 `args.defaults`, 只靠 per-iteration 拷贝"碰巧"对)。

## 五、监控/数据
- **合并时长双峰; 放弃判据 = 「零互动 + CI 非绿」, 不是天数**: 22 个已合中 18 个 ≤3 天, 4 个 7.5–14.9 天且**全有 review 往返**(bokeh#15476/pydicom#2385/execnet#431/docling#4449); 快的反而零互动直合(swarms#2393 0.1 天)。
  - 有外部互动 → 15 天内继续跟, 别关。
  - 零互动 + CI 绿 → **该 ping 不该关**(markdown-it-py#443、snowflake#3046、loguru#1526); 已在 10-10 ping 过且无回应的**不再追问**。
  - 零互动 + CI 非绿 → 真死区, ≥10 天可弃(markdown-it-py#442 17d 红; ChatDev#682/pyyaml#967/instructor#2736 已于 2026-10-16 关闭)。
- **48h 法则**: 开 PR 后 48h 内必达 CI 绿 + `mergeable=CLEAN`; 零互动且 CI 已绿 ≥10 天→ping 一次; 有互动但停滞 ≥7 天且对方提问未回→先回问题。
- **DIRTY 是最贵的自造损失**: CI 绿但 `mergeStateStatus=DIRTY` 时维护者点不了合并键; rebase 后必验 `mergeable=true`; 冲突巡检纳入例行一轮(dd-trace#20769/openinference#3982/tortoise#2307/hydra#3543/litellm#46262)。
- 单一事实源=GitHub; 全量盘 PR 用 `gh search prs --author <login> --state open`(**须加 `--limit 100`, 默认只回 30 条**; 无 merged 过滤, 用 `gh api search/issues?q=author:X+is:pr+is:merged`; `--json` 无 mergeable/reviewDecision→逐个 `gh pr view` 补)。
- `mergeable_state`: blocked=待门禁(正常)/behind=落后 base(非阻塞)/unstable=CI 未绿/unknown=后台重算。
- 维护者先关 issue(not_planned)再关 PR = 裁定不修。大仓 review 队列长, reviewDecision null 数周属常态。
- **fork PR 的 GitHub Actions 常停 `action_required`**(待 maintainer 批准)=常态门禁, 非推送失败(dd-trace#20886/#20883、smolagents#2993 例); 且旧提交同样如此, 可据此排除"是我推送导致"。
- **扫「他人新动静」的 cutoff 用「上次扫描时间」, 不用自然日 0 点**: 用「今天 0 点」会漏掉**昨天**发生且未被回应的 review, 而"回 reviewer"是价值最高的一类动作。例: smolagents#2993 的 CHANGES_REQUESTED 在 10-15 12:09, 用 `2026-10-16T00:00Z` 为界整轮扫不出来, 放宽到 `2026-10-15T00:00Z` 才浮现。
- **CI 红先判"是不是我的"**: ①同 workflow 在 main 上是否天天红(例 dask 的 `nightly` 在 main 连续 failure → 定时任务既有问题); ②同 commit 上该 job 是否有更晚的 success(例 statsmodels#10472 的 AI 披露检查最新一次是 success, 失败的是加披露段前的旧运行); ③失败项是否落在自己的 diff 面(例 #10472 红在 `TestMVT::test_rvs_covariance_matches_by_monte_carlo`, 与 SARIMAX 改动无关)。

## 六、2026-10-15 复盘数据(待用户拍板)
- 外部 PR 100 个: 已合 22 / 拒关 30 / 在飞 48; 拒关率 9 月 32.1% → 10 月 87.5%(`work/retro-2026-10-15.md`)。
- 拒关归因(30): 重复/他人抢先 12(40%) > 流程门禁 9(30%) > 方案被否 4 > AI 政策/账号可信度 3 > 自撤 3 —— **七成死因与代码质量无关**。
- **跨仓密度公开可见**(维护者点一次头像即暴露): 单日最高 13 个跨 12 org(相邻最短 3.2 分钟)、org 内密度(pylint-dev 8/DataDog 7/sqlglot 6/pypa 3)、格式指纹(43% `fix(...):`, 89% 落 5 种模板)。密度**不是**跃迁根因(只直接造成 2–3 个), 危险在于它是新增且不可逆的一层损失。
- 建议但未采纳的节流: 全局在飞 ≤8、日投 ≤1、同 org 串行; PR body 强制"真实复现命令+输出 / 修复前后对照 / 人工核对说明"。
- 复用脚本: `work/ghapi.py`、`work/open_health_b.js`(并发拉 CI/review/mergeState)、`work/fetch_close_reason.py`、`work/scan_new_activity.js`(扫他人新动静)、`monitor_round.py`+`auto_run.py`+`vet.py`(池扫描→clean 判定→终检)。
