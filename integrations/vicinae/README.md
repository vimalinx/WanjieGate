# 从 Vicinae 打开意图泡泡

macOS 原生透明浮层复用万界门 `/launcher` 前端。它作为一个 Vicinae 脚本命令运行，保留 Vicinae 原主搜索界面。

在项目根目录执行：

```sh
python3 integrations/vicinae/install.py
```

安装器构建应用，校验并安装唯一的 `wanjiegate-intent.sh`，再通知 Vicinae 重新扫描脚本目录。不会覆盖不属于本项目的同名脚本。需要已安装 Vicinae、Python 3、Xcode Command Line Tools 的 Swift 编译器。

服务端通过 `WANJIE_ENV_FILE` 读取已有配置。桌面启动可将 env 文件的绝对路径写在本地 `.data/jev-env-path`，不复制密钥。首次在窗口内启用 Jev，授予当前空间 1 小时、100 次的能力调用范围。代码执行和测试不会自动发布社交帖子。

在 Vicinae 搜索“万界门”，运行“万界门 · 意图泡泡”。也可执行：

```sh
python3 integrations/vicinae/launch.py
```

启动一次后，应用常驻；默认全局快捷键为 **Control + Option + Space**，Esc 隐藏。未设置开机自启。空闲时只显示搜索框，输入后展开磨砂玻璃面板，透明泡泡在搜索框周围显示。齿轮内可打开产物、添加资料和普通命令搜索。

服务监听 127.0.0.1:5175。运行数据、构建产物和本地配置位于 `.data/`，不提交 Git。启动脚本会在服务未运行时启动它。输入参数仅用于首次打开；窗口已经打开时复用当前窗口。

恢复原状只需删除本项目安装的 `~/.local/share/vicinae/scripts/wanjiegate-intent.sh` 并重新扫描脚本目录。无需卸载或重装 Vicinae。

详见 [验收记录](../../docs/acceptance-vicinae-bubbles.md)。
