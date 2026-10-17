# agent.md — 开源贡献流水线 · 新会话交接文档

## 当前入口（2026-10-15 可靠性优化）

当前工作方式是脚本辅助扫描，由对话中的 agent 完成复现、修复、回归验证和提交。
`auto_run.py` 的自动修复钩子仍未接入；不要把候选已扫描或 `needs_repro` 记账当作 PR 已完成。
本节之后保留的是历史交接材料，其中的任务周期、PR 数量、旧节号和自动启动步骤不代表当前运行状态。

### 本地候选流程

```powershell
python -S monitor_round.py --out work/round_candidates_latest.json
python -S work/filter_cands.py work/round_candidates_latest.json
python -S vet.py --candidates work/round_candidates_latest.json
```

扫描和终检需要已登录的 GitHub CLI；过滤只读取本地文件。`-S` 用于标准库脚本，可避开本机历史 site 初始化故障。
扫描所有仓库列表请求失败时保留旧快照；部分失败会返回非零状态，须查看输出。
只有完成当前检查的 `CLEAN` 候选可以进入人工判断。`UNKNOWN` 是待复核，不等于无人认领；终检不替代仓库贡献政策阅读。

### 状态与监控

- `dispatched.json` 是候选处理状态。所有筛选复用 `DispatchedStore`：`needs_repro`/`repro_failed` 可重试，`running`/`needs_fix`/`pr_opened` 暂停重复派发，`dropped`/`merged`/`closed` 不重派。
- `deferred` 须带 `reason` 和 `retry_after`（带时区的 ISO 时间或 Unix 秒）；未知或损坏状态不会被当成空状态放行。
- `STATE.md` 保留跟踪范围与历史记录。`.trash/monitor_scope.py` 和 `.trash/monitor_oss.py` 查询成功后共同维护 `pr_state.json`，并生成 `PR_STATUS.md`。报告中的 `checked_at` 是最后成功核验时间，查询错误单独记录。
- `pr_state.json` 首次运行时从旧 scope 基线读取历史状态，旧文件保留；文件存在后优先使用统一状态。没有联网刷新前，历史快照不代表 GitHub 当前状态。
- `.trash/monitor_fresh.py` 与独立 `repo-monitor/monitor.py` 使用每仓成功扫描时间，失败不推进。旧状态首次迁移会回看至少 7 天，依靠 seen 集去重，可能增加首次查询量。
- 本地写入使用稳定的 `.lock` 文件与原子替换。进程退出会释放操作系统锁；`.lock` 文件保留是正常现象，不要删除正在使用的锁文件。改写状态的其他脚本也必须遵守同一锁协议。
- `repo-monitor` 是独立 Git 仓库，修改本地代码不等于 GitHub Actions 已更新；任务是否正在定时运行须检查实际调度配置。

### 离线验证

```powershell
python -S -B -m unittest discover -s tests -v
python -S -B -m unittest discover -s repo-monitor/tests -v
```

测试使用假 API 和临时状态，不扫描真实仓库、不发送通知。近期工作明细见 `.workbuddy/memory/`；历史统计与日志不用于代替实时 PR 核验。

---

## 历史交接材料（保留作背景）

> 下列内容保留原写作时点，不作为自动执行授权或当前状态依据。
> 最后更新:2026-09-29。维护者:inchang-ing(GitHub)/ yiyiyi(飞书)。

---

## 一、这个项目是什么

一个**半自动化的 GitHub 开源贡献流水线**:持续监控约 391 个优质仓库的新 issue,自动评估撞车风险与政策合规,命中后以账号 `inchang-ing` 提交高质量修复 PR(修复 + 修复前失败的回归测试 + 诚实 AI 披露),并跟进全部在飞 PR 的评审与 CI。

**当前状态快照**(以 `STATE.md` 第四节为准,此处为写文档时点):
- 在飞 open PR ≈ **13 个**;已合并 **7 个**(celery/SeaTunnel/pylint/sqlglot×2/astroid/mypy)
- 监控:15 分钟一轮,三层结构(agent 核心 96 仓全扫 + 通用/高知名度 295 仓轮转 1/3)
- 飞书通知:✅ 已打通(群聊路线,详见第四节)
- 自动化:`automation-311a7469-f456-4b35-b659-a18c8cff34c8`(15 分钟;**会话边界会丢失,丢了就重建**,见第二节)

