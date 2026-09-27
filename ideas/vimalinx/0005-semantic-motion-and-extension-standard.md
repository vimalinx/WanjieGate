# IDEA-0005 · 语义动效与可批量扩展标准

- 作者：vimalinx
- 整理者：Wilson
- 日期：2026-09-27
- 状态：implemented（控制器与工具接口；完整动效演示尚未验收）
- 关联：IDEA-0003、IDEA-0004
- kanemaverick：未收到意见。

## 总纲

没有东西瞬移，没有东西无缘无故消失，没有东西为了好看而移动。人的动作高于 AI 预测。用户无需理解内部 Intent / Artifact / Capability 分类。

六种运动：APPROACH、EXPAND、RECEDE、BRANCH、MERGE、SETTLE。特殊态：GHOST、FREEZE。语义状态触发动效，不把连续概率直接映射成位移和透明度。Ghost 不可交互；Preview 保留原实体；Commit 落定。动画可中断、不冻结输入，只移动发生语义变化的局部对象。Pin 必须改变布局策略。退场必须有去处，减少动态效果仍完成同样的状态改变。

## 交付

- [MOTION_SPEC_v0.1](../../docs/standards/MOTION_SPEC_v0.1.md)：时长、曲线、映射、降级、实现边界。
- [扩展标准](../../docs/standards/EXTENSIONS_v0.1.md)：模块身份、manifest、Schema、生命周期、固定摘要。
- [批量执行标准](../../docs/standards/BATCH_v0.1.md)：依赖、并发、预算、落盘、失败和未知结果。

用户明确自行测试，因此最新标准只做静态检查，不把之前的真实 JEV/浏览器证据等同于本轮全部通过。BRANCH/MERGE 等原语存在不代表完整自动分支演示已实现。
