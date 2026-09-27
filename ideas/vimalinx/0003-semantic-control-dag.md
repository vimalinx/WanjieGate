# IDEA-0003 · 正交 IntentFrame 与 Semantic Control DAG

- 作者与提交人：vimalinx
- 日期：2026-09-27
- 状态：accepted；首个可执行切片已实现并完成真实链路验证，完整愿景待推进
- related：IDEA-0001、IDEA-0002
- supersedes：把 coding/researching 等活动标签作为 Intent 身份的分类方式
- 标签：架构与协议、Context、执行与权限、语音、交互

## 用户提出的方向

一条稳定执行主干 OBSERVE → ORIENT → LOCATE → INTERPRET → PREPARE → COMPOSE → COMMIT → EXECUTE → VERIFY → LEARN，搭配独立维度：线程关系、线程、动作、目标、阶段、注意力与投入程度。阶段枚举按原方案实际列出的六项保存。

五类语义职责：Orientation、Resolver、Action Interpreter、Resource Router、Attention/Event Router。独立问题共享快照并批量判断；只有候选依赖、扩大上下文、风险边界才另起层级。JEV 通过类型化状态协作。

Intent 生命周期持久；Working Set 高频变化；半句话产生软状态；显式确认与权限产生硬状态。新意图判断不自动建空间。相关性不等于权限，通知归属不等于打断紧迫性，工具结果不等于用户目标完成。

复合请求保留原文片段，复杂切分可以交给 System 2。显式动作优先于事实、已有硬状态、模型信号和历史推测。分 Fast / Work / Reflection 三个时间尺度；JEV 主要负责前两层。

## 本轮实现与证据

- [v0.2 协议](../../protocol/v0.2/README.md)：Frame、原始事件、十阶段契约、显式提交、生命周期和兼容边界。
- [验收](../../docs/acceptance-runtime-v02.md)：真实 OpenRouter JEV、用户既有百炼实时 ASR、Hyprland 当前窗口事件、浏览器。
- 首轮有限候选在一次 JEV 请求内并行求值；复杂切分及跨线程不明确引用会停留在 unresolved。
- 尚未完成的多层解析、常驻源、异步资源路由、Reflection 与通用目标验证器明确列在协议中，不将这份愿景整体标记为完成。

## 协作者状态

尚未收到 kanemaverick 对本提案的意见，不推定共同提出或共同认可。后续更新继续同步双方独立提案与统一进展。
