# WanjieGate 决策管线全景

两个时钟解耦:**渲染循环 60fps**(本地,永远流畅)与**决策循环 ~3Hz**(KEV 一次前向传播,实测 57–191ms)。KEV 只产出"目标态",屏幕上所有运动由本地弹簧完成。

## 1. 输入路径

```
textarea input 事件
  → latestText = value
  → #app.classList.toggle("idle", 空?)
  → 空: clearScene() 全量复位,不再问模型
  → 非空: 本地派生卡即时刷新(summary/note/timeline/alert 文本类)
  → debounce 320ms → decide()
```

`decide()`: `seq++` 帧序号 → `inflight.abort()` 取消上一帧 → mock 或真 KEV → 回来先比 `seq`,旧帧直接丢弃。

## 2. 决策源(两条,可互换)

- **真实**: `POST {baseUrl}/v1/systemone`,body = `{state, model, questions}`。state 含 `role/note/user_text_so_far/currently_visible`。
- **Mock**: `?mock=1` → `mockDecide()` 用关键词正则伪造同构 answers,无 GPU 时调手感用。

## 3. 问题集(每帧一次前向传播,目前 ~25 题)

| 问题 | 类型 | 作用 |
|---|---|---|
| `intent` | choice(7) | 意图:analyze-data / write-document / monitor-status / plan-work / report-issue / check-social / explore |
| `layout` | choice(4) | empty / focus / split / dashboard → 容量上限 |
| `density` | score(0–4) | → densityCap = [0,2,4,7,10] |
| `emphasis` | choice | 强调卡 id → 强制进主列 + accent 描边 |
| `vis_<id>` | noul ×12 | 每个组件"该显示吗"的独立概率 |
| `bind_<id>` | choice ×4 | chart/table/metric/hero 绑哪份数据集 |
| `att_<ctx>` | noul ×7 | 附件:photos/news/logs/tasks/datasets/moments/services |

## 4. 判定标准(applyAnswers 里的全部阈值)

| 常量 | 值 | 含义 |
|---|---|---|
| `COMMIT_MARGIN_IN` | 0.30 | 意图头两名概率差 ≥0.30 → **已知意图**(committed) |
| `COMMIT_MARGIN_OUT` | 0.15 | 滞后带:差距跌回 0.15 才退回未定 |
| `GHOST_LO` | 0.15 | 显隐概率的入场门槛(幽灵态) |
| `SOLID` | 0.55 | 已定时实体化的最低概率;也是幽灵/实体分界线 |
| `MOUNT_P` | 0.03 | 挂载/卸载阈值 |
| attach argmax | >0.3 | 附件题头名 >0.3 才显示;已定时退回场景预设 `scene.attach` |

**承诺语义**:未定 → `target = p`(概率即透明度,幽灵层);已定 → `p>=SOLID` 才 `target=1`,其余退场。`pin` 组件(nav-rail/intent-chip/alert-banner)绕过布局容量裁剪。nav-rail 另有壳保底 `p = max(model, 0.6)`。

## 5. 布局路径(pack,每次 dirty 重算)

```
top 条带(alert-banner)    全宽 × 54px
bottom 条带(action-bar)   全宽 × 54px
nav 列(nav-rail)         200px,右缘发丝线
main 列(主内容)          剩余宽度,组内 12px 间隔
side 列(信息卡)          292px
主列为空 → side 内容并入主列;Wi<980 → 单列+导航变横条
栏内按 minH 权重铺满高度
```

## 6. 渲染路径(tick,每帧)

- `c.delay > 0` → 只扣 delay(场景错峰调度),不积分
- 否则弹簧 `m += (target-m)·(1-e^{-dt/τ})`,进场 τ=0.16s / 退场 τ=0.5s(不对称:进快出慢)
- `m<0.03` 且 target=0 → 卸载 DOM
- 位置宽高走 CSS transition(.48s);transform/clip-path/opacity 每帧直写
- 进场方式按组件 `enter`:wipe=横向扫入 / zoom=缩放 / spring=上浮弹簧 / ghost=缓升
- 模糊只属于运动:`|target-m|>0.015` 才 blur,静止必锐利
- 幽灵 = 虚线轮廓;实体 = 发丝描边(强调区 accent 色);`--co=m^1.5` 让字比线慢半拍出现

## 7. 输入框自身也是状态

- `data-cmode` = 意图头名(即时,不等承诺):caret/mode/pulse 变色;write-document 长高+衬线字体;plan-work 微增
- `placeholder` 随场景换文案(`manifest.prompts`)
- `#mode` 标签 = 已承诺意图
- `#attach` 附件区 = `att_*` argmax 或场景预设
- `#hint` 逐层披露:未定露 `hints[0]`(半透明),已定露 `hints[1]`

## 8. 页面生命周期

- 已承诺意图变化 = 换页(`sceneId` 跟踪)
- 旧场景卡:target→0,错峰 delay `i*30ms` 退场
- 新场景卡:delay `140ms + i*45ms` 错峰进场
- 清空 → `clearScene()`:committed/sceneId/attach/hint/mode/cmode/placeholder/卡片 p·target 全复位

## 9. 其他路径

- **重绑**: `.a-chip` 点击 → `__rebind(key)` → 所有可绑组件 `setBinding` → 重渲染(不换数据语义)
- **调试**: `` ` `` 键开 `#debug` 面板(每卡 p→m 实时条);`dataset.p/target` 供自测断言
- **自测**: `tools/selftest.py`(Playwright)7 个阶段断言 + `.ai/shots/` 截图