---

## 二、核心文件地图

| 文件/目录 | 作用 |
|---|---|
| `E:\zcode-PR\agent.md` | 本文件 —— 入口与飞书用法 |
| `E:\zcode-PR\STATE.md` | **规则手册 + 在飞 PR 台账 + 轮次流程(必读,唯一权威)** |
| `E:\zcode-PR\rounds-log.md` | 全部轮次日志(追加式,含每轮侦察/产出/教训) |
| `E:\zcode-PR\.trash\monitor_fresh.py` | 新 issue 增量监控器(391 仓,详见第三节) |
| `E:\zcode-PR\.trash\monitor_state.json` | 监控状态(seen 集 + last_check + rot_index + textual_last) |
| `E:\zcode-PR\.trash\feishu_push.py` | 飞书推送脚本(自愈式,详见第四节) |
| `E:\zcode-PR\.trash\pr_status.py` | 在飞 PR 状态查询(**一次只接受一个仓库参数**):`python .trash/pr_status.py <owner/repo> <pr_num>` |
| `E:\zcode-PR\.trash\scan_agent.py` 等 | 池扫描脚本(scan_agent/scan_agent2/scan_recon2-6),各池仓库列表的权威来源 |
| `E:\zcode-PR\workspaces\<repo>` | 各仓库克隆;`<repo>-venv` 或 repo 内 venv(见 STATE.md 环境清单) |
| `C:\Users\ROG\.Codex\feishu.json` | 飞书凭证(**含 SECRET,绝不入库**) |

---

## 三、监控与自动化

### 3.1 定时触发
- 一个 **15 分钟**的定时自动化每轮执行:监控 diff → 有 NEW 则评估/出手 → 在飞 PR 跟进 → 飞书事件通知 → 安静轮秒退。
- **定时自动化绑定创建它的会话;会话结束即消失**。每轮开头若 `CronList` 为空,必须用原提示词重建(完整提示词保存在 STATE.md"轮次"段落与飞书推送的历史记录中;核心要点:监控优先、撞车五查、礼让规则、每轮最多 1 PR、飞书事件通知、textual 重试、crewAI 标签 ping)。
- 手动补跑一轮 = 直接执行 `python E:/zcode-PR/.trash/monitor_fresh.py` 并按 STATE.md 第六节流程走。

### 3.2 GitHub Actions 直连监测器(准实时通知,2026-09-30 上线)

