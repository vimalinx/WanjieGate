# 万界门泡泡 Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在本机浏览器中交付中央胶囊、真实 Jev 候选判断、拖拽融合，以及资料写作和股票研究两条可运行流程。

**Architecture:** 新增 `/demo` 泡泡入口，保留 `/` 工作台。候选和融合决策均通过 Runtime 能力调用，组合保存为 Artifact，运行使用现有 Command、Task、SQLite。前端状态与动画分开，服务端冻结所选资料并绑定运行身份。

**Tech Stack:** Python 3 标准库、原生 ES Modules、CSS、SQLite、OpenRouter Decisions API 与 Chat Completions。首版使用 Pointer Events 和稳定布局，不新增交互框架或物理引擎。

**Spec:** [已批准的设计规格](../specs/2026-09-27-bubble-demo-design.md)。用户于本会话发出“开始开发”，视为规格批准；本计划尚待审阅与执行方式选择。

## Global Constraints

- 开发预算为 1 小时，队员整合和展示准备另有时间；预算不等于已验证工期。
- 中央胶囊固定，轮廓完整，边缘泛光；泡泡轻缓浮动，操作时稳定。
- 首次最多 6 个候选；每次增加最多 3 个；最多 12 个未合并候选；最多 4 个执行步骤。
- 换一批保留选中、用户固定及已合并泡泡。输入变化不擅自修改组合。
- Jev 使用 `https://openrouter.ai/api/alpha/decisions`，模型 `typesafe/jev-1.13`。
- 服务端读取用户指定项目 `.env` 中的 `OPENROUTER_API_KEY`，不复制密钥到源码、浏览器、Git 或日志。
- 本次授权包含少量真实 Jev 和生成模型调用；继续执行现有能力权限、费用声明和本机同源检查。
- 无通用网页搜索 API；使用预置真实来源、粘贴链接和打开外部搜索页。行情显示实际来源时间。
- 保留其他未提交工作。文档与代码分开提交，不提交 `.superpowers/`、私有回执或密钥文件。

## Review Focus

1. 中文输入法中途组成字符、快速否定或改口：旧响应不得恢复过时的代写候选；归任务 4、5。
2. 松手后用户取消、再次拖动或刷新页面：晚到判断不融合、不丢成员；归任务 4、5。
3. 两份资料都被选中，但工作集预算排除一份：运行必须报告不足或使用显式完整快照，不能静默遗漏；归任务 3。
4. 请求已受理但响应丢失，用户再次点击：核对同一个运行身份，不新增收费任务；归任务 2、4。
5. 资料正文包含 HTML 或伪造来源编号：按文本呈现，未知编号不给有效来源链接；归任务 3、5。

## 文件与接口分工

| 文件 | 职责 |
|---|---|
| `backend/bubble_providers.py` | 密钥配置、Jev 请求、OpenRouter 生成适配、响应校验 |
| `backend/bubble_catalog.py` | 真实候选、类型、有限组合选项与初始阈值 |
| `backend/runtime/bubbles.py` | 注册 Demo 能力、保存结构校验、运行快照和执行组合 |
| `backend/runtime/kernel.py`、`protocol/v0.1/commands.json` | `bubble.run` 命令、运行去重、冻结上下文接入 |
| `backend/runtime/artifacts.py` | `bubble-canvas` 内容结构与版本边界 |
| `backend/server.py` | `/demo` 路由、注入可选 OpenRouter 提供者，保留现有服务行为 |
| `static/demo.html`、`static/demo.css` | 布局、胶囊、泡泡、融合反馈、详情和结果 |
| `static/js/bubbles/state.mjs` | 候选、融合状态机、失效判断、撤销、运行身份 |
| `static/js/bubbles/client.mjs` | Runtime Command/Task 调用、状态恢复、明确请求身份 |
| `static/js/bubbles/app.mjs` | DOM、Pointer Events、键盘、实时输入、结果渲染 |
| `tools/test_bubble_providers.py`、`tools/test_bubble_runtime.py` | 隔离提供者与执行回归 |
| `tools/test_bubble_state.mjs` | 纯状态机回归 |
| `tools/check_bubble_live.py` | 显式运行的真实 API 冒烟检查；不加入离线回归 |

## Task 1：接入 Jev 与生成提供者

**Files:** 新建 `backend/bubble_providers.py`、`backend/bubble_catalog.py`、`tools/test_bubble_providers.py`。

**Interfaces:** `load_config(env_file: str | None) -> dict`；`JevClient.decide(state: dict, questions: dict) -> dict` 返回 `answers/model/provider/elapsed_ms/usage`；`OpenRouterGenerator.generate(prompt, purpose, call_id) -> (str, dict)` 兼容现有 Generator；`candidates(text: str, artifacts: list[dict]) -> list[dict]`；`merge_options(left: dict, right: dict) -> dict`。

