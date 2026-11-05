"""Local contribution restrictions shared by screening and follow-up tools.

Each owner/repository has one record. Evidence preserves local observations;
this module does not assert that upstream policy was rechecked today.
"""

ACCOUNT = "inchang-ing"
ALL_KINDS = ("bug", "docs", "small_fix", "tooling")

OWNER_POLICIES = {'langchain-ai': {'reason': '须先分配给当前账号',
                  'evidence': [{'scope': 'owner',
                                'source': 'RULES.md / repository_policy.py',
                                'review': '沿用现有本地限制；未重新调查上游政策'}],
                  'allowed_kinds': ALL_KINDS,
                  'requires_assignment': True},
 'pallets': {'reason': '本地禁投记录，解除前须核验账号权限',
             'evidence': [{'scope': 'owner',
                           'source': 'RULES.md / repository_policy.py',
                           'review': '沿用现有本地限制；未重新调查上游政策'}],
             'allowed_kinds': (),
             'blocked': True},
 'pre-commit': {'reason': '本地禁投记录，解除前须核验账号权限',
                'evidence': [{'scope': 'owner',
                              'source': 'RULES.md / repository_policy.py',
                              'review': '沿用现有本地限制；未重新调查上游政策'}],
                'allowed_kinds': (),
                'blocked': True},
 'pycqa': {'reason': '重新确认账号投稿权限后解除',
           'evidence': [{'scope': 'owner',
                         'observed_at': '2026-10-18',
                         'source': '.workbuddy/memory/blocked-repos.md',
                         'review': '重新确认账号投稿权限后解除'}],
           'allowed_kinds': (),
           'blocked': True},
 'python-jsonschema': {'reason': '本地禁投记录，解除前须核验账号权限',
                       'evidence': [{'scope': 'owner',
                                     'source': 'RULES.md / repository_policy.py',
                                     'review': '沿用现有本地限制；未重新调查上游政策'}],
                       'allowed_kinds': (),
                       'blocked': True},
 'sqlalchemy': {'reason': '重新确认账号访问权限后解除',
                'evidence': [{'scope': 'owner',
                              'observed_at': '2026-10-18',
                              'source': '.workbuddy/memory/blocked-repos.md',
                              'review': '重新确认账号访问权限后解除'}],
                'allowed_kinds': (),
                'blocked': True},
 'textualize': {'reason': 'PR 创建对本账号双通道封锁（API CreatePullRequest FORBIDDEN + 网页 compare 表单不渲染，2FA '
                          '配置后仍如此）；外部账号 2026-05 仍可正常开 PR，判定为账号特定限制；残余测试仅剩 GitHub 完全重登。handoff-only：修复推 fork '
                          '后在 issue 留 compare 链接请维护者代开（rich#4233 先例）；禁止重试 API 创建以免加固封锁标记',
                'evidence': [{'scope': 'owner',
                              'observed_at': '2026-10-24',
                              'source': '.workbuddy/memory/2026-10-24.md',
                              'review': 'PR 创建对本账号双通道封锁（API CreatePullRequest FORBIDDEN + 网页 compare '
                                        '表单不渲染，2FA 配置后仍如此）；外部账号 2026-05 仍可正常开 PR，判定为账号特定限制；残余测试仅剩 GitHub '
                                        '完全重登。handoff-only：修复推 fork 后在 issue 留 compare 链接请维护者代开（rich#4233 '
                                        '先例）；禁止重试 API 创建以免加固封锁标记'}],
                'allowed_kinds': (),
                'blocked': True}}

