# 合并产出调度：首期试运行

目标是增加成功合并数量、减少无效投入。使用现有扫描结果、贡献证据和 PR 缓存；不自动发言、认领、推送或提交 PR。

## 每轮流程

```powershell
python -S tools/monitor_fresh.py
python -S tools/monitor_round.py --pending
python -S tools/monitor_round.py
python -S tools/monitor_oss.py
python -S tools/work_queue.py refresh
```

需要接入云端发现时，先执行 `python -S tools/inbox.py import`；精选扫描和文档扫描也写入相同的待核验收件箱，再运行 `monitor_round.py --pending`。导入只增加本地待核验项，不对远端发言。

默认路径的扫描结束后自动刷新队列；自定义 `--out` 是独立快照，不覆盖主队列。PR 监控后再执行 refresh。打开 `WORK_QUEUE.md`，从上向下选择下一项；默认只展示前 50 项，`refresh --limit 0` 可展开全部；完整任务和过滤原因始终保存在 `work_queue_view.json`。

每轮只运行一次 `monitor_oss.py`，一次获取 PR 状态、评审、合并信息和 CI，并更新状态报告与台账。`monitor_scope.py` 保留为不查 CI 的按需入口，无需在同一轮重复运行。

初始优先级：已确认的小修改 100、已确认合并冲突 90、正式请求修改 85、已确认 CI 待办 80、待核查 CI 70、候选最多 65、方向讨论 20、未分类反馈 15、过期 PR 状态核验 10。候选内排序：明确意图 20、已复现 15、可测试 10、小范围 10、新问题 5、同仓合并经验 5。分值是可解释的初始规则，不是统计概率。待核验和可执行事项分组排序；政策、撞车、意图缺失不能用分数抵消。

首轮用旧缓存生成基线；没有新扫描时间的旧候选全部要求重扫，不伪造核验。自有仓库不进入外部贡献队列及周报。既有规则的并发限制仍有效：队列不是提交许可。

## 少量核验记录

下面使用示例编号，执行时换成真实任务和原始证据链接。`task_state.json` 是持久状态，不要删除它来刷新报告；`work_queue_view.json` 和 Markdown 报告可重新生成。

```powershell
python -S tools/work_queue.py assess owner/repo#123 policy yes --source https://github.com/owner/repo/blob/main/CONTRIBUTING.md --note "已阅读当前贡献及 AI 政策"
python -S tools/work_queue.py assess owner/repo#123 collision yes --source https://github.com/owner/repo/issues/123 --note "已完成 RULES.md 五查，无认领和关联实现" --minutes 5
python -S tools/work_queue.py assess owner/repo#123 intent yes --source https://github.com/owner/repo/issues/123#issuecomment-123 --note "维护者确认期望行为"
python -S tools/work_queue.py stage owner/repo#123 probe --note "开始限时复现"
```

`yes` 表示录入者报告证据检查通过，`no` 表示不通过；CLI 可由 agent 调用，这些记录不证明真人审阅，不得据此填写 human reviewed。系统记录来源、时间、理由，不能代替阅读原文。六个信号分别为 policy、collision、intent、reproduced、testable、small。核验 24 小时后需要刷新；正式修复还必须有 reproduced 和 testable。原始测试日志继续放入贡献记录；具体提交的质量要求见 RULES.md「当前重心」。

测试条件未知时可以限时探路；明确记录 `testable no` 后，候选保持可见，但下一步为延期或退出，不再推荐复现。该否定结论不会随 24 小时过期自动解除；环境改善后用 `assess ... testable yes` 附新依据恢复。系统不会自动改写人工阶段或删除历史。

扫描先检查已有 issue 数据中的仓库限制、必需标签和分配人，再请求时间线及评论。只有通过本地门禁的完整数据才进入联网查重；字段不完整仍保留未知状态，不能视为核验通过。

```powershell
python -S tools/work_queue.py stage owner/repo#123 stopped --note "20 分钟仍无法复现，停止投入" --minutes 20
python -S tools/work_queue.py stage owner/repo#124 deferred --retry-at 2026-10-25T00:00:00Z --note "等待维护者确认"
python -S tools/work_queue.py stage owner/repo#125 fixing --note "复现成功，预计 45 分钟修复" --minutes 15
python -S tools/work_queue.py stage owner/repo#125 submitted --note "已提交 PR，链接记录在 contributions"
```

