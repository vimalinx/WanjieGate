# WanjieGate Object Graph v0.1

日期：2026-09-27。设计与实现整理：Wilson。状态：本地源码实现，静态检查；用户运行验收待完成。协议扩展叠加于现有 v0.2 Command Bus，不替换它。

## 对象身份与权限

Artifact 是稳定对象：一个 `id`、一份内容及版本，可同时被多个 Intent 和多个 Context Role 引用。新增引用不会复制 Artifact，不改变 `Artifact.intent`。该字段暂继续作为安全归属；只有归属 Intent 可通过 `artifact.update` 修改内容、标题、scope 和对象级 pinned。

跨 Intent 读取需要同时满足 `scope=shared` 和目标 Intent 内至少一个 active、explicit ContextRelation。Computed Query、JEV 分数、普通 `relation.add` 和 localProperties 均不能取得访问权。共享撤回后，关系历史仍保留，但当前 Artifact、Context 和 View 不再包含该跨空间对象；重新共享会恢复尚未撤销的显式引用。移除最后一个 active 显式引用同样撤销当前跨空间读取。

共享读取不授予共享写入。对共享对象设置本地 role、localProperties、View 或读取深度，只修改目标 Intent 的引用/视图。它们不是 Artifact 内容补丁。现有能力、network/localOnly、Grant、L0–L3 权限流程保持原入口。`principal` 来自现有受信运行时，不增加多用户身份或网络 ACL。

## ContextRelation

持久实体沿用 `type=member` 和 SQLite 实体存储；新 schema 位于 `protocol/extensions/v0.1/context-relation.schema.json`。这是兼容型 ContextRelation，不是普通 subject/predicate/object Relation 的替代。

| 字段 | 含义 |
|---|---|
| intent / artifact | 引用所属上下文 / 稳定对象 ID |
| role | 上下文角色，默认 `context`，同对象可拥有不同角色 |
| relevance | 0–1 的本地相关度，不是访问权 |
| state | `active`、`inactive`、`removed`；removed 是保留历史的墓碑 |
| localProperties | 任意 JSON 属性，仅为本地上下文数据，不合并进对象内容或权限 |
| origin | `explicit` 或 `computed` |
| pinned | 本地固定；计算关系不能固定或覆盖固定关系 |
| tier / detail | 兼容 HOT/WARM/COLD 与 full/excerpt/metadata |
| reason / version / created / updated | 来源说明与持久版本时间 |

唯一键为 `(intent, artifact, role)`。默认 role 的 ID 保持旧 `intent:artifact`；其他 role 使用带前缀的稳定摘要。显式更新同一键接管该键；计算更新遇到同键显式关系（含 inactive/removed）即拒绝。任一固定关系保护该对象免受计算修改。人可修改显式关系；固定引用须先取消固定再移除。Artifact 级 pinned 同样保护计算路径。

每次关系更改写 `context.relation.changed`，包含完整 `before` 与 `relation`，并保留 `context.changed` 兼容事件。新建时 before=null。移除不物理删除；移除尚未持久化的查询命中会创建 explicit 墓碑，以阻止同角色自动再出现。查询更改写 `context.query.changed`，同样保留 before；定义移除也保留墓碑。旧日志不清理、不重写。关系/查询修改推进 Intent revision，使旧语义结果失效。

## Explicit Set + Computed Query

Explicit Set 是当前可访问的 active explicit 关系集合；它不是另一个 Artifact 副本表。

`context.query.set` 保存一个 Intent 内的声明式查询，查询定义只由 human principal 改动。过滤字段为 `kinds`、`titleContains`（不区分大小写的子串）、`source`（精确值）、`roles` 和 `minRelevance`，字段之间为 AND；kinds/roles 数组内部为 OR。role/relevance 过滤只查看已有持久 active 关系，不递归依赖其他查询结果。

查询每次读取时在 **accessible 集合内** 求值，没有 SQL、任意表达式、网络或模型调用。匹配结果产生虚拟 `origin=computed` 的 ContextRelation，附 `query` 定义 ID；不为每次 snapshot 写库。持久关系总是优先于查询；同键显式墓碑阻止查询恢复。固定对象不生成新查询角色。多个查询命中同一键时按查询稳定 ID 字典序选第一个；这是确定性选择，不是智能合并。

定义和对象变更有日志，虚拟命中结果不逐次记日志，也不提供历史时点自动重建接口。查询集合随对象修改/共享撤回自然更新。此版本不含递归、OR 表达式树、集合嵌套、任意属性过滤或全文索引。

## Context 与 View 投影

`context.items` 按 Artifact 去重，正文只计算一次预算，附 `roles`、`contextRelations`。选择代表关系按 pinned、explicit、tier、relevance、默认 role 和稳定 ID 排序。存在多个 active explicit 读取要求时，正文使用其中最严格的 detail；计算角色不能扩大显式读取深度。媒体仍只送 metadata。detail 控制工作集表示，不是新的 Artifact ACL，也不替代现有能力的显式目标读取规则。

`views` 按 `(artifact, role)` 投影，附 `role`、`contextRelation`、`localProperties`。reference/source 默认 Inspector，task 默认 Timeline，其他 role 沿用 Artifact kind 的 Primitive；`view.set` 可以按 role 覆盖 primitive、placement、state。role 自由命名但不会自动装入未知组件。不同角色/Intent 的 View 状态独立；默认 role 保留旧 View ID 行为。

没有 active 关系的已知对象不进入工作集/投影；自身归属对象仍可在 artifacts 中检索，以便恢复引用。COLD 仍保留关系和隐藏 View，但不进入未固定工作集。已排队任务启动前复核访问范围、Artifact 版本、工作集 detail 和关系快照；后续共享撤回不主动取消已经运行的外部调用。

