# zcode-PR — 开源贡献流水线

半自动化的 GitHub 开源贡献流水线:持续监控约 391 个优质仓库的新 issue,自动评估撞车风险与政策合规,命中后以账号 `inchang-ing` 提交高质量修复 PR(修复 + 修复前失败的回归测试 + 诚实 AI 披露),并跟进全部在飞 PR 的评审与 CI。

> 工作模式:脚本辅助扫描,由对话中的 agent 完成复现、修复、回归验证与提交。

当前重心为高质量贡献：先完成真实路径验证、影响范围审查和必要的评审返工，再按仓库政策提交。每次返工重验，准确披露 AI 协助和验证局限，减少没有新信息的评论与同步。具体执行见 [RULES.md 的当前重心](RULES.md#当前重心高质量贡献2026-10-23)。

## 目录结构

```
E:\zcode-PR\
├── README.md            # 本文件
├── RULES.md             # 硬规则 / AI 政策 / 身份红线(动手前必读)
├── STATE.md             # 跟踪范围(在飞 PR 表,监控脚本解析它)
├── PR_STATUS.md         # 实时状态(自动生成,勿手改)
├── pr_state.json        # 机器可读权威状态
├── rounds-log.md        # 逐轮日志(追加式)
├── STATE-archive.md     # 历史归档(已合并/关闭 PR 的验证记录)
├── tools/               # 全部可执行代码
│   ├── monitor_round.py     # 权威仓库池扫描 → 候选
│   ├── scan_candidates.py   # 精选仓库池初筛，配置为 tools/quality_repos.json
│   ├── filter_cands.py      # 本地只读候选过滤(复用共享规则)
│   ├── vet.py               # 开 PR 前终检 CLEAN/WARN/DROP/UNKNOWN
│   ├── quality_check.py     # 首次提交/返工前检查版本、证据、正文和反馈对应关系
│   ├── auto_run.py          # 候选 → PR 落地管线(修复钩子未接入,见下)
│   ├── monitor_scope.py     # 在飞 PR 状态 → pr_state.json + PR_STATUS.md
│   ├── monitor_oss.py       # 在飞 PR + CI 检查
│   ├── monitor_fresh.py     # 391 仓新 issue 增量监控
│   ├── pr_status.py         # 单 PR 状态查询
│   ├── feishu_push.py       # 飞书通知(自愈式)
│   ├── scan_agent*.py / scan_recon*.py   # 池定义(被 monitor_fresh 引用)
│   └── pipeline_state.py / pr_state.py / gh_checks.py
├── tests/               # 离线回归测试
├── repo-monitor/        # Git 子模块:GitHub Actions 按工作流配置定时轮询
├── work/                # 活跃工作台:克隆 / 复现 / 临时产物；仅保留扫描兼容入口
├── workspaces/          # 各仓库克隆 + venv(gitignore,可重建)
└── archive/             # 归档的早期一次性脚本
```

## 跑一条流水线

```powershell
python -S tools/monitor_round.py --out round_candidates.json   # 扫描权威池 → 候选
python -S tools/filter_cands.py                                # 本地只读过滤(不联网)
python -S tools/vet.py --candidates round_candidates.json      # 开 PR 前终检
```

`round_candidates.json`(仓库根)是**唯一权威候选文件**,`auto_run.py` 与 `vet.py` 都读它。
只有终检为 `CLEAN` 的候选才能进入人工判断(`UNKNOWN` 必须复核)。之后:复现 → 修复 + 回归测试 → 覆盖率自检 → 提 PR,遵守 `RULES.md`。

精选仓库池的初筛使用 `python -S tools/scan_candidates.py --days 4 --max 5`，仓库池维护在 `tools/quality_repos.json`。旧命令 `python -S work/scan_candidates.py` 保留为兼容入口，两者执行同一份代码。初筛报告仍输出到 `work/ledger/candidates.json`，与权威候选文件分开；查询失败记为 `UNKNOWN` 并返回非零，不能当作没有撞车或认领。首次迁移缺少旧在飞台账时读取 `pr_state.json` 缓存。

常规扫描对最新十条之外的已有候选按编号复核；查询失败时保留并标为未知，确认关闭或不合格后才移除。

> `auto_run.py` 的自动修复钩子(FIXERS)目前**未接入**。以后接入钩子也只准备本地补丁，停在 needs_verification；须落入目标 Git checkout，完成最终提交与证据检查后按规则提交。此入口不自动推送或创建 PR。

本地准备不要求所有候选先发占位留言；讨论和分配按目标仓库政策执行，已有仓库限制、分配门禁和并发限制继续生效。

## 合并产出工作队列

默认扫描结束后自动生成 [工作队列](WORK_QUEUE.md)，将候选核验、复现和已有 PR 的修改请求放在一起排序。
使用 `python -S tools/work_queue.py refresh` 可离线刷新队列和 [七天产出统计](WEEKLY_CONTRIBUTIONS.md)。
阶段、退出原因、实际工时及反馈分类的操作见 [试运行说明](QUEUE_GUIDE.md)。缺少政策、撞车或维护者意图证据的候选只能先核验；高分不能绕过门禁。

## 可验证贡献记录

每项贡献保存在 `contributions/records/`，证据保存在 `contributions/evidence/`。格式和录入方法见 [贡献记录说明](contributions/README.md)。

```powershell
python -S tools/contributions.py check
python -S tools/contributions.py render
```

生成的 [贡献台账](CONTRIBUTIONS.md) 包含政策、撞车、测试证据、反馈、建议待办，以及按仓库/问题类型/修复方式的样本统计。历史陈述与已核验事实分开，PR 状态只读取现有缓存。首版不替换 `STATE.md` 的监控范围。

首次提交和每次返工推送前，执行 `tools/quality_check.py prepare/check`，核验最终提交、测试日志、实际 PR 正文和反馈处理是否对应。具体命令见 [提交前与返工检查](contributions/README.md#提交前与返工检查)。旧记录可以继续读取，但缺少新版证据字段时不会通过提交检查。

## 状态与监控

```powershell
python -S tools/monitor_scope.py                    # 在飞 PR state/review/mergeable
python -S tools/monitor_oss.py                      # 在飞 PR + CI 检查
python -S tools/monitor_fresh.py                    # 391 仓新 issue 增量
python -S tools/pr_status.py <owner/repo> <pr_num>  # 查单个 PR
```

- **权威源 = GitHub**。`pr_state.json` 是机器可读状态;`PR_STATUS.md` 是自动生成的只读视图(勿手改);`STATE.md` 只声明跟踪范围(两张 `OPEN(...)` 表)。
- `pr_status.py` 完整分页读取评审、普通评论、行内评论和 CI 检查，再显示最近反馈及检查汇总。任一读取失败标记 `UNKNOWN`，仍继续检查其余 PR，最后返回非零退出码。
- `repo-monitor/` 是独立仓库,其 GitHub Actions 定时轮询新 issue 与在飞 PR 变化,只推通知、不动手。通知为 best-effort:飞书认证/发送失败不再使运行失败,状态照常落盘,未送达事件记入子仓 `undelivered.jsonl`(随 state 一起提交,保留最近 200 行)作兜底记录。频率以子仓库的 [工作流配置](https://github.com/inchang-ing/repo-monitor/blob/main/.github/workflows/monitor.yml) 为准；修改调度时间只需更新该配置。

## 离线验证

```powershell
python -S -B -m unittest discover -s tests -v
python -S -B -m unittest discover -s repo-monitor/tests -v
```

测试使用假 API 与临时状态,不扫描真实仓库、不发送通知。

## 飞书通知

- 账号为豆包账号个人版飞书,该租户永久禁用机器人单聊(230101)与群自定义机器人 webhook → 一律走**自建应用机器人 + 机器人自建群**。
- 凭证:`C:\Users\ROG\.Codex\feishu.json`(含 SECRET,**绝不入库**)。
- 推送:`python tools/feishu_push.py "标题" "**markdown** 正文"`;自愈:`python tools/feishu_push.py --ensure`。

## 环境 / 换机

- 需要保留 **GitHub 云端记录**、**代码和规则/台账**，以及 **`contributions/` 的记录与证据**；clone、venv 等可重建，原始核验日志不能当作可重建缓存丢弃。
- 新机器:装 git 与 GitHub CLI → `gh auth login` → SSH 走 443(`~/.ssh/config` 指向 `ssh.github.com:443`)→ 拷规则与脚本 → 按需 `git clone` + `python -m venv <repo>-venv` + `pip install -e .`。
- 装完必验:`python -c "import <包名>; print(<包名>.__file__)"` 必须指向克隆目录(防 site-packages 遮蔽)。

## git 安全网

- 本目录已是 git 仓库；`workspaces/`、`work/`、`.trash/`、`*-src`、`*-venv`、各类缓存均被 `.gitignore` 忽略，`work/scan_candidates.py` 兼容入口除外。长期扫描代码和仓库池位于 `tools/`，应随代码一起保存。
- 回滚:`git checkout -- <file>` 或 `git revert <sha>`;查看历史:`git log --oneline`。
- `repo-monitor/` 由 `.gitmodules` 声明；新克隆使用 `git clone --recurse-submodules <根仓库地址>`，已有克隆运行 `git submodule update --init --recursive`。
- 子模块修改须先在 `repo-monitor/` 提交，再在根仓库提交子模块指针。发布时先推送子仓库提交，再推送根仓库；仅有本地子仓库提交时，其他机器不能从远端恢复该版本。