- [ ] 先写受控 HTTP 测试 `test_decisions_shape`、`test_invalid_answers_fail`、`test_key_never_in_error`、`test_generation_failure_not_retried`。断言 Decisions URL 与指定模型准确；缺题、未知 Choice、非有限概率失败；异常不含测试密钥；一次调用最多一次上游请求。
- [ ] 运行 `python3 -m unittest tools.test_bubble_providers -v`，确认因未实现而失败。
- [ ] 实现提供者。环境变量优先；本地密钥文件由 `WANJIE_ENV_FILE` 指定。Jev 超时 12 秒，生成超时 45 秒；错误返回可读状态，不回显原始上游错误或头部。生成模型取 `WANJIE_GENERATION_MODEL`；默认候选 `openai/gpt-4.1-mini`，执行真实检查时必须确认目录可用，不可用则明确报告并设置已验证替代型号。收费调用只在 Runtime 授权后发生。
- [ ] 实现带稳定 ID 的候选目录：资料、链接、动作、股票查询和空白文稿；不使用虚构的个人笔记。生成来源是目录或实际 Artifact。写作、提纲、资料集合、资料对比和研究卡片作为有限组合。自动融合初始条件为最高概率至少 0.85、与第二项差距至少 0.25、无约束冲突且答案不是 `none`；否则返回待选择。阈值仅用于 Demo 校准。
- [ ] 运行上述测试，全部通过后提交本任务文件。

## Task 2：组合保存与稳定运行身份

**Files:** 新建 `backend/runtime/bubbles.py`、`tools/test_bubble_runtime.py`；修改 `backend/runtime/kernel.py`、`backend/runtime/artifacts.py`、`protocol/v0.1/commands.json`。

**Interfaces:** `validate_canvas(content: dict) -> None`；`prepare_run(tx, intent: str, payload: dict) -> dict`；`install_bubbles(kernel, jev, generator) -> None`。命令 `bubble.run` 输入 `{runId, canvas, version, groupId, text}`，响应沿用 `{task}`。画布为 `kind=bubble-canvas` 的 Artifact，内容为 `{input, inputRevision, bubbles, groups, positions}`。泡泡保存 `{id, kind, title, resource, selected, pinned}`；组合保存 `{id, version, members, operation}`；位置为归一化坐标。

- [ ] 写 `test_canvas_roundtrip_and_version_conflict`、`test_run_dedup_and_payload_conflict`、`test_run_snapshot_survives_canvas_edit`：保存再读取保留成员和固定位置；旧版本保存被拒；同 `runId` 得到相同 Task，修改载荷被拒；任务受理后编辑画布不改变已冻结输入。
- [ ] 运行 `python3 -m unittest tools.test_bubble_runtime -v`，确认失败后实现。
- [ ] 用现有 `artifact.create/update` 保存画布，不新建数据库。新内容类型显式校验成员存在、引用唯一、无循环和步骤上限。仅保存用户组织状态，待融合请求不持久化为已组合。
- [ ] 接入 `bubble.run`：要求 Command `id` 等于 `payload.runId`，显式幂等键若存在也必须相同。复用 Kernel 的事务、指纹和去重表。首次受理从服务端画布编译并冻结运行，不接收客户端任意函数或执行序列。重复请求先返回原 Task，不重新读取已改变的画布。
- [ ] 增加可选的显式任务 Context 注入，仅限已校验的 `bubble.run`。它只包含选中资料，不含可变画布；运行前继续检查资料访问权限，但不因与本次运行无关的 Artifact 改变而失败。保留旧能力的原上下文语义。
- [ ] 运行本任务测试与 `python3 -m unittest tools.test_runtime -v`。通过后提交本任务文件。

## Task 3：资料快照与两条共享执行流程

**Files:** 修改 `backend/runtime/bubbles.py`、`backend/runtime/capabilities.py`、`tools/test_bubble_runtime.py`；复用 `backend/runtime/web.py`、`backend/market.py`。

**Interfaces:** `freeze_sources(tx, intent: str, refs: list[dict], budget: int) -> list[dict]` 返回 `{id, version, title, source, detail, text}`；`execute_bubble(task, progress, cancel) -> dict` 返回标准 Artifact 输出；`validate_citations(text: str, sources: list[dict]) -> None`。注册 `bubble.execute`，生成输入包含 `request`、`constraints`、`sources`，三者分离。

