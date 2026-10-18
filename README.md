# zcode-PR — 开源贡献流水线

半自动化的 GitHub 开源贡献流水线:持续监控约 391 个优质仓库的新 issue,自动评估撞车风险与政策合规,命中后以账号 `inchang-ing` 提交高质量修复 PR(修复 + 修复前失败的回归测试 + 诚实 AI 披露),并跟进全部在飞 PR 的评审与 CI。

> 工作模式:脚本辅助扫描,由对话中的 agent 完成复现、修复、回归验证与提交。

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
│   ├── filter_cands.py      # 本地只读候选过滤(复用共享规则)
│   ├── vet.py               # 开 PR 前终检 CLEAN/WARN/DROP/UNKNOWN
│   ├── auto_run.py          # 候选 → PR 落地管线(修复钩子未接入,见下)
│   ├── monitor_scope.py     # 在飞 PR 状态 → pr_state.json + PR_STATUS.md
│   ├── monitor_oss.py       # 在飞 PR + CI 检查
│   ├── monitor_fresh.py     # 391 仓新 issue 增量监控
│   ├── pr_status.py         # 单 PR 状态查询
│   ├── feishu_push.py       # 飞书通知(自愈式)
│   ├── scan_agent*.py / scan_recon*.py   # 池定义(被 monitor_fresh 引用)
│   └── pipeline_state.py / pr_state.py / gh_checks.py
├── tests/               # 离线回归测试
├── repo-monitor/        # Git 子模块:GitHub Actions 每 10 分钟轮询
├── work/                # 活跃工作台:克隆 / 复现 / 临时产物(gitignore)
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

> `auto_run.py` 的自动修复钩子(FIXERS)目前**未接入**,`run` 语义仅为占位;实际修复仍由 agent 手动完成。不要把它当成已闭环的自动化。

## 可验证贡献记录

每项贡献保存在 `contributions/records/`，证据保存在 `contributions/evidence/`。格式和录入方法见 [贡献记录说明](contributions/README.md)。

```powershell
python -S tools/contributions.py check
python -S tools/contributions.py render
```

生成的 [贡献台账](CONTRIBUTIONS.md) 包含政策、撞车、测试证据、反馈、建议待办，以及按仓库/问题类型/修复方式的样本统计。历史陈述与已核验事实分开，PR 状态只读取现有缓存。首版不替换 `STATE.md` 的监控范围。

## 状态与监控

```powershell
python -S tools/monitor_scope.py                    # 在飞 PR state/review/mergeable
python -S tools/monitor_oss.py                      # 在飞 PR + CI 检查
python -S tools/monitor_fresh.py                    # 391 仓新 issue 增量
python -S tools/pr_status.py <owner/repo> <pr_num>  # 查单个 PR
```

- **权威源 = GitHub**。`pr_state.json` 是机器可读状态;`PR_STATUS.md` 是自动生成的只读视图(勿手改);`STATE.md` 只声明跟踪范围(两张 `OPEN(...)` 表)。
- `repo-monitor/` 是独立仓库,其 GitHub Actions 每 10 分钟轮询新 issue 与在飞 PR 变化,只推飞书通知、不动手。

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

- 本目录已是 git 仓库;`workspaces/`、`work/`、`.trash/`、`*-src`、`*-venv`、各类缓存均被 `.gitignore` 忽略,只跟踪代码 / 文档 / 小状态。
- 回滚:`git checkout -- <file>` 或 `git revert <sha>`;查看历史:`git log --oneline`。
- `repo-monitor/` 由 `.gitmodules` 声明；新克隆使用 `git clone --recurse-submodules <根仓库地址>`，已有克隆运行 `git submodule update --init --recursive`。
- 子模块修改须先在 `repo-monitor/` 提交，再在根仓库提交子模块指针。发布时先推送子仓库提交，再推送根仓库；仅有本地子仓库提交时，其他机器不能从远端恢复该版本。
