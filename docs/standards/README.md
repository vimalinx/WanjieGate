# 万界门工程标准

版本：2026-09-27。内部消息继续使用 Intent Runtime Protocol v0.2；扩展、组合、对象图和动效分别使用独立的 v0.1 契约。

## 路径

```text
输入 / 行为 → Event → 有界 Context → JEV Typed Signal
                                    ↓
                  Policy + 人工约束 + Permission
                                    ↓
          Object Graph Query → Context Role → Working Set
                                    ↓
                    Component Projection + Motion
                                    ↓
              显式操作 → Command → Task → Result
```

## 标准索引

| 标准 | 管什么 |
|---|---|
| [组合](COMPOSITION_v0.1.md) | 无排他场景、独立组件、视图作为输入、滞回、人工优先 |
| [对象图](OBJECT_GRAPH_v0.1.md) | 稳定身份、多意图引用、上下文角色、显式与计算集合、安全归属 |
| [动效](MOTION_SPEC_v0.1.md) | 语义原语、可中断变化、退场目的地、减少动态效果 |
| [扩展](EXTENSIONS_v0.1.md) | 包目录、版本、Schema、组件生命周期、可信提供者、安装摘要 |
| [批量](BATCH_v0.1.md) | 单机 DAG、并发/提交预算、持久日志、无盲目重放 |
| [主协议](../../protocol/v0.2/README.md) | 四类消息、IntentFrame、执行主干、权限与因果链 |

## 数据与边界

正文、对象、关系、命令与执行记录先保存在本机 SQLite。组件个人展示偏好可保存在浏览器；它不是跨设备数据库。本版本根据 vimalinx 明确允许付费调试与运行的授权，默认开启真实 JEV 自动协助；实际输入或恢复空间时，申请当前 Intent 的有限 L0 网络授权（100 次、1 小时）。空白入口不调用模型；用户可在历史抽屉暂停，暂停选择在当前浏览器会话内保留。

模型读取经过权限、上下文预算和字段筛选的内容，图片像素不通过当前视图摘要外发。公开检索摘要带来源，摘要不等于已核实的事实；用户决定是否引入正文。

当前扩展是本机可信代码，不是恶意插件沙箱。批量运行是单机有界工具，不是分布式调度平台。模型判断不创建执行权限；网络和有副作用能力继续走 Kernel。

## 开发入口

```sh
bin/wanjie module list
bin/wanjie module check
bin/wanjie module new component notes.counter
# 编辑 manifest / index.js，审查本机可信代码后：
bin/wanjie module install notes.counter
# 刷新页面；Python capability 的安装需要有计划地重启服务。
bin/wanjie batch examples/batches/local-search.json
# 补入自己的 Intent 和合法输入，再显式 --run。
```

验收范围和未完成事项见 [本轮实现记录](../acceptance-adaptive-standards.md)。用户自行交互验收；本轮未运行付费批量任务。
