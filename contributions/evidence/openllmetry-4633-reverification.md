# openllmetry #4633 补做验证

这是 2026-10-18 新执行的验证，不是找回的原始 PR 测试日志。

- 原 PR base：`94d3f04bd9a7eec0804562fe8126c01a4f342b18`
- 原 PR head：`92925a7345b856a914b77b843c646e91a370d8f6`
- 验证 baseline：`9bf151cc60017bfef7bd3dc047db3035c7dc2831`
- 验证 after：`d035ea8bb22ef54d4fec01516df0e131a6500b08`

原克隆是 shallow/promisor 仓库，离线克隆缺少对象。因此建立仅包含 `packages/traceloop-sdk/` 的独立验证仓库：baseline 使用原 base 源码并加入 PR 中的同一份回归测试，after 仅加入原 PR 的两处判断修复。上述验证提交不是线上 PR 提交。

`openllmetry-4633-source-proof.json` 记录了 165 个文件的内容核对结果。Windows 工作树使用 CRLF；将 CRLF 统一为 LF 后，after 与 PR head 的 SDK 文件一致，baseline 与 base 加该测试文件一致。文件原始字节并非完全相同，不能声称整个仓库逐字节一致。

## 本次结果

- before：退出码 1，2 failed，均为 `DID NOT RAISE Exception`，不是依赖或环境失败。
- after：退出码 0，2 passed。
- 运行日志先打印并断言 Column/Row 实际导入路径，防止误测已安装包。
- 用例 mock 了 DELETE 503 响应。关闭 tracing、metrics、logging、OTEL SDK 和 pytest 第三方插件自动加载；这些设置在两次运行中一致。
- 使用本机 CPython 3.12.4 和已有依赖；环境清单记录全部已发现发行包版本。未声称复现项目声明的 Python 3.11 或整个测试矩阵。
- 仅执行两条目标回归用例，没有重跑整个 datasets 套件；历史提及的其他网络/cassette 失败也未在本次重新核验。

## 证据文件

- `openllmetry-4633-before.log`、`openllmetry-4633-after.log`：命令、路径、时间、提交、退出码、完整输出。
- `openllmetry-4633-environment.json`：解释器、系统、依赖版本和显式环境开关，不包含完整环境变量或凭证。
- `openllmetry-4633-runs.json`：结构化运行记录。
- `openllmetry-4633-verification.bundle`：可恢复上述两个验证提交的小型 Git 仓库。
- `openllmetry-4633-production-fix.patch`：两次验证之间的源码差异。

恢复时将 bundle 克隆到新的临时目录，分别 checkout 上述两个验证提交，在 `packages/traceloop-sdk/` 中设置 `PYTHONPATH` 为该目录，按环境清单设置开关，执行 `python -B -m pytest tests/datasets/test_delete_failure.py -q -p no:cacheprovider`。精确的本次执行命令见日志；换机器需重建对应依赖环境。
