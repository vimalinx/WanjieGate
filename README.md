# 万界门 · WanjieGate

一个可以把意图组合成内容、工具与行动的本地工作台。

入口只有胶囊输入框与淡淡的 WanJie 背景。开始输入时，背景切成 12 条百叶窗，交替上下移出；即时组合和 KEV 判断同时开始，边打字边出现可编辑草稿、清单或数据视图，无需回车。连续输入优先判断最新文字；Enter 只换行，云端撰写由“生成内容”触发。历史默认藏在胶囊左侧的时钟按钮里，没有预置推荐卡片或演示入口。

数据分析、文稿、行动清单按输入组合；产物可编辑、固定、勾选、导出。首页 `/` 始终是空白入口，已保存空间通过历史或 `/w/<id>` 恢复。仅浏览或输入预览不会创建空白历史。

## 运行

```sh
./bin/web-serve.sh                  # http://127.0.0.1:5173
./bin/kev-serve.sh                  # 可选，本机 KEV 决策服务 :8208
```

Web/API 仅依赖 Python 3 标准库；前端为原生 ES Modules，无打包步骤、外部字体或 CDN。只监听 loopback。没有 KEV 时保留本地组合预览，状态会明确显示。

生成使用已有 LocalRouter CLI 的 `lr exec`，精确模型校验、预检、单次调用与回执保留均由该入口执行。默认通道见 `backend/providers.py`，可以在启动前设置：

```sh
WANJIE_MODEL_PACK=llm7 WANJIE_MODEL=minimax-m2.7 ./bin/web-serve.sh
```

切换配置只影响新调用，不重放已有请求。密钥不进入本项目源码或浏览器。选择“仅本地”可使用统计与笔记，禁止云端生成；云端发送会包括当前输入与关联工作区内容。

## 组成

- `static/registry.json`：能力、组件、类型、成本与表达规格。
- `backend/composition.py`：多标签意图、能力依赖、预算约束下的组件选择。
- `backend/providers.py`：KEV 决策与 LocalRouter 生成适配。
- `backend/scheduler.py`：并发队列、幂等、取消、逐阶段产物。
- `backend/store.py`：SQLite 状态与乐观版本检查。
- `backend/server.py`：同源 API、静态资源、导出与请求校验。
- `static/js/`：API、即时组合、组件渲染、图标；`static/app.js` 负责交互编排。

组合器优先覆盖不同能力，在组件预算内最大化效用，并给已有预览小幅稳定性奖励。实际组件选择写入产物；被压缩的明细可在图表中展开。真实产物不会因输入变化而消失。

数据在 `.data/workspaces.sqlite3`，调用证据在 `.data/receipts/`；均忽略入 Git。候选验证数据使用 `.ai/test-data/`，与日常数据分开。

## 验证

```sh
python3 tools/selftest.py
```

离线测试不访问真实模型。覆盖组合、数据校验、发送幂等、取消、失败保留、本地模式、编辑冲突、持久化、重启中断、HTTP Origin/Host 边界与导出。真实模型和页面验收见 [验收记录](docs/acceptance-v2.md)。

## 当前边界

当前执行器提供数据统计、文稿生成、任务拆解、问题回答和本地笔记。没有接入真实社交、监控或外部消息发送。“发送”是把目的交给工作台执行。生成按阶段返回，当前不是逐 token 流式显示。

取消会阻止后续步骤与当前结果写回，不能撤回已经发出的上游请求。模型失败不会自动重试；重启中的任务标为中断，不宣称已完成。

[架构与设计](docs/workbench-v2.md) · [决策管线](docs/decision-pipeline.md)