`--minutes` 是本次新增的实际工时，不是累计数；重复录入会重复累计。停止和已提交任务不会因重新扫描复活。需要继续时显式改为 new/probe；延期到期后重新核验。阶段是工作记录，不能绕过执行前核验。每次操作追加事件，不删除历史。

收件箱的 `inbox.py done owner/repo#123 --note "处理原因"` 同样会隐藏队列中的该任务；队列的 stopped/submitted 也会让收件箱不再推荐它。显式执行 `inbox.py reopen owner/repo#123 --note "新证据"` 或较新的 `work_queue.py stage ... new/probe` 才恢复候选。收件箱、队列、过滤、终检与执行入口均通过 TaskStore 读取同一份状态快照，按最新显式决策判断；仍在执行的任务不会被重开操作覆盖。延期任务到期后恢复核验。

若登记后的视图刷新失败，命令会明确提示状态已保存；修正错误后只运行 `refresh`，不要重复登记同一次工时。

## 统一状态存储与迁移

根目录 `task_state.json` 是任务状态的唯一写入位置，版本号为 1。文件内保留派发、收件箱处理、队列三个分区，因为它们分别记录执行结果、处理决定和核验/工时历史；PR 的反馈确认、证据及事件列表也完整保留。一次修改只在持有统一文件锁时重新读取、校验并原子保存，旧快照不能覆盖其它会话的新记录。

升级时先结束正在运行的旧版本机流水线进程，换用新版代码，然后执行：

```powershell
python -S tools/task_state.py migrate
python -S tools/work_queue.py refresh
```

迁移会同时锁定旧 `dispatched.json`、`tools/inbox_handled.json`、`work_queue.json`，校验后将原始字节和清单备份到 `task_state.backups/<唯一编号>/`，再原子生成新文件。旧文件保留原样；重复运行迁移不会重复导入或覆盖后续记录。仅查看状态不会触发迁移；未显式迁移时，第一次状态写入也会执行相同迁移流程。

迁移后的入口只读取新文件，并核对旧文件的 SHA256。如果旧程序或手工编辑又改变了旧文件，会报错并停止，需先停止旧写入方、检查差异，再决定如何补录；不能通过删除新文件、修改指纹或重跑旧迁移来忽略差异。损坏或不支持版本的统一文件也不会回退到旧文件继续执行。

需要退回旧版程序时，应先停止所有本机状态写入，并导出**最新**状态到一个尚不存在的目录：

```powershell
python -S tools/task_state.py export-legacy .tmp/task-state-rollback-new
```

导出不会修改当前状态。核对导出后，恢复旧版程序，将导出的三份文件放回其原路径，并将当前 `task_state.json` 单独归档，最后才恢复运行。迁移前备份仅用于恢复当时原件；迁移后已产生新记录时，应使用上述最新导出，避免丢掉新记录。该回退过程应在停机期间完成，不能让新旧程序混写。

认领凭证 `session_claims.json`、发现消费记录 `discovery_state.json`、评论缓存和 `pr_state.json` 保持各自用途，不属于这三份任务记录的迁移范围。GitHub 仍只扫描和通知，本机负责实际任务。

## PR 反馈调度

```powershell
python -S tools/work_queue.py pr-action owner/repo#456 small_fix --source https://github.com/owner/repo/pull/456#issuecomment-123 --note "维护者仅要求补一个边界测试"
python -S tools/work_queue.py pr-action owner/repo#457 discussion --source https://github.com/owner/repo/pull/457#issuecomment-124 --note "方向争议，限时分析"
python -S tools/work_queue.py pr-action owner/repo#458 wait --source https://github.com/owner/repo/pull/458 --note "暂无人工修改请求，继续等待"
```

分类支持 small_fix、ci、discussion、wait、done。自动发现使用 CHANGES_REQUESTED 状态、当前提交的具体 CI 结果和已有贡献反馈；评审者身份须读原文确认，不推断为真人。所有分类绑定具体观测结果及本地贡献反馈内容，新增或修改反馈后重新分类；仅刷新核验时间或调整反馈顺序不改变已有判断。没有明确分类的自然语言反馈需读原文。小修改完成并验证后记 done，避免重复推荐。policy_hold 表示已知对外沟通限制：可准备本地材料和只读观察，不自动发表评论或推送跟进。

旧版确认没有绑定本地反馈内容，升级后需重新分类一次，已有判断及操作历史仍保留。

## 一周后复盘