- 仓库:[inchang-ing/repo-monitor](https://github.com/inchang-ing/repo-monitor)(公开,Actions 免费)
- 工作流:`.github/workflows/monitor.yml`,**每 30 分钟**跑 `monitor.py`(轮转层 1/3,90 分钟全覆盖)(stdlib-only),并发锁防重叠
- 职责:**只推通知,不动手** —— ①391 仓新 issue(增量,分批卡片)②inchang-ing 的 open PR 状态变化(合并🎉/关闭/新评审/新评论);本地自动化负责评估与出手,分工无重叠
- 状态:`state.json` 由工作流每轮 commit 回仓库(seen 集 + PR 缓存 + rot_index);首跑为静默基线 + "已上线"卡片
- Secrets:`FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_CHAT_ID`(已配置;更新用 `gh secret set X --repo inchang-ing/repo-monitor --body "<值>"`,**值必须剥空白符**——曾因 Windows CRLF 混入 
 导致飞书 10003)
- 手动触发:`gh api -X POST repos/inchang-ing/repo-monitor/actions/workflows/monitor.yml/dispatches -f ref=main`
- 排障:`gh run list --repo inchang-ing/repo-monitor --limit 1` + `gh run view <id> --log`;少数 404 WARN 为失效 slug(已修 6 删 3),跳过无害
- **注意:向 GitHub push 代码可能被本地代理阻断(git 443 连接失败),改用 Contents API 逐文件 PUT(见 rounds-log)**

### 3.3 monitor_fresh.py(本地评估线)
- 三层:T1+T2 常扫 96 仓(agent 核心 + 政策观察 + 池 G)/ 每 15 分钟;T3 轮转 295 仓(通用 + 池 A-E)/ 每轮 1/3,45 分钟全覆盖(rot_index 持久化)。
- 每仓 1 个 REST 调用(sort=created desc, per_page=15),过滤 PR 与 ScreenContextAgent 噪音;**只报上次检查之后新建的 issue**(age/labels/author)。
- `--init`:重建基线(不报历史);`TEXTUAL-RETRY: yes/no` 内部节流(约每小时一次 textual #6706 重试)。
- 速率:每轮 ~195 调用 ≈ 780/h(GitHub 限额 5000/h)。

---

## 四、飞书集成(正确详细用法)

### 4.1 架构(为什么是现在这样)
- 账号:豆包账号个人版飞书,租户 `icno7mior52s`(用户 yiyiyi)。**该租户:①平台级禁用机器人单聊推送(API 返回 230101);②管理策略禁用群自定义机器人(webhook)**。
- 因此唯一可行方案:**自建应用机器人 + 机器人自建群推送**:
  - 自建应用「流水线通知」(open.feishu.cn 开发者后台,App ID `cli_aa31c15727f99be4`,已发布 v1.0.3)
  - 能力:机器人;权限:`im:message`(收发单聊群组消息)、`im:chat`(群组信息)、`contact:user.base:readonly`、`contact:contact.base:readonly`(后两个用于查询 open_id),数据范围=全部成员,可用范围=部分成员(所有者)
  - 传输:机器人自建群 **「PR流水线通知」**(`oc_952daf83141bab0a7ba0571f8ded92f9`),所有者已入群 —— **所有通知发到这个群**

### 4.2 配置文件
`C:\Users\ROG\.Codex\feishu.json`(**含 SECRET,绝不提交、绝不贴聊天记录**):
```json
{
  "mode": "app",
  "app_id": "cli_aa31c15727f99be4",
  "app_secret": "<32位密钥>",
  "open_id": "ou_...",   // 所有者的 open_id(用于拉人回群)
  "chat_id": "oc_..."    // 通知群(推送目标)
}
```

### 4.3 推送脚本(自愈式)
```bash
# 推送一条卡片通知(标准用法)
python E:/zcode-PR/.trash/feishu_push.py "标题" "**markdown** 正文"

# 自检:发送测试卡片;若缓存群失效,自动重建群+拉人+重发(自愈)
python E:/zcode-PR/.trash/feishu_push.py --ensure

# 同 --ensure 但固定文案
python E:/zcode-PR/.trash/feishu_push.py --test
```
- 成功输出 `sent OK, message_id: om_...`;失败抛 RuntimeError(含 code/msg)。
- **自愈逻辑**:send 失败(群被删/被移出)→ 自动重建群 + 拉所有者 + 重发一次 + 更新配置。
- 事件触发时机(cron 已配置):①新 PR 开启 ②PR 被合并 ③收到评审待响应 ④监控捕获可出手候选。

### 4.4 如果飞书链路彻底坏了(换软件/换账号后重建步骤)
1. 检查 `feishu.json` 是否存在且 app_id 一致;token 自测:`POST /auth/v3/tenant_access_token/internal`,code=0 即凭证有效。
2. 若凭证失效/应用被删:open.feishu.cn → 开发者后台(用飞书账号登录)→ 创建企业自建应用 → 添加「机器人」能力 → 权限管理开通 `im:message` + `im:chat`(免审)→ 版本管理与发布(个人版免审即上线)→ 凭证页复制 App ID/Secret 更新 `feishu.json`。
3. 群路线重建:直接运行 `python E:/zcode-PR/.trash/feishu_push.py --ensure`(自动建群+拉人+发测试卡)。
4. 若要找回用户 open_id:开 `contact:user.base:readonly` + `contact:contact.base:readonly` 后调 `GET /contact/v3/users/find_by_department?department_id=0&user_id_type=open_id`(数据范围需含该用户所在部门)。
5. 保险丝:p2p(open_id 直发)在该租户永久 230101,**不要浪费时间重试单聊**;一律走群。

---

## 五、硬规则(违反 = 劣质轮次,详见 STATE.md)

1. **撞车 v4 五查**(动手前 + push 前终查):编号搜索 / 标题关键词 / 时间线交叉引用 / 同文件 open PR / 崩溃签名。`gh search` 404 的仓库(agentscope 等)用 `gh pr list` 全量手工比对;**agentscope 的 `/assign` 评论 = bot 正式认领,必须读 issue 评论**。
2. **礼让**:报告者正文含 "I will / I can open a PR / I will add tests / I have a patch / Codex is assisting" 一律让。
3. **AI 披露**:如实披露(ZCode/GLM),绝不写 "No AI use" 虚假声明。各仓政策:pallets 禁 AI、camel 关 LLM PR、inspect_ai 需 `accepted` 标签、langchain-ai 需先被 assign、dspy 禁 agent、mem0 需 `accepted` issue(自动重开机制)、docling 需 DCO(`git commit -s`)。
4. **质量红线**:每轮最多 1 个新 PR;修复必须带**修复前失败的回归测试**;宁缺毋滥,空手轮是常态。
5. **工程**:仓库级身份(inchang-ing / `197932532+inchang-ing@users.noreply.github.com`);token 直推 `git -c credential.helper= push "https://x-access-token:$(gh auth token)@github.com/inchang-ing/<repo>.git" <branch>:<branch>`;gh 全路径 `/c/Program Files/GitHub CLI/gh.exe`;**新分支必须 `git checkout -b <name> origin/main`**(曾发生继承旧分支提交 → rebase --onto 修正);覆盖率门禁;DCO 仓库用 `-s`。
6. **删除安全**:只动 `E:\zcode-PR` 内本流水线创建的文件。

---

## 六、在飞 PR 台账(动态,以 STATE.md 第四节为准)

撰写时点(轮 #58):open = crewAI #7795、setuptools #5337、execnet #431、markdown-it-py #442、ariadne #1337、bokeh #15476、agno #10654、instructor #2717、pyyaml #967、ChatDev #682、Qwen-Agent #986、docling #4439、docling #4449;已合并 7(最新 mypy #22058)。
每轮第一优先级 = 跟进这些 PR(评审当轮响应、CI 判归属、bot 推送同步)。

---

## 七、环境速查(全部现成,勿重复搭建)

- agentscope:`workspaces/agentscope` + repo 内 `agentscope-venv`(`-e ".[rag]"` + apscheduler/fastapi/pytest)
- docling:`workspaces/docling` + repo 内 `docling-venv`(**最小环境**:docling-core + arelle-release + pydantic(-settings) + bs4 + lxml + filetype + langcodes + tqdm + rtree + pytest + ruff;XBRL 后端可直接实例化,无需 torch)
- Qwen-Agent:`workspaces/Qwen-Agent` + `qwen-agent-venv`(`-e ".[rag]"` + numpy/soundfile/tqdm/dateutil)
- ChatDev:`workspaces/ChatDev`(系统 Python 即可,stdlib-only 目标)
- mem0:`workspaces/mem0` + `mem0-venv`(vector-stores extras + opensearch-py)
- 其余见 STATE.md 第一节。

## 八、复活线监控池(报告者 PR 停滞 >7d 可评估接管)

mem0 #7491/#7493、openinference #3860、docling #4429、agentscope #2983/#2986/#2985、本地分支 `local-3024-mcp-rename-yielded`(#3024 被认领)、`local-2985-media-type-yielded`(#2985 被认领)。

---

## 九、新会话启动清单(照做即可继续跑)

1. 读本文件 → 读 `STATE.md` → 看 `rounds-log.md` 尾部 3 轮。
2. `CronList` 为空 → 用第二节要点重建 15 分钟自动化。
3. `python E:/zcode-PR/.trash/monitor_fresh.py` → 处理 NEW 候选(第五节硬规则)。
4. `pr_status.py` 逐仓库扫在飞 PR → 有评审响应,有 CI 修。
5. 有实质事件 → 飞书推送(`feishu_push.py`)+ 更新 STATE.md + 追加 rounds-log。
6. 安静轮:stdout 一行报告,零文件写入。
