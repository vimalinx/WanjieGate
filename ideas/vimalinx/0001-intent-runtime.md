# IDEA-0001 · 最小语义操作系统与 Intent Runtime

| 字段 | 内容 |
|---|---|
| 作者 / 提交人 | vimalinx |
| 整理者 | Wilson |
| 创建 / 更新 | 2026-09-27 |
| 状态 | accepted（vimalinx 授权实现）；本地 v0.1 已实现，外部接入未完成；尚未记录双方共同采纳 |
| 来源 | 2026-09-27 本项目会话中的完整架构提案；随后作者确认“我和 kanemaverick；这份是我的” |
| 分类 | 架构与协议、Context 与记忆、交互与组合、执行与权限 |
| 范围 | 在 WanjieGate 中探索协议与原型；AI OS 跨项目接入由根协调者协调 |
| 关联 | [REVIEW-0001](../reviews/0001-runtime-gap-review.md)、[统一进展](../ROADMAP.md) |

本文是对作者原消息的结构化整理，保留全部 17 个议题、核心字段和例子，非逐字原文。工程补充与异议另列于 REVIEW-0001。

> 所有东西都是模块；所有模块只通过类型化消息交换；Intent 是动态重组这些模块的依据；JEV 只负责产生语义信号，Kernel 负责把这些信号变成确定性的系统行为。

> App 不再是基本单位。Intent 才是基本单位。

## 1. 十个原语

| 原语 | 含义 |
|---|---|
| Intent | “我正在做哪件事”的持久语义空间 |
| Artifact | 被使用、产生、修改的文件、网页、代码、消息、图片和结果 |
| Event | 已经真实发生的事实 |
| Signal | 对情况的语义判断，允许概率 |
| Command | 请求系统做一件事 |
| Capability | 系统会做什么 |
| Task | Capability 的一次具体执行实例 |
| Context | 当前 Intent 此刻需要的一小部分世界 |
| View | Context / Artifact 的屏幕投影 |
| Policy | Signal + State → 系统如何变化 |

传统应用拆成可组合部件：VSCode 对应 Repo / File Artifact、Code View、编辑/搜索/Git/终端能力、诊断事件源；Chrome 对应 Web Artifact / View、导航/搜索/下载能力和 DOM 事件源。Runtime 根据任务需要组合代码、Repo、Terminal 与测试能力。

## 2. Intent 是正交状态

```text
IntentState { thread, goal, domain, phase, target, attention, commitment, urgency }
```

例如 JEV-Hackathon / build-prototype / software / implementation / intent-runtime / foreground / actively-working / today。

“晚上记得给电脑充电”形成新的分支，domain=personal、phase=remember、attention=background、urgency=tonight。Intent 不能压缩成 coding / reminder / chatting 的单个标签。

## 3. 四种消息

| kind | 回答的问题 | 示例 |
|---|---|---|
| EVENT | 发生了什么 | window.focus.changed、file.opened、agent.finished、asr.partial.received |
| SIGNAL | 意味着什么 | intent.continuity、artifact.relevance、attention.interruptible |
| COMMAND | 希望发生什么 | workspace.activate、skill.warm、agent.spawn、artifact.open |
| RESULT | 请求的结果 | success、failure、partial、cancelled，可附 Artifact |

循环：EVENT → SIGNAL → POLICY → COMMAND → RESULT → EVENT。

## 4. 语义与执行分离

JEV 只产生 Signal；Policy 决定是否准备动作、是否需要确认；Capability 执行动作。对“可能想发送”的高分判断不能直接变成发送动作。prepare / commit 是两个阶段。

## 5. 统一 Module Manifest

每个模块声明输入、输出、所需 Context、副作用、权限和适用场景。

```yaml
id: skill.repo-search
kind: capability
provides: [repo.search]
accepts: [command.repo.search]
emits: [artifact.search-results, event.search.completed]
requires_context: [repo]
side_effect: none
latency: low
reversible: true
permissions: [filesystem.read]
```

View 示例：`view.code-editor` 接受 `artifact.code`，支持 `intent.domain.software`，提供 `ui.code-editor`。

通知 Policy 接受通知事件、相关性与可打断性信号，发出 attach / defer / interrupt 命令。模块可由不同语言、本地或远程服务实现，共用协议。

## 6. Capability Registry

注册 repo.search、web.search、text.edit、code.run、image.generate、message.send、calendar.read/create、memory.retrieve、video.play 等能力。

先确定任务需要的能力，再选择具体提供者：repo.search 可对应 ripgrep、GitHub Search 或 Agent Repo Skill；docs.search 可对应浏览器、本地索引或 Web Search。

## 7. 小 Skill 与组合图

基础 Skill 拆为 repo.search、repo.inspect、test.run、error.parse、docs.lookup、dependency.inspect、patch.apply、git.diff。