REPOSITORY_POLICIES = {'ansible/ansible': {'reason': '当前账号贡献被以自主投稿关闭；停止本项目自动投稿和跟进写入，待维护者明确允许后复核',
                     'evidence': [{'scope': 'repo',
                                   'observed_at': '2026-10-23',
                                   'source': 'https://github.com/ansible/ansible/pull/87712#issuecomment-6349441213',
                                   'review': '当前账号贡献被以自主投稿关闭；停止本项目自动投稿和跟进写入，待维护者明确允许后复核'}],
                     'allowed_kinds': (),
                     'blocked': True,
                     'interaction_hold': '该账号投稿已被明确拒绝；停止自动跟进写入，保留只读观察'},
 'apache/arrow': {'reason': '本机缺少可靠构建与测试条件',
                  'evidence': [{'scope': 'repo',
                                'source': 'RULES.md / repository_policy.py',
                                'review': '沿用现有本地限制；未重新调查上游政策'}],
                  'allowed_kinds': (),
                  'non_testable': True},
 'apache/seatunnel': {'reason': '主仓为 Java/Scala（Connector-V2 = Java），本机不具备构建与测试条件；已合 PR 的经验不足以抵消可测性门槛',
                      'evidence': [{'scope': 'repo',
                                    'observed_at': '2026-10-29',
                                    'source': '.workbuddy/memory/2026-10-29.md',
                                    'review': '主仓为 Java/Scala（Connector-V2 = Java），本机不具备构建与测试条件；已合 PR '
                                              '的经验不足以抵消可测性门槛'}],
                      'allowed_kinds': (),
                      'non_testable': True},
 'arize-ai/phoenix': {'reason': 'CONTRIBUTING 明写「An open issue is not an invitation to submit a PR」，须 '
                                'maintainer 明确确认后才可开工',
                      'evidence': [{'scope': 'repo',
                                    'observed_at': '2026-10-29',
                                    'source': 'https://raw.githubusercontent.com/Arize-ai/phoenix/main/CONTRIBUTING.md',
                                    'review': '「Issues First」节明写 open issue 不等于邀请提 PR，须等 maintainer '
                                              '明确确认；未确认的 PR 大概率直接关闭。另：仓库自带 claude-implement-issue / '
                                              'factory-* 工作流，issue 多由内部自动化承接'}],
                      'allowed_kinds': (),
                      'manual_gate': True},
 'camel-ai/camel': {'reason': '本地禁投记录，解除前须核验账号权限',
                    'evidence': [{'scope': 'repo',
                                  'source': 'RULES.md / repository_policy.py',
                                  'review': '沿用现有本地限制；未重新调查上游政策'}],
                    'allowed_kinds': (),
                    'blocked': True},
 'encode/httpx': {'reason': '本地禁投记录，解除前须核验账号权限',
                  'evidence': [{'scope': 'repo',
                                'source': 'RULES.md / repository_policy.py',
                                'review': '沿用现有本地限制；未重新调查上游政策'}],
                  'allowed_kinds': (),
                  'blocked': True},
 'frappe/frappe': {'reason': 'vouched 资格未核验',
                   'evidence': [{'scope': 'repo',
                                 'observed_at': '2026-10-18',
                                 'source': '.workbuddy/memory/blocked-repos.md',
                                 'review': '须确认当前账号已获 vouched'}],
                   'allowed_kinds': (),
                   'manual_gate': True},
 'geopandas/geopandas': {'reason': '方案共识须专项核验',
                         'evidence': [{'scope': 'repo',
                                       'observed_at': '2026-10-18',
                                       'source': '.workbuddy/memory/blocked-repos.md',
                                       'review': '须核验现有 issue 上的方案共识'}],
                         'allowed_kinds': (),
                         'manual_gate': True},
 'google/adk-python': {'reason': '外部 PR 须先签 Google '
                                 'CLA（cla.developers.google.com，需账号持有者网页签署，流水线无法代办）；CONTRIBUTING「For other '
                                 'issues, please kindly ask before contributing」+「Large or Complex Changes: '
                                 'Open an Issue First, Gather Feedback」，即非 GFI/help-wanted 的 issue 必须先征询维护者',
                       'evidence': [{'scope': 'repo',
                                     'observed_at': '2026-11-04',
                                     'source': 'https://github.com/google/adk-python/blob/main/CONTRIBUTING.md',
                                     'review': '两道门叠加：①所有贡献须附 Google '
                                               'CLA（cla.developers.google.com，需账号持有者网页签署，无人值守流程无法完成，PR 会停在 '
                                               'cla:no）；②「For other issues, please kindly ask before '
                                               'contributing to avoid duplication」+「Large or Complex '
                                               'Changes: Open an Issue First, Gather Feedback」，非 '
                                               'good-first-issue/help-wanted 的 issue 必须先征询。仓内 100+ open '
                                               'PR、AGENTS.md 另有 uv/breeze 工具链要求。判定为人工门禁（#7974 workflow '
                                               '中断传播、#7968 SSRF 因此弃）；CLA 若由账号持有者签署后可复核本条'}],
                       'allowed_kinds': (),
                       'manual_gate': True},
 'google/jax': {'reason': 'blocked.reasons 记录 CONTRIBUTING 禁止 agent 自主开 PR，#41846/#41847 已弃；本地补充见 '
                          '.workbuddy/memory/2026-10-22.md；其他写入范围待复核',
                'evidence': [{'scope': 'repo',
                              'observed_at': '2026-10-22',
                              'source': 'tools/quality_repos.json',
                              'review': 'blocked.reasons 记录 CONTRIBUTING 禁止 agent 自主开 PR，#41846/#41847 '
                                        '已弃；本地补充见 .workbuddy/memory/2026-10-22.md；其他写入范围待复核'}],
                'allowed_kinds': (),
                'blocked': True,
                'interaction_hold': '本地记录禁止 agent 自主开 PR；只准备本地材料，其他写入范围待复核，保留只读观察'},
 'gradio-app/gradio': {'reason': '本地禁投记录，解除前须核验账号权限',
                       'evidence': [{'scope': 'repo',
                                     'source': 'RULES.md / repository_policy.py',
                                     'review': '沿用现有本地限制；未重新调查上游政策'}],
                       'allowed_kinds': (),
                       'blocked': True},
 'home-assistant/core': {'reason': 'AGENTS.md「AI policy」节：Follow Open Home Foundation AI Policy，Autonomous '
                                   'contributions are not accepted，禁止自主开 '
                                   'issue/PR、禁止未经用户复核代为评论。整仓跳过（#189835/#189837/#189840 因此弃）；另有 Windows '
                                   '侧可测性障碍（fcntl/uvloop）',
                         'evidence': [{'scope': 'repo',
                                       'observed_at': '2026-11-01',
                                       'source': 'https://github.com/home-assistant/core/blob/dev/AGENTS.md',
                                       'review': 'AGENTS.md「AI policy」节：Follow Open Home Foundation AI '
                                                 'Policy，Autonomous contributions are not accepted，禁止自主开 '
                                                 'issue/PR、禁止未经用户复核代为评论。整仓跳过（#189835/#189837/#189840 因此弃）；另有 '
                                                 'Windows 侧可测性障碍（fcntl/uvloop）'}],
                         'allowed_kinds': (),
                         'blocked': True,
                         'interaction_hold': 'AGENTS.md 不接受自主投稿；只准备本地材料，须用户本人投稿'},
 'huggingface/peft': {'reason': 'AGENTS.md「Mandatory Agentic contribution policy」明写「Pure code-agent PRs are '
                                'not allowed: a human submitter must understand and can defend the change '
                                'end-to-end」，且 PR 描述须附「issue 讨论与协调/批准评论」链接；CONTRIBUTING 要求维护者在 issue 上留 '
                                '`/peft-triage approved` 并指派，无该评论的 PR 由自动化直接关闭。即无自助认领通道 + 明禁纯 agent 提交（#4117 '
                                'LoHa rank_dropout NaN、#4118 IA3 feedforward_modules 因此弃）',
                      'evidence': [{'scope': 'repo',
                                    'source': 'RULES.md / repository_policy.py',
                                    'review': '沿用现有本地限制；未重新调查上游政策'}],
                      'allowed_kinds': (),
                      'manual_gate': True,
                      'requires_assignment': True},
 'huggingface/trl': {'reason': 'CONTRIBUTING「AI usage policy」：不会评审 first-time contributor 的全 AI 生成 PR（「we '
                               'will not review fully AI-generated PRs from first-time contributors」），且对 '
                               'issue 同样要求作者写过真实使用场景。本账号在该仓无已合 PR（非 first-time 门槛无法自证），加之仓内 100+ open '
                               'PR，判为人工门禁（#8127 optimizer_cls_and_kwargs 缺失因此弃）',
                     'evidence': [{'scope': 'repo',
                                   'source': 'RULES.md / repository_policy.py',
                                   'review': '沿用现有本地限制；未重新调查上游政策'}],
                     'allowed_kinds': (),
                     'manual_gate': True},
 'hypothesisworks/hypothesis': {'reason': '本地禁投记录，解除前须核验账号权限',
                                'evidence': [{'scope': 'repo',
                                              'source': 'RULES.md / repository_policy.py',
                                              'review': '沿用现有本地限制；未重新调查上游政策'}],
                                'allowed_kinds': (),
                                'blocked': True},
 'jax-ml/jax': {'reason': '与 blocked.reasons.google/jax 使用同一禁投记录（本地补充 '
                          '.workbuddy/memory/2026-10-22.md）；规范名称及重定向依据 '
                          '.workbuddy/memory/2026-09-30.md；未重新调查上游政策',
                'evidence': [{'scope': 'repo',
                              'observed_at': '2026-10-22',
                              'source': 'tools/quality_repos.json',
                              'review': '与 blocked.reasons.google/jax 使用同一禁投记录（本地补充 '
                                        '.workbuddy/memory/2026-10-22.md）；规范名称及重定向依据 '
                                        '.workbuddy/memory/2026-09-30.md；未重新调查上游政策'}],
                'allowed_kinds': (),
                'blocked': True,
                'interaction_hold': '本地记录禁止 agent 自主开 PR；只准备本地材料，其他写入范围待复核，保留只读观察'},
 'langfuse/langfuse': {'reason': '仓级不可测（TypeScript 全栈 monorepo，非 Python 包，不满足权威池准入门槛①）：CONTRIBUTING 列明构建需 '
                                 'Node+pnpm+Rust(rustup，worker 的 napi-rs 原生插件 + AI gateway)+native '
                                 'linker，运行时需 PostgreSQL/ClickHouse/Redis/S3 全套服务；本机实测无 rustc/cargo、Docker '
                                 'daemon 未运行、无 psql。另注：该仓自带 AGENTS.md 且明确面向外部贡献者与 agent（无 AI 禁投条款），登记 '
                                 'NON_TESTABLE 仅为可测性门槛，非封禁',
                       'evidence': [{'scope': 'repo',
                                     'observed_at': '2026-10-29',
                                     'source': 'https://raw.githubusercontent.com/langfuse/langfuse/main/CONTRIBUTING.md',
                                     'review': '仓级不可测（TypeScript 全栈 monorepo，非 Python '
                                               '包，不满足权威池准入门槛①）：CONTRIBUTING 列明构建需 '
                                               'Node+pnpm+Rust(rustup，worker 的 napi-rs 原生插件 + AI '
                                               'gateway)+native linker，运行时需 PostgreSQL/ClickHouse/Redis/S3 '
                                               '全套服务；本机实测无 rustc/cargo、Docker daemon 未运行、无 psql。另注：该仓自带 '
                                               'AGENTS.md 且明确面向外部贡献者与 agent（无 AI 禁投条款），登记 NON_TESTABLE '
                                               '仅为可测性门槛，非封禁'}],
                       'allowed_kinds': (),
                       'non_testable': True},
 'matplotlib/matplotlib': {'reason': '本地禁投记录，解除前须核验账号权限',
                           'evidence': [{'scope': 'repo',
                                         'source': 'RULES.md / repository_policy.py',
                                         'review': '沿用现有本地限制；未重新调查上游政策'}],
                           'allowed_kinds': (),
                           'blocked': True},
 'mem0ai/mem0': {'reason': 'issue 须有 accepted 标签',
                 'evidence': [{'scope': 'repo',
                               'source': 'RULES.md / repository_policy.py',
                               'review': '沿用现有本地限制；未重新调查上游政策'}],
                 'allowed_kinds': ALL_KINDS,
                 'required_label': 'accepted'},
 'mlflow/mlflow': {'reason': 'issue 须有 ready 标签',
                   'evidence': [{'scope': 'repo',
                                 'source': 'RULES.md / repository_policy.py',
                                 'review': '沿用现有本地限制；未重新调查上游政策'}],
                   'allowed_kinds': ALL_KINDS,
                   'required_label': 'ready'},
 'modelcontextprotocol/python-sdk': {'reason': '外部 PR 须 maintainer 先 assign；CONTRIBUTING 明令「不要用 agent '
                                               '发认领评论」「若 agent 在自主提 PR 请关掉本仓」',
                                     'evidence': [{'scope': 'repo',
                                                   'observed_at': '2026-10-18',
                                                   'source': '.workbuddy/memory/blocked-repos.md',
                                                   'review': '每次核验当前账号分配状态'},
                                                  {'scope': 'repo',
                                                   'observed_at': '2026-11-03',
                                                   'source': 'https://github.com/modelcontextprotocol/python-sdk/blob/main/CONTRIBUTING.md',
                                                   'review': '三处叠加：①外部 PR 仅当 maintainer 把 issue assign 给你，否则 '
                                                             'bot 自动关；②「Comments that only ask to be '
                                                             "assigned don't factor into it, so please skip "
                                                             "those (and don't have an agent post "
                                                             'them)」；③「If you have an agent filing PRs '
                                                             'against open issues autonomously, please turn '
                                                             'it off for this '
                                                             'repository」，且须真人实际踩过问题并读过输出。判定为自主流水线停投（#3813 '
                                                             'add_template 重复告警因此弃），只准备本地材料'}],
                                     'allowed_kinds': (),
                                     'manual_gate': True,
                                     'requires_assignment': True,
                                     'interaction_hold': 'CONTRIBUTING 要求真人实际复现并负责，agent 自主 '
                                                         'PR/认领评论会被无预警关闭；本项目停投，只准备本地材料'},
 'modelcontextprotocol/servers': {'reason': 'handoff-only：修复推 fork 后请维护者代开 PR',
                                  'evidence': [{'scope': 'repo',
                                                'observed_at': '2026-10-24',
                                                'source': '.workbuddy/memory/2026-10-24.md',
                                                'review': 'POST /pulls 对本账号 404（两次复现；issue '
                                                          '评论仍可发）；handoff-only：修复推 fork + issue 留 compare '
                                                          '链接请维护者代开（time 服务器 LOCAL_TIMEZONE 修复先例，分支 '
                                                          'fix/time-docker-env-entrypoint）。python-sdk 的 '
                                                          'assign 门禁独立存在'}],
                                  'allowed_kinds': (),
                                  'manual_gate': True},
 'netflix/metaflow': {'reason': 'AGENTS_EXTERNAL.md：①「PRs without a linked, maintainer-acknowledged issue '
                                'will be closed regardless of quality」，issue 须 open、未指派且有维护者明确同意的方案；②「STOP '
                                'if: Typo/comment/docstring fix → closed」，文档类也不收；③ core '
                                'runtime（runtime.py/task.py/flowspec.py/datastore/…）另需先讨论。issue '
                                '未获维护者回复即不可开工（#3432 validate_tag 错误消息因此弃）',
                      'evidence': [{'scope': 'repo',
                                    'source': 'RULES.md / repository_policy.py',
                                    'review': '沿用现有本地限制；未重新调查上游政策'}],
                      'allowed_kinds': (),
                      'manual_gate': True},
 'openai/openai-agents-python': {'reason': '「Pull requests are limited to repository collaborators. We do '
                                           'not accept pull requests from non-collaborators, including '
                                           'documentation or example changes.」→ 外部零 PR 通道，与 AI '
                                           '政策无关的硬门槛。整仓跳过（#5493 Windows 编码 issue 因此弃）。附注 AGENTS.md 另有「Never '
                                           'push, open a PR, or otherwise mutate GitHub」，同向',
                                 'evidence': [{'scope': 'repo',
                                               'observed_at': '2026-11-03',
                                               'source': 'https://github.com/openai/openai-agents-python/blob/main/CONTRIBUTING.md',
                                               'review': '「Pull requests are limited to repository '
                                                         'collaborators. We do not accept pull requests from '
                                                         'non-collaborators, including documentation or '
                                                         'example changes.」→ 外部零 PR 通道，与 AI '
                                                         '政策无关的硬门槛。整仓跳过（#5493 Windows 编码 issue 因此弃）。附注 '
                                                         'AGENTS.md 另有「Never push, open a PR, or otherwise '
                                                         'mutate GitHub」，同向'}],
                                 'allowed_kinds': (),
                                 'blocked': True},
 'openhands/enterprise': {'reason': 'POST /pulls 对本账号 404（两次复现；GET /pulls 正常，仓内 30 个开放 PR）——handoff-only：修复推 '
                                    'fork 后在 OpenHands/OpenHands（原 All-Hands-AI/OpenHands，307 迁移）的 issue 留 '
                                    'compare 链接请维护者代开（bootstrap 可选脚本修复先例，分支 fix/bootstrap-optional-scripts）',
                          'evidence': [{'scope': 'repo',
                                        'observed_at': '2026-10-29',
                                        'source': '.workbuddy/memory/2026-10-26.md',
                                        'review': 'POST /pulls 对本账号 404（两次复现；GET /pulls 正常，仓内 30 个开放 '
                                                  'PR）——handoff-only：修复推 fork 后在 OpenHands/OpenHands（原 '
                                                  'All-Hands-AI/OpenHands，307 迁移）的 issue 留 compare '
                                                  '链接请维护者代开（bootstrap 可选脚本修复先例，分支 '
                                                  'fix/bootstrap-optional-scripts）'}],
                          'allowed_kinds': ALL_KINDS},
 'openhands/openhands': {'reason': 'PR 描述含真人专属段：模板首行必须是 `HUMAN:`，`.github/scripts/check_pr_description.py` '
                                   '要求该段 ≥20 字符并勾选 human-tested，且模板明写「Just running unit tests is NOT '
                                   'sufficient」须 e2e 证据（日志/截图）。真人声明不能代签',
                         'evidence': [{'scope': 'repo',
                                       'source': 'RULES.md / repository_policy.py',
                                       'review': '沿用现有本地限制；未重新调查上游政策'}],
                         'allowed_kinds': (),
                         'manual_gate': True},
 'pandas-dev/pandas': {'reason': '仓根 AGENTS.md「Interactions on GitHub」明写：不得代表用户执行任何 issue/PR 相关动作（含推代码、开 '
                                 'issue/PR、回复 issue/PR/评审）；agent 生成文本须由用户标注。判定为禁 agent 自主投稿，整仓跳过（#71819 因此弃）',
                       'evidence': [{'scope': 'repo',
                                     'observed_at': '2026-11-01',
                                     'source': 'https://github.com/pandas-dev/pandas/blob/main/AGENTS.md',
                                     'review': '仓根 AGENTS.md「Interactions on GitHub」明写：不得代表用户执行任何 issue/PR '
                                               '相关动作（含推代码、开 issue/PR、回复 issue/PR/评审）；agent 生成文本须由用户标注。判定为禁 '
                                               'agent 自主投稿，整仓跳过（#71819 因此弃）'}],
                       'allowed_kinds': (),
                       'blocked': True,
                       'interaction_hold': 'AGENTS.md 禁止代表用户执行任何 issue/PR 动作；只准备本地材料，须用户本人投稿'},
 'prefecthq/fastmcp': {'reason': '贡献门禁要求外部 PR 必须同时「链接 issue」且「作者已被 assign」（除非 issue 带 `prs welcome`），否则 bot '
                                 '自动关闭；同一页又明令「Do not post comments just to claim an issue or ask to be '
                                 'assigned」+「The issue reporter has first claim」→ 无自助通道，须 maintainer 主动 '
                                 'assign 才能落地',
                       'evidence': [{'scope': 'repo',
                                     'observed_at': '2026-11-04',
                                     'source': 'https://raw.githubusercontent.com/PrefectHQ/fastmcp/main/docs/development/contributing.mdx',
                                     'review': '「Issues and assignment」节：外部 PR 须带 auto-close 关键字链接 '
                                               'issue，且作者须已被 assign（除非 issue 带 `prs welcome` 标签），两者缺一 bot '
                                               '自动关闭；同节又写「Do not post comments just to claim an issue or ask '
                                               'to be assigned」「The issue reporter has first claim on '
                                               'implementing the fix」。即无自助认领通道，只能等维护者主动 '
                                               'assign（#6294/#6295/#6296 因此弃）'}],
                       'allowed_kinds': (),
                       'manual_gate': True},
 'psf/requests': {'reason': '本地禁投记录，解除前须核验账号权限',
                  'evidence': [{'scope': 'repo',
                                'source': 'RULES.md / repository_policy.py',
                                'review': '沿用现有本地限制；未重新调查上游政策'}],
                  'allowed_kinds': (),
                  'blocked': True},
 'pydantic/pydantic-ai': {'reason': '写入通道被封：`gh issue comment` (GraphQL addComment) 返回「User is blocked」，REST '
                                    'POST /issues/12367/comments 返回 403 Blocked——两个独立端点复现，非超时/限流。该仓 '
                                    '.github/workflows/pr-guard.yml 规定非 docs-only 且 PR 作者≠issue 作者的 PR，须把 '
                                    'issue assign 给作者，否则自动关闭；既然评论被封就无法请求 assign，整仓不可投。原 ASSIGN_REPOS 条目升级为 '
                                    'BLOCKED_REPOS（#12367 mixed-base 修复已完成本地验证但无法提交）',
                          'evidence': [{'scope': 'repo',
                                        'observed_at': '2026-11-04',
                                        'source': '.workbuddy/memory/2026-11-04.md',
                                        'review': '写入通道被封：`gh issue comment` (GraphQL addComment) 返回「User is '
                                                  'blocked」，REST POST /issues/12367/comments 返回 403 '
                                                  'Blocked——两个独立端点复现，非超时/限流。该仓 '
                                                  '.github/workflows/pr-guard.yml 规定非 docs-only 且 PR '
                                                  '作者≠issue 作者的 PR，须把 issue assign 给作者，否则自动关闭；既然评论被封就无法请求 '
                                                  'assign，整仓不可投。原 ASSIGN_REPOS 条目升级为 BLOCKED_REPOS（#12367 '
                                                  'mixed-base 修复已完成本地验证但无法提交）'}],
                          'allowed_kinds': (),
                          'blocked': True},
 'pypa/packaging': {'reason': 'blocked.reasons 记录 #934 维护者要求勿再开 PR；本地补充见 '
                              '.workbuddy/memory/2026-10-19.md；待明确允许后复核，未重新调查上游政策',
                    'evidence': [{'scope': 'repo',
                                  'observed_at': '2026-10-19',
                                  'source': 'tools/quality_repos.json',
                                  'review': 'blocked.reasons 记录 #934 维护者要求勿再开 PR；本地补充见 '
                                            '.workbuddy/memory/2026-10-19.md；待明确允许后复核，未重新调查上游政策'}],
                    'allowed_kinds': (),
                    'blocked': True,
                    'interaction_hold': '维护者已要求勿再开 PR；本地暂缓自动跟进写入，沟通范围待复核，保留只读观察'},
 'python-markdown/markdown': {'reason': '禁止 agent 自主提交/评论，须由作者本人理解并参与',
                              'evidence': [{'scope': 'repo',
                                            'observed_at': '2026-10-23',
                                            'source': 'https://python-markdown.github.io/contributing/#ai-contributions',
                                            'review': '禁止 agent 自主提交 issue、PR、评论；只准备本地材料，作者须自行理解并参与'}],
                              'allowed_kinds': (),
                              'manual_gate': True,
                              'interaction_hold': '只准备本地修复和答复材料；作者须按仓库政策亲自参与沟通'},
 'python/mypy': {'reason': '本地降级（非上游封锁）：外部修复 PR 三连无声离场（#22288、#22291 未合并关闭且零人工互动，#22056 被维护者自有 PR 取代；唯一合并 '
                           '#22058 为文档区）。停止投递新的 mypy 修复 PR，纯文档类可例外；在飞为零，已关闭项不申诉',
                 'evidence': [{'scope': 'repo',
                               'observed_at': '2026-10-26',
                               'source': '.workbuddy/memory/2026-10-26.md',
                               'review': '本地降级（非上游封锁）：外部修复 PR 三连无声离场（#22288、#22291 未合并关闭且零人工互动，#22056 被维护者自有 '
                                         'PR 取代；唯一合并 #22058 为文档区）。停止投递新的 mypy 修复 PR，纯文档类可例外；在飞为零，已关闭项不申诉'}],
                 'allowed_kinds': ('docs',)},
 'sqlalchemy/sqlalchemy': {'reason': '本地禁投记录，解除前须核验账号权限',
                           'evidence': [{'scope': 'repo',
                                         'source': 'RULES.md / repository_policy.py',
                                         'review': '沿用现有本地限制；未重新调查上游政策'}],
                           'allowed_kinds': (),
                           'blocked': True},
 'stanfordnlp/dspy': {'reason': '本地禁投记录，解除前须核验账号权限',
                      'evidence': [{'scope': 'repo',
                                    'source': 'RULES.md / repository_policy.py',
                                    'review': '沿用现有本地限制；未重新调查上游政策'}],
                      'allowed_kinds': (),
                      'blocked': True},
 'ukgovernmentbeis/inspect_ai': {'reason': 'issue 须有 accepted 标签',
                                 'evidence': [{'scope': 'repo',
                                               'source': 'RULES.md / repository_policy.py',
                                               'review': '沿用现有本地限制；未重新调查上游政策'}],
                                 'allowed_kinds': ALL_KINDS,
                                 'required_label': 'accepted'},
 'useblocks/sphinx-needs': {'reason': '本地禁投记录，解除前须核验账号权限',
                            'evidence': [{'scope': 'repo',
                                          'source': 'RULES.md / repository_policy.py',
                                          'review': '沿用现有本地限制；未重新调查上游政策'}],
                            'allowed_kinds': (),
                            'blocked': True},
 'vllm-project/vllm': {'reason': '本机缺少可靠构建与测试条件',
                       'evidence': [{'scope': 'repo',
                                     'source': 'RULES.md / repository_policy.py',
                                     'review': '沿用现有本地限制；未重新调查上游政策'}],
                       'allowed_kinds': (),
                       'non_testable': True}}

