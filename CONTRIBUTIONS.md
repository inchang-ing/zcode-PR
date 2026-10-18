# 贡献记录

生成时间：2026-10-18T14:26:44+00:00

由 contributions/records/*.json 生成，请勿手改。仅覆盖已导入样本，不代表全部贡献。
PR 状态只读取 pr_state.json 缓存，展示最后核验时间；未联网更新。
测试“证据齐全”指记录字段和本地日志摘要通过校验，不代表本次重新执行测试或审核日志语义。

| 贡献 | 问题类型 / 修复方式 | 缓存状态 / 核验时间 | 政策 / 撞车 | 测试证据 |
| --- | --- | --- | --- | --- |
| [bashtage--linearmodels--issue-768](#bashtage--linearmodels--issue-768) | argument-validation / explicit-error | OPEN / 2026-10-18T05:51:05+00:00 | unverified / unverified | unverified |
| [bashtage--linearmodels--issue-823](#bashtage--linearmodels--issue-823) | numerical-stability / column-normalization | OPEN / 2026-10-18T05:51:06+00:00 | unverified / unverified | unverified |
| [traceloop--openllmetry--issue-4630](#traceloop--openllmetry--issue-4630) | error-handling / check-return-value | OPEN / 2026-10-18T05:52:18+00:00 | unverified / unverified | unverified |

## 样本统计

unknown 表示尚未核验；未结束的 PR 不计入已结束样本分母。
本表按缓存统计，不据此自动推荐仓库；小样本不能推断贡献质量。


### 按仓库

| 分组 | 样本 | MERGED | CLOSED | OPEN | 未知/查询失败 | 已结束样本合并比 |
| --- | --- | --- | --- | --- | --- | --- |
| bashtage/linearmodels | 2 | 0 | 0 | 2 | 0 | 不适用 |
| traceloop/openllmetry | 1 | 0 | 0 | 1 | 0 | 不适用 |

### 按问题类型

| 分组 | 样本 | MERGED | CLOSED | OPEN | 未知/查询失败 | 已结束样本合并比 |
| --- | --- | --- | --- | --- | --- | --- |
| argument-validation | 1 | 0 | 0 | 1 | 0 | 不适用 |
| error-handling | 1 | 0 | 0 | 1 | 0 | 不适用 |
| numerical-stability | 1 | 0 | 0 | 1 | 0 | 不适用 |

### 按修复方式

| 分组 | 样本 | MERGED | CLOSED | OPEN | 未知/查询失败 | 已结束样本合并比 |
| --- | --- | --- | --- | --- | --- | --- |
| check-return-value | 1 | 0 | 0 | 1 | 0 | 不适用 |
| column-normalization | 1 | 0 | 0 | 1 | 0 | 不适用 |
| explicit-error | 1 | 0 | 0 | 1 | 0 | 不适用 |

## 任务详情

## bashtage--linearmodels--issue-768

预测接口静默忽略输出选项

[Issue](https://github.com/bashtage/linearmodels/issues/768) · [PR](https://github.com/bashtage/linearmodels/pull/849)

导入依据：[来源1](contributions/evidence/bashtage--linearmodels--issue-768-history.txt)

**政策核验**：未核验；时间：未记录。尚未核验当时的仓库政策原文；历史日志不能替代政策来源。 无

**撞车核验**：未核验；时间：未记录。历史日志记录了无人认领等判断；缺少当时完整查询结果和精确核验时间。 [来源1](contributions/evidence/bashtage--linearmodels--issue-768-history.txt)

**测试**：未核验。历史日志记载 panel 套件 7061 passed / 73 skipped / 47 xfailed；没有导入原始执行日志、完整提交号和环境，未核验 fail→pass。

**维护者反馈**：最后核验 未记录。
尚未录入反馈，不等于维护者没有回复。

**结果归因**：unknown。 无

**建议待办（非维护者指令）**：

- 核验当前 PR 状态和维护者反馈并保存来源。
- 补齐政策来源、撞车证据与修复前后测试日志；找不到的证据保持未核验。

## bashtage--linearmodels--issue-823

工具变量量纲差异导致误判秩亏

[Issue](https://github.com/bashtage/linearmodels/issues/823) · [PR](https://github.com/bashtage/linearmodels/pull/850)

导入依据：[来源1](contributions/evidence/bashtage--linearmodels--issue-823-history.txt)

**政策核验**：未核验；时间：未记录。尚未核验当时的仓库政策原文；历史日志不能替代政策来源。 无

**撞车核验**：未核验；时间：未记录。历史日志记录了无人认领等判断；缺少当时完整查询结果和精确核验时间。 [来源1](contributions/evidence/bashtage--linearmodels--issue-823-history.txt)

**测试**：未核验。历史日志记载 IV 套件 9522 passed / 2400 skipped；没有导入原始执行日志、完整提交号和环境，未核验 fail→pass。

**维护者反馈**：最后核验 未记录。
尚未录入反馈，不等于维护者没有回复。

**结果归因**：unknown。 无

**建议待办（非维护者指令）**：

- 核验当前 PR 状态和维护者反馈并保存来源。
- 补齐政策来源、撞车证据与修复前后测试日志；找不到的证据保持未核验。

## traceloop--openllmetry--issue-4630

远程删除失败仍修改本地数据

[Issue](https://github.com/traceloop/openllmetry/issues/4630) · [PR](https://github.com/traceloop/openllmetry/pull/4633)

导入依据：[来源1](contributions/evidence/traceloop--openllmetry--issue-4630-history.txt)

**政策核验**：未核验；时间：未记录。尚未核验当时的仓库政策原文；历史日志不能替代政策来源。 无

**撞车核验**：未核验；时间：未记录。历史日志记录了无人认领等判断；缺少当时完整查询结果和精确核验时间。 [来源1](contributions/evidence/traceloop--openllmetry--issue-4630-history.txt)

**测试**：未核验。历史日志声称新增删除失败用例修复前 2 failed、修复后 2 passed；没有导入原始日志、完整提交号和环境，不能据此标为证据齐全。

**维护者反馈**：最后核验 未记录。
尚未录入反馈，不等于维护者没有回复。

**结果归因**：unknown。 无

**建议待办（非维护者指令）**：

- 核验当前 PR 状态和维护者反馈并保存来源。
- 补齐政策来源、撞车证据与修复前后测试日志；找不到的证据保持未核验。
- 历史日志提到 CLA 待签，需重新核验；不能由 agent 代签。
