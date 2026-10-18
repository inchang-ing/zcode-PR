# 可验证的贡献记录

一项贡献一个 `records/*.json`，原始证据放在 `evidence/`。本目录和证据应一起纳入 Git、一起备份；不要只保留生成的 Markdown。

## 操作

在仓库根目录运行：

```powershell
python -S tools/contributions.py new owner/repo 123 "问题标题" --pr 456 --problem-type correctness --approach input-validation
python -S tools/contributions.py check
python -S tools/contributions.py render
```

`new` 不覆盖同一 issue 的已有记录。编辑 JSON 后运行 `check`，再运行 `render` 更新根目录 `CONTRIBUTIONS.md`。记录 ID 和文件名稳定，不随标题、结果变化。

这是以单人编辑、脚本串行生成为边界的第一版。脚本写入持有共享锁并原子替换；手工编辑时先完成保存，再运行校验/生成，不同时写同一记录。

`STATE.md` 继续用于旧监控入口的跟踪范围，`pr_state.json` 继续作为唯一 PR 状态缓存。记录中只关联 PR 编号，不复制一份可手改的 OPEN/MERGED 状态。新增贡献目前仍需加入 `STATE.md` 才会被现有监控查询；本工具不自动改变监控范围。

## 字段和证据

- `policy`、`collision`：状态、最后核验时间、结论、来源。默认 `unverified`；改成 `verified` 必须有时间、摘要和来源。结构校验不能代替阅读政策或完成所有撞车检查。
- `verification`：`unverified` 或 `recorded`；后者仅表示 fail→pass 证据字段和日志摘要齐全，不声称工具重新执行过测试。
- `feedback`：维护者原话/事实用 `fact`，自己的理解用 `interpretation`。事实必须附原始评论或评审链接；没有反馈条目不代表维护者没回复，须查看 `checked_at`。
- `outcome`：记录原因及证据，类别为 `unknown / duplicate / scope / tests / other`。非 unknown 必须有原始链接和解释，不能从“关闭”推测拒绝原因。
- `next_actions`：自己的建议待办，不冒充维护者指令。
- `provenance`：导入来源。历史日志摘录只是历史陈述，不自动成为政策、撞车或测试已核验的证明。

来源对象有两种形式：

```json
{"kind": "url", "ref": "https://github.com/owner/repo/pull/456#issuecomment-123"}
```

```json
{"kind": "local", "ref": "contributions/evidence/task-before.log", "sha256": "文件完整 SHA256"}
```

本地文件必须存在且摘要匹配。先检查日志是否含凭证等敏感内容，必要时脱敏，注明脱敏，再计算摘要；不能用摘要证明日志中的结论真实。

```powershell
(Get-FileHash contributions/evidence/task-before.log -Algorithm SHA256).Hash.ToLower()
```

## 完整的修复验证

`verification.case` 是同一个回归用例的稳定标识。`before` 和 `after` 都必须保存以下运行对象：

```json
{
  "commit": "完整的40位提交SHA",
  "command": "python -m pytest tests/test_example.py::test_regression -q",
  "environment": "Python版本、操作系统、依赖锁文件或依赖快照标识",
  "test_case": "tests/test_example.py::test_regression",
  "ran_at": "2026-10-18T12:00:00+00:00",
  "exit_code": 1,
  "result": "regression_failed",
  "log": {"kind": "local", "ref": "contributions/evidence/task-before.log", "sha256": "日志摘要"}
}
```

修复前须是目标回归失败，修复后须退出码 0 且 `result=passed`；环境和用例标识须一致，提交号须不同。依赖安装失败等应记为 `environment_error`，不能凑成 fail→pass。修复前的测试提交应已经包含回归用例，但尚未包含修复。命令可以因工作目录不同而不同，须在日志中说明。

## 统计口径

报告按仓库、问题类型、修复方式展示样本数量及缓存状态。`MERGED/(MERGED+CLOSED)` 只针对有核验时间、无查询错误的已结束样本；OPEN 和未知不进入分母。报告保留缓存时间，不把缓存冒充实时状态。

首批只有三个历史样本，尚不足以比较贡献质量；没有补造维护者反馈、归因或工作时长。后续有证据再补充。校验失败时生成命令退出非零，保留上一份报告，避免将坏数据替换成新台账。
