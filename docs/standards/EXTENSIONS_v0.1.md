# Extension Standard v0.1

状态：本地扩展协议与工具已实现；本轮只进行静态检查，没有运行新扩展、浏览器交互或真实服务调用。

## 目标与边界

扩展围绕当前内容和对象独立加入工作集，不声明互斥的“写作／股票／搜索模式”。用户固定与拖动位置优先于语义分数。模块只提供有稳定身份的内容投影或能力，动效交给宿主的语义动效体系。

本标准包括三类可信本地包：

| kind | 目录 | entry | 用途 |
|---|---|---|---|
| component | `modules/components/<id>/` | JavaScript ES module | 已有对象和内容的投影 |
| capability | `modules/capabilities/<id>/` | Python module | 由 Kernel 授权并执行一次操作 |
| workflow | `modules/workflows/<id>/` | batch JSON | 有依赖的能力调用清单 |

它们是应用进程内的可信代码，不是安全沙箱。安装操作表示信任精确版本的代码；Manifest 是供运行时调度的契约，不能阻止恶意 Python 直接访问系统，也不能阻止恶意 JavaScript 访问同源数据。来自模型或网页的文本绝不能自动安装为扩展。

## 命令

在项目目录运行：

```sh
bin/wanjie module new component notes.counter
bin/wanjie module check
bin/wanjie module list
bin/wanjie module install notes.counter
bin/wanjie module catalog
bin/wanjie module uninstall notes.counter
```

`new` 只生成文件，不安装也不执行。`check` 校验全部包结构和契约，不导入代码。`install` 将包的 SHA-256 写入 `modules/installed.json`，并重新生成前端 catalog。组件需刷新页面加载；Python capability 在下一次正常启动后加载，本命令不重启服务。

修改已安装包后要重新检查、安装。摘要与安装锁不匹配的包不再被新一轮加载选中；已加载进程不会热卸载代码。移除包同样需要刷新页面或正常重启对应进程。旧摘要的静态包保留，避免破坏已打开页面的模块依赖；catalog 不再引用它们。

`list` 区分 `builtin`、`installed`、`disabled/changed`，显示精确摘要。内置包名单由宿主固定，不接受任意包自行声明 `builtin=true`。

## Manifest

机器契约：[`module.schema.json`](../../protocol/extensions/v0.1/module.schema.json)。

必需字段包括 `id/version/apiVersion/title/description/owner/kind/entry/builtin`，`accepts/provides/permissions`，`sideEffect/network/cost/reversible`，以及 `inputSchema/outputSchema/stateSchema`。

- `id`：稳定命名空间，例如 `notes.counter`；目录名必须相同，跨 kind 唯一。
- `version`：三段数字版本；v0.1 不自动进行状态迁移。破坏性状态变更升版本并在包内提供迁移说明。
- `apiVersion`：严格为 `0.1`。
- `entry/style`：包内规范相对路径，禁止绝对路径、`..`、符号链接和外部 URL；style 只能为组件 CSS。
- 单包源文件总量最多 10 MB；SHA-256 覆盖路径和内容，只排除 Python 缓存。
- 组件额外要求 `placement/activation/ports`。`activation.cue` 描述当前对象何时有用，可供 JEV 对有限候选打分；`threshold/minimumCharacters` 是确定性准入条件，不授予执行权限。
- `slotKey` 只对应稳定投影身份，不是页面模式。
- `ports` 声明输入或输出端口及接受的 text/citation/image/artifact/component 类型；具体交互由宿主支持的拖拽协议实现。
- component 必须为 `L0`、`network=false`、`cost=none`，且无 permissions/provides。产生副作用的操作另建 capability。
- capability 每包只提供一个能力；输入输出必须是 object，输出 schema 必须要求 `artifacts` 数组。
- workflow 入口是 batch 契约；只在明确运行 batch 时执行。

