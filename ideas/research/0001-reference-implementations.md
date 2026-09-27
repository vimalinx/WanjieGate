# RESEARCH-0001 · 参考实现与复用决策

- 整理与源码评估：Wilson
- 日期：2026-09-27
- 来源：vimalinx 在本会话提交的参考项目清单；关联 [IDEA-0001](../vimalinx/0001-intent-runtime.md)
- kanemaverick 的观点：未收到。本报告不代表双方共识。
- 方法：核对官方仓库、固定 commit 源文件、根许可证、json-render 官方发布记录与 npm 包内容；读取本项目协议、Context、Policy、Capability 与前端实现。只读取第三方源码，未安装或执行第三方程序，未调用付费模型。
- 范围：重点核对 Intern、json-render、JCR、Astra、OpenViking。原清单其余项目尚未逐个源码核验，不沿用占位引用作为证据。

## 结论与重要修正

当前 Python + 原生 JS + SQLite 内核适合继续演进。最先采用输入竞态保护、明确的上下文读取层级和声明式候选约束；无需为这些能力替换框架。

1. **Intern 的固定快照没有发现根 LICENSE。**公开可读不能作为复制授权；本轮只借鉴交互机制并自主实现。
2. **OpenViking 当前固定快照的根许可证是 AGPL-3.0。**本轮不复制其代码、不把它引入当前依赖；若将来整合，应先确定所选版本及分发/服务方式，并核对完整许可要求。[固定 LICENSE](https://github.com/volcengine/OpenViking/blob/a09a9d20a8e07d08973aee177802d00e08df29e6/LICENSE)
3. **json-render 文档与发布包有时间差。**[Jev 文档](https://json-render.dev/docs/jev)仍称 API 未发布；但 [v0.21.0 发布记录](https://github.com/vercel-labs/json-render/releases/tag/v0.21.0)已列出它们。本轮读取 [npm metadata](https://registry.npmjs.org/@json-render/core/latest) 得到 `0.21.0`，并只读检查其 tarball 中 `package/dist/index.js`，确认 `experimental_composeSpec` 导出存在。因此不能继续断言“只能源码构建”。API 仍为实验性；若采用，应固定精确版本并检查升级差异。

## 固定源码与决策

HEAD 使用 `git ls-remote ... HEAD` 获取；链接固定到此次读取的 commit，后续变化不自动适用本报告。

| 项目 | 此次 commit | 许可证据 | 当前决策 | 与本项目适配成本 |
|---|---|---|---|---|
| Intern | `c0bedee4b374b5f177b670016f5ff2b8e5bcf7eb` | [仓库快照](https://github.com/dabit3/intern/tree/c0bedee4b374b5f177b670016f5ff2b8e5bcf7eb)：根未发现 LICENSE | 只借鉴，自主实现 | 输入序列/候选身份逻辑低；Swift/macOS 搜索与窗口实现高且跨平台 |
| json-render | `c2600d73908ed505e6d726f5b6f969ba8f597ce7` | [Apache-2.0](https://github.com/vercel-labs/json-render/blob/c2600d73908ed505e6d726f5b6f969ba8f597ce7/LICENSE) | 可作为独立适配器复用，当前先借契约 | TS core 中等，需要构建与 renderer 桥；不用迁移全部前端 |
| JCR | `138b3832eabaf899dbb8366520a676682bbdf2e5` | [MIT](https://github.com/NiazMorshed2007/jcr/blob/138b3832eabaf899dbb8366520a676682bbdf2e5/LICENSE)；附带 Skills 有各自条款 | 可复用 resolver/MCP 边界，暂不引入整个 harness | 独立 Node 服务中等；少量能力时自主有界筛选更低 |
| Astra | `239f7c2b4ff2ca06f4c656b063052bf34604dc55` | [Apache-2.0](https://github.com/matrixorigin/Astra/blob/239f7c2b4ff2ca06f4c656b063052bf34604dc55/LICENSE) | 借鉴判断契约和解释记录；暂缓整套 runtime | Rust 服务与现有 Kernel 重叠，整体替换高 |
| OpenViking | `a09a9d20a8e07d08973aee177802d00e08df29e6` | [AGPL-3.0](https://github.com/volcengine/OpenViking/blob/a09a9d20a8e07d08973aee177802d00e08df29e6/LICENSE) | 只借鉴分层读取；直接集成暂缓 | Python 接口表面低，存储迁移、服务运维和许可选择高 |

未来实际复制 MIT/Apache 代码须保留相应版权与许可文件，Apache 修改还应标明改动并处理适用的 NOTICE。本轮没有 vendor 第三方源码，也没有新增第三方运行依赖；上述判断不等于全仓库所有资产均由同一许可证覆盖。

## 1. Intern：输入状态的连续性

[Sources/InternModel.swift](https://github.com/dabit3/intern/blob/c0bedee4b374b5f177b670016f5ff2b8e5bcf7eb/Sources/InternModel.swift) 中存在独立 sequence、queryGeneration、indexGeneration、executionGeneration，以及 manuallySelectedID。请求完成前核对序列和取消状态；排序后按身份恢复手选行；旧执行完成不能关闭新输入。取消与序列检查共同防止晚返回污染当前工作。

对应万界门应冻结 `intentId + inputRevision + text`，在取消旧任务后和新任务受理后都重新核对；若期间换空间，取消应发往原 Intent。清空输入也使旧建议失效。组件和手选对象继续使用 Artifact ID，不能靠数组下标。这里不复用 Swift 源码，也不接入它的浏览历史读取。

## 2. json-render：候选有边界，状态不属于模型

[experimental-compose.ts](https://github.com/vercel-labs/json-render/blob/c2600d73908ed505e6d726f5b6f969ba8f597ce7/packages/core/src/experimental-compose.ts) 的候选是应用拥有的原子 element；初始化检查组件、props、动作和参数，候选 ID 唯一。`resource` 限制互斥资源，`maxUses` 限制重复；已有 Spec 的增删移换受到目录约束。[core 导出](https://github.com/vercel-labs/json-render/blob/c2600d73908ed505e6d726f5b6f969ba8f597ce7/packages/core/src/index.ts)提供实验 compose/evaluator。

可映射为 `candidate={id,artifactId,artifactVersion,primitive,allowedPlacements,allowedActions,resource}`。Operator 只返回候选 ID 和有限排列选择；Policy 检查新鲜度与人工锁定；动作仍进入现有 Command/Grant。现阶段原生 JS 已能稳定投影，直接搬入 React UI 没有必要。真实采用 core 时要编译模块并写 native renderer adapter，不应宣称“装包即接入”。

## 3. JCR：能力发现有终点，发现不等于执行

[src/jcr/resolve.ts](https://github.com/NiazMorshed2007/jcr/blob/138b3832eabaf899dbb8366520a676682bbdf2e5/src/jcr/resolve.ts) 的 beamResolve 对树逐层选择，默认最多 16 轮；路径累计概率转换为几何平均分，保留 none、歧义和 depth 终态。它返回文档，不执行目标命令；根 package 未作为 npm 库发布。[固定 README](https://github.com/NiazMorshed2007/jcr/blob/138b3832eabaf899dbb8366520a676682bbdf2e5/README.md)

万界门目前能力数少，先提供纯发现 `capability.resolve` 更合适：输入目标与候选 scope，输出 `matched|ambiguous|no_match|unavailable`、候选、依据与截断原因；不生成 Grant、不自动启动 Task。以后目录扩大再用独立 MCP resolver，且只导入经许可核对的操作目录，不能把它附带 Skills 全部视为 MIT。

## 4. Astra：保留判断的类型和未知状态

[crates/astra-turn-types/src/judgment.rs](https://github.com/matrixorigin/Astra/blob/239f7c2b4ff2ca06f4c656b063052bf34604dc55/crates/astra-turn-types/src/judgment.rs) 区分原生概率与离散答案，检查每个问题的对应响应、分布范围和语义一致性；普通 LLM 的 unknown 不被伪造成概率。 [semantic_judgment_observation.rs](https://github.com/matrixorigin/Astra/blob/239f7c2b4ff2ca06f4c656b063052bf34604dc55/crates/astra-turn-types/src/semantic_judgment_observation.rs) 明确 decided、abstained、conflicting、invalid、not dispatched、unavailable 及关联记录。

现有 Signal score 不应混装规则结果、LLM 自报信心与 Jev 原生分数。后续可增加 `assessmentKind`、`outcome` 与 provider provenance；没有判断保持 unavailable，不能用零分当“不相关”。Context 的 item/excluded 记录应保留每次装配的依据及内容版本。暂不引入第二套持久 Work/调度系统。

## 5. OpenViking：读取精度与工作集热度分开

[jev_rerank.py](https://github.com/volcengine/OpenViking/blob/a09a9d20a8e07d08973aee177802d00e08df29e6/openviking/models/rerank/jev_rerank.py) 为每份候选文档生成独立 Noul，批量请求后按原顺序返回分数，检查答案类型和 0–1 范围；失败返回 None，让调用方选择后续处理。不能把该文件失败回退机制直接当作万界门已有能力。[项目结构介绍](https://github.com/volcengine/OpenViking/blob/a09a9d20a8e07d08973aee177802d00e08df29e6/README.md)描述统一 URI 和内容分层。

我们可以自主实现 `full / excerpt / metadata`：全文、明确标记的原文片段、已有元数据。它们与 HOT/WARM/COLD 正交。片段必须标明裁剪，不能称为模型摘要；保留 Artifact ID/version 和全文成本。既不重写原内容，也不为节约上下文删除历史。

## 本轮最优先的三个接口改动

### P1 · 输入与任务归属

- 客户端冻结输入快照，受理前后校验，切换或清空立即失效。
- 取消命令显式携带原 Intent，旧结果仅归档不覆盖当前候选。
- 保留稳定 Artifact/View 身份和人工状态。

### P2 · 显式 Context 读取层级

- `context.set` 增加 `detail=full|excerpt|metadata`，默认 full。
- `Context.items` 记录 `detail / originalCost / cost / artifact / version`，片段附截断标记；预算与排除原因可解释。
- detail 改变使已排队旧快照和相关旧语义失效，全文读取需求不得被片段悄悄满足。
- 主实现已反馈采用此接口，并以 1200 字原文前缀实现 excerpt；**本报告未运行其测试，不声明该改动已验证**。

### P3 · 声明式候选与有界解析

先把现有 View/Capability 列表变成受限候选：稳定 ID、资源归属、允许动作、人工锁定、候选版本。解析只输出候选与明确终态，Kernel 独立检查授权后执行。目录规模扩大时再考虑 JCR，复杂 UI 接入时再考虑固定版本 json-render core。

## 未核验与后续

- 未运行这五个第三方项目，未验证它们在本机的性能、安装包、云服务与模型效果。
- 未在本轮核验 Omarchy Island、Disco、Intent、A2UI、AG-UI、Tambo 等完整源码与许可证；它们保留为研究队列。
- 没有复制代码，没有新增公开服务、桌面权限、浏览器历史采集或外部通知权限。
- 本项目后续实施证据由 [ROADMAP](../ROADMAP.md) 和实际验收记录维护；本报告描述源码核验与设计建议，不能替代实现验收。
