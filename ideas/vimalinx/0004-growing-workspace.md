# IDEA-0004 · 无模式的生长工作集

- 作者：vimalinx
- 整理者：Wilson
- 日期：2026-09-27
- 状态：implemented（局部实现，最新组合链待用户交互验收）
- 关联：IDEA-0001、IDEA-0002、IDEA-0003、IDEA-0005、IDEA-0006
- kanemaverick：尚未收到意见，不代表共同采纳。

## 用户要求

空白与胶囊是入口；生长对象包含整片工作现场。直接写正文时原输入区域成为持续编辑的文稿，大纲、引用、案例、图片、行情可独立出现、同时存在。前台不显示排他的“写作/市场/自由”模式。用户可拖拽组件、把资料拖入正文、把文字拖为独立笔记。

界面内容本身可成为下一轮 JEV 的有界输入：当前正文、选区、可见内容摘要、人工固定或收起状态。JEV 判断缺少什么，不直接生成执行代码、替用户改写或放权。用户行为高于模型软信号。

## 实现落点

- `static/js/adaptive-space.js`：同一编辑节点、正文保存、选择/光标、组件身份、布局、资料和素材拖拽。
- `backend/runtime/presentation.py`：独立编辑器/行情/辅助组件判断，可共存；有限检索候选。
- `protocol/extensions/v0.1/view-context.schema.json`：有界视图数据协议。
- `static/js/component-registry.js`：声明式目录与可信组件生命周期。
- `docs/standards/COMPOSITION_v0.1.md`：组合策略与预算。

当前仍保留旧 `surface.mode` 字段读取兼容，只承担文稿编辑器几何状态；新的语义判断不使用 Surface Choice，也不据此关闭其他组件。通用任意布局、富文本块编辑、跨设备同步不在本轮完成声明中。