Schema 使用项目运行时支持的子集：`type/properties/required/additionalProperties/items/enum/const/minLength/maxLength/pattern/minimum/maximum/minItems/maxItems`，以及描述字段 `title/description/$schema/$id`。不支持 `$ref/oneOf/anyOf/format/default` 等关键字；检查器会拒绝这些字段，避免以为已经验证。空 schema `{}` 表示任意 JSON 数据。

## Component 生命周期

脚手架：

```js
export function mount(root, context) {
  const count = document.createElement('p');
  root.append(count);
  return {
    update(input) { count.textContent = input.text.length + ' 字符'; },
    dispose() { count.remove(); }
  };
}
```

宿主负责同一 Intent 内的实例身份；更新数据调用 `update`，避免重复 mount。`input` 是当前输入的快照，含 `intent/text/selection/artifacts`；artifacts 为可用对象的元数据，而非全部世界数据。异步工作必须自行取消旧请求，dispose 清理监听、定时器和资源。禁止整体替换宿主编辑器、重置其 selection 或让用户等待动画。

`context.getState()/setState(value)` 保存小型组件交互状态，`context.insert(text)` 只在宿主认可的用户手势中执行插入。输入与状态按 Manifest 中声明的 schema 子集检查。当前组件状态按 Intent、模块和版本在浏览器本地存储，单份限制 8 KB；它不是 Artifact 数据库，也不提供跨浏览器同步。正文、引用和执行结果应进入对象体系，不能只放组件状态里。

Catalog 的 entry/style 均指向内容摘要固定的 `/extensions/packages/<id>/<sha>/...`。宿主根据 catalog 加载，不扫描任意目录。CSS 需以自己的组件标识限定作用域，避免影响编辑器及其他模块。组件不是自治 Agent；JEV 只建议它是否相关。

拖拽物料使用 `application/vnd.wanjie.material+json`，契约见 [`material.schema.json`](../../protocol/extensions/v0.1/material.schema.json)。保留 `intent`、稳定 ID、对象引用和来源；不得把显示文本当作权限。跨 Intent 内容必须经对象层授权流程，而不是任意读取拖拽载荷指向的对象。

## Capability 生命周期

```sh
bin/wanjie module new capability notes.character-count
# 编辑 provider.py 和 manifest.json
bin/wanjie module check
bin/wanjie module install notes.character-count
```

入口函数（包内辅助模块可通过相对导入 `from .helpers import ...` 使用）：

```python
def execute(task, progress, cancelled):
    # task 包括 input/context/intent；context 已由运行时选择。
    # 长操作必须定期检查 cancelled()。
    return {'artifacts': []}
```

输入先按 schema 校验，再通过现有 permission broker、Intent scope、localOnly 和队列限制。进度使用 `progress({'text': '阶段完成'})`；结果 artifacts 包含 `kind/title/content/source`，由 Kernel 建立身份与来源关系。不要自行写数据库，也不要把推测包装成工具已完成的事实。

加载器先检查安装摘要，再导入代码并检查入口函数。禁止覆盖现有模块／能力。单个模块导入失败记录于 `kernel.extension_errors` 与服务 stderr，其余模块继续加载。运行失败由正常 Task 错误路径处理。导入阶段应无网络和副作用，因为导入发生在 Task 授权之前。

L0–L3、网络、权限和计费声明必须如实填写。加载成功不代表当前 Intent 已授权调用；扩展安装不会创建 grant，不改变 localOnly，不生成云服务密钥。

## 批量与发布流程

1. 生成包，写契约、来源与权限。
2. `module check` 校验结构；另行按需执行代码与用户交互验收。
3. `module install <id>` 固定可信内容摘要，生成 catalog。
4. 正常刷新／启动后加载；保留旧版本与迁移记录。
5. 多次调用使用 [Batch v0.1](BATCH_v0.1.md)，由同一 Kernel 控制能力执行。

本地静态校验不证明组件视觉效果、真实外部服务、并发稳定性或第三方代码安全。v0.1 尚未实现包签名、远程市场、跨机器安装、进程沙箱及分布式执行。