- [ ] 写 `test_two_selected_sources_reach_generator`、`test_selected_version_and_budget_checked`、`test_unknown_citation_fails`、`test_stop_preserves_read_artifact`、`test_old_quote_timestamp_preserved`。受控生成器断言两份原文都存在且无关工作集内容不存在；目录读取不能充当正文；超预算明确失败；`[99]` 在两份来源时失败；取消后无后续生成；行情保留源时间。
- [ ] 运行 `python3 -m unittest tools.test_bubble_runtime -v`，先失败再实现对应行为。
- [ ] 实现本次运行的资料快照，上限沿用当前 Intent 的 `contextBudget`，默认 12000 字符。所选内容超预算时整次运行明确拒绝，显示调整读取范围提示，绝不静默裁掉一个来源。原文片段最多 1200 字符并记录范围；仅目录不能进入要求正文的生成。
- [ ] 编译有限步骤：读取网页／读取所选 Artifact／查询行情 → 汇集全部结果 → 写作、提纲、对比或研究卡片。每步调用已注册的真实提供者，沿用工作流执行前权限检查、逐步权限消费、阶段产物保存和取消机制。新逻辑放在 `bubbles.py`，不改变旧 `workflow.run` 的单产物绑定契约。
- [ ] 前置步骤完成后冻结全部实际产物，不能只取第一个。来源编号固定为 `[1]` 等；源链接由程序拼接。正文未知编号使生成步骤返回引用校验失败，保留资料。研究卡片没有新闻时使用明确缺失说明。空白文稿与集合不调用生成模型。
- [ ] 明确否定正文生成的约束进入运行快照；冲突时阻止相应动作，并保留用户组合。无需自动把旧组合改成别的动作。
- [ ] 运行本任务测试及现有 Runtime 回归，通过后提交。

## Task 4：候选与融合前端状态机

**Files:** 新建 `static/js/bubbles/state.mjs`、`static/js/bubbles/client.mjs`、`tools/test_bubble_state.mjs`；修改 `static/js/runtime-client.js`、`backend/runtime/bubbles.py`。

**Interfaces:** `initialState(saved={}) -> State`；`reduce(state, event) -> State`；`mergeRequest(state, leftId, rightId) -> object`；`createClient(transport, storage) -> {command, run, reconcile, watch}`。注册 `bubble.suggest` 和 `bubble.merge` 网络收费能力，返回 `artifacts: []` 与额外 `decision` 字段，不为每个按键创建可见文稿。

- [ ] 先写 Node 断言：初始候选 `<=6`；更多灵感增加 `<=3`；总数 `<=12`；刷新保留 selected、pinned 与 group；过时输入响应不更新；融合取消后返回不能合并；拆开恢复成员；撤销不删除已运行结果；持久化恢复不恢复 pending fusion；两次 run 复用相同身份。
- [ ] 运行 `node tools/test_bubble_state.mjs`，确认失败再实现状态模块。
- [ ] 使用融合状态 `preview/pending/choice/merged/cancelled/failed`。靠近目标停留 250 ms 后请求；12 秒服务端超时，前端 14 秒结束等待。松手后 mouseleave 不取消；重新拖动成员、输入版本变化或取消事件使身份失效。失败或超时恢复旧位置，手动选择始终标为用户选择。
- [ ] 候选调度在中文 compositionend 和正常 input 后启动；仅一个候选请求在途，队列保留最新输入。融合请求独立，等待时允许取消。Runtime 任务结果通过轮询取得；旧结果依照 inputRevision、interactionId 和成员版本丢弃。
- [ ] 按稳定候选 ID 去重，已展示候选优先排除；无新候选显示事实。网络失败不替换当前泡泡。操作时立即冻结视觉位置，业务状态不记录动画相位。
- [ ] 为 CommandClient 增加可选显式 `id`，旧用法不变。先在浏览器存储保存 runId 再发送；收到成功后仍保留业务运行身份。再次运行由独立按钮生成新身份。未知响应用已保存 Command 查询，不自动生成新 ID。
- [ ] 运行 `node tools/test_bubble_state.mjs` 和 `node tools/test_runtime_client.mjs`，通过后提交。

## Task 5：完整画布、结果与服务接入

**Files:** 新建 `static/demo.html`、`static/demo.css`、`static/js/bubbles/app.mjs`；修改 `backend/server.py`；补充 `tools/test_api.py`。

**Interfaces:** `/demo` 返回新页面，`/` 保留旧工作台；前端调用任务 4 的 client/state。`create_server()` 仅当 `WANJIE_DEMO=1` 时加载 Demo 提供者并注册能力，已有离线测试默认行为不变。本地配置示例仅列环境变量名称与占位路径。

