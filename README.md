# 万界门 · WanjieGate

围绕持久 Intent 组织内容、能力、工作集和视图的本地工作台。前端通过类型化 Command 与 Runtime 通信；语义模型输出 Signal，Policy 决定状态变化，Capability 执行动作。

[共同设计区](ideas/README.md) · [Intent Runtime Protocol v0.1](protocol/v0.1/README.md) · [本轮验收](docs/acceptance-runtime-v01.md)

## 泡泡 Demo（黑客松）

新增 `/demo`：中央胶囊、真实 Jev 候选、浮动泡泡、拖拽融合、资料写作和行情研究。`/` 保留原工作台。

```sh
WANJIE_DEMO=1 \
WANJIE_ENV_FILE="/你的本地路径/JEV 黑客松/.env" \
WANJIE_GENERATION_MODEL=deepseek/deepseek-chat-v3.1 \
NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost \
python3 -m backend.server --port 5174 --data-dir .data/bubble-demo
```

打开 <http://localhost:5174/demo>，在“连接设置”启用当前空间的有限授权。配置文件包含 `OPENROUTER_API_KEY`，仅由服务端读取，不要复制到前端或提交 Git。未设置 `WANJIE_DEMO=1` 时不会装载 Demo 提供者。

Jev 使用 Decisions API 与 `typesafe/jev-1.13`；文稿默认使用已实测的 `deepseek/deepseek-chat-v3.1`。最初候选 `openai/gpt-4.1-mini` 在本机请求被地区限制拒绝，故替换。两者可能产生 API 费用，调用失败不会自动重试。

[演示步骤、验收范围与整合事项](docs/acceptance-bubble-demo.md)。在意图中输入需求，添加自己的资料，把资料与动作拖到一起；检查来源后点击“运行”。融合本身不执行工作。首次最多 6 个候选，`＋` 每次最多增加 3 个，`↻` 保留固定及组合成员。

## 启动

```sh
./bin/web-serve.sh                 # http://127.0.0.1:5173
./bin/kev-serve.sh                 # 可选：已有本机 KEV 启动入口
```

Web/API 使用 Python 3 标准库，前端为原生 ES Modules，无打包步骤。只监听 loopback。KEV 默认地址为 `http://127.0.0.1:8208`，可通过 `WANJIE_KEV_URL` 设置既有服务；未连接时显示失败，不用规则冒充语义模型。

云端生成沿用 LocalRouter `lr exec`，默认 `llm7:minimax-m2.7`，可在启动前配置：

```sh
WANJIE_MODEL_PACK=llm7 WANJIE_MODEL=minimax-m2.7 ./bin/web-serve.sh
```

新 Intent 默认仅本地。需要网络或模型时关闭“仅本地”，然后在“授权”页指定能力、期限、调用次数和参数范围。自动内容也受同一授权与任务边界约束。密钥不进入源码或浏览器；调用前检查与私有回执继续由生成适配器和 LocalRouter 保留。

## 已实现的本机功能

- **Intent**：八维状态、创建/激活/暂停/归档/分支、刷新恢复；用户明确设置优先。
- **Artifact 与 Relation**：独立身份、编辑版本、来源、固定、跨 Intent 显式共享引用，以及七种关系。
- **Working Set**：HOT/WARM/COLD、字符预算、全文/原文片段/仅目录读取、选入/排除原因、固定与运行依赖保护。
- **统一执行**：分析、生成、行情、公开网页读取、记忆检索、仓库搜索/读取、文件修改、Git diff、测试、隔离 Python 执行。
- **组合与临时 worker**：有序依赖图、步骤产物绑定、阶段保存、失败保留、取消；`agent.run` 使用同一图执行协议。
- **语义与策略**：KEV 相位/连续性/相关性/能力选择/通知判断，版本与最新输入检查；可替换 Operator。
- **模块和权限**：统一 Manifest、提供者选择、启停、限时限次 Grant、撤销、网络与副作用独立检查。
- **消息与追踪**：四种消息、原子状态/日志提交、游标读取、因果链、命令去重、响应丢失恢复、重启不重放。
- **界面**：内容、工作集、关系、过程、授权，Artifact 编辑/固定/视图切换、提醒管理与 Markdown 导出。

Python 执行需要本机 `bubblewrap` 和 `prlimit`，在无网络、无用户目录挂载的隔离环境中运行；不满足条件时明确失败。它不提供宿主通用 shell。

## 结构

| 路径 | 责任 |
|---|---|
| `protocol/v0.1/` | Message/实体 Schema、命令/事件 payload、可验证生命周期样例 |
| `backend/runtime/kernel.py` | 命令受理、Intent、Registry、权限、Task 生命周期 |
| `backend/runtime/storage.py` | SQLite 状态投影与消息日志 |
| `backend/runtime/context.py` | 工作集与视图投影 |
| `backend/runtime/policies.py` | 确定性语义策略 |
| `backend/runtime/capabilities.py` | 本机能力、语义/生成/行情适配、组合图 |
| `backend/runtime/artifacts.py` | 产物内容校验 |
| `backend/runtime/web.py` | 受限公网 HTTPS 文档读取 |
| `static/runtime-app.js` | Bus Client 与界面交互 |
| `static/js/runtime-client.js` | 命令身份保留与未知响应核对 |
| `ideas/` | vimalinx / kanemaverick 的提案、评估、状态与分歧 |

## 数据与迁移

日常数据仍在 `.data/workspaces.sqlite3`。新增 `rt_*` 表，旧 workspace / jobs 表保留；首次迁移非空旧库前生成 `.data/backups/before-intent-runtime-*.sqlite3`。旧空间 ID、产物 ID、内容、编辑版本和任务记录迁入新运行时，未完成旧任务不会重跑。

私有调用记录在 `.data/receipts/`。验收数据使用 `.ai/test-data/`，与日常空间隔离。上述数据目录均不提交 Git。旧写接口已关闭，历史读取继续可用；旧 V2 源码与验收资料保留供追溯。

## 命令行与验证

```sh
./bin/intent-runtime state
./bin/intent-runtime command intent.create '{"title":"一个目标"}'
./bin/intent-runtime watch --once
./bin/intent-runtime validate protocol/v0.1/examples/lifecycle.json
python3 tools/selftest.py
```

自动化回归使用隔离数据库和受控提供者，不调用真实云端模型。浏览器和本机 sandbox 的实际验证记录见 [验收文档](docs/acceptance-runtime-v01.md)。

## 当前边界

本轮交付是 WanjieGate 的本机单用户 Runtime。十种 View Primitive 有统一登记与投影状态，但并非十套完整桌面应用。网页显示只读摘录；代码视图和受控执行不等于完整 IDE；临时 worker 不宣称接入了外部自治 Agent。

桌面窗口、系统通知源、日历、语音、远程设备及其他 VimalinxOS 项目的接入需要对应 owner 完成适配和验证，详见 [交接清单](docs/runtime-integration-handoff.md)。模型生成和真实行情的当前可用性不由离线测试证明。取消不能撤回已发送的上游请求；未知结果不自动重试。
