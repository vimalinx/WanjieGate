# Intent Runtime Protocol v0.1

本协议由 WanjieGate 实现，当前作用域是可信本机单用户运行时。它提供类型化消息、持久状态和模块接入契约；不声明已经接管桌面、其他注册项目或远程设备。

## 原语与实现

| 原语 | 契约 | 实现 |
|---|---|---|
| Intent | 稳定 ID、八维 state、status、version、parent、fieldSources、preferences | `backend/runtime/kernel.py` |
| Artifact | 独立 ID、kind、版本、内容、来源、范围、provenance | `artifacts.py`、`storage.py` |
| Event | 事实类型与 payload 契约 | `events.json`、追加消息日志 |
| Signal | 判断值、score、Operator、所依据的 revision、有效期与证据 | `schemas/signal.schema.json`、`capabilities.py` |
| Command | 按 type 验证 payload，来源、目标、去重键与预期版本 | `commands.json`、`Kernel.execute` |
| Capability | 能力定义与 module 提供者绑定，输入输出 Schema、权限、副作用 | `schemas/capability.schema.json` |
| Task | 一次执行的持久实例、Context 快照、进度、产物与终态 | `schemas/task.schema.json` |
| Context | 字符预算、版本、选入与排除原因、HOT/WARM/COLD | `context.py` |
| View | 指向 Artifact 的投影、primitive、placement、state | `schemas/view.schema.json`、前端投影 |
| Policy | 版本、接受的 Signal、阈值与动作 | `policies.py` |

Relation 为独立关系记录，支持 belongs_to / references / produced_by / depends_on / supports / conflicts_with / derived_from。

## Envelope

四种 kind 固定为 `event | signal | command | result`。必填字段：`protocolVersion="0.1"`、`id`、`kind`、`type`、`timestamp`、`source`、`payload`。所有时间戳为 Unix 毫秒，`ttl` 也是毫秒。

- `intent` 标记状态所属空间。`artifact` 可指向主要对象。
- `correlationId` 标记整条流程；根命令未提供时由 Kernel 使用命令 ID 补全。
- `causationId` 标记直接原因。Signal、Policy Command、Result 和衍生 Event 连在同一因果链上。
- `expectedRevision` 对 Intent 做乐观版本检查；编辑 Artifact 另传其版本。
- `idempotencyKey` 在主体范围内唯一。相同键与相同请求返回原受理结果；同键不同请求拒绝。
- score 只表示 Operator 的判断分数，不等价于已校准正确率，更不构成权限。

Envelope 在 [message.schema.json](schemas/message.schema.json)。Command payload 在 [commands.json](commands.json)，Event payload 在 [events.json](events.json)，Signal / Result 有各自 Schema。`backend/runtime/protocol.py` 实现所用 JSON Schema 子集校验：type、const、enum、required、properties、additionalProperties、数组/文字边界、数值边界、pattern 和文件内 `$ref`。不声称支持整个 JSON Schema 标准。

Manifest 的 accepts / emits 使用 `kind.type` 选择器，例如 `command.capability.run` 对应 kind=command、type=capability.run；`signal.intent.phase` 对应 kind=signal、type=intent.phase。

客户端不能通过发布 Signal / Event 伪造模型判断、执行结果或授权主体。HTTP 命令来源固定 `renderer`；这是受信任本机用户入口，不是多租户认证。可信提供者注册通过 Python 宿主 API 完成，不接受浏览器上传可执行模块。

## 状态与投递

SQLite `rt_entities` 是当前状态投影，`rt_messages` 是按序追加的四类消息日志。每次状态变化与对应事实在同一个事务中提交。HTTP 通过游标读取消息：消费者保存最后收到的 `seq`，断线后继续读取。

没有对端确认的消息可能被再次读取，消费者按 `id` 或 `seq` 去重。数据库 seq 提供单机确定顺序；不承诺分布式全局顺序或外部动作 exactly-once。

Command 受理与持久 Task 在同一事务中提交，然后唤醒 worker。服务在提交后、执行前退出时，该任务下次启动标为 interrupted，不自动重放。执行中断为 outcome_unknown。回放/读取日志从不重新调用 Capability。

当前 3 个 worker、全局最多 12 个非终态任务、每 Intent 最多 3 个。队列满返回明确错误。模块停用拒绝新的执行；已开始的调用通过 Task.cancel 单独停止后续写回。

## Intent 与 Context

state 有 thread / goal / domain / phase / target / attention / commitment / urgency。生命周期独立使用 active / warm / suspended / archived；分支创建新 ID 并保留 parent。

用户显式设置的维度标记 human，语义策略不能覆盖。默认 phase 可被高分且未过期的 Signal 更新。每次语义任务记录 Intent revision；较新输入替换 latest command，旧结果只留证据，不应用到当前状态。

Artifact 的本体独立存储。共享是显式 scope=shared，再由另一 Intent 加入工作集引用；停止共享后其他 Intent 无法继续读取。原 Intent 才能编辑内容。Relation 保留对象关系，View 切换不复制内容。

Working Set 默认 12000 字符预算，可调 256–40000。固定对象和执行依赖优先，HOT 先于 WARM，COLD 不自动进入 Context；超预算有明确排除原因。固定不代表可以突破预算。语义策略可 HOT → WARM → COLD，用户明确指定热度或固定后不被自动覆盖。移出工作集不删除 Artifact。

## 权限与副作用

