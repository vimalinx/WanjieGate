# Ideas · 统一进展与待决定事项

更新：2026-09-27。代码评估基线：`22f9541`。本文件汇总双方提案与实现状态，执行顺序为 Wilson 的建议。

## 已确认与尚未确认

- 已确认：vimalinx 与 kanemaverick 为共同设计参与者；本目录统一维护双方 idea。
- 已确认：IDEA-0001 的作者是 vimalinx，内容是最小语义操作系统与 Intent Runtime 方向。
- 尚未确认：kanemaverick 的具体提案、对 IDEA-0001 的回应，以及双方共同采纳的协议细节。
- 已完成：提案收录、作者分类、主题索引、源码对照、后续更新约定。
- vimalinx 已授权继续完整实现；本地 Protocol、Kernel、工作集、统一执行和 UI 已实现，见 [实现与验收记录](../docs/acceptance-runtime-v01.md)。
- 外部桌面、设备和其他项目适配尚未完成；最后修订未重跑验收。双方共同采纳仍未确认。

## 议题对照

| 议题 | vimalinx | kanemaverick | Wilson 评估 | 当前结论 |
|---|---|---|---|---|
| Intent 为组织单位 | 持久语义空间与八维状态 | 未收到 | 支持；补身份、生命周期、字段来源 | 本地已实现；作者授权 |
| 四种消息 | EVENT / SIGNAL / COMMAND / RESULT | 未收到 | 支持；补版本、payload 校验与投递语义 | 本地已实现；作者授权 |
| Kernel / 模块 | 小内核、统一 Manifest | 未收到 | 从本进程模块开始，逐步增加隔离 | 本地已实现；作者授权 |
| Working Set / Relation | HOT/WARM/COLD、小关系集合 | 未收到 | 加预算、固定对象、引用版本与来源 | 本地已实现；作者授权 |
| 前端作为 Bus Client | 围绕 State 自动投影 | 未收到 | 保留 HTTP 传输适配，可渐进迁移 | 本地已实现；作者授权 |
| L0–L3 | 分级副作用，严格治理 L3 | 未收到 | 单列网络、费用、授权与可补偿性 | 本地已实现；作者授权 |
| Protocol v0.1 | 建议下一步正式定义 | 未收到 | 先协议草案与一个完整生命周期样例 | v0.1 本地实现 |

上述“支持”仅为评估者意见。没有记录到双方实际分歧，不能把“未收到”写成反对或共识。

## 建议阶段

| 阶段 | 交付 | 完成条件 | 状态 |
|---|---|---|---|
| P0 · 收录与评估 | 来源、作者、分类、代码映射 | 当前提案可查、未知状态明确 | 本轮完成 |
| P1 · Protocol v0.1 草案 | Message、Manifest、Intent、Artifact、Capability Schema；Task / Signal / Result 类型；生命周期例子 | 字段与错误语义明确，合法/非法样例可校验；有评审记录 | 本地实现；证据见验收记录 |
| P2 · 本地最小闭环 | Bus、State、Intent / Capability Registry、Task 调度、权限检查 | 用户激活 Intent → 本地分析 → Artifact → View；因果链可解释 | 本地实现；证据见验收记录 |
| P3 · 现有路径接入 | 手动 Scheduler、实时 LiveRuntime、KEV / 生成 / 行情适配 | 执行统一受理，保留旧数据、去重、失败与取消语义 | 本地实现；证据见验收记录 |
| P4 · 工作集与重组 | Context、Relation、phase 切换、局部 View 更新 | 返回 Intent 恢复相关对象，保留编辑与固定项，过期判断不覆盖 | 本地实现；证据见验收记录 |
| P5 · 外部模块 | 桌面、Agent、记忆、通知等协议对接 | 根协调者确认项目 owner 和接口；各项目分别验收 | 仅接口设想 |

## 协议设计检查项