# Compatibility views: these are derived, never separately maintained policy.
BLOCKED_OWNERS = {key for key, rule in OWNER_POLICIES.items() if rule.get("blocked")}
BLOCKED_REPOS = {key for key, rule in REPOSITORY_POLICIES.items() if rule.get("blocked")}
ASSIGN_OWNERS = {key for key, rule in OWNER_POLICIES.items() if rule.get("requires_assignment")}
ASSIGN_REPOS = {key for key, rule in REPOSITORY_POLICIES.items() if rule.get("requires_assignment")}
REQUIRED_LABELS = {key: rule["required_label"] for key, rule in REPOSITORY_POLICIES.items()
                   if rule.get("required_label")}
MANUAL_GATES = {key: rule["reason"] for key, rule in REPOSITORY_POLICIES.items() if rule.get("manual_gate")}
NON_TESTABLE = {key for key, rule in REPOSITORY_POLICIES.items() if rule.get("non_testable")}
INTERACTION_HOLDS = {key: rule["interaction_hold"] for key, rule in REPOSITORY_POLICIES.items()
                     if rule.get("interaction_hold")}
POLICY_EVIDENCE = {key: rule["evidence"][-1] for key, rule in
                   {**OWNER_POLICIES, **REPOSITORY_POLICIES}.items()}

