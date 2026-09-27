# IDEA-0006 · 稳定对象与上下文关系图

- 作者：vimalinx；来源：本轮明确授权的对象图启动任务。
- 整理、设计细化与实现评估：Wilson。
- 日期：2026-09-27。
- 状态：implemented（本地未提交源码）；验证：仅静态语法/schema 检查，运行验收由用户完成。
- related：IDEA-0001 Context/Relation、IDEA-0003 Semantic Control DAG。
- kanemaverick：未收到本议题观点；不代表双方共识。

## 提案

稳定 Artifact 可被多个 Intent 引用，由 ContextRelation 保存 role、relevance、state、localProperties、origin（explicit/computed）和 pinned。Explicit Set 保存用户明确选择，Computed Query 在授权对象集合内计算当前匹配。同对象按 Context Role 呈现，不依靠复制对象实现不同身份。

Artifact.intent 暂保留安全归属；跨空间需要 shared 与显式引用。共享读不授予共享写，语义分数不构成权限。JEV 计算建议不覆盖 explicit/pinned，历史保留。

## Wilson 的实现与评估

- `backend/runtime/object_graph.py`：旧 member 兼容视图、访问集合、角色关系、墓碑与历史事件、查询求值和快照。
- `backend/runtime/context.py`：工作集正文去重、读取深度、角色投影。
- `backend/runtime/kernel.py`、`policies.py`：命令入口、snapshot、排队校验与 JEV 相关性策略。
- `protocol/extensions/v0.1/context-relation.schema.json`、v0.2 commands/events/view schema：静态契约。
- [对象图标准与迁移说明](../../docs/standards/OBJECT_GRAPH_v0.1.md)：设计输入、兼容规则、命令样例和边界。
- [.ai 交接结果](../../.ai/handoffs/object-graph-result.md)：本次实际文件与静态检查证据。按用户要求不提交，暂无本轮 commit 证据。

Anytype 官方哲学参考已在线核对，来源与探索/pre-release 状态详见标准文档；没有复制未知许可代码或声称完整照搬。

当前是后端对象图切片。前端多角色呈现、运行持久性、真实 JEV role/query 提议均未验收；本轮没有运行测试、调用付费模型或重启服务。查询按现有安全集合确定性计算，不承担跨空间发现和授权。

## 索引合并

本提案应进入 `ideas/README.md` 的 IDEA-0006 索引及 `ideas/ROADMAP.md` 的 Context/Working Set 进展。为避免覆盖主 Agent 并行文档，本轮将合并条目写入交接文件，由主 Agent 完成共享索引整合。
