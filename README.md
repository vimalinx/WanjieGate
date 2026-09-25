# WanjieGate · 万界门

决策模型驱动的自适应界面实验:你打字,[Kev](https://huggingface.co/jaredpalmer/kev-4b) 持续对每个 UI 决策输出校准概率,前端把概率直接渲染成"凝实程度"(透明度/模糊/位移)——元素像从雾里长出来,而不是闪现。

## 架构

```
输入框 ──debounce 320ms──> POST /v1/systemone ──> kev.serve (:8208)
                              state + 19 个类型化问题
                                    │
                  概率分布 ──> policy(容量裁剪/迟滞)──> m 标量弹簧 ──> 60fps 渲染
```

- `static/manifest.json` — 组件注册表 + 问题集模板 + 内置数据集。所有 UI 能力都是选择题。
- `static/app.js` — 决策循环与渲染循环解耦;`?mock=1` 用本地伪概率调手感,不依赖 GPU。
- `tools/sanity.py` — 对 kev 服务发中英文探针,打印每题分布与延迟。

## 运行

```bash
./bin/kev-serve.sh     # GPU 推理(nvidia-run 托管);默认 KEV_RUN=jaredpalmer/kev-0.8b
./bin/web-serve.sh     # 静态页 :5173
# 打开 http://127.0.0.1:5173/index.html        (真模型)
# 打开 http://127.0.0.1:5173/index.html?mock=1 (无 GPU 调动画)
```

按 `` ` `` 切换 debug 面板(实时概率条)。

## 当前部署事实

- HF CDN(xet)此刻对本机不可达;0.8B 基座经 ModelScope 落到 `artifacts/models/Qwen3.5-0.8B-Base/`,适配器快照在 `artifacts/models/kev-0.8b/`(head.pt 的 `meta.base` 已改指本地基座路径)。
- 5070 Ti 仅 11.6GB,Musicllm 的 `gcg_minicpm.py` 常驻 6.3GB → 现在用 kev-0.8b(~2GB,91ms/19问)。腾出显存后可 `KEV_RUN=jaredpalmer/kev-4b ./bin/kev-serve.sh` 上 4B(需 ~9GB)。
- 8008 被别的服务占着,kev 用 **8208**。

## 手感参数(app.js 顶部)

`DEBOUNCE_MS` 决策触发间隔 · `TAU_IN/TAU_OUT` 进/退场时间常数 · `GHOST_LO/SOLID` 幽灵/实体阈值 · manifest 里每组件 `span/minH` 决定网格占位。
