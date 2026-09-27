# COMPOSITION v0.1

提案作者：vimalinx。确定性策略实现与整理：Wilson。日期：2026-09-27。

组成界面的最小单位是具有稳定身份的对象投影与组件。正文、行情、资料、大纲可同时出现，不需要让用户选择或学习「页面模式」。Intent 身份保持稳定；变化的是当前 Working Set。此文不推定 kanemaverick 已认可方案。

## 1. 语义输入是受限的数据快照

`protocol/extensions/v0.1/view-context.schema.json` 定义：

| 字段 | 范围 |
|---|---|
| revision | 当前非负整数修订号 |
| document | 当前文档 ID，最长 160 字符 |
| selection | 显式选中的文本，最多 1200 字符 |
| blocks | 最多 16 个组件摘要 |
| block.id / title | 稳定 ID 与标题，最长 160 / 200 字符 |
| block.excerpt | 最多 600 字符 |
| block.pinned / hidden | 用户固定与隐藏约束 |

它提供结构化文本数据，不传 HTML、不传图片像素。输入是当前页面的有界快照，不表示已经实现完整桌面截图、全局窗口读取或持续屏幕监控。

JEV 分别判断 editor、market、supports、components 的相关分数；不要求先选唯一 surface，再强制替换整页。Intent、任务、权限和对象内容仍由 Runtime 管理。

前端输入采用 900 ms debounce；网络语义请求需当前 Intent 允许自动协助并具备有效授权，`localOnly` 阻止外发。模型响应经 stateVersion、请求归属与输入修订检查后才可进入组合策略。过期结果不能修改当前 UI；快照修订号不是额外授权。

## 2. 默认确定性策略

实现：`static/js/composition-policy.js`。

| 输入 | 接纳条件 | 输出 |
|---|---|---|
| score ≥ .75 | 一份新的、有效且已接受的样本 | hot |
| .55 ≤ score < .75 | 连续两份新的有效样本 | 从 cold/park 进入 near |
| .30 ≤ score < .55 | 保持现状，重置进出计数 | 不变化 |
| score < .30 | 连续两份新有效样本 | 从 near/hot 进入 park |
| pinned / explicit | 用户约束，优先于模型分数 | hot |
| interacting | 聚焦、编辑或拖动中 | 保持现状，重置进出计数 |
| dismissed | 持续人工约束，优先于自动建议 | 已出现的对象 park，未出现的对象 cold |

near 是可交互 preview；hot 表示当前活动组件。park 必须保留 rail 恢复入口，不能删除 Artifact 或 Intent。cold 表示尚未出现。强分数后的中弱分数不会立即缩小组件，也不会根据数值细微波动反复位移。

这里的连续是「被接受的语义样本」，不是渲染次数或时钟 tick。相同 Task ID 再次刷新不会累加。无效分数和重复样本不推进状态。人工约束期间的有效样本会被记录为已消费，解除约束后不会重放旧结果。

用户 dismiss 的约束持续存在；模型高分、缺省参数或 `dismissed:false` 都不能自动解除。用户恢复时调用 `restore(id)`。pin 与 dismiss 同时存在时先遵循 dismiss；恢复入口应同时更新 Runtime 中的对应人工状态。

## 3. API

```js
import {createCompositionPolicy} from './composition-policy.js';
const policy = createCompositionPolicy();
const id = `${intentId}:${componentId}`;

const next = policy.evaluate(id, {
  score: acceptedResult.components[componentId],
  sample: acceptedTask.id,
  pinned: layout.pinned,
  explicit: explicitlyAdded,
  interacting: hasFocusOrDrag,
  dismissed: layout.hidden
});
// next = {id, state, transition, changed, accepted, reason}
// 只有 changed 才需布局转场；不要将同一建议每帧重播。

// rail 入口上的显式点击：
const restored = policy.restore(id);
```

`sample` 必须是非空字符串，通常为已接纳的语义 Task ID。`score` 必须是有限的 0..1 数值。调用方必须先拒绝过期或非当前请求；策略只去重，不推断 Task ID 的时间先后。

`transition` 映射：初次 hot 为 FOREGROUND、初次 near 为 READY、退到 rail 为 PARK、从 park 返回为 RETURN；无状态变化为 null。该值可交给 `semanticTransition`，退出仍须提供目的地 rect。

`accepted` 表示本次新有效样本已消费，不表示内容事实已证实、不表示获准执行能力。`changed` 只描述建议状态变化，不说明宿主布局已经移动。

也导出模块级 `evaluate(id, options)`、`restore(id)` 便于小型接入；长期页面推荐实例化策略以明确状态归属。

## 4. 生命周期与持久化

策略不触碰 DOM、网络、存储或 Capability，也不会创建 Intent。每个实例按稳定 ID 保存状态、计数、人工隐藏约束和已见样本集合。

人工固定、显式加入、隐藏等 durable 状态由宿主通过 Command 持久化，页面恢复时重新提供。`restore` 只解除当前策略实例约束；宿主必须同步取消持久化隐藏状态，避免下一次快照重新隐藏。

已见 Task ID 在实例生命周期内精确去重。Intent 永久卸载时调用 `forget(id)` 释放单组件状态，或销毁工作空间实例时 `clear()`；不能每次 render 清空，否则滞回和去重失效。后台但可恢复的 Intent 不应因一次收起丢失状态。

重新加载页面后的语义历史去重和布局恢复由宿主负责，本模块不声称跨进程 exactly-once。规模化运行仍由批量执行与持久化 Task 层处理。

## 5. 接线和验证边界

本策略已提供独立、确定性的实现；宿主需要在每次接纳语义结果后调用，并以返回状态执行组件投影。它不自动重排布局、不自动隐藏焦点元素，也不保证网络响应顺序。

静态检查仅覆盖 JavaScript 语法。按用户安排未新增或执行交互测试和真实模型调用；实际输入连续性、人工约束恢复与侧栏布局由后续用户测试确认。


## 已接宿主

`adaptive-space.js` 为每个 Intent 建立策略实例，使用已接受的 presentation.task 去重；引用、图片、行情和扩展组件各自决定加入/保留/退到 rail。人工导入素材、显式添加、固定与恢复会保留对应组件。编辑器已有正文后不会因低分自动关闭。退到 rail 不删除 Artifact。

`component-registry.js` 实现 mount/update/dispose、版本隔离的本地状态、受限 Schema 校验、可选包内 CSS 与局部故障显示；SDK insert 要求用户手势。可信插件仍可访问同源 DOM，这不是安全沙箱。
