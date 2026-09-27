# MOTION_SPEC v0.1

提案作者：vimalinx。工程整理与实现：Wilson。日期：2026-09-27。

本规范将用户提出的「流体工作集」转换为组件接口。它不表示 kanemaverick 已确认此方案；其相关意见尚未收到。

## 1. 基本约束

1. 对象拥有稳定 ID；展开、缩小、换位置复用原节点，编辑内容和选区归属于对象。
2. 只有发生语义变化的对象运动，不对整个工作页淡入、滑动或缩放。
3. 收起必须有目的地，例如同一组件在边缘栏的入口。目的地保留身份和恢复入口。
4. 用户的拖动、固定、焦点和明确选择优先。系统不能为完成动画而冻结输入。
5. 动画只呈现已被 Policy 接纳的状态；不能创建 Intent、修改权限或声称任务已完成。
6. 概率不能逐帧驱动坐标或透明度。控制器读取离散状态，不自行解释 JEV 输出。

## 2. 速度与运动原语

| 原语 | 默认时长 | 曲线 | 意义 |
|---|---:|---|---|
| APPROACH | 240 ms | ease-out | 对象进入当前工作集 |
| EXPAND | 220 ms | 低过冲曲线 | 同一对象展开，保留相对位置 |
| RECEDE | 180 ms | ease-in | 向明确入口退远 |
| BRANCH | 260 ms | 低过冲曲线 | 已确认的新分支与原任务分开 |
| MERGE | 280 ms | 低过冲曲线 | 对象投影移动到共同区域 |
| SETTLE | 120 ms | 低过冲曲线 | 位置或选择确定；1 → .985 → 1 |
| GHOST | 160 ms | ease-out | opacity .45、blur .5 px 的非交互预测态 |
| FREEZE | 120 ms | 低过冲曲线 | 人工固定后的落定反馈 |

当前实现使用 Web Animations API 和 `cubic-bezier(.2,.8,.2,1)` 近似阻尼响应，未引入物理弹簧引擎。靠近采用 `cubic-bezier(.16,1,.3,1)`，退出采用 `cubic-bezier(.4,0,1,1)`。不通过拉伸文字表现容器形变。

Hover/press 建议 70–100 ms，输入微响应 100–140 ms；它们只表示收到用户操作，不表示语义判断成功。相关对象的 stagger 上限 50 ms；任何动画不得成为开始编辑的前置条件。

## 3. Semantic transition 映射

| 状态变化 | 原语 | 时长 | 条件 / 目的地 |
|---|---|---:|---|
| WARM | APPROACH | 240 ms | 已确定需要的边缘对象 |
| FOREGROUND | EXPAND | 220 ms | 已有对象展开 |
| RETURN | EXPAND | 300 ms | 原工作集恢复；需调用方提供旧入口与新位置 |
| CORRECT | RECEDE | 180 ms | 旧建议退回原点；新建议单独 APPROACH |
| BRANCH | BRANCH | 260 ms | Runtime 已产生分支；动画不能伪造它 |
| MERGE | MERGE | 280 ms | Runtime 已合并，提供目标容器 |
| PARK | RECEDE | 260 ms | 同一对象的 rail 入口 |
| INTERRUPT | APPROACH | 180 ms | Policy 已确定必须打断 |
| COMMIT | SETTLE | 120 ms | 用户或确定性规则已确认 |
| HYPOTHESIS / PREPARED | GHOST | 160 ms | 稳定候选；不接受点击、拖动或键盘焦点 |
| READY | EXPAND | 220 ms | 恢复原交互属性成为 preview |
| FREEZE | FREEZE | 120 ms | 先持久化用户固定，再给落定反馈 |

BRANCH 在提供 `from/to` 时采用带中点偏移的三段路径近似弧线，中点上移 16 px；它不是完整物理液滴效果。MERGE 移动现有投影，不复制底层 Artifact。语义请求格式见 `protocol/extensions/v0.1/motion.schema.json`；`cause` 引用原 Event/Command，`destination` 是稳定实体标识，由前端解析为 DOM rect。

## 4. 可调用控制器

源文件：`static/js/semantic-motion.js`。

```js
import {motion, relocate, semanticTransition, setMotionPinned, disposeMotion}
  from './semantic-motion.js';

// 系统移动：固定、焦点或拖动期间，mutate 不会运行。
relocate(block, () => lane.append(block), 'APPROACH', false);

// 用户收起：先创建带同一 entity ID 的恢复入口。
motion(block, 'RECEDE', {
  to: railButton.getBoundingClientRect(),
  human: true,
  done: () => { block.hidden = true; }
});

// 用户固定：布局持久化由 Command 负责，控制器只管理运动。
setMotionPinned(block, true);
motion(block, 'FREEZE', {human: true});

// 已确认的语义变化。
semanticTransition(block, 'COMMIT', {human: true});
```

### 参数与完成语义