L0 Observe、L1 Prepare、L2 Reversible、L3 Irreversible 是副作用维度；网络、计费与权限分别声明。

Grant 绑定用户、Intent、能力列表、过期时间、剩余调用次数、网络许可、最高副作用、参数等值约束与理由。排队和执行前分别检查，真正执行前原子扣减次数。撤销、过期、localOnly 和停用模块均可阻止尚未开始的执行。L3 要求完整参数绑定。

本地纯计算可直接使用。外部查询、云端生成、项目文件读取/修改、进程执行需要相应 Grant。开启自动内容只改变交互调度，不会创建权限。模型调用仍经过已有 LocalRouter `lr exec`，本协议不扩大其上游权限。

取消阻止后续阶段和结果写回，无法撤回已完成的外部副作用。失败后保留已完成 Artifact；unknown 不自动重试。文件修改保留修改前 Artifact，并校验文件哈希。Python 代码执行使用 bubblewrap 隔离网络和宿主数据、prlimit 限制内存/CPU/文件大小；缺少环境时失败，不退回宿主裸执行。

## Capability / Module / Skill

每个 Module Manifest 声明版本、kind、provides、accepts、emits、Context、权限、副作用、网络和成本。kind 包括 capability / operator / view / policy / source。Artifact 类型是消息中的引用或 Result 产物，不增加第五类消息。

注册 API：`Kernel.register(capability_spec, manifest, handler)`；handler 接受 `(task, progress, cancelled)`，返回经 outputSchema 校验的对象。外部实现可经可信宿主适配器注册，不能直接写数据库。一个能力可注册多个提供者；Command 可指定 provider，否则按已启用 module ID 排序选择。不会在未知结果后换提供者重放。

`register_module(manifest)` 注册策略/视图等模块。`module.set` 启停提供者；停用某种 View 仅停止它的投影，内容仍存在。当前政策由 `builtin.policy` 管理。

小 Skill 使用 `workflow.run` 的有序 DAG，字段为 `id / capability / input / dependsOn / bindings`。bindings 把依赖步骤的第一个 Artifact ID 写入下游输入字段。每步独立校验与授权，不允许组合递归；阶段结果立即持久化。`agent.run` 是同一组合图的临时 worker 入口，Intent / Context 持久；不是已接入外部自治 Agent 服务。

已注册能力：data.import、data.analyze、text.generate、market.query、web.read、semantic.observe、memory.retrieve、repo.search、repo.read、patch.apply、git.diff、test.run、code.run、workflow.run、agent.run。

## 传输与使用

```sh
./bin/web-serve.sh
./bin/intent-runtime state
./bin/intent-runtime command intent.create '{"title":"协议工作","state":{"goal":"验证完整生命周期"}}'
./bin/intent-runtime command intent.activate '{}' --intent <id>
./bin/intent-runtime command capability.run '{"capability":"data.import","input":{"text":"日期,数量\n一,10\n二,15"}}' --intent <id> --key import-example-1
./bin/intent-runtime watch --intent <id> --after 0 --once
./bin/intent-runtime trace <correlation-id>
```

| HTTP | 用途 |
|---|---|
| POST `/api/runtime/commands` | 提交 Command |
| GET `/api/runtime/commands/<id-or-key>` | 查询已受理命令，不再次执行 |
| GET `/api/runtime/state` | 总览、模块和当前空间 |
| GET `/api/runtime/intents/<id>` | 指定 Intent 的状态投影 |
| GET `/api/runtime/messages/<cursor>[/<intent>]` | 按序读取消息 |
| GET `/api/runtime/trace/<correlation>` | 因果链，最多 500 条；长链可用消息游标读取 |
| GET `/api/runtime/schema/<name>` | 协议 Schema |

HTTP 是 Bus 的传输适配器。旧接口只保留历史读取；所有新写入走 Command。

## 生命周期样例

[examples/lifecycle.json](examples/lifecycle.json) 由隔离运行时实际执行本地导入和分析产生，覆盖 Command → Task → Result → Artifact / Event。

```sh
./bin/intent-runtime validate protocol/v0.1/examples/lifecycle.json
python3 tools/selftest.py
```

语义循环另由测试注入可控 Operator 验证：Command.semantic.observe → Task → Signal → Policy Command → Result → Intent / Context / Notification Event。真实 KEV 与云端链路需要独立验收，不能由注入测试推出。

## 扩展边界

前端提供十种 View Primitive 的登记和投影状态。当前内容渲染覆盖文本、代码、终端输出、表格、统计、任务清单、网页摘录、场景块和 Inspector；尚未成为完整浏览器、IDE、媒体播放器或绘图编辑器。

Hyprland、语音、日历、外部通知源、远程设备、外部 Agent 以及图像/视频生成服务归属其他项目或提供者。此版本提供接入契约，未宣称这些系统已接入。邮箱禁令继续生效；任何 Manifest、分数或已有 Git 元数据都不能绕过它。

## 上下文读取范围

`context.set` 可选 `detail: full | excerpt | metadata`，默认 full，独立于 HOT/WARM/COLD。全文维持原 content；excerpt 是文字或序列化内容的前 1200 字符，标记 `representation=verbatim-prefix` 与 `truncated`，不生成摘要；metadata 只提供身份、标题、类型和来源。Context item 保留 Artifact ID/version、detail、originalCost、cost 与原因。预算不足仍明确排除，不静默降级。变更读取范围不会修改原 Artifact；排队执行与语义提交检查原快照的读取范围。