# Pool slug hygiene (2026-10-30): the scan_recon*/scan_agent2 pool lists carry slugs
# that 404 every round or have moved orgs. `_norm` in monitor_fresh (and every
# pool builder that calls build_tiers) applies this map: value = the correct
# slug, or None = unresolvable, drop the entry. Evidence: fresh-lane ERROR lines
# ("query incomplete") repeated every round for these slugs.
DEAD_OR_RENAMED = {
    "aiohttp-libs/aiohttp": "aio-libs/aiohttp",       # aiohttp moved to aio-libs
    "pyjwt/jwt": "jpadilla/pyjwt",                    # pyjwt lives under jpadilla
    "encode/httpx-ws": "frankie567/httpx-ws",         # httpx-ws lives under frankie567
    "daily-co/pipecat": "pipecat-ai/pipecat",         # pipecat moved to pipecat-ai
    "python-opencv/opencv-python": "opencv/opencv-python",
    "psf/pycodestyle": None,                          # pycqa/pycodestyle; pycqa is blocked
    "hegel-ai/promptic": None,                        # unresolvable (10-24 pool hygiene)
    "portkey-ai/portkey-python": None,                # unresolvable
    "pytest-dev/pytest-lazy-fixture": None,           # unresolvable
    "wnblm/nox": "wntrblm/nox",                       # nox: wnblm is a typo of wntrblm
}

