# REVIEW-0001 · Intent Runtime 源码对照与工程评估

- 评估者：Wilson。
- 日期：2026-09-27。
- 对象：[vimalinx 的 IDEA-0001](../vimalinx/0001-intent-runtime.md)。
- 代码基线：`22f9541`；本次只读检查源码与现有文档，没有重新执行程序、测试、模型或外部服务。
- 范围：WanjieGate。其他注册项目的实现情况为 `unknown`，下文不代表 AIOS 整体审计。
- 结论：现有应用有可复用的工作台部件；距离提案中的语义微内核，主要差距是共享协议、持久 Intent 和统一执行治理。

## 逐项实现情况

“部分”指有局部对应实现，不能据此称为已经符合提案协议。

| 目标 | 当前状态 | 源码证据与缺口 |
|---|---|---|
| 持久 Intent 与八维状态 | 尚未实现 | [store.py](../../backend/store.py) 持久化 workspace，含 title、dataset、artifacts、messages、revision；无独立 Intent、父子分支、phase / attention / commitment 状态 |
| Artifact | 部分 | `Store.put_artifact / edit_artifact` 有 ID、type、version、source、固定状态；内容嵌入 workspace JSON，缺独立引用、跨空间共享与 Relation Schema |
| Event | 部分 | [scheduler.py](../../backend/scheduler.py) 的 `event()` 将阶段状态写入 job.events；无统一总线、订阅游标或完整因果链 |
| Signal | 部分 | [providers.py](../../backend/providers.py) 的 `Kev.decide()` 返回各能力分数和来源信息；未封装统一 Signal，无通用 evidence / basedOnRevision / expiresAt |
| Command / Result | 部分 | [server.py](../../backend/server.py) 的 HTTP 请求与响应承担动作请求和结果；无统一消息类型、命令生命周期与结果 Schema |
| Capability Registry | 部分 | [registry.json](../../static/registry.json) 声明 analyze / write / plan / answer、输入输出与成本；提供者选择和执行仍写在 Python 分支内 |
| Task / Scheduler | 部分 | 手动任务有队列、每空间串行限制、request_id 去重、阶段记录、取消与重启中断；没有通用模块任务协议 |
| Context / Working Set | 部分 / Working Set 未实现 | `Scheduler.run()` 取最近四个产物；preview 取最近若干标题、文稿和分析。没有基于关系的相关性检索、HOT/WARM/COLD、上下文预算与选入理由 |
| View | 部分 | [components.js](../../static/js/components.js) 按 Artifact 类型生成组件；[scene.js](../../static/js/scene.js) 另渲染即时内容。有数据与视图区分，但组件集与布局仍由应用维护 |
| Policy | 部分 | [composition.py](../../backend/composition.py) 包含阈值、依赖与组件预算；[live_runtime.py](../../backend/live_runtime.py) 包含路由与缓存规则。尚无版本化 Policy 或可追溯决定记录 |
| Manifest / 模块生命周期 | 尚未实现 | 注册表没有完整 accepts / emits、权限、健康、加载、停止、版本兼容与注销契约 |
| Permission Broker | 尚未实现 | 有 local_only、同源/Host 校验和生成适配边界；不等价于按模块、资源、动作、预算授权 |
| Relation / Work Graph | 尚未实现 | workspace、job、artifact 有局部 ID 关联；没有提案中的通用关系类型、来源与版本 |
| 可替换 Semantic Operator | 部分 | KEV 与生成适配器已分离，但 KEV 知道固定 capability 和 market cue；尚无统一 Operator 接口与运行时选择 |

## 最需要先统一的地方

当前有两条执行路径：

| 路径 | 入口与状态 | 迁移时要补的部分 |
|---|---|---|
| 手动执行 | `/api/workspaces/<id>/jobs` → Scheduler → SQLite job / Artifact | 接入通用 Command、Permission 和 Result，保留现有去重与失败保留 |
| 实时内容 | `/api/preview` → LiveRuntime → 自动行情或模型生成 | session / pending / cache 主要在内存中，调用回执另存；需要统一 Task、授权、预算、结果归属和恢复语义 |

实时路径在非仅本地模式下可以自动触发网络查询或云端生成，不能从 `preview` 名称推断它没有成本或数据外发。README 的“云端撰写由生成按钮触发”尚未反映该路径；这是文档与实现的差异。

建议先让两条路径进入同一命令执行边界，同时保留不同的界面交互。增加一条新的 Bus 路径而保留两条绕行路径，会让治理继续分散。

## 支持的设计方向

1. Intent 持久、Agent 临时：任务恢复依赖明确状态与 Context，可避免把长期项目身份绑定到某个 Agent 进程。
2. Event / Signal / Command / Result 分离：事实、判断、请求与执行结果各有责任，便于追踪和拒绝过期判断。
3. Artifact 与 View 分离：可复用现有产物版本和组件投影能力，逐步引入稳定引用。
4. JEV 只输出 Signal：Policy 和权限检查决定动作，模型分数不构成授权。
5. 小能力与组合图：现有 analyze → write → plan 可以成为第一条迁移样例。

以上是 Wilson 的支持意见，不表示 kanemaverick 已同意，也不表示微内核已实现。

## 建议补齐或调整的契约

