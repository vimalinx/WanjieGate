# v0.2 · 真实语义与流式输入验收

日期：2026-09-27。范围：WanjieGate 本机单用户运行时；不代表其他项目或完整通用桌面已完成。

## 真实服务路径

- 后端 OpenRouter Decisions：`typesafe/jev-1.13`；回执实际模型 `typesafe/jev-1.13-20260917`。
- 百炼：复用用户配置的 `bailian` 与 `bl-live-asr`。语音合成 `cosyvoice-v3-flash` / `longanyang`，实时识别 `fun-asr-realtime`。
- Hyprland：`hyprctl -j activewindow`，只保留 class/pid/monitor，不采集窗口标题或网页正文。
- 浏览器：`http://127.0.0.1:5174`，独立 `.ai/test-data/intent-runtime-browser`。

[官方 Decisions 接口](https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-request)与[模型页](https://openrouter.ai/typesafe/jev-1.13)用于核对请求格式；成功结论来自本地捕获的真实回执。

LocalRouter 当前未发现对应的 OpenRouter Decisions Pack，故直接使用后端现有 `OPENROUTER_API_KEY` 环境。没有复制密钥、修改外部项目、创建新账号或读取邮箱。真实调用不自动重试。每次保留请求、原始响应、耗时与用量，位于 gitignored 的私有目录。

## 流式链路

合成语音原文：“请查一下万界门的接口文档。顺便晚上十点提醒我给电脑充电。”

这是真实 TTS → 真实实时 ASR → 真实 JEV；音源是合成测试素材，**不是用户真人口述或麦克风验收**。

结果：1 个 Hyprland 事件、9 个 ASR partial、1 个 ASR final，3 次 JEV 请求全部成功。

| 输入 | 模型耗时 | 结果 |
|---|---:|---|
| 当前窗口类别 | 2181ms | CONTINUE / OBSERVE / EXPLORE |
| 中间转写 | 876ms | CONTINUE / RETRIEVE / EXPLORE |
| 完整转写 | 1378ms | 两个 Frame：CONTINUE / RETRIEVE / EXPLORE 与 BRANCH / ORGANIZE / WAIT |

最终文档引用匹配测试空间中的真实 note ID。运行结束仍只有初始化的一个 Intent；没有自动创建提醒空间，也没有设置计时器、发送消息或执行外部动作。

3 次 JEV 返回费用合计 `$0.000380772`；百炼 CLI 此次没有输出完整账单，TTS/ASR 费用未核对。Fast Loop 50–500ms 目标尚未达成。

私有证据：

- `.ai/live-smoke/control-v02-speech.wav`、`control-v02-tts.json`（后者含临时音频 URL，不提交）。
- `.ai/live-smoke/control-v02/0a7e8234c8cd442491bf681ee872c3bd/report.json`、`events.jsonl`、`receipts/semantic/`。
- 同目录 `replay-current.json`：最终补丁后，以捕获响应离线重放；三个输入均通过当前十阶段契约，中间转写 commitment=HYPOTHESIS，最终两个片段 READY。没有重复调用上游；该重放不算新增真实服务验收。

## 浏览器

在测试 Intent `49adaa7348b54211975c87ea020117f4` 的胶囊输入同样的复合请求：真实 JEV 1416ms，HTTP 200，费用 `$0.00018459`，返回 CONTINUE/RETRIEVE/EXPLORE 与 BRANCH/ORGANIZE/WAIT。页面显示分支建议，过程页显示两个独立 Frame，浏览器错误日志为空。

回执 ID `6ae15619ad194632a71a27870f03adda`，任务 `8c2ce323d2744c6d8095741f89157177`。数据位于上述测试数据目录。

视觉检查：首屏为单胶囊 + 大写 WANJIE；12 片百叶窗使用交错位移；背景轨道、点、十字与胶囊浮动。截图检查桌面布局；窄屏实际 CSS 宽 433px，scrollWidth 433px，无横向溢出。关闭“动态效果”后实测 orbit animation=none，shutter transition=0s，开关 aria-pressed=false；随后恢复。系统 reduced-motion 的 CSS/媒体查询已实现，本轮未切换操作系统偏好验证。

## 离线回归

`python3 tools/selftest.py`：**77 项 Python 测试 + 3 组 Node 测试全部通过**。测试不使用真实付费提供者。

新覆盖：候选排序后截断、复合输入、十阶段输入输出契约、模型不能授权执行、partial 降为 HYPOTHESIS、乱序事件拒绝、较新 partial 使在途判断失效、CLOSED 保留与恢复、显式 frame.commit、重复提交拒绝、状态变化与新观察使候选失效、相关性与通知紧迫性独立，以及验证结果不冒充目标完成。

OpenRouter 测试覆盖类型/概率分布校验、模型身份、读取深度、回执权限与凭据不落盘、HTTP 拒绝、网络未知结果、缺少密钥、无自动重试。

## 保留失败记录

早期 v0.1 语义实验中，写作请求被判 exploring（0.54），另有数据 fixture 缺少 numeric 字段、在本地被拒。修正活动提问措辞与 fixture 后五例通过；历史报告保留在 `.ai/live-smoke/jev-runtime/41656de6f80d4537b5570a1494d12b6b/report.json`。这是修正后的 v0.1 阶段结果，不当成 v0.2 新协议验收。

新 frame.commit 测试曾因 CSV 只有一行数据被真实本地校验拒绝；fixture 补足两行后通过，没有放松能力输入限制。

## 可复现入口

```sh
# 离线测试，不产生付费请求
python3 tools/selftest.py

# 只读 Hyprland 当前窗口 -> JSONL
python3 tools/event_bridge.py --hyprland

# 用户配置的百炼 CLI 实时转写现有音频 -> JSONL（真实调用）
python3 tools/event_bridge.py --audio /absolute/path/speech.wav

# 隔离数据库，真实 ASR + Hyprland + JEV，至多 8 次 JEV，无重试
python3 tools/live_control.py --run --audio /absolute/path/speech.wav

# 有界独立语义用例；不带 --case 会跑五例（真实付费）
python3 tools/live_semantic.py --run --case research
```

## 尚未完成

[协议边界](../protocol/v0.2/README.md)列出了自动扩展候选、多层解析、独立异步资源路由、长期反思、常驻桌面源、麦克风入口、通用目标验证等后续工作。当前 LEARN 只留存事实和因果，不自动写长期记忆。上述合成语音用例不证明噪声、口音、真人打断、长会话或持续多窗口切换的稳定性。