# Issue-level suppressions for adjudications that survive dropping the repo name.
# Never put a repo-wide trait here; those belong in NON_TESTABLE / MANUAL_GATES.
# `updated_at` is the upstream state the decision was made against: when upstream
# moves (new comment, label, assignee), the suppression lapses so it cannot
# silently bury a candidate forever.
ISSUE_SUPPRESSIONS = {
    "huggingface/huggingface_hub#5109": {
        "observed_at": "2026-10-29",
        "updated_at": "2026-10-08T17:25:56Z",
        "reason": "不可复现(issue 级)：根因在第三方 CAS 返回 401 + 镜像站 + 间歇性失败，maintainer 已按环境问题排查，完整复现需约 47GB 下载",
    },
}


def issue_suppression(repo, number, updated_at=None):
    """Reuse an already-adjudicated issue-level rejection; empty means re-screen."""
    entry = ISSUE_SUPPRESSIONS.get(f"{repo}#{number}".lower())
    if not entry:
        return ""
    if not isinstance(updated_at, str) or not updated_at:
        return ""  # Missing state evidence never suppresses: re-screen instead.
    recorded = entry.get("updated_at")
    if not isinstance(recorded, str) or not recorded or updated_at != recorded:
        return ""  # Upstream moved since the decision; re-adjudicate.
    return f"issue 级已裁定({entry.get('observed_at', '?')}): {entry['reason']}"


