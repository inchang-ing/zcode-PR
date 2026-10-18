# 贡献记录

生成时间：2026-10-18T14:41:51+00:00

由 contributions/records/*.json 生成，请勿手改。仅覆盖已导入样本，不代表全部贡献。
PR 状态只读取 pr_state.json 缓存，展示最后核验时间；未联网更新。
生成器只校验测试证据字段和日志摘要；是否补做、何时执行，以任务说明和运行时间为准，不自动审核日志语义。

| 贡献 | 问题类型 / 修复方式 | 缓存状态 / 核验时间 | 政策 / 撞车 | 测试证据 |
| --- | --- | --- | --- | --- |
| [bashtage--linearmodels--issue-768](#bashtage--linearmodels--issue-768) | argument-validation / explicit-error | MERGED / 2026-10-18T14:36:25.963790+00:00 | unverified / unverified | unverified |
| [bashtage--linearmodels--issue-823](#bashtage--linearmodels--issue-823) | numerical-stability / column-normalization | OPEN / 2026-10-18T14:36:25.828076+00:00 | unverified / unverified | unverified |
| [traceloop--openllmetry--issue-4630](#traceloop--openllmetry--issue-4630) | error-handling / check-return-value | OPEN / 2026-10-18T14:36:25.669274+00:00 | unverified / unverified | recorded |

## 样本统计

unknown 表示尚未核验；未结束的 PR 不计入已结束样本分母。
本表按缓存统计，不据此自动推荐仓库；小样本不能推断贡献质量。


### 按仓库

| 分组 | 样本 | MERGED | CLOSED | OPEN | 未知/查询失败 | 已结束样本合并比 |
| --- | --- | --- | --- | --- | --- | --- |
| bashtage/linearmodels | 2 | 1 | 0 | 1 | 0 | 1/1 |
| traceloop/openllmetry | 1 | 0 | 0 | 1 | 0 | 不适用 |

### 按问题类型

| 分组 | 样本 | MERGED | CLOSED | OPEN | 未知/查询失败 | 已结束样本合并比 |
| --- | --- | --- | --- | --- | --- | --- |
| argument-validation | 1 | 1 | 0 | 0 | 0 | 1/1 |
| error-handling | 1 | 0 | 0 | 1 | 0 | 不适用 |
| numerical-stability | 1 | 0 | 0 | 1 | 0 | 不适用 |

### 按修复方式

| 分组 | 样本 | MERGED | CLOSED | OPEN | 未知/查询失败 | 已结束样本合并比 |
| --- | --- | --- | --- | --- | --- | --- |
| check-return-value | 1 | 0 | 0 | 1 | 0 | 不适用 |
| column-normalization | 1 | 0 | 0 | 1 | 0 | 不适用 |
| explicit-error | 1 | 1 | 0 | 0 | 0 | 1/1 |

## 任务详情

## bashtage--linearmodels--issue-768

预测接口静默忽略输出选项

[Issue](https://github.com/bashtage/linearmodels/issues/768) · [PR](https://github.com/bashtage/linearmodels/pull/849)

导入依据：[来源1](contributions/evidence/bashtage--linearmodels--issue-768-history.txt)、[来源2](contributions/evidence/bashtage--linearmodels--pr-849--github-20261018T143619Z.json)

**政策核验**：未核验；时间：未记录。尚未核验当时的仓库政策原文；历史日志不能替代政策来源。 无

**撞车核验**：未核验；时间：未记录。历史日志记录了无人认领等判断；缺少当时完整查询结果和精确核验时间。 [来源1](contributions/evidence/bashtage--linearmodels--issue-768-history.txt)

**测试**：未核验。历史日志记载 panel 套件 7061 passed / 73 skipped / 47 xfailed；没有导入原始执行日志、完整提交号和环境，未核验 fail→pass。

**维护者反馈**：最后核验 2026-10-18T14:36:25.963790+00:00。
- 事实：维护者 bashtage 留言“Thanks. LGTM.”；PR 已合并。 （2026-10-18T14:12:00Z）[来源1](https://github.com/bashtage/linearmodels/pull/849#issuecomment-6250914406)、[来源2](contributions/evidence/bashtage--linearmodels--pr-849--github-20261018T143619Z.json)

**结果归因**：other。已合并，维护者明确表示 LGTM；只记录接受事实，不推断合并的因果因素。 [来源1](https://github.com/bashtage/linearmodels/pull/849)、[来源2](contributions/evidence/bashtage--linearmodels--pr-849--github-20261018T143619Z.json)

**建议待办（非维护者指令）**：

- 归档为已接受样本；原始测试证据仍待补齐，不因合并自动标记已验证。

## bashtage--linearmodels--issue-823

工具变量量纲差异导致误判秩亏

[Issue](https://github.com/bashtage/linearmodels/issues/823) · [PR](https://github.com/bashtage/linearmodels/pull/850)

导入依据：[来源1](contributions/evidence/bashtage--linearmodels--issue-823-history.txt)、[来源2](contributions/evidence/bashtage--linearmodels--pr-850--github-20261018T143619Z.json)

**政策核验**：未核验；时间：未记录。尚未核验当时的仓库政策原文；历史日志不能替代政策来源。 无

**撞车核验**：未核验；时间：未记录。历史日志记录了无人认领等判断；缺少当时完整查询结果和精确核验时间。 [来源1](contributions/evidence/bashtage--linearmodels--issue-823-history.txt)

**测试**：未核验。历史日志记载 IV 套件 9522 passed / 2400 skipped；没有导入原始执行日志、完整提交号和环境，未核验 fail→pass。

**维护者反馈**：最后核验 2026-10-18T14:36:25.828076+00:00。
- 事实：维护者 bashtage 质疑归一化秩检查：回归仍使用原始列尺度，原尺度秩检查可能在保护用户免受数值问题影响；询问我们的看法。 （2026-10-18T14:08:32Z）[来源1](https://github.com/bashtage/linearmodels/pull/850#issuecomment-6250879385)、[来源2](contributions/evidence/bashtage--linearmodels--pr-850--github-20261018T143619Z.json)

**结果归因**：unknown。PR 仍开放；维护者提出设计疑问，尚不能记为拒绝或关闭。 [来源1](contributions/evidence/bashtage--linearmodels--pr-850--github-20261018T143619Z.json)

**建议待办（非维护者指令）**：

- 先分析维护者对原始尺度秩检查的疑问，形成数值稳定性依据和答复草稿；本次不发送评论或修改PR。
- 补齐当时政策核验、撞车及测试证据。

## traceloop--openllmetry--issue-4630

远程删除失败仍修改本地数据

[Issue](https://github.com/traceloop/openllmetry/issues/4630) · [PR](https://github.com/traceloop/openllmetry/pull/4633)

导入依据：[来源1](contributions/evidence/traceloop--openllmetry--issue-4630-history.txt)、[来源2](contributions/evidence/traceloop--openllmetry--pr-4633--github-20261018T143619Z.json)、[来源3](contributions/evidence/openllmetry-4633-after.log)、[来源4](contributions/evidence/openllmetry-4633-before.log)、[来源5](contributions/evidence/openllmetry-4633-environment.json)、[来源6](contributions/evidence/openllmetry-4633-production-fix.patch)、[来源7](contributions/evidence/openllmetry-4633-reverification-setup.json)、[来源8](contributions/evidence/openllmetry-4633-reverification.md)、[来源9](contributions/evidence/openllmetry-4633-runs.json)、[来源10](contributions/evidence/openllmetry-4633-source-proof.json)、[来源11](contributions/evidence/openllmetry-4633-verification.bundle)

**政策核验**：未核验；时间：未记录。尚未核验当时的仓库政策原文；历史日志不能替代政策来源。 无

**撞车核验**：未核验；时间：未记录。历史日志记录了无人认领等判断；缺少当时完整查询结果和精确核验时间。 [来源1](contributions/evidence/traceloop--openllmetry--issue-4630-history.txt)

**测试**：已记录 fail→pass 证据。2026-10-18 补做验证：原 PR 的同一份两条用例在原 base 加测试的隔离 SDK 快照上 2 failed（DID NOT RAISE），加入原修复后 2 passed。原仓为浅克隆，使用独立验证提交而非线上提交；165 个 SDK 文件与原版本在统一 CRLF/LF 后一致。环境 CPython 3.12.4；仅验证目标用例，未跑完整套件。详见补做说明、源码核对及 bundle。

- before: commit=9bf151cc60017bfef7bd3dc047db3035c7dc2831；环境=CPython 3.12.4 Windows; contributions/evidence/openllmetry-4633-environment.json SHA256=6b61dc0eaccda6a85e49a0991eaaf1d1747056bd0ea3faf2692081a4c0788a82；命令=E:\zcode-PR\.venv312\Scripts\python.exe -B -c "from pathlib import Path; import traceloop.sdk.datasets.column as col; import traceloop.sdk.datasets.row as row; import pytest; print('COLUMN_SOURCE='+str(Path(col.__file__).resolve()),flush=True); print('ROW_SOURCE='+str(Path(row.__file__).resolve()),flush=True); assert Path(col.__file__).resolve()==Path('traceloop/sdk/datasets/column.py').resolve(); assert Path(row.__file__).resolve()==Path('traceloop/sdk/datasets/row.py').resolve(); raise SystemExit(pytest.main(['tests/datasets/test_delete_failure.py','-q','-p','no:cacheprovider']))"；退出码=1；结果=regression_failed；时间=2026-10-18T14:39:35.927864+00:00；[来源1](contributions/evidence/openllmetry-4633-before.log)

- after: commit=d035ea8bb22ef54d4fec01516df0e131a6500b08；环境=CPython 3.12.4 Windows; contributions/evidence/openllmetry-4633-environment.json SHA256=6b61dc0eaccda6a85e49a0991eaaf1d1747056bd0ea3faf2692081a4c0788a82；命令=E:\zcode-PR\.venv312\Scripts\python.exe -B -c "from pathlib import Path; import traceloop.sdk.datasets.column as col; import traceloop.sdk.datasets.row as row; import pytest; print('COLUMN_SOURCE='+str(Path(col.__file__).resolve()),flush=True); print('ROW_SOURCE='+str(Path(row.__file__).resolve()),flush=True); assert Path(col.__file__).resolve()==Path('traceloop/sdk/datasets/column.py').resolve(); assert Path(row.__file__).resolve()==Path('traceloop/sdk/datasets/row.py').resolve(); raise SystemExit(pytest.main(['tests/datasets/test_delete_failure.py','-q','-p','no:cacheprovider']))"；退出码=0；结果=passed；时间=2026-10-18T14:39:41.273526+00:00；[来源1](contributions/evidence/openllmetry-4633-after.log)

**维护者反馈**：最后核验 2026-10-18T14:36:25.669274+00:00。
- 事实：CLAassistant（机器人）确认所有提交者已签署 CLA；当前提交的 license/cla 状态为 success，历史待签记录已过时。 （2026-10-18T07:54:08Z）[来源1](https://github.com/traceloop/openllmetry/pull/4633#issuecomment-6246212617)、[来源2](contributions/evidence/traceloop--openllmetry--pr-4633--github-20261018T143619Z.json)
- 事实：CodeRabbit（自动评审）没有生成可操作的代码评论；其报告另有 docstring coverage 33.33% 低于80%的警告，不代表人类维护者已批准。 （2026-10-18T05:50:29Z）[来源1](https://github.com/traceloop/openllmetry/pull/4633#issuecomment-6246214428)、[来源2](contributions/evidence/traceloop--openllmetry--pr-4633--github-20261018T143619Z.json)

**结果归因**：unknown。 无

**建议待办（非维护者指令）**：

- 等待人类维护者评审；CLA 已通过，无需再提醒签署。
- CodeRabbit 提示文档字符串覆盖不足；先区分机器人建议与仓库硬门禁，再决定是否处理。
- 当时的政策与撞车原始证据仍缺失，保持未核验；补做测试不代替这些核验。