- [ ] 写 API 用例：`/demo` 返回页面；未开启 Demo 不暴露密钥状态或自动联网；跨域请求仍被拒；开启后能力声明为 network 与 metered。运行 `python3 -m unittest tools.test_api -v`，确认新增行为尚未实现。
- [ ] 实现页面与模块引用，遵守现有 CSP，不把交互脚本写入 HTML。复用已选草图的布局与配色，生成正式 DOM；示例内容全部替换为目录或真实响应。资料、动作、集合、执行组合有文字与图标区分。
- [ ] 中央胶囊右端放“更多灵感”和“换一批”；显示明确等待、离线与无更多候选状态。使用稳定环绕锚点、轻缓 CSS 漂移，拖动冻结；布局避开中央胶囊。窄面板允许滚动和收起详情，文字可读。
- [ ] 实现 Pointer Events 拖动和靠近预览；键盘 Enter 打开，Esc 关闭并恢复焦点；详情中提供“与其他泡泡组合”作为拖拽替代；reduced-motion 禁用漂移。待组合连接、歧义选项、撤销和拆开复用状态机。
- [ ] 首次使用在设置区完成一次明确的 Demo 网络授权，列出 Jev、生成、网页和行情能力；设置 Intent `localOnly=false`，Grant 有效期 3600 秒、每组最多 100 次调用。耗尽或过期提示重新授权，不偷偷续期。开发实测由 CLI 使用同样的 Runtime Command 配置。
- [ ] 实现资料链接输入、读取范围选择、执行前来源预览、停止、核对结果、再次运行、可编辑正文、复制及 Markdown 下载。未经读取的链接只标为入口。DOM 用 textContent 构造结果；来源链接只接受已校验的 HTTPS 地址。
- [ ] 每次组织改变后 300 ms 合并保存；运行前等待保存成功。恢复时加载当前 Intent 画布与 Task；冲突或保存失败保留本地副本并提示。调试面板显示实际模型、概率、耗时和结果状态，不暴露凭据。
- [ ] 浏览器验证：中文输入与否定、增加和刷新、拖拽与按钮组合、异步取消、拆开、页面刷新、可编辑结果。注入含 HTML 的测试文稿只显示文本。API 与状态测试通过后提交。

## Task 6：真实验证、回归与交接

**Files:** 新建 `tools/check_bubble_live.py`、`docs/acceptance-bubble-demo.md`；修改 `tools/selftest.py`、`README.md`、`ideas/README.md`、`ideas/ROADMAP.md`、`ideas/unknown/0002-bubble-hackathon-demo.md`、`.gitignore`。

**Interfaces:** 实测脚本接受 `--env-file`、`--model`、`--flow writing|market|decisions`；私有回执写 `.ai/test-data/bubble-live/`，终端只打印模型、耗时、状态与产物路径；离线 selftest 不调用外部 API。

- [ ] 将新增受控测试加入 `tools/selftest.py`。为 `.superpowers/` 和本地配置补忽略项，不将密钥复制到本项目。
- [ ] 核验生成模型目录，跑一次短请求，再通过 Runtime 跑 2 条真实流程。Jev 用少量代表样例验证“自己写／不要代写／先找资料／改成股票”和融合歧义；记录真实结果与初始阈值调整，不宣称统计准确率。
- [ ] 运行 `python3 tools/selftest.py`。故障只修与本次变更有关的部分；已有故障单独记录。验证 `git diff --check`，检查待提交内容无密钥或私有回执。
- [ ] 浏览器运行完整展示路径。检查重复运行只产生一个 Task、刷新不重跑、取消保留资料、报价时间可见、缺少新闻不编造、来源编号可映射。记录已验证范围，不将受控提供者结果当作外部成功。
- [ ] 文档写明启动命令、配置路径、两条演示步骤、已实现状态及剩余整合项。按具体文件提交本轮改动，保留其他人的未提交研究工作。

## 一小时执行安排与风险

建议本会话直接执行，避免多次交接。各任务接口紧密，现有代码量小，适合保持一个实现上下文。

目标时间分配：提供者 8 分钟；保存与运行身份 8 分钟；共享执行 10 分钟；状态机 10 分钟；画布与接入 16 分钟；真实验证与交接 8 分钟。共 60 分钟，是预算而非保证。

前端布局复用已确认的视觉草图，把实现时间用于真实交互和结果展示；不扩大后端重构。超出预算时先减少装饰动画与候选目录广度，不删除资料绑定、运行去重、保存恢复、取消语义或真实验证。若外部接口失败则报告具体阻塞，不伪造成功，也不静默缩减已批准的功能。

## 计划自检

规格中的候选管理、融合状态、资料快照、保存、去重、停止、两条流程与验收均有对应任务。五类 Review Focus 已分别落到测试。复用原 Runtime；不新增调度池、不改外部项目、不引入尚未验证的开源依赖。待用户审阅本计划并选择执行方式后开始产品实现。