- 兼容原接口 `motion(el, primitive, {from, to, human, done})`、`relocate(el, mutate, primitive, human)`、`stopMotion(el)`。
- `from/to` 是 viewport rect。通常先读旧 rect，完成 DOM 布局更新，读取新 rect，使用 FLIP 平移。
- RECEDE 只需 `to`；当前位置自动读取。`direction: 'exit'` 也可明确要求向目标退场。
- 没有退出目的地时返回 `suppressed/destination-required`，保留对象，不调用 `done`。
- 被 pin/focus/drag 拦截时返回 `suppressed/user-control`。尤其不能先改 DOM 再检查；使用 `relocate` 包裹布局修改。
- `human: true` 仅由用户事件处理链设置。它允许明确收起当前聚焦对象，避免 `done` 永远不能到达；JEV signal 不得冒充人工操作。
- 返回 `{status, finished, cancel?}`；`finished` 解析为 completed/cancelled/suppressed。被替代动画的旧 `done` 不执行，以免旧回调隐藏新状态。
- 正在运行的系统动画遇到对象上的 focus/pointerdown/dragstart 会取消。显式人工动画可以被新的人工请求替代。
- 重定向先读取当前视觉 transform/opacity/filter，再取消旧动画；不等待旧动画结束。布局移动用视觉 rect 计算新的 FLIP 起点。
- `GHOST` 的透明度和不可交互状态持续保留到预览；设置 `inert`、`aria-hidden` 和 `pointer-events:none`。后续非 GHOST 请求恢复之前的值。
- `disposeMotion` 用于模块销毁，取消动画并清理临时属性；`stopMotion` 只停止运动，不把预测态变成可操作对象。
- `.motion-off` 或 `prefers-reduced-motion:reduce` 开启时，新请求直接完成布局与回调；MutationObserver 与 media-query change 也会立即结束正在运行的 WAAPI 动画，完成回调只执行一次。仍保留预测态、人工固定等语义。

## 5. 布局与滞回策略

COLD/WARM/NEAR/HOT 由上游组合策略决定；动效层不能把 .61/.64/.62 直接映射为往返运动。固定对象优先于自动排序，隐藏对象保持人工约束。默认进入与退出阈值及样本滞回由 `composition-policy.js` 实现，见 [COMPOSITION_v0.1](COMPOSITION_v0.1.md)。本控制器不实现语义判断或驻留计时。

z-index 由宿主样式统一管理，模块不得自行无限提高：普通工作内容为基准层，预测态在旁侧辅助层，拖动预览在浮动层，真正需要中断的内容在中断层。控制器不提升 z-index、不抢焦点；中断的键盘策略由宿主处理。

## 6. 接入与验证边界

已提供可复用控制器、原语、状态映射、协议 schema、人工优先保护、非交互 ghost、可取消重定向和退出目的地检查。宿主组件可以通过原 API 接入，不需要替换编辑器。

BRANCH / MERGE / RETURN / INTERRUPT 的映射是可接接口，不代表所有 Runtime 生命周期已接上对应动画。工作集中的每个稳定对象及其 rail 入口需要宿主维护；通知吸收、跨 Intent 共享元素、完整分支弧线路径仍需对应真实事件接线。不得用演示动画冒充已经发生的任务或分支。

本次只做 JavaScript 语法与 JSON 解析检查。按用户安排，未新增或运行交互测试、浏览器测试和真实模型调用；视觉连续性、输入不中断及 reduced-motion 实际效果仍由后续交互验收确认。


宿主本轮已接入：辅助块 APPROACH、人工拖动 FLIP 后 FREEZE、人工收起/计算退场指向 rail 按钮的 RECEDE、rail 恢复 RETURN；切换 Intent 时调用 disposeMotion 清理旧实例。没有全屏转场或编辑冻结。BRANCH/MERGE/INTERRUPT 仍保留上文接线边界。

## 7. 回到原点与进入下一件事

来源：vimalinx 后续交互修正。用户主动新开工作面时允许当前各内容块分别离场：每块向左退场 280 ms，错开不超过 48 ms；这是明确新建动作的全工作集切换，不用于普通模型重排。当前内容先保存到原 Intent，历史保留其身份。

`workspace-transition.js` 的 `returnToOrigin({reset, slide})` 使用只读、不可交互的离场投影，并保留原输入节点收回新胶囊（340 ms）；WANJIE 各条百叶窗上下反向回位（240 ms + 每条 10 ms）。用户开始操作即可中止胶囊动画，减少动态效果时立即完成状态切换。

未固定文稿清空时 `slide=false`，保存空正文、解除该文稿的当前投影再回原点，不删除对象。`surface.manual=true` 表示用户固定编辑区，清空不自动收回。

输入手势：自然滚动触控板的横向负 deltaX 累计 110 px、水平量至少为垂直 1.6 倍；双触点向右移动采用同一阈值并排除缩放。保留可横向滚动内容、弹窗和拖拽的操作权；惯性锁避免一次手势创建多个起点。手势依赖操作系统滚动方向，另提供历史中的“新的空间”和 Ctrl/Cmd+Shift+N。物理设备手感尚未实测。

左侧无组件时，边缘停留 180 ms 非模态浮出历史；离开 260 ms 收起，历史内部焦点或显式点击入口保留。历史浮出不使正文 inert，不抢输入焦点。
