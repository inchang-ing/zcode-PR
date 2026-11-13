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

REPOSITORY_POLICIES = {'all-hands-ai/openhands': {'reason': '改名仓旧 slug 兜底门禁：该仓已迁至 OpenHands/OpenHands，'
                                                             '新 slug 的 PR 模板要求 `HUMAN:` 真人专属段（≥20 字符且须 '
                                                             'human-testify 勾选），属人工门禁。按字符串查 policy_reason 的 '
                                                             '链路不认重定向，只查旧 slug 会返回空并把门禁仓误判为可投；'
                                                             'DEAD_OR_RENAMED 已同步加映射（池层规范化），此处补兜底',
                                                  'evidence': [{'scope': 'repo',
                                                                'observed_at': '2026-11-09',
                                                                'source': 'tools/repository_policy.py (OpenHands/OpenHands 条目)',
                                                                'review': '反向自查发现 dispositions 中 4 条 '
                                                                          'all-hands-ai/openhands#* 均记 ready-for-dev + '
                                                                          'HUMAN 真人段门禁，但 policy_reason(旧 slug) 返回空；'
                                                                          '新 slug 已编码，属改名 slug 伪阳性，按规律 118 '
                                                                          '补映射 + 旧 slug 兜底'}],
                                                  'allowed_kinds': (),
                                                  'manual_gate': True},
 'apache/iceberg-python': {'reason': 'AGENTS.md「GitHub Write Approval」把 GitHub 设为默认只读：'
                                              '任何写操作（issue/PR/评论/review/标签/分支/合并）须用户在本会话中'
                                              '针对该具体动作明确批准，并先展示完整拟发内容；且明写「Never treat a '
                                              'request to investigate, implement, fix, draft, or prepare as approval '
                                              'to write to GitHub」，故通用流水线授权不构成批准。无人值守轮次无法'
                                              '取得逐动作批准，须账号持有人本人在会话内逐项确认后方可解禁',
                                    'evidence': [{'scope': 'repo',
                                                  'observed_at': '2026-11-09',
                                                  'source': 'https://github.com/apache/iceberg-python/blob/main/AGENTS.md',
                                                  'review': '默认分支 main 的 AGENTS.md「GitHub Write Approval」段：'
                                                            'Never modify GitHub state without explicit user approval '
                                                            'for that specific action in the current session; Ask first '
                                                            'before any GitHub write... This includes creating, editing, '
                                                            'or deleting issues, pull requests, comments, reviews, '
                                                            'labels, and branches; Never treat a request to investigate, '
                                                            'implement, fix, draft, or prepare as approval. 该仓 1168 星'
                                                            '但属 ASF 基金会官方仓故准入合格；本轮 #4318 五项全清、纯 '
                                                            'Python 且带最小复现，policy_reason 却返回空，险些被当干净候选。'
                                                            '属会话内逐动作批准型人工门禁（非整仓禁投），双通道都须封闭'}],
                                    'allowed_kinds': (),
                                    'manual_gate': True,
                                    'interaction_hold': 'AGENTS.md 要求任何 GitHub 写动作须用户在本会话对具体动作'
                                                        '明确批准；本流水线不发认领评论、不回复评审、不开 PR、不建分支，'
                                                        '只保留只读观察'},
 'agno-agi/agno': {'reason': 'issue 须有 ready 标签',
                     'evidence': [{'scope': 'repo',
                                   'observed_at': '2026-11-08',
                                   'source': 'https://github.com/agno-agi/agno/blob/main/CONTRIBUTING.md',
                                   'review': 'CONTRIBUTING「Link to a Ready Issue」明写 Only start work once a maintainer '
                                             'has added the `ready` label；外部贡献者 PR 若关联 issue 未打 `ready` 会由 '
                                             'pr-lint.yml 自动关闭且仅维护者可重开（联网复核原文 + 仓库确有 ready/'
                                             'issue-not-ready 两个标签）。dispositions.json 中 #11465/#11466/#11469/'
                                             '#11470/#11473/#11478/#11509/#11510/#11511/#11513/#11514 共 11 条均记此门禁，'
                                             '但 policy_reason() 返回空 → 2026-11-08 本轮 #11521 险些被当成干净候选。'
                                             '用 required_label 而非 blocked：带 `ready` 标签的 issue 仍可投，不误杀未来干净候选'}],
                     'allowed_kinds': ALL_KINDS,
                     'required_label': 'ready'},
 'ansible/ansible': {'reason': '当前账号贡献被以自主投稿关闭；停止本项目自动投稿和跟进写入，待维护者明确允许后复核',
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
 'embedchain/embedchain': {'reason': '改名仓旧 slug 兜底门禁：该仓已迁至 mem0ai/mem0，适用同一 '
                                     'issue-readiness 门禁（issue 须有 accepted 标签）。发现层按请求 slug '
                                     '原样记录候选，用旧 slug 查 policy_reason 会返回空并把门禁仓误判为可投；'
                                     'DEAD_OR_RENAMED 已同步加映射（池层规范化去重），此处补兜底',
                           'evidence': [{'scope': 'repo',
                                         'observed_at': '2026-11-13',
                                         'source': 'https://github.com/mem0ai/mem0/issues/7906',
                                         'review': 'round 187 全池 --all 同时产出 embedchain/embedchain#7906 与 '
                                                   'mem0ai/mem0#7906 两条同物理 issue（同一 reporter TylerES777、'
                                                   '同标题同标签）。gh api repos/embedchain/embedchain 返回 '
                                                   'full_name=mem0ai/mem0、html_url=https://github.com/mem0ai/mem0；'
                                                   'gh issue view 7906 -R embedchain/embedchain 的 url 也是 '
                                                   'mem0ai/mem0。按规律 118 以 html_url 判政策：新 slug 有 '
                                                   'required_label=accepted 门禁，policy_reason(旧 slug) 却为空。'
                                                   '池 CORE 存新 slug、G 存旧 slug，两者各查一次造成重复扫描'}],
                           'allowed_kinds': ALL_KINDS,
                           'required_label': 'accepted'},
 'encode/httpx': {'reason': '本地禁投记录，解除前须核验账号权限',
                  'evidence': [{'scope': 'repo',
                                'source': 'RULES.md / repository_policy.py',
                                'review': '沿用现有本地限制；未重新调查上游政策'}],
                  'allowed_kinds': (),
                  'blocked': True},
 'falconry/falcon': {'reason': 'CONTRIBUTING「Use of LLMs ("AI")」明写「autonomous coding agents must never open '
                                'pull requests on their own」「A human contributor remains responsible for every '
                                'submitted change」；AGENTS.md「Operator boundaries」进一步禁止 agent 以任何机制创建/'
                                '提交 PR（含推分支后接受 GitHub 建议、draft PR），且「opening issues, posting comments '
                                'or reviews, and editing pull request metadata are all reserved for the human '
                                'operator」，只许准备改动与验证证据后请 human operator 代开。故：可改代码、不可自主开 PR、'
                                '不可发认领评论/回复评审。AI 参与须在 PR 描述披露且不得写 Co-authored-by。'
                                '（2026-11-08 联网复核原文；此前该仓 #2756/#2767 已有弃单但未编码，'
                                'policy_reason 返回空导致本轮 #2797 险些被当干净候选）',
                     'evidence': [{'scope': 'repo',
                                   'observed_at': '2026-11-08',
                                   'source': 'https://github.com/falconry/falcon/blob/master/CONTRIBUTING.md',
                                   'review': 'CONTRIBUTING 第 184-203 行 Use of LLMs ("AI") 节 + '
                                             'https://github.com/falconry/falcon/blob/master/AGENTS.md '
                                             'Operator boundaries 节（AGENTS.md 自 2026-07-18 起在默认分支 master）。'
                                             '两处一致禁止 autonomous agent 自主开 PR；AGENTS.md 另禁 agent 发 '
                                             'issue/评论/review 等一切对外动作，须 human operator 执行。'
                                             '注意 CONTRIBUTING 给人类贡献者的「留个 comment 避免重复」建议 '
                                             '不适用于 agent（AGENTS.md 明禁），因此交互通道整体封闭'}],
                     'allowed_kinds': (),
                     'manual_gate': True,
                     'interaction_hold': 'AGENTS.md 禁止 agent 自主开 PR，且禁止发 issue/评论/review/'
                                         '改 PR 元数据；只准备本地材料与验证证据，须 human operator 代开 PR，'
                                         '本流水线不发认领评论、不回复评审、不做任何对外写入'},
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
 'googleapis/python-genai': {
     'reason': 'CONTRIBUTING.md 全文仅一句「The Google Gen AI SDK will accept contributions in the '
               'future.」（当前不接收外部贡献）；外部 PR 另须 Google '
               'CLA（cla.developers.google.com，账号持有者网页签署，无人值守流水线无法代办，PR 会停在 '
               'cla:no）。历史 #3262/#3308/#3313 三条 disposition 均据此判人工门禁，但结论只落在 '
               'dispositions.json，policy_reason() 返回空有误投风险（2026-11-08 本轮 #3317 复核后补编码）',
     'evidence': [{'scope': 'repo',
                   'observed_at': '2026-11-08',
                   'source': 'https://github.com/googleapis/python-genai/blob/main/CONTRIBUTING.md',
                   'review': '联网复核 CONTRIBUTING.md 原文＝「The Google Gen AI SDK will accept '
                             'contributions in the future.」；dispositions.json 中 #3262/#3308/#3313 三条均记 '
                             '「外部 PR 须先签 Google CLA（本人网页签署，流水线无法代办）」；本轮 #3317 正文另为 '
                             '方案语义待定（作者反问维护者 0.5s/8s 是否保留为 Interactions 专属）'}],
     'allowed_kinds': (),
     'manual_gate': True},
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
 'huggingface/accelerate': {"reason": "CONTRIBUTING 新版（2026-11 过渡期，SunMarc 据此批量关闭存量 PR）要求每个 PR 描述含"
                            "「## Use case」段（账号持有人真实使用场景；agent 只能写用户提供的用例，没有则须如实写"
                            "「I do not have a use case」），空用例/超 250 词的 PR 在 open/reopen 时被 bot 自动关闭，"
                            "须维护者人工重开。本流水线无真实用例可填 → 存量 PR 不可合规重开（#4504/#4507 2026-11-13 "
                            "被过渡期批量关闭未合并）",
                      'evidence': [{'scope': 'repo',
                                    'source': 'CONTRIBUTING.md via gh api (2026-11-14)',
                                    'observed_at': '2026-11-14',
                                    'note': '关闭评论: "We have introduced a new contribution guide and are closing existing PRs as we transition to the updated process"'}],
                      'allowed_kinds': (),
                      'blocked': False,
                      'interaction_hold': '须账号持有人提供真实 use case 并本人复核后才可参与'},
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
 'huggingface/transformers': {
     'reason': 'CONTRIBUTING 开头 WARNING 明写「we\'d also ask autonomous agents not to open any PRs or issues '
               'for the moment」「PRs that appear to be agent-written will probably be closed without review, '
               'and we may block users who do this repeatedly」，AGENTS.md「Before opening a PR」另写 '
               '「First-time contributors should not submit agent-written PRs or issues」。本账号在该仓零历史 PR '
               '（即 first-time），两条禁令同时命中 → 整仓禁投（2026-11-08 联网复核原文；此前仅记在 blocked-repos.md，'
               'policy_reason 为空有误投风险，#50476 批量 Idea 提案因此前置剔除）',
     'evidence': [{'scope': 'repo',
                   'observed_at': '2026-11-08',
                   'source': 'https://github.com/huggingface/transformers/blob/main/CONTRIBUTING.md',
                   'review': 'CONTRIBUTING WARNING 要求 autonomous agents 不得开 PR/issue，agent-written PR '
                             '会被直接关闭甚至封号；AGENTS.md 另禁 first-time contributor 提交 agent PR/issue'}],
     'allowed_kinds': (),
     'blocked': True,
     'interaction_hold': 'CONTRIBUTING 不接受自主投稿；只做只读观察，不代开 PR/issue、不代发认领评论'},
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
 'livekit/agents': {'reason': '首个 PR 须签 LiveKit CLA：CONTRIBUTING「On your first pull request, the CLA '
                              'Assistant bot will give you a link to sign this project\'s Contributor License '
                              'Agreement」——标准 CLA Assistant 网页 OAuth，须账号持有者本人签署，'
                              '非可评论自助签（custom-pr-sign-comment）通道，无人值守流水线无法代办。'
                              'dispositions 已有 #8367/#8380/#8405/#8406/#8426/#8427/#8438/#8441 共 8 条同源弃单，'
                              'policy_reason 却返回空（2026-11-09 反向自查发现）。判为人工门禁，'
                              '账号持有者签署后可复核解除，非整仓禁投',
                   'evidence': [{'scope': 'repo',
                                 'observed_at': '2026-11-09',
                                 'source': 'https://github.com/livekit/agents/blob/main/CONTRIBUTING.md',
                                 'review': '联网复核 CONTRIBUTING 第 37-38 行：「On your first pull request, '
                                           'the CLA Assistant bot will give you a link to sign this '
                                           'project\'s Contributor License Agreement, required to add your '
                                           'code to the repository.」为链接签署（标准 CLA Assistant 网页 '
                                           'OAuth），非评论式自助签；与 googleapis/python-genai 的 Google CLA '
                                           '同形态。历史 8 条弃单均记「须账号持有者网页签署」'}],
                   'allowed_kinds': (),
                   'manual_gate': True},
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
 'pydicom/pydicom': {'reason': '.github/PULL_REQUEST_TEMPLATE.md 开头明写「We do not accept AI-only PRs - they will '
                               'be closed」，要求 human-written summary，正文「We expect authors to have fully '
                               'reviewed any AI-generated code line by line」，且 checklist 须勾选「Author has '
                               'created all code and/or has reviewed AI-generated code line by line」。流水线无法'
                               '诚实提供人类撰写的总结或代声明未发生的逐行人工审阅，属人工门禁（human operator '
                               '亲自审阅并撰写后可解除），非整仓禁投——该仓外部人类 PR 正常接收。'
                               '（2026-11-09 本轮 #2425 已完成全部本地修复与判别力验证，却因只读到 CONTRIBUTING '
                               '未读 PR 模板而险些投稿；policy_reason 当时返回空）',
                     'evidence': [{'scope': 'repo',
                                   'observed_at': '2026-11-09',
                                   'source': 'https://github.com/pydicom/pydicom/blob/main/.github/PULL_REQUEST_TEMPLATE.md',
                                   'review': '联网复核模板原文：第 2-3 行「We do not accept AI-only PRs - they '
                                             'will be closed. We expect a human-written (and easily '
                                             'human-readable) summary」；正文「We expect authors to have fully '
                                             'reviewed any AI-generated code line by line to ensure '
                                             'correctness.」；第 23 行 checklist「Author has created all code '
                                             'and/or has reviewed AI-generated code line by line」。模板由 '
                                             '#2366 于 2026-10-24T17:55:50Z 修订（commit 705332479c），'
                                             'CONTRIBUTING.md 无对应条款，仅 grep DCO/CLA 关键词会漏检。'
                                             '政策不禁止 issue 评论，故只编 manual_gate、不编 interaction_hold。'}],
                     'allowed_kinds': (),
                     'manual_gate': True},
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
 'sympy/sympy': {'reason': '人工门禁（AI 政策 + AGENTS.md 双约束）：AI 生成代码政策「New Contributors」段明写新贡献者实质由 AI 生成的 '
                           'issue/discussion/PR 大概率直接关闭，且「Do not waste developers time by submitting code that is fully or mostly '
                           'generated by AI」；「Communication」段禁止在开发者沟通中由 AI 代发言（仅允许翻译/语法润色），明写 '
                           '「Human-to-human communication is essential」；AGENTS.md 另要求 PR 描述优先由用户本人撰写、AI 代写须逐处披露、'
                           '所有代码须经真人审阅且由开 PR 的真人负全责。无人值守流水线既无法提供真人沟通，也不能代声明真人审阅 → 准入与交互写动作一并停。'
                           '归类 manual_gate 而非 blocked：AGENTS.md 本身给出了真人在场时 agent 开 PR 的合规路径（标题/正文首字符 robot 标记 + '
                           '必填的 AI Generation Disclosure 段），故真人主导后可复核解除',
                 'evidence': [{'scope': 'repo',
                               'observed_at': '2026-11-11',
                               'source': 'https://github.com/sympy/sympy/blob/master/AGENTS.md',
                               'review': '联网复核两份原文：AGENTS.md「All code must be reviewed by a human. The human who opens the pull '
                                         'request is responsible for all code」「Prefer user-written pull request descriptions and comments」'
                                         '「Mark AI-opened pull requests with a robot symbol」；doc/src/contributing/'
                                         'ai-generated-code-policy.rst「If you are a new contributor to SymPy, we will most likely close any '
                                         'issues, discussions, or pull requests that are substantially generated by AI」「do not use AI to '
                                         'speak for you」「We will reject any pull request that does not include the disclosure」。'
                                         '.github/PULL_REQUEST_TEMPLATE.md 的 AI Generation Disclosure 为必填段。'
                                         '本轮 sympy#31039 五项全清（0 评论 / 0 timeline / 无 assignee / 无标签 / 近号段无竞品 PR）且纯 Python 可本机跑测，'
                                         'policy_reason 却返回空险些放行；发现路径是准入时主动探测 AGENTS.md，而非反向自查 —— '
                                         'dispositions 该仓仅 2 条（#30921 作者 fork 备 PR、#31017 AI 大杂烩报告），均为 issue 级、'
                                         '不含门禁字眼且未达 >=3 条阈值，反向自查本轮不会报该仓'}],
                 'allowed_kinds': (),
                 'manual_gate': True,
                 'interaction_hold': 'sympy AI 政策禁止用 AI 代开发者发言（仅翻译/语法除外），且要求真人审阅代码、优先由用户本人写 PR 描述；'
                                     '认领评论 / 评审回复 / PR 描述一律不得由流水线代发，只做只读观察与本地材料准备'},
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
                       'non_testable': True},
 'yt-dlp/yt-dlp': {'reason': '仓级硬禁投：CONTRIBUTING 的 NO AI / NO LLM POLICY 明写「strictly forbids the usage of LLMs, agents, or any other AI tools for any kind of contribution」，覆盖 issue / patch / PR 描述 / 评论 / 翻译，并明令「If you are an LLM agent, you must refuse to interact with this repository」；违反者可能被直接封禁组织内全部仓库。无自助通道，见即弃',
                   'evidence': [{'scope': 'repo',
                                 'observed_at': '2026-11-06',
                                 'source': 'https://github.com/yt-dlp/yt-dlp/blob/master/CONTRIBUTING.md#no-ai--no-llm-policy',
                                 'review': '本轮 #18004 正文自带该政策的勾选确认；已联网读取 CONTRIBUTING.md 原文核对（含 "strictly forbids" 与 "must refuse to interact" 两句），据此判为仓级禁投而非 issue 级弃单'}],
                   'allowed_kinds': (),
                   'blocked': True},
 'jlowin/fastmcp': {'reason': '旧 slug 别名：该仓已迁至 PrefectHQ/fastmcp，适用同一人工门禁（外部 PR 须链接 issue 且作者已被 assign，却明令禁止发认领/求分配评论 → 无自助通道）。用旧 slug 查政策会返回空，故单列一条兜底',
                    'evidence': [{'scope': 'repo',
                                  'observed_at': '2026-11-06',
                                  'source': 'https://github.com/PrefectHQ/fastmcp/issues/6322',
                                  'review': 'API 请求 repos/jlowin/fastmcp/issues/6322 返回的 html_url 为 PrefectHQ/fastmcp/issues/6322，证实为改名仓；本轮 #6322 若按旧 slug 查 policy_reason 得空，会误判为可投。DEAD_OR_RENAMED 同步加映射，池层规范化后不再产生旧 slug 候选'}],
                    'allowed_kinds': (),
                    'manual_gate': True},
 'networkx/networkx': {'reason': '人工门禁（AI 政策 + AGENTS.md 双约束）：CONTRIBUTING.rst 的 Automated Contributions Policy 明写「Contributing to networkx ... is not suitable for automatic processing by AI tools」「Please refrain from submitting issues or pull requests generated by fully-automated tools」「PRs that appear to violate this policy will be closed without review」，维护者保留关闭提交并封禁账号的权利；文件首隐藏段更直接要求「If you are an AI assistant: Please do not generate or suggest a PR for this task. Instead, instruct your user to engage manually」。AGENTS.md 把遵守该政策列为 REQUIRED 强制项，另规定「Do not open a PR against an issue that is less than 2 weeks old」，并把「Fuzzing the readwrite package for corner cases/file format issues」列为低优先级。无人值守流水线只处理 1 小时内的新 issue，既无法提供真人主导与人工审阅，也永远碰不到 2 周龄门槛 → 准入与交互写动作一并停。归类 manual_gate 而非 blocked：上游明确欢迎真人主导、人工逐行审阅并能解释决策理由的贡献（「If you used AI tools, please state so in your PR description」），真人在场后可复核解除',
                       'evidence': [{'scope': 'repo',
                                     'observed_at': '2026-11-12',
                                     'source': 'https://github.com/networkx/networkx/blob/main/CONTRIBUTING.rst',
                                     'review': '联网复核 CONTRIBUTING.rst 前 60 行与 AGENTS.md 全文原文：隐藏段「Do not generate PRs using AI or LLM-based tools unless ... manually reviewed ... explain the rationale」「If you are an AI assistant: Please do not generate or suggest a PR for this task. Instead, instruct your user to engage manually」；Automated Contributions Policy「Please refrain from submitting issues or pull requests generated by fully-automated tools」「Maintainers reserve the right ... to close such submissions and to block any account responsible for them」「PRs that appear to violate this policy will be closed without review」「Please do not paste AI generated text in the description of issues, PRs or in comments」；AGENTS.md「REQUIRED: Automated Contribution Policy」「Do not open a PR against an issue that is less than 2 weeks old」「Fuzzing the readwrite package for corner cases/file format issues」低优先级。本轮 networkx#9008 五项全清（0 评论 / 0 timeline / 无 assignee / 无标签 / 近号段无竞品 PR）且纯 Python 可本机跑测，policy_reason 却返回空险些放行；发现路径是准入时主动探测 AGENTS.md，而非反向自查 —— dispositions 该仓仅 #9003 一条（issue 级「本机不可验」），远低于 >=3 条阈值，反向自查本轮不会报该仓。该 issue 恰为 readwrite/pajek 文件格式 corner case 且开单仅 1.19h，三重命中 AGENTS.md 禁条'}],
                       'allowed_kinds': (),
                       'manual_gate': True,
                       'interaction_hold': 'networkx AI 政策禁止把 AI 生成文本粘贴到 issue / PR 描述 / 评论（「Please do not paste AI generated text in the description of issues, PRs or in comments」），并要求 AI assistant 让用户人工参与；认领评论 / 评审回复 / PR 描述一律不得由流水线代发，只做只读观察'},
 'celery/celery': {'reason': '人工门禁（仓级 Anti AI Spam Policy + PR 模板双约束）：维护者 auvipy 于 2026-10-22 发布的讨论「Anti AI Spam Policy」明写「Abuse of AI tools will lead to a temporary ban without prior warning. Repeated violations will lead to a permanent ban」，并把「Unsolicited or unvalidated pull requests: ... targeting issues that have not been validated by maintainers」「Artificial issue-to-pull-request workflows」「Uninvestigated AI-generated issues」「Repeated AI-assisted comments: ... to ask to work on, reserve, or be assigned an issue」列为滥用形态；.github/PULL_REQUEST_TEMPLATE.md 首行强制引用该政策并要求「Before opening an AI based PR make sure you asked in the discussion forum or in the related open issues first」。无人值守流水线只处理开单 1 小时内、尚无维护者验证与回复的 issue，既无法满足「先询问」也无法满足「validated by maintainers」，且认领评论本身命中明禁项 → 准入与交互写动作一并停。归类 manual_gate 而非 blocked：政策原文「AI assistance is permitted ... but contributors must use it responsibly」，真人在场、事先询问且经维护者验证后可复核解除',
                   'evidence': [{'scope': 'repo',
                                 'observed_at': '2026-11-12',
                                 'source': 'https://github.com/celery/celery/discussions/10932',
                                 'review': '联网读取讨论 #10932 全文（作者 auvipy、General 分类、2026-10-22 发布；正文有 OpenWISP 复制粘贴残留但与本仓政策身份无关，PR 模板的强制引用已确认其为 celery 官方门禁）与 .github/PULL_REQUEST_TEMPLATE.md 前 12 行原文核对。本轮 celery#11078 / #11079 五项全清（0 评论 / timeline 无 xref / 无 assignee / 仅 Issue Type: Bug Report / 近号段仅同作者文档 PR 不覆盖），policy_reason 却返回空险些放行；发现路径是准入时主动探测 PR 模板与讨论政策，而非反向自查 —— dispositions 该仓 15 条历史弃单全为 issue 级（软认领 / 竞品 PR / 需真实 broker 不可验），无一门禁型，反向自查不会报该仓。政策发布日 2026-10-22 晚于我方该仓最后一个 PR #10845（2026-10-11 CLOSED），属新增门禁'}],
                   'allowed_kinds': (),
                   'manual_gate': True,
                   'interaction_hold': 'Anti AI Spam Policy 明禁「Repeated AI-assisted comments ... to ask to work on, reserve, or be assigned an issue」，PR 模板又要求 AI PR 前须先在讨论区或相关 issue 询问；认领评论 / 询问评论 / 评审回复 / PR 描述一律不得由流水线代发，只做只读观察'},
 'great-expectations/great_expectations': {'reason': '人工门禁（AGENTS.md CLA 硬停止 + CONTRIBUTING 认领标签双约束）：AGENTS.md「Before opening a pull request」明写「The CLA must be signed before the pull request is opened」「**If you are an agent, this is a hard stop.** The CLA is a legal affirmation by the human on whose behalf you are working — you cannot sign it, agree to it, or complete it for them ... If they have not, or you cannot reach them to ask, **stop and do not open the pull request.**」；签署入口为 Google Form，PR 上的 `@cla-bot check` 仅重跑检查、不代替签署，agent 无自助通道。CONTRIBUTING.md 第 1 节另设认领门禁「Issues open for claiming carry the `ready-for-work` label. To claim one, comment `/assign-me`」「If an issue doesn\'t carry `ready-for-work`, it isn\'t open for claiming yet」。无人值守流水线既不能代签法律协议，也不能在未获真人确认时开 PR，本轮 #12370 亦无该标签 → 准入与交互写动作一并停。归类 manual_gate 而非 blocked：真人在场、本人签署 CLA 并向 agent 确认后可复核解除',
                   'evidence': [{'scope': 'repo',
                                 'observed_at': '2026-11-12',
                                 'source': 'https://github.com/great-expectations/great_expectations/blob/develop/AGENTS.md',
                                 'review': '联网读取 AGENTS.md 全文（含 Integration test requirement / CLA hard stop / RFC 门槛 / 标题前缀 / 不改 changelog）与 CONTRIBUTING.md 第 1、3 节及 CLA 段原文核对。本轮 #12370 五项全清（0 评论 / timeline 0 events / 无 assignee / 无标签 / 号段 +1..+4 全 404）且正文给出可复现脚本，policy_reason 却返回空险些放行；同仓在飞 PR #12367 另改同一函数 ExpectationSuite.add_expectation（针对另一缺陷），改动会冲突。发现路径是准入时主动探测 AGENTS.md，而非反向自查 —— dispositions 该仓 5 条历史弃单全为 issue 级（Trino/Spark/SQLAlchemy 方言不可验、reporter 自开竞品 PR），无一门禁型'}],
                   'allowed_kinds': (),
                   'manual_gate': True,
                   'interaction_hold': 'AGENTS.md 明写 CLA 的「If you are an agent, this is a hard stop」且 CONTRIBUTING 要求用 `/assign-me` 命令认领并须 `ready-for-work` 标签；门禁未解除前认领评论 / 评审回复 / PR 一律不得由流水线代发，只做只读观察'},
 'kedro-org/kedro': {'reason': '人工门禁（贡献开放范围 + bot PR 须事先批准双约束）：CONTRIBUTING.md 明写「Only issues on the open source ticket board are open for community contributions. Other issues are not ready yet, the core team needs to review and scope them first before they can be picked up」；「Note for agents and bots」段明写「We do not welcome AI contributions by bots with no human in the loop. Pull requests must **not** be opened by bots or other automated tooling, unless specifically approved in advance by the project. To request permission to submit a PR, the human owner of the bot must open an issue for approval in advance of the PR\'s submission」。无人值守流水线既无法取得事先批准（须真人 bot 持有者先开 issue 申请），也无法确认 issue 已进入 curated ticket board → 准入与交互写动作一并停。归类 manual_gate 而非 blocked：上游认可真人把关的贡献（「Pull requests containing AI-generated code the contributor has not personally understood, tested, and verified will likely be closed without review」反向即欢迎真人理解/测试/验证过的 AI 辅助代码），真人在场并取得事先批准后可复核解除',
                     'evidence': [{'scope': 'repo',
                                   'observed_at': '2026-11-13',
                                   'source': 'https://github.com/kedro-org/kedro/blob/main/CONTRIBUTING.md',
                                   'review': '联网读取 CONTRIBUTING.md 贡献段原文：「Only issues on the open source ticket board are open for community contributions」+「Note for agents and bots：Pull requests must not be opened by bots or other automated tooling, unless specifically approved in advance by the project. To request permission to submit a PR, the human owner of the bot must open an issue for approval in advance」+ AI 代码须贡献者 personally understood/tested/verified。本轮 kedro#5856 五项全清（claim_check CLEAR 0 评论 / timeline 0 xref / 无 assignee / 仅 Community 标签 / 号段 +1..+3 全 404）且为纯 Python 编码缺陷（%load_node 在 Windows 用平台默认编码读源文件），本机恰为 Windows 可直接复现，policy_reason 却返回空险些开工；发现路径是准入时主动探测 CONTRIBUTING.md，而非反向自查 —— dispositions 该仓 4 条历史弃单（#5850/#5851 feature+assign、#5852/#5854 reporter 自开竞品 PR）全为 issue 级，无一门禁型，低于 >=3 条门禁弃单阈值，反向自查不会报该仓'}],
                     'allowed_kinds': (),
                     'manual_gate': True,
                     'interaction_hold': 'CONTRIBUTING「Note for agents and bots」禁止无人工把关的 bot 开 PR（须真人持有者先开 issue 取得事先批准），且仅 curated ticket board 上的 issue 开放社区贡献；门禁未解除前认领评论 / 评审回复 / PR 一律不得由流水线代发，只做只读观察'}}

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
    "jlowin/fastmcp": "prefecthq/fastmcp",            # 2026-11-06: moved to PrefectHQ (old slug resolves via redirect)
    "all-hands-ai/openhands": "openhands/openhands",  # 2026-11-09: org renamed (307 migration); old slug in dispositions
    "boltons/boltons": "mahmoud/boltons",  # 2026-11-11: POOL_E carried this 404 typo next to the correct slug; every
                                           # --all round reported "boltons query incomplete; watermark unchanged" and
                                           # maintainer_sweep emitted SKIP boltons. normalize_repos de-dupes the mapped
                                           # value against the existing mahmoud/boltons entry.
    "embedchain/embedchain": "mem0ai/mem0",  # 2026-11-13 round 187: org/repo renamed (307 redirect); CORE kept the new
                                              # slug while pool G kept the old one, so --all scanned one physical repo
                                              # twice. normalize_repos de-dupes the mapped value against the CORE entry.
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