JEV 现有 artifact.relevance 信号经确定性 policy 转为 `context.relate(origin=computed)`。显式/pinned 与执行依赖优先，过时响应拒绝应用。当前未扩展模型输出 schema 以自由生成新 role/query；新的 role 可通过命令建立。不得把本切片称为完整 JEV 对象发现系统。

## Snapshot 与命令

snapshot 新增：

```text
objectGraph.version = "0.1"
objectGraph.relations       # 当前 effective 关系，含虚拟 computed/query
objectGraph.storedRelations # 本 Intent 的持久关系，含 inactive/removed 和旧共享引用元数据
objectGraph.explicitSet     # 当前可访问的 active explicit 关系
objectGraph.queries         # 持久查询定义，含 removed
context.items[].roles
context.items[].contextRelations
views[].role / contextRelation / localProperties
```

既有 `members` 仍返回原持久行；旧行可能没有新增字段。新消费者使用 objectGraph。`storedRelations` 保留本地历史属性，既不携带当前 Artifact 内容，也不表示仍有权限。

以下是标准 Command 的 type/payload 部分；调用者补现有 protocolVersion、id、kind=command、timestamp、source=renderer、intent，可继续使用 expectedRevision/idempotencyKey。示例不会自动执行。

```json
{"type":"context.relate","payload":{"artifact":"artifact-a","role":"source","origin":"explicit","relevance":0.9,"tier":"HOT","detail":"excerpt","pinned":true,"localProperties":{"caption":"写作依据"}}}
```

在第二个 Intent 使用同一 artifact-a（拥有者须已将 scope 设为 shared）：

```json
{"type":"context.relate","payload":{"artifact":"artifact-a","role":"reference","origin":"explicit","localProperties":{"caption":"对比资料"}}}
{"type":"context.query.set","payload":{"query":"research-notes","role":"evidence","filter":{"kinds":["note","document"],"titleContains":"研究"},"tier":"WARM","detail":"excerpt","relevance":0.7}}
{"type":"view.set","payload":{"artifact":"artifact-a","role":"reference","primitive":"Inspector","placement":"side","state":{"expanded":true}}}
{"type":"context.relate","payload":{"artifact":"artifact-a","role":"source","pinned":false}}
{"type":"context.remove","payload":{"artifact":"artifact-a","role":"source"}}
{"type":"context.query.remove","payload":{"query":"research-notes"}}
```

计算建议命令示例（不能覆盖同键 explicit/pinned，也不能自行跨空间授权）：

```json
{"type":"context.relate","payload":{"artifact":"artifact-a","role":"candidate","origin":"computed","relevance":0.8,"tier":"WARM"}}
```

## 兼容与迁移

无需立即改写数据库或重新导入 Artifact。读取时补默认 role/context、state/active、localProperties/{}、detail/full、relevance/.5、tier/WARM、pinned/false。旧 `reason=用户选择` 或未知来源保守视为 explicit；`语义相关性`、`当前产生或导入` 视为 computed。旧语义成员不能成为跨空间显式授权；因此旧的仅语义共享引用会停止读取，需要人重新执行 context.set 或 context.relate。

旧 `context.set` 继续更新默认 context role；human 操作成为 explicit，并激活先前 inactive/removed 的默认关系。旧 `view.set` 不传 role 时仍命中原默认视图。原 generic relations、surface.update、extensions 安装代码保留。没有 schema migration 批处理、历史删除或降级重写。

前端本轮不改。旧客户端若用 artifact ID 当 View 唯一键，可能只呈现一个角色；需组合工作衔接采用 `(artifact, role)`/View ID，不能声称 UI 已验收。正式上线前由用户验证持久性、多角色、共享撤回、显式/pinned、查询与任务竞争路径。本轮按授权没有新增或执行测试，没有启动内核、付费调用或重启服务。

## 设计参考及范围

2026-09-27 在线核对 [Anytype February Community Update](https://blog.anytype.io/february-community-update-2026/)：Collections 2.0 当时被明确描述为探索/原型方向，强调对象关系与上下文，并非已定案的完整实现。本项目将这一哲学作为设计输入，具体的安全归属、ContextRelation 和命令语义由 Wilson 为 WanjieGate 独立设计。

同日核对 [Anytype API v2 官方参考](https://developers.anytype.io/docs/reference/v2/anytype-api/)：页面标注 pre-release，描述稳定对象标识、查询实时选择与手工集合，并分别限定空间和权限。本实现没有集成 Anytype API，没有移植其代码，也不声称复制其完整架构或兼容 API。


## 主集成补充

前端已按稳定 `View ID` 呈现多角色，显示可选 caption，引用／证据角色提供内容与来源；共享对象只显示读取与上下文固定，不提供跨空间正文编辑。拖入正文仍引用同一个 Artifact。默认 View ID 统一为 `view:<intent>:<artifact>`，与显式 view.set 创建的 ID 一致，避免设置投影后换身份；没有修改 Artifact ID。

JEV 增加每个有界对象的有限角色 Choice：NONE/reference/evidence/draft/background-reading。它产生 `artifact.context-role` 信号；Policy 在相关性和选择置信度均达 .85、对象已可访问、无人工固定/同角色显式关系/运行依赖时，建立 computed 关系。NONE 不删除已有关系，角色称为 evidence 不代表事实已核实。Query 定义仍只由显式命令设置，没有自由 SQL 或模型生成查询代码。

新建的人工作品（artifact.create）默认关系记为 explicit；执行产生的对象为 computed。历史行按上文兼容规则读取。上述接线仅静态检查，未运行交互或模型测试。
