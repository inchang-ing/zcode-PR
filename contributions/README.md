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
- `kind`：`bug / docs / small_fix / tooling`，缺失时按 bug 兼容。`new --kind docs` 可创建文档记录；类型不改变仓库准入与撞车要求。
- `verification`：`unverified` 或 `recorded`；后者仅表示所选验证方式的证据字段和日志摘要齐全，不声称工具重新执行过测试。默认 `method=regression` 使用 fail→pass；纯文档可用下述 documentation 方式。
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
  "scope": "project",
  "log": {"kind": "local", "ref": "contributions/evidence/task-before.log", "sha256": "日志摘要"}
}
```

修复前须是目标回归失败，修复后须退出码 0 且 `result=passed`；环境和用例标识须一致，提交号须不同。依赖安装失败等应记为 `environment_error`，不能凑成 fail→pass。修复前的测试提交应已经包含回归用例，但尚未包含修复。命令可以因工作目录不同而不同，须在日志中说明。

## 纯文档验证

`new --kind docs` 初始化 `verification.method=documentation`。记录 `base_commit`（PR 完整改动所基于的完整提交 SHA）、`summary`（原说明的问题与确认依据）、`case` 和成功的 `after` 运行。after 仍需命令、环境、时间、用例、当前提交 SHA 及原始日志，scope 可为 `documentation` 或 `project`；before 可为空，无需人为制造失败测试。

实际运行相关示例、文档构建、渲染或链接检查，选择能证明修正的方式。提交检查要求基线是当前 HEAD 的祖先，并检查整个 `base_commit..HEAD`：仅允许 `.md/.markdown/.rst/.txt/.adoc/.mdx` 文件，且必须存在改动；requirements/constraints 清单、CMakeLists.txt 以及代码重命名为文档均不能走此路径。修改 Python docstring、可执行示例、CI 或工具链仍使用 regression 方式与前后对照证据，不能仅改 kind 绕过回归验证。基线必须覆盖整个 PR，工具不会替录入者从远端确认 PR 基线。

## 提交前与返工检查

`quality_check.py` 复用本记录与日志，离线检查准备提交的具体版本。首次提交和每次评审返工使用相同流程。先完成最终 Git 提交、真实入口测试、政策和撞车核验；已有 PR 还须刷新原始反馈并逐项录入事实。远端配置中应包含记录仓库（通常为 upstream），工作区须干净，包括未跟踪文件。

```powershell
python -S tools/quality_check.py prepare owner--repo--issue-123 --checkout E:/zcode-PR/work/repo --body E:/zcode-PR/work/pr-body.md
# 编辑 contributions/records/owner--repo--issue-123.json 的 submission
python -S tools/quality_check.py check owner--repo--issue-123 --checkout E:/zcode-PR/work/repo --body E:/zcode-PR/work/pr-body.md
```

`prepare` 保存正文的精确 UTF-8 字节与摘要，写入当前 HEAD，初始化尚未核验的字段；不更改政策、测试或反馈核验时间。重新 prepare 会把旧 submission 留在 submission_history，并清空本轮判断，避免沿用旧检查结果。正文文件放在目标 checkout 外；Windows 下保存为不带 BOM 的 UTF-8。正文或代码改变后重新准备，不手改摘要掩盖变化。

在生成的 submission 中填写：

```json
{
  "claims": [{"text": "Regression test passed.", "run": "after"}],
  "limitations": ["Windows was not tested."],
  "feedback": [{
    "fingerprint": "保留 prepare 生成的原始反馈指纹",
    "request": "保留原始反馈摘要，方便对照",
    "status": "addressed",
    "summary": "具体改了什么，以及如何验证该反馈要求的行为",
    "test_case": "与 verification.case 一致的回归用例标识"
  }]
}
```

这只是需要编辑的字段，保留 prepare 已生成的 head 和 body。没有反馈时 feedback 为 `[]`。每条事实反馈都需分类：`addressed` 关联本轮回归验证；`not_actionable` 说明无需代码修改的理由；`unresolved` 写明未解决原因并阻止通过。指纹绑定来源、摘要和观察时间，插入或修改反馈不能继承旧的“已处理”。维护者建议的行为要求仍须阅读理解，工具不替代这一判断。

regression 方式下 before/after 的 `scope` 如实录入 `project`（真实项目入口及依赖）、`isolated`（抽取代码或独立脚本）、`stub`（替代依赖）；后两者只算局部证据，不能通过本检查。after.commit 必须等于当前 HEAD，before 提交必须能在本地 Git 中解析；测试时间不可在未来或前后倒置。工具不重新执行测试，不自动确认导入路径、平台和依赖是否真实，录入者须核验日志。

policy、collision 需有 24 小时内的核验记录；标签/分配门禁仓还需在 policy 中记录 `labels`、`assignees` 字符串列表。共享禁投/暂缓规则照常执行，不能靠 verified 标记绕过。已有 PR 或已记录事实反馈时，feedback.checked_at 也须在 24 小时内；查看远端后如实更新，离线工具不会自动抓取新评论。

每条 claims.text 必须出现在实际正文中，并关联当前提交成功的 after 运行；所有登记的 limitations 也必须写入正文。只登记具体测试结论，不能用一个局部测试支持“全部正确”。工具核对登记声明与证据的对应关系，不自动发现正文中遗漏登记的声明、不审阅文字语义；其余正文仍需审阅。未验证的范围应明确披露。

退出码 0 输出 `EVIDENCE_OK`，仅表示证据一致性检查通过，不构成投稿授权、真人签字或 CI 全绿声明。缺失、过期或不一致退出码 1，显示需补齐事项。继续按 RULES.md 完成实时终检、政策和并发检查后，才进入实际提交步骤；此工具不推送、不发表评论。

## 统计口径

报告按贡献类型、仓库、问题类型、修复方式展示样本数量及缓存状态，文档与 bug 分开统计。`MERGED/(MERGED+CLOSED)` 只针对有核验时间、无查询错误的已结束样本；OPEN 和未知不进入分母。报告保留缓存时间，不把缓存冒充实时状态。

首批只有三个历史样本，尚不足以比较贡献质量；没有补造维护者反馈、归因或工作时长。后续有证据再补充。校验失败时生成命令退出非零，保留上一份报告，避免将坏数据替换成新台账。