DebugSkill 是 error.parse → repo.search → code.inspect → 可选 docs.lookup → patch.apply → test.run 的组合图，可按需加载和替换。

## 8. Memory = Artifact + Relation

记忆保留独立事实、关系、scope、source、confidence 与 status。例如 Agent 是临时 worker，Intent 是持久工作上下文，并保留支持架构决定的关系与原会话来源。

语义层判断某条记忆是否相关，Context Manager 选择当前所需的小集合；作者提出 5–20 条作为直观例子。

## 9. Working Set

每个 Intent 有 HOT / WARM / COLD：当前 Repo、架构、文档、规则在 HOT；之前 UI 思路、语音管线、通知概念在 WARM；旧实验在 COLD。

语义判断为 promote / demote / keep / evict 提供依据，Agent 被唤醒时得到 HOT 与必要的 WARM。具体状态变更仍遵守 §4 的 Policy / Capability 分层。

## 10. View Primitive

Text、Code、Terminal、Web、Media、Canvas、Timeline、Table、Conversation、Inspector。

Artifact 定义内容身份，View 定义呈现方式，Intent 决定当前显示与布局。同一 Markdown Artifact 可作为 Note、Preview、Side Panel 或 Context Inspector，无需复制数据。

## 11. 前端作为 Bus Client

Renderer 发出 `command.intent.activate`，Kernel 更新状态并发布 `event.intent.activated`；Context、Skill、Memory、Notification 等模块响应，UI 从新 State 投影。

作者希望系统中心是 Bus + State，避免所有能力都耦合到一个大后端接口。

## 12. Semantic Microkernel

Kernel 只负责 Event Bus、State Store、Intent Registry、Capability Registry、Scheduler、Permission Broker、Module Lifecycle。

AI、搜索、记忆总结、UI、Agent、语音、通知理解均为模块。语义模型可以替换，系统仍有明确的运行行为。

## 13. Semantic Operator

Classifier、Ranker、Gate、Matcher、ContinuityDetector、InterruptibilityDetector、RelevanceScorer 提供统一接口。

实现可由 JEV、规则、Embedding、LLM 或用户显式选择提供。例：`semantic.relevance(artifact, intent)`；以后可先 Embedding，再对歧义情况使用 JEV。

## 14. Intent 驱动重组的生命周期

1. session.started，读取已授权日历信息、上次 Intent、Repo 和暂停状态。
2. Operator 给出 resume_candidate，Policy 判断是否预热。
3. 模块准备记忆、Skill、Artifact、View、通知与 Agent 执行上下文。
4. 用户 Resume 后激活工作现场。
5. “查一下还有没有别的 Jev demo”将 phase 从 implementation 改为 researching，搜索/文档前置，代码保留 WARM。
6. “回去写吧”恢复 implementation 与代码视图。

## 15. Relation / Work Graph

Relation 可放在 Artifact metadata 内，不必增加第 11 个顶层原语，但需要明确存在。

限定初始关系：belongs_to、references、produced_by、depends_on、supports、conflicts_with、derived_from。

对象关联到 Intent，记忆支持决定，产物有来源与依赖，系统形成 Work Graph。

## 16. Message Envelope 初案

```ts
type Message = {
  id: string
  kind: "event" | "signal" | "command" | "result"
  type: string
  timestamp: number
  source: string
  intent?: string
  artifact?: string
  correlationId?: string
  causationId?: string
  payload: unknown
  confidence?: number
  priority?: number
  ttl?: number
  provenance?: Provenance
}
```

correlationId / causationId 用于解释某条通知为何隐藏、Agent 为何启动、Skill 为何加载。以上是作者的概念草案，尚无可执行 Schema 与校验器。

## 17. 副作用分级

| 等级 | 作者定义 | 示例 |
|---|---|---|
| L0 | Observe | 读文件 |
| L1 | Prepare | 预加载网页 |
| L2 | Reversible | 打开窗口、修改草稿 |
| L3 | Irreversible | 发送消息、付款、删除数据 |

语义层大量为 L0 / L1 提供判断，可影响 L2；L3 需更严格 Policy / 用户确认。工程评估将补充网络、费用与授权不能仅由这个分级表达。

## 作者建议的下一步

编写 **Intent Runtime Protocol v0.1**：固定 Message Schema、Module Manifest、Intent Schema、Artifact Schema、Capability Schema 和完整生命周期，再让 UI、桌面、语义模型、Memory、Agent 接入。

本记录收录该建议；协议尚未发布，实现状态见评估，不将文字方案视作已完成工程。

## 双方回应与更新

- vimalinx：提出以上方向，明确作者身份，要求统一收录双方 idea。
- kanemaverick：尚未收到回应或单独提案。
- Wilson：意见与源码证据见 REVIEW-0001。
- 2026-09-27：首次整理，保留全部 17 个议题；未产生双方共同采纳记录。
