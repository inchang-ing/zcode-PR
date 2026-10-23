# 合并产出调度：首期试运行

目标是增加成功合并数量、减少无效投入。使用现有扫描结果、贡献证据和 PR 缓存；不自动发言、认领、推送或提交 PR。

## 每轮流程

```powershell
python -S tools/monitor_fresh.py
python -S tools/monitor_round.py --pending
python -S tools/monitor_round.py
python -S tools/monitor_scope.py
python -S tools/monitor_oss.py
python -S tools/work_queue.py refresh
```

默认路径的扫描结束后自动刷新队列；自定义 `--out` 是独立快照，不覆盖主队列。PR 监控后再执行 refresh。打开 `WORK_QUEUE.md`，从上向下选择下一项；完整过滤原因保存在 `work_queue_view.json`。

初始优先级：已确认的小修改 100、正式请求修改 85、已确认 CI 待办 80、待核查 CI 70、候选最多 65、方向讨论 20、未分类反馈 15、过期 PR 状态核验 10。候选内排序：明确意图 20、已复现 15、可测试 10、小范围 10、新问题 5、同仓合并经验 5。分值是可解释的初始规则，不是统计概率。待核验和可执行事项分组排序；政策、撞车、意图缺失不能用分数抵消。

首轮用旧缓存生成基线；没有新扫描时间的旧候选全部要求重扫，不伪造核验。自有仓库不进入外部贡献队列及周报。既有规则的并发限制仍有效：队列不是提交许可。

## 少量核验记录

下面使用示例编号，执行时换成真实任务和原始证据链接。`work_queue.json` 是持久状态，不要删除它来刷新报告。

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

## PR 反馈调度

```powershell
python -S tools/work_queue.py pr-action owner/repo#456 small_fix --source https://github.com/owner/repo/pull/456#issuecomment-123 --note "维护者仅要求补一个边界测试"
python -S tools/work_queue.py pr-action owner/repo#457 discussion --source https://github.com/owner/repo/pull/457#issuecomment-124 --note "方向争议，限时分析"
python -S tools/work_queue.py pr-action owner/repo#458 wait --source https://github.com/owner/repo/pull/458 --note "暂无人工修改请求，继续等待"
```

分类支持 small_fix、ci、discussion、wait、done。自动发现使用 CHANGES_REQUESTED 状态、当前提交的具体 CI 结果和已有贡献反馈；评审者身份须读原文确认，不推断为真人。所有分类绑定具体观测结果，变化后重新分类；相同观测保留已经录入的判断。没有明确分类的自然语言反馈需读原文。小修改完成并验证后记 done，避免重复推荐。policy_hold 表示已知对外沟通限制：可准备本地材料和只读观察，不自动发表评论或推送跟进。

## 一周后复盘

`WEEKLY_CONTRIBUTIONS.md` 是滚动七天统计：按真实提交日期分批，等待不计失败，合并日期缺失单列；台账导入时间和 updatedAt 均不能替代提交/合并日期。新版 monitor_scope 会采集这些日期，旧记录需重新查询或使用已保存的原始 GitHub 证据补齐。

首期只显示已记录工时，不把不完整工时算作每个合并成本。周报范围是当前跟踪缓存，不是账号全量；少量样本不推导仓库合并概率。重点检查：推荐误报、无法复现的耗时、重复劳动、人工反馈处理情况，以及随后实际合并的数量。

这是手动轮次试运行，未配置后台定时任务。试运行七天后再决定调整分值、扩展反馈采集或集中投入哪些仓库。

## 2026-10-21 数据流修正

增量监控先把新 issue 写入 `tools/fresh_candidates.json`，再推进已见记录和扫描时间；写入失败不会吞掉本轮发现。`--init` 仍仅建立基线，不导入历史问题。
`monitor_round.py --pending` 按编号核验收件箱中的 issue，复用正文、评论、时间线和共享政策检查。issue、评论或时间线检查失败的精确候选会保留，可再次运行 `--pending`；同仓库其他已完成的候选独立处理。明确通过或淘汰后才移出收件箱。自定义 `--out` 仅生成检查快照，不消耗主收件箱。
普通扫描只替换成功仓库的候选；失败仓库保留旧项并标记未知，未扫描仓库保持原状。待核验项在队列可见，但不能直接执行。
PR 的所有分类绑定更新时间、评审决定、提交 SHA 和具体 CI 检查指纹。指纹包含检查名称、运行标识、状态和结果，失败数量相同但失败项改变也会重新提示。CI 单独保存对应提交和查询时间；缺少绑定、提交已改变或观测过期时要求运行 `monitor_oss.py`，旧绿色 CI 不能证明当前提交已通过。明确查询到没有检查与尚未查询分开处理；旧缓存和旧确认需刷新后重新分类。
新增本地门禁的来源、观察日期和复核条件见 `repository_policy.py` 的 POLICY_EVIDENCE。frappe/geopandas 是待人工核验的暂缓门禁，不宣称它们永久禁止贡献；确认资格或方案共识后再更新配置。dbt 的 CLA/CI 步骤仍按仓库要求办理，不当作永久禁投。

## 每次提交与返工前

完成最终提交和相关测试后，运行 `tools/quality_check.py prepare` 保存实际正文并初始化未核验项，再填入逐条验证声明、未验证范围与反馈处理，运行 `check`。命令和字段见 [提交前检查说明](contributions/README.md#提交前与返工检查)。代码、正文或反馈改变后重新准备和检查；队列的 ready 和 done 均不能替代此检查。
