# Batch Standard v0.1

状态：有界单机 DAG runner 已实现；本轮未运行真实 batch，仅做契约与语法检查。

## 入口

```sh
bin/wanjie module new workflow project.inspect
# 修改 modules/workflows/project.inspect/batch.json 的 intent 和 jobs
bin/wanjie batch modules/workflows/project.inspect/batch.json
bin/wanjie batch modules/workflows/project.inspect/batch.json --run
```

默认命令是**离线计划**，不访问服务、不提交任务、不消费模型。`--run` 明确提交到默认 `http://127.0.0.1:5174`；可用 `--base http://127.0.0.1:PORT` 指定同机 Runtime。只接受精确 loopback URL，不跟随重定向，不使用系统 HTTP 代理。

workflow 安装不启动任务。batch 文件可以独立使用，不依赖 workflow 包安装。

## 契约

机器契约：[`batch.schema.json`](../../protocol/extensions/v0.1/batch.schema.json)。可直接修改 [本地检索示例](../../examples/batches/local-search.json)，然后运行 `bin/wanjie batch examples/batches/local-search.json` 查看计划。

```json
{
  "version": "0.1",
  "id": "project-references-001",
  "intent": "00000000000000000000000000000000",
  "maxParallel": 2,
  "maxSubmissions": 10,
  "timeoutSeconds": 300,
  "jobs": [
    {"id": "notes", "capability": "memory.retrieve", "input": {"query": "架构决定"}, "dependsOn": []},
    {"id": "sources", "capability": "repo.search", "input": {"query": "IntentFrame"}, "dependsOn": ["notes"]}
  ]
}
```

全零 intent 是占位，执行前换成真实 Intent ID。`repo.search` 需要现有 filesystem.read 调用授权。

- 每批 1–1000 个 job；ID 唯一，依赖必须存在且无环，不允许重复依赖。
- `maxParallel` 为 1–3，且受该 Intent 中其他正在运行的任务占位影响。
- `maxSubmissions` 为整批总提交预算，必须覆盖 jobs；不会因为失败增加自动重试。
- `timeoutSeconds` 限制本次 CLI 等待，1–86400 秒。下一次调用获得新的等待窗口，但沿用原日志与提交次数。
- 当前 `dependsOn` 只表达执行先后；不支持字符串模板、结果变量注入、动态展开或生成新 job。

离线 plan 校验 batch 结构和拓扑。`--run` 首先读取 Runtime 中实际 capability schema，逐个校验 input。实际排队仍由 Kernel 检查现有 grant、网络范围、localOnly 和队列容量；runner 不生成权限、不修改授权、不替用户确认高风险操作。

## 稳定身份与恢复

日志位于 `.data/batches/<batch-id>/journal.json`，目录权限 700，日志 600，不提交 Git。每批使用文件锁，避免两个 runner 同时提交同一批次。

提交前依次完成：

1. 生成固定 command ID 和 idempotency key，使用当前客户端协议 `source=renderer`。
2. 将 `submitting` 状态与完整命令写入日志，flush/fsync 并原子替换。
3. 只执行一次 POST。
4. 保存 task ID 和状态；随后 GET 观察任务。

响应丢失、JSON 无法解析、5xx 或提交期间中断，都不能推断“未执行”。runner 会停止追加工作；下一次用相同命令运行时，先 GET `/commands/<id>` 对账，再读取对应 Task。

**GET 查不到 receipt 时，仍保持 unknown，不重放 POST。**这也涵盖“写入日志后、发送前进程退出”的情况：安全优先，需人工核对日志和服务记录。不要删除日志或换 batch ID 来碰运气重试。

恢复要求 batch 内容摘要与 endpoint 完全相同。更改 job/input/intent/预算后属于另一批工作，应先处理原批次的未知或正在运行任务，再创建新的 batch ID。

## 失败与退出

| exit | outcome | 含义 |
|---|---|---|
| 0 | success | 所有 job 都有实际 success 状态 |
| 2 | failure / 命令错误 | 完成但有失败、依赖跳过，或输入配置错误 |
| 3 | pending | 等待窗口结束、任务仍在进行，或尚未提交全部 job |
| 4 | unknown | 有无法确定结果的提交／运行，必须核对 |

失败、partial、cancelled、interrupted 不算成功，其下游标记 skipped。`outcome_unknown` 停止整批继续调度。独立 job 可以在其他 job 明确失败后继续；存在未知结果时不再追加。

Ctrl-C 只停止 runner 等待，不取消已被 Runtime 接受的任务；已有任务仍按 Kernel 生命周期运行。若要取消，用现有 Task 取消入口。恢复命令也不会重放成功、失败或跳过的 job。

当前范围是单机、有界并发、可核对日志。它不承诺分布式 exactly-once、不自动退款、不恢复外部服务结果，也不把 HTTP 接受当作任务成功。