1. **Message**：协议版本、kind/type、Schema 引用、目标、时间单位、有效期、correlation/causation、权限主体；Signal 所依据的状态版本；Command 去重与结果不明。
2. **Module Manifest**：模块身份与版本，provides/accepts/emits、所需 Context、权限/费用/外发声明、启动停止和兼容行为。Artifact 类型引用如何装入四种消息。
3. **Intent**：稳定 ID、八维状态、生命周期、父子分支、版本、显式选择的优先级与恢复规则。
4. **Artifact**：身份、类型、内容引用、版本、来源、访问范围、Relation、与 View 解耦。大内容通过引用传递。
5. **Capability / Task**：能力定义与提供者绑定分开，输入输出类型、Task 状态机、排队取消、部分完成、未知结果和补偿。
6. **Policy / Permission**：Policy 的版本与输入快照、授权引用、拒绝理由、已有授权复用、撤销、预算与资源约束。
7. **完整生命周期**：激活 → 收到事实 → Signal → Policy → Command → Task → Result → 提交事实 → UI 投影；包含失败、重复、过期、取消和重启。

上述检查项的当前定义见 [Protocol v0.1](../protocol/v0.1/README.md)。v0.1 为本地实现契约，外部插件兼容性尚未验收。

## 跨项目交接事项

| 外部范围 | 本项目已观察事实 | 待决定 | 应交给谁 |
|---|---|---|---|
| AIOS / 桌面 / Agent / Memory / 通知 | 本轮只观察到 WanjieGate 中的接口需求；对方实现 unknown | 协议归属、适配 owner、授权边界、版本兼容 | VimalinxOS 根协调者确认注册项目 owner |
| LocalRouter | 本项目 Generator 调用 `lr exec`，没有修改其代码或配置 | Runtime 如何表达并复用已有调用权限与预算 | 根协调者协调 LocalRouter owner；不在此新增管理路径 |

## 后续更新记录

| 日期 | 更新者 | 来源 | 变化 | 实现与验证 |
|---|---|---|---|---|
| 2026-09-27 | Wilson | vimalinx 本轮提案与作者确认；源码 `22f9541` | 建立索引、提案、评估、阶段与协作规则 | 仅文档变更；未做 Runtime 实现或运行验收 |

- 2026-09-27：按 vimalinx 的实现授权落地本地 Runtime；保留 kanemaverick 未提交状态。新增第三方参考研究任务，不能把用户转贴的研究报告当作已核验源码或 kanemaverick 的提案。

## 泡泡 Demo 实现状态（2026-09-27，Codex）

IDEA-0002 已有本机 `/demo` 产品入口：胶囊、浮动泡泡、融合、显式运行、来源绑定、编辑和恢复。复用 IDEA-0001 的 Command / Task / Artifact / Grant；实现证据 `453c651`、`0eac612` 及本分支后续提交。真实 Jev、两条生成流程与本机交互已验收，范围见 [记录](../docs/acceptance-bubble-demo.md)。外部搜索 API、多人编辑和队员服务整合仍未完成；kanemaverick 具名意见仍未收到。

## IDEA-0004 · 本项目实施与验证

2026-09-27：用户授权自主开发，视觉采用现有 5174 Demo。万界门侧实时判断、6 个 Vicinae 入口、双击执行、组合产物与原生磨砂面板已实现。实际验证桌面交接、股票研究卡片、Python 官方资料提纲、社交草稿；[文件与验证证据](../docs/acceptance-vicinae-bubbles.md)。离线覆盖旧响应、重复运行和画布版本。原主搜索框改造及外部 owner 仍待根协调者确定；社交仅编辑器交接，无实际发帖。提案作者 unknown，评估和本次实现 Codex，未收到双方具名共识。

2026-09-27 用户补充：入口采用全局快捷键搜索浮层，随后明确去掉框外底板、只保留搜索框；已在 `integrations/vicinae/IntentPanel.swift` 和 `static/launcher.css` 实现透明承载、输入展开泡泡。原生视觉与 Esc 日志已检查；全局物理快捷键仍未实测，详见验收记录。作者归属保持 unknown。

2026-09-27 后续：修复桥接漏掉 Vicinae 应用启动项的问题，“帮我打开微信”已真实返回启动泡泡；按用户反馈改为输入展开磨砂面板、提高泡泡对比度。代码与 85 用例回归范围见 [验收记录](../docs/acceptance-vicinae-bubbles.md)。实现 Codex，提案作者 unknown，保留前版视觉选择为历史。

2026-09-27：用户反馈仍像实体界面，尚待区分视觉不透明与外部应用跳转。Codex 先修正已观察到的叠层遮挡：降低 `static/launcher.css` 的展开底色、搜索框与结果抽屉不透明度。已检查原生窗口加载，未修改微信交接行为；不据单窗口截图声称桌面背景模糊已完成端到端验证。
