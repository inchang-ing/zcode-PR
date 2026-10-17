# 流水线迁移指南(换电脑 / 换 AI 工具)

## 核心原则
真正重要的状态只有两类:**GitHub 云端**(PR/fork/评审,天然跟随账号)+ **STATE.md**(规则手册与进度)。其余皆可重建。

## 一、需要拷贝的文件(整个目录即可)
```
E:\zcode-PR\
├── STATE.md          # 核心:规则手册 v2 + 在飞 PR 台账 + 策略经验(必带)
├── rounds-log.md     # 25 轮历史日志(建议带)
├── auto-pr-prompt.md # 最初的流水线提示词(建议带)
└── workspaces\       # 可不带:全部是公开仓库克隆,新机重新 git clone 即可
```

## 二、新机器初始化清单
1. 安装 git 与 GitHub CLI(gh)
2. 登录 GitHub:`gh auth login`(浏览器流)—— 本机的 gh token 不会自动转移
3. SSH 二选一:
   - 拷贝本机 `C:\Users\ROG\.ssh\id_rsa` 与 `id_rsa.pub`
   - 或新机生成新密钥,公钥添加到 https://github.com/settings/keys
4. 新机如被墙:SSH 走 443 —— `~/.ssh/config` 写入
   ```
   Host github.com
       HostName ssh.github.com
       Port 443
       User git
   ```
5. 拷贝/同步 `E:\zcode-PR\STATE.md` 等文件
6. 按需重建工作区:`git clone https://github.com/inchang-ing/<repo>` + `python -m venv <repo>-venv` + `pip install -e .`
   **装完必验**:`python -c "import <包名>; print(<包名>.__file__)"` 必须指向克隆目录(防 site-packages 遮蔽)

## 三、恢复自动化(定时轮次)
用创建定时任务的功能,提示词模板:
```
执行一轮开源贡献流水线(每 60 分钟一轮)。第一步通读 <STATE.md 路径>(规则手册,严格遵守其中硬性规则与策略经验)。
本轮按序:①评审响应优先——跟进 STATE.md 第四节每个 open PR 的 CI/评审,有意见当轮修;
②侦察扫描 STATE.md 第五节项目池(48h 窗口、无 assignee、评论≤2),按规则 3 的撞车查证 v3 四查;
③候选时间盒诊断后执行修复 PR(遵守仓库模板与 AI 披露要求);
④在 rounds-log.md 记录,时间戳用 date -u。上限:每轮 1 个新 PR,全局 open ≤ 5,同仓库 ≤2 不同子系统。
```

## 四、若"其它软件"= 另一个 AI 工具(如 Claude Code / Cursor)
1. 把 STATE.md 全文作为系统上下文/首条消息给新工具(它就是完整交接文档)
2. 告知新工具:仓库级 git 身份、每仓库的 AI 披露要求(见 STATE.md 规则 4)
3. 首轮让它:读 STATE.md → 逐项检查第四节 4 个在飞 PR → 报告状态
4. 注意:各仓库的 AI 政策照旧适用;pylint #11474 等 Pierre 复审,SeaTunnel #12488 等合并动作

## 五、当前在飞 PR(2026-09-28 快照)
| PR | 状态 |
|---|---|
| celery #10714 | ✅ 已合并 |
| SeaTunnel #12488 | ✅ APPROVED + 全绿,等合并 |
| pylint #11474 | 🟡 覆盖率 100% 已修,等 Pierre 复审 |
| mypy #22056 / #22058 | 🟢 CI 全绿,等首评 |
