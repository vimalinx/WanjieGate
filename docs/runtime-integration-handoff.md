# Runtime 跨项目接入交接

日期：2026-09-27。发出项目：WanjieGate。交接给 VimalinxOS 根协调者确认各注册项目 owner；此文件记录交接内容，不表示已经向其他 Agent 或外部渠道发送消息。

## 已提供的接口

- [Protocol v0.1](../protocol/v0.1/README.md)：四种消息、实体、Manifest、权限与生命周期。
- `Kernel.register(spec, manifest, handler)`：可信宿主提供者接入；支持同能力多个提供者。
- `./bin/intent-runtime`：本机命令、状态、消息游标、追踪、校验入口。
- `/api/runtime/commands` 与只读投影/消息接口：本机单用户语义，尚无远程主体认证。
- Runtime 已实现 Intent、Context、Artifact、关系、Task、Grant、通知记录和临时 worker。

## 需由对应 owner 实现或决定

| 范围 | 需要对接的事实与能力 | 当前直接观察 | owner / 待决定 |
|---|---|---|---|
| 桌面 / Hyprland | window.focus.changed、workspace.activate、窗口 View | unknown，本轮未读取或修改该项目 | 根协调者确认注册项目 owner；显式桌面权限 |
| 外部 Agent / Skill 宿主 | Task 接收、Context 引用、取消、阶段 Result、worker 释放 | unknown；本项目 agent.run 是本地组合图 worker | 根协调者确认 owner；不能把会话恢复等同进程恢复 |
| 系统通知 / 日历 | 通知输入、只读日历事件、延后/关联投影 | unknown；本项目只有本地通知记录与策略 | 根协调者确认 owner 和授权范围 |
| Memory 服务 | Artifact/Relation 来源、范围、撤销与检索 | unknown；本项目有本地记忆 Artifact 和文字检索 | 根协调者确认 owner；共享权限需双端一致 |
| 语音 / 远程设备 | ASR 事件、设备身份、能力 Manifest、命令结果 | unknown | 先确定认证、投递、断线与 unknown outcome 协议，再启用远程监听 |
| 生成 / 图像 / 视频服务 | 已发布能力、准确模型目录、输入输出与预算 | 本项目已有文本生成 `lr exec` 适配；其余 unknown | LocalRouter / 对应能力 owner，按已有协议接入 |

## 外部验收要求

适配方需证明真实 Event 来源、主体鉴别、权限拒绝、取消边界、结果不明核对、重启不重放、引用权限撤销和端到端因果链。模拟提供者只证明本机协议行为。

当前服务继续只监听 loopback；不因存在 Manifest 就开放 LAN/公网，不从其他项目数据库读取身份或凭据。邮箱禁令独立且继续有效。