`WEEKLY_CONTRIBUTIONS.md` 是滚动七天统计：按真实提交日期分批，等待不计失败，合并日期缺失单列；台账导入时间和 updatedAt 均不能替代提交/合并日期。monitor_oss 会采集这些日期，旧记录需重新查询或使用已保存的原始 GitHub 证据补齐。

首期只显示已记录工时，不把不完整工时算作每个合并成本。周报范围是当前跟踪缓存，不是账号全量；少量样本不推导仓库合并概率。重点检查：推荐误报、无法复现的耗时、重复劳动、人工反馈处理情况，以及随后实际合并的数量。

这是手动轮次试运行，未配置后台定时任务。试运行七天后再决定调整分值、扩展反馈采集或集中投入哪些仓库。

## 2026-10-21 数据流修正

增量监控先把新 issue 写入 `tools/fresh_candidates.json`，再推进已见记录和扫描时间；写入失败不会吞掉本轮发现。`--init` 仍仅建立基线，不导入历史问题。
`monitor_round.py --pending` 按编号核验收件箱中的 issue，复用正文、评论、时间线和共享政策检查。issue、评论或时间线检查失败的精确候选会保留，可再次运行 `--pending`；同仓库其他已完成的候选独立处理。明确通过或淘汰后才移出收件箱。自定义 `--out` 仅生成检查快照，不消耗主收件箱。
精确扫描先读取共享处理结论：已处理、已提交或延期未到期的任务不调用 GitHub，仍保留原记录；显式重开或到期后恢复。扫描锁在联网前获取，避免重叠扫描重复查询；收件箱锁仅用于读取快照和合并结果，联网期间允许增量写入。新到条目和期间被修改的条目不会被旧扫描结果清除。
普通扫描只替换成功仓库的候选；失败仓库保留旧项并标记未知，未扫描仓库保持原状。待核验项在队列可见，但不能直接执行。
PR 的所有分类绑定更新时间、评审决定、提交 SHA、是否存在已确认合并冲突和具体 CI 检查指纹。新出现的 `CONFLICTING` 会使旧 wait/done 失效并重新进入队列；`UNKNOWN` 不判为冲突，旧版无冲突确认继续有效。指纹包含检查名称、运行标识、状态和结果，失败数量相同但失败项改变也会重新提示。CI 单独保存对应提交和查询时间；缺少绑定、提交已改变或观测过期时要求运行 `monitor_oss.py`，旧绿色 CI 不能证明当前提交已通过。明确查询到没有检查与尚未查询分开处理；旧缓存和旧确认需刷新后重新分类。
新增本地门禁的来源、观察日期和复核条件见 `repository_policy.py` 的 POLICY_EVIDENCE。frappe/geopandas 是待人工核验的暂缓门禁，不宣称它们永久禁止贡献；确认资格或方案共识后再更新配置。dbt 的 CLA/CI 步骤仍按仓库要求办理，不当作永久禁投。

候选 `kind` 支持 bug、docs、small_fix、tooling，旧记录按 bug 读取。贡献类型用于正确筛选和分组统计，不能生成政策、意图或测试通过的证明。文档类的 reproduced/testable 核验应写明原说明如何出错、如何通过真实示例、渲染或链接检查确认修正。

## 每次提交与返工前

完成最终提交和相关测试后，运行 `tools/quality_check.py prepare` 保存实际正文并初始化未核验项，再填入逐条验证声明、未验证范围与反馈处理，运行 `check`。命令和字段见 [提交前检查说明](contributions/README.md#提交前与返工检查)。代码、正文或反馈改变后重新准备和检查；队列的 ready 和 done 均不能替代此检查。

## 结构调整后的恢复方式

- 完成的来源版本保存在 `tools/discovery_state.json`。重复导入或收件箱删除失败不会再次查询；有新证据时使用 `inbox.py reopen ... --note ...`，不要靠删除状态文件重试。
- 云端评论在本地按更新时间增量缓存，优先解析版本化事件；损坏的新格式直接报错，不退回猜测展示文本。
- 贡献记录异常单独列在工作队列中，相关 PR 暂不可就绪，其他任务继续展示。队列不重新读取全部历史测试日志，提交仍需完整 `quality_check`。
- 扫描成功但报表刷新失败会提示“候选扫描已保存”并返回 2；运行 `work_queue.py refresh` 恢复视图，不必重新扫描。
- 会话认领返回 token，后续 `--release` / `--renew` 都需 `--token <token>`。没有凭证的历史认领保留至到期，不能由另一会话释放。