def policy_reason(repo, labels=(), assignees=(), kind="bug"):
    """Empty means eligible. Omitted kind retains the historic bug-fix gate."""
    repo = repo.lower()
    owner = OWNER_POLICIES.get(repo.split("/", 1)[0], {})
    rule = REPOSITORY_POLICIES.get(repo, {})
    if owner.get("blocked") or rule.get("blocked"):
        return f"受限/禁投仓库: {repo}"
    if rule.get("manual_gate"):
        return "人工门禁: " + rule["reason"]
    if rule.get("non_testable"):
        return f"非可测仓(重构建/重依赖): {repo}"
    if not isinstance(assignees, (list, tuple)) or any(
            not isinstance(name, str) or not name for name in assignees):
        return "分配人数据无效，需重新核验"
    assigned = {name.lower() for name in assignees}
    if assigned - {ACCOUNT}:
        return "已被 assign 给其他贡献者"
    if (owner.get("requires_assignment") or rule.get("requires_assignment")) and ACCOUNT not in assigned:
        return "assign 门禁仓: 须先分配给当前账号"
    required = rule.get("required_label")
    if required and (not isinstance(labels, (list, tuple)) or
                     required not in {label.lower() for label in labels if isinstance(label, str)}):
        return f"issue-readiness 门禁仓: 缺少 {required} 标签"
    for restriction in (owner, rule):
        if "allowed_kinds" in restriction and kind not in restriction["allowed_kinds"]:
            return "贡献类别门禁: " + restriction["reason"]
    return ""
