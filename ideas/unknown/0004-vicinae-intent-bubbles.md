# IDEA-0004 · Vicinae 意图输入与灵感泡泡

- 作者：当前会话用户，具体署名 unknown；不根据 GitHub 登录账号推定身份。
- 来源：2026-09-27 当前会话。
- 整理与评估：Codex；本记录未冒用 Wilson 署名。
- 状态：万界门侧桥接与原生面板 implemented；原生主搜索框整合尚未实施。实际验证范围见文末验收记录。
- 关联：IDEA-0001 Intent Runtime、IDEA-0002 胶囊与浮动泡泡、Jev 场景种子语料。

## 用户构想

将万界门与 Vicinae 结合，利用 Jev 理解一段想法，匹配 Vicinae 命令，并将候选呈现为对话框之外的灵感泡泡。

## Codex 初步评估（保留早期方案，后续选择见下文）

建议由万界门管理 Intent、上下文、候选泡泡和执行记录，Jev 对已登记能力做语义判断，Vicinae 负责桌面命令及扩展运行。先桥接验证，再决定是否把入口和泡泡整合进 Vicinae 原生窗口。

候选须关联真实命令 ID、参数约束、可用状态、输入对象与输入版本。缺少参数时显示补充入口，无匹配时允许无候选。候选不自动执行。资料与动作组合需要兼容的输入输出类型，打开界面的命令不可假定提供可组合结果。

优先验证命令清单、参数传递、启动反馈和结果回传。命令已受理、界面已打开与业务完成必须分别记录。首版可选少量低风险能力；数量和具体场景待用户决定。

窗口方案有三种：扩展内部候选列表、万界门独立桌面浮层、Vicinae 原生窗口内的输入区与泡泡区。建议先用现有万界门界面完成桥接，再以第三种作为候选产品形态。若要求泡泡超出操作系统窗口边界，需要独立透明窗口及焦点管理，不能由网页样式直接完成。

## 已观察证据

- 本地 `backend/runtime/capabilities.py` 的 Semantic.observe 默认调用 KEV，当前能力判断是固定的 5 项；尚未接入动态 Vicinae 命令目录。
- 本地 `backend/runtime/policies.py` 已有 capability.selection 建议策略。
- Vicinae 上游 main 的 [CLI 源码](https://github.com/vicinaehq/vicinae/blob/main/src/cli/src/cli.cpp)包含 `cmd ls --json`、`cmd launch`、参数和 query 传递。此处为可变 main 的阅读结果，实现前需固定版本并实测。
- [Vicinae README](https://github.com/vicinaehq/vicinae)说明已有应用搜索、文件搜索、剪贴板、扩展和脚本支持。
- 已安装 Jev 浏览器技能的 helper 依赖 Codex CUA，不是独立产品桌面驱动；产品语义适配需独立设计，不能假定复制技能就完成接入。

## 双方回应与项目边界

vimalinx 与 kanemaverick 的具名回应均未收到，不推定共识。本项目可负责 Runtime 适配契约与万界门界面；Vicinae fork 的实现 owner 和注册项目归属 unknown，需要根协调者确认。当前未修改外部仓库。

## 实现与验证

仅收录提案、关联索引和初步评估；未修改产品代码。验证范围为本地源码与上游文档/源码阅读，未运行 Vicinae、未调用 Jev、未验证命令桥接或桌面泡泡。

## 用户已确认的选择（2026-09-27）

用户明确要求：输入框周围为磨砂式界面，出现透明泡泡；万界门操作逻辑嵌入 Vicinae 搜索框；场景包含调研、看股票、发推特或其他社交媒体；双击执行、拖拽合并；Jev 实时判断并添加泡泡；泡泡随输入更新；先跑通。

这些选择替代前文尚未决定的布局、触发和更新建议；保留早期评估供追溯。实时请求合并时长、候选数量和首条技术测试用例是 Codex 的实施建议，不写成用户原话。

首版书面设计：[Vicinae 意图泡泡规格](../../docs/superpowers/specs/2026-09-27-vicinae-intent-bubbles-design.md)。本机只读探测确认 macOS arm64、Vicinae v0.29.0（c3415a3ed）及 226 项命令目录；每项仅有 id/name。观察到文件搜索、剪贴板、浏览器标签页入口，未验证其实际执行。未调用 Jev、行情或社交接口，未修改产品代码。

Vicinae 原生修改的项目 owner 仍 unknown；万界门侧契约与交接边界已写入规格。双方具名回应仍未收到，不推定共识。

## 实施更新（2026-09-27）

用户明确要求停止 brainstorming，自主开发测试，并以 `http://localhost:5174/demo` 为视觉参考。已在独立 `codex/vicinae-bubbles` 工作树复用指定前端快照，新增万界门侧 Vicinae 目录/执行桥接、实时候选、双击任务、原生磨砂面板与 Vicinae 脚本入口。详见 [验收记录](../../docs/acceptance-vicinae-bubbles.md)。

本项目部分已实施并做离线与真实调用验证：桌面命令交接、股票组合、公开资料提纲和社交草稿。当前是从 Vicinae 命令进入原生面板；原生主搜索框替换尚未实现。社交没有自动发帖。外部 fork owner 仍 unknown，交接事项见验收记录；作者署名与双方共识状态不变。

2026-09-27 用户补充：入口采用全局快捷键搜索浮层，随后明确去掉框外底板、只保留搜索框；已在 `integrations/vicinae/IntentPanel.swift` 和 `static/launcher.css` 实现透明承载、输入展开泡泡。原生视觉与 Esc 日志已检查；全局物理快捷键仍未实测，详见验收记录。作者归属保持 unknown。