### 1. 消息类别可以稳定，协议需要版本演进

保留四种 kind，但为 Envelope 增加 `protocolVersion`，为 type 绑定 payload Schema 版本。`payload: unknown` 只适合入口解析阶段；校验后应是按 kind / type 区分的结构。

明确 `timestamp` 的单位与时区、TTL 的计算方式、必填目标与终态。Signal 的 `score` 与可靠性说明分开，排序分不能默认解释为正确概率。

Manifest 中的 `artifact.search-results` 应表示产物类型引用；在总线上通过 Result.artifacts 或 Event 的 Artifact 引用传递，避免出现隐含的第五种消息。

### 2. 因果追踪还需要状态版本与命令去重

correlationId 表示一次流程，causationId 表示直接原因；需要定义触发链的必填条件。Signal 记录 `basedOnRevision`、证据引用、Operator / 模型版本与有效期。

Command 记录 `idempotencyKey`、`expectedRevision`、调用主体、目标与授权引用。过期 Signal 不能更新新 Intent；重复 Command 返回已有任务，不重复产生副作用。

需要确定事件投递、订阅恢复、单 Intent 排序、队列上限与背压。外部调用超时可能是 `outcome_unknown`，不能自动判为“没发生”后重试。该状态可作为 Task 的协调状态或失败 Result 的 outcome 细分，不必新增第五种消息。

日志回放只重建状态。对未完成外部动作先核对结果，不能按历史 Command 重新执行。写入任务状态与发布事件需要一致性方案，例如同一数据库事务记录 outbox。

### 3. Bus 与 HTTP 可以共存

Bus 定义交互语义，HTTP / WebSocket / 进程内调用定义传输方式。现有 Python 与 HTTP 可作为第一版适配器；引入消息协议并不要求同时替换前端框架、部署方式和全部接口。

Kernel 持有权威状态；模块接收被授权的投影、提出 Command，不能通过共享数据库绕开校验。确定性需要记录 Policy 版本、输入快照与处理顺序。

### 4. 副作用、费用和权限是不同维度

保留 L0–L3 作为副作用说明，同时单列：资源范围、网络目标、数据外发、成本预算、可补偿性与已有授权。

例如读取私有文件需要资源权限，预加载远程网页会产生网络请求，生成模型会消耗额度并发送上下文。不能因标为 L0/L1 就默认允许。

L3 根据已有有效授权与具体参数决定是否还需确认；不要求对已批准范围重复询问。Grant 应绑定主体、能力、目标/参数范围、期限、额度和撤销状态。Manifest 自报权限只是需求声明，Kernel 仍需独立验证。准备状态不等于提交授权。

Mailbox 使用禁令等现有明确限制继续有效；设计示例不授予任何外部操作权限。

### 5. Working Set 需要容量和稳定性策略

5–20 条是直观示例，实际预算应考虑 token / 字节、来源可靠性、任务依赖、数据权限和成本。HOT/WARM/COLD 描述可见性与装载优先级；evict 默认只移出工作集，不删除 Artifact。

用户固定的对象、尚未保存的编辑和正在执行任务的依赖应保留。阶段切换需要迟滞，避免每个词都重排界面。用分数辅助排序，不让模型直接修改存储或释放资源。

### 6. Intent 生命周期与恢复对象需要明确

持久 ID、父 Intent、生命周期状态和版本应与八维语义属性分别定义。`phase=implementation` 与 `status=suspended` 是不同维度；用户手动选择的字段要记录来源，避免被低可信 Signal 静默覆盖。

“恢复 Agent”建议解释为恢复任务和 Context，按需创建 worker。只有明确具备安全恢复协议的提供者，才承诺复用旧进程或会话。

### 7. 模块边界与权限隔离分开设计

先把跨模块的类型消息契约固定，模块内部仍可使用普通函数。统一 Manifest 不会自动让不可信插件安全；未来加载第三方模块需要独立执行隔离与权限校验。

“所有东西都是模块”的工程表达可收紧为：运行能力由模块提供，Intent / Artifact / Context 是模块共享的类型化数据。无需给每个 Artifact 启动一个模块实例。

## 最小迁移验证场景建议

同一 Intent 中执行“导入数据 → 分析 → 查看结果”，随后切换 phase，再回到原内容。该闭环先验证 Intent、消息、Task、Artifact、View 与恢复的连接；生成能力后续通过同一执行入口接入。

未来验收应覆盖：重复 Command 只执行一次、旧 Signal 不改变新状态、权限拒绝无动作、部分完成仍保留产物、重启回放不重发外部请求、切换 View 不丢编辑、模型缺席时明确显示状态。

此处是后续验收设计；本次没有运行这些测试，也未改造 Runtime。

## 更新记录

- 2026-09-27：完成对 IDEA-0001 的首次源码对照，列出迁移入口与待补契约。

## 后续实现说明 · 2026-09-27

本文保留 `22f9541` 基线评估。后续按 vimalinx 授权实现的本地协议、Kernel 与工作台见 [ROADMAP](../ROADMAP.md) 与 [验收记录](../../docs/acceptance-runtime-v01.md)；基线缺口表不应解读为当前源码状态。第三方研究独立记录，未收到 kanemaverick 新观点。
