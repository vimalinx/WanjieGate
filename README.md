# 万界门 · WanjieGate

以胶囊条为入口，围绕持久 Intent 组织内容、能力、工作集和视图的本地工作台。输入后展开内容；历史、工作集和空间设置按需打开。前端通过类型化 Command 与 Runtime 通信；语义模型输出 Signal，Policy 决定状态变化，Capability 执行动作。

[共同设计区](ideas/README.md) · [Intent Runtime Protocol v0.2](protocol/v0.2/README.md) · [本轮验收](docs/acceptance-runtime-v02.md)

## 启动

```sh
./bin/web-serve.sh                 # http://127.0.0.1:5173
./bin/kev-serve.sh                 # 可选：已有本机 KEV 启动入口
```

Web/API 使用 Python 3 标准库，前端为原生 ES Modules，无打包步骤。只监听 loopback。语义判断默认使用 OpenRouter `typesafe/jev-1.13`，后端从既有 `OPENROUTER_API_KEY` 环境读取凭据，不进入浏览器或源码。缺少凭据或上游失败会明确报错。显式设置 `WANJIE_SEMANTIC_PROVIDER=kev` 才使用原本机 KEV（`WANJIE_KEV_URL`，默认 `http://127.0.0.1:8208`），没有静默回退。

云端生成沿用 LocalRouter `lr exec`，默认 `llm7:minimax-m2.7`，可在启动前配置：

```sh
WANJIE_MODEL_PACK=llm7 WANJIE_MODEL=minimax-m2.7 ./bin/web-serve.sh
```

当前浏览器版本按用户已给出的付费授权，默认开启真实 JEV 自动协助。首次有效输入或恢复空间时，为语义判断、公开资料与行情建立最多 100 次、1 小时的 L0 网络授权；空白入口不调用模型。可在历史抽屉关闭自动协助或设置仅本地；生成与其他动作仍受独立授权边界约束。Kernel 新建 Intent 的本地默认值不变。密钥不进入源码或浏览器；调用前检查与私有回执继续由生成适配器和 LocalRouter 保留。

## 已实现的本机功能

- **Intent**：八维状态、创建/激活/暂停/归档/分支、刷新恢复；用户明确设置优先。
- **Artifact 与 Relation**：独立身份、编辑版本、来源、固定、跨 Intent 显式共享引用，以及七种关系。
- **Working Set**：HOT/WARM/COLD、字符预算、全文/原文片段/仅目录读取、选入/排除原因、固定与运行依赖保护。
- **统一执行**：分析、生成、行情、公开网页读取、记忆检索、仓库搜索/读取、文件修改、Git diff、测试、隔离 Python 执行。
- **组合与临时 worker**：有序依赖图、步骤产物绑定、阶段保存、失败保留、取消；`agent.run` 使用同一图执行协议。
- **语义与策略**：JEV 批量输出正交 IntentFrame、相关性/能力建议/独立通知紧急度；DAG 阶段记录、显式 frame.commit、流式事件去旧。
- **模块和权限**：统一 Manifest、提供者选择、启停、限时限次 Grant、撤销、网络与副作用独立检查。
- **消息与追踪**：四种消息、原子状态/日志提交、游标读取、因果链、命令去重、响应丢失恢复、重启不重放。
- **界面**：内容、工作集、关系、过程、授权，Artifact 编辑/固定/视图切换、提醒管理与 Markdown 导出。

Python 执行需要本机 `bubblewrap` 和 `prlimit`，在无网络、无用户目录挂载的隔离环境中运行；不满足条件时明确失败。它不提供宿主通用 shell。

## 结构

| 路径 | 责任 |
|---|---|
| `protocol/v0.2/` | Message/实体 Schema、命令/事件 payload、可验证生命周期样例 |
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

已增加百炼 ASR 文件流桥接和 Hyprland 当前窗口的只读观察工具；尚无常驻桌面观察与胶囊麦克风入口。系统通知源、日历、远程设备及其他 VimalinxOS 项目的接入需要对应 owner 完成适配和验证，详见 [交接清单](docs/runtime-integration-handoff.md)。模型生成和真实行情的当前可用性不由离线测试证明。取消不能撤回已发送的上游请求；未知结果不自动重试。

## 组件、对象图与批量扩展

[工程标准入口](docs/standards/README.md)统一维护组件协议、对象关系、语义动效和批量执行规范。前台使用独立组件组合，正文、引用、图片和行情可以共存；模型读取有界上下文，只产生建议，执行和权限留在 Runtime。

```sh
bin/wanjie module list
bin/wanjie module new component notes.counter
bin/wanjie module check
bin/wanjie module install notes.counter
```

批量任务默认只显示计划；加 `--run` 才提交。具体上限与未知结果恢复规则见 [批量标准](docs/standards/BATCH_v0.1.md)。最新实现与验收边界见 [本轮记录](docs/acceptance-adaptive-standards.md)。
