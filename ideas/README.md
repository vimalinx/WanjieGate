# Ideas · 万界门共同设计区

这里统一收录 **vimalinx 与 kanemaverick** 的想法，保留作者、演变、分歧与实现证据。Wilson 负责整理和技术评估，评估不代表任何一方作出决定。

## 当前入口

| 编号 | 作者 | 主题 | 状态 | 内容 |
|---|---|---|---|---|
| IDEA-0001 | vimalinx | 架构、协议、Context、组合、权限 | accepted · 本地已实现，外部待接入 | [最小语义操作系统与 Intent Runtime](vimalinx/0001-intent-runtime.md) |
| 待提交 | kanemaverick | 待提交 | awaiting-submission | [协作者入口](kanemaverick/README.md) |
| REVIEW-0001 | Wilson | 当前实现与迁移建议 | review | [源码对照评估](reviews/0001-runtime-gap-review.md) |

[统一进展与待决定事项](ROADMAP.md) · [新增提案模板](TEMPLATE.md)

## 分类

提案按作者存放，主题通过标签交叉索引；同一想法只保留一份正文。

| 分类 | 覆盖范围 | 当前记录 |
|---|---|---|
| 架构与协议 | 原语、消息、Manifest、Kernel、生命周期 | IDEA-0001 §1–7、§11–13、§16 |
| Context 与记忆 | Working Set、来源、Relation、Work Graph | IDEA-0001 §8–9、§15 |
| 交互与组合 | View、注意力、阶段切换、恢复现场 | IDEA-0001 §2、§10、§14 |
| 执行与权限 | Task、Policy、副作用、授权、因果追踪 | IDEA-0001 §3–4、§12、§16–17 |
| 集成与证据 | 现有代码、接口边界、实验、验收 | REVIEW-0001、ROADMAP |

## 两人共同更新的方式

1. 新想法复制模板，分配下一个 `IDEA-NNNN`，放入实际作者目录。记录作者与提交人；代转内容保留原作者，来源不明时写 `unknown`。
2. 修订已有提案时保留编号，增加更新记录。方向发生重大变化时新建提案，用 `supersedes` 或 `related` 关联旧提案。原提案的立场不被整理者的结论覆盖。
3. 每次设计或实现更新，都检查与其相关的**双方提案**，同步本索引、源码评估和 ROADMAP。没有收到另一方意见就记录“未收到”，不推定同意、反对或共同提出。
4. 冲突在 ROADMAP 中并列呈现双方观点、取舍和待决定人。只有明确确认后，才写明谁采纳了什么；“共同采纳”需要双方明确记录。
5. `implemented` 需要代码位置与提交证据；`validated` 另需注明验证方法、时间和范围。历史测试、代码存在和真实外部系统验收分别记录。
6. 提案里涉及其他 VimalinxOS 项目的内容只记录接口需求，交给根协调者确认 owner；本目录不授予跨项目修改、外部动作或付费调用权限。

状态：`proposed` → `discussing` → `accepted` → `implemented` → `validated`；另可标 `deferred` / `superseded`。状态描述设计推进，不替代执行授权。`review` 和 `awaiting-submission` 是评估/入口状态。

## 更新记录

- 2026-09-27：建立共同设计区；vimalinx 明确确认 IDEA-0001 为本人方案，共同参与者为 vimalinx 与 kanemaverick。尚未收到 kanemaverick 的具体提案。加入基于源码提交 `22f9541` 的评估。

- 2026-09-27：vimalinx 授权完整实现；本地 Runtime 已落地，证据与未验收项见 [验收记录](../docs/acceptance-runtime-v01.md)。第三方参考研究由 Wilson 整理于 [研究记录](research/0001-reference-implementations.md)，不推定为双方共同观点。

- [参考研究后的本地改动](reviews/0002-reference-driven-changes.md)：请求身份、旧响应保护、显式读取深度与执行边界。

## IDEA-0002 实现更新（2026-09-27，Codex）

本会话用户选择原会话执行后，泡泡 Demo 已在 `codex/bubble-demo` 实现。代码：`static/js/bubbles/`、`backend/runtime/bubbles.py`；早期实现提交 `453c651`、`0eac612`。真实 Jev、资料写作、行情研究与浏览器交互的证据见 [验收与交接](../docs/acceptance-bubble-demo.md)。本条更新实现状态，前面的未实现描述保留为历史。作者保持 unknown，未收到双方具名共识。

## IDEA-0004 · Vicinae 意图泡泡实施

[提案](unknown/0004-vicinae-intent-bubbles.md) · [验收](../docs/acceptance-vicinae-bubbles.md)：用户指定 5174 画风并授权自主开发测试；Codex 在独立工作树完成万界门侧桥接和原生面板。未替换 Vicinae 主搜索框，未自动发帖。关联 IDEA-0001/0002，不推定双方共识。

2026-09-27 用户补充：入口采用全局快捷键搜索浮层，随后明确去掉框外底板、只保留搜索框；已在 `integrations/vicinae/IntentPanel.swift` 和 `static/launcher.css` 实现透明承载、输入展开泡泡。原生视觉与 Esc 日志已检查；全局物理快捷键仍未实测，详见验收记录。作者归属保持 unknown。

2026-09-27 后续：修复桥接漏掉 Vicinae 应用启动项的问题，“帮我打开微信”已真实返回启动泡泡；按用户反馈改为输入展开磨砂面板、提高泡泡对比度。代码与 85 用例回归范围见 [验收记录](../docs/acceptance-vicinae-bubbles.md)。实现 Codex，提案作者 unknown，保留前版视觉选择为历史。
