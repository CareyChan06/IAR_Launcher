# IAR Launcher 1.1

根据 `.eww` / `.ewp` 工程里的 toolchain，自动选择对应版本的 IAR 打开，避免多个 IAR 版本抢占 `.eww` 文件关联。

## 功能

- 双击 exe 打开主界面；双击工程或拖到 exe 图标上则静默启动，不显示界面。
- 首次启动没有工具链时会提示自动扫描；工具链页空状态也把“自动扫描”作为主按钮。
- 最近项目：搜索、置顶、路径失效提示、右键打开所在文件夹/复制路径/指定 IAR 版本/移除。
- 工具链：自动扫描本机 IAR、手动增删改、自定义工具链名称（AVR、8051 等）、导入/导出配置。
- 工程级版本锁定：某个工程可以指定具体 IAR 版本，覆盖 ewp 里的 toolchain。
- 外观：浅色/深色/跟随系统，六种主题色；原生 Windows 标题栏也会跟随主题，不再出现白条。
- 文件关联：在“关于”页一键注册到当前用户（不申请管理员权限）。
- 单实例：已有界面时再次双击只激活窗口。
- 静默启动只加载标准库，不初始化 Qt，保持双击 `.eww` 的启动速度。

## 使用方法

```
IAR_Launcher.exe                    # 打开界面
IAR_Launcher.exe path\demo.eww      # 静默启动
IAR_Launcher.exe --ui demo.eww      # 强制显示界面（不启动工程）
IAR_Launcher.exe --legacy demo.eww  # 运行旧版实现
IAR_Launcher.exe --config D:\path\config.json  # 指定配置（测试/便携）
```

## 配置文件

优先使用 exe 同目录的 `config.json`；目录不可写时改用 `%LOCALAPPDATA%\IAR_Launcher\config.json`。

首次运行会创建 v2 配置。旧的 v1 配置（`iar_paths`）会自动迁移，并在同目录保留 `config.json.v1.bak`。v2 结构：

```json
{
  "schema": 2,
  "toolchains": [
    {"id": "tc-...", "chain": "ARM", "version": "9.60.3",
     "path": "C:\\iar\\ewarm-9.60.3\\common\\bin\\IarIdePm.exe", "added_at": 0}
  ],
  "recent_projects": [
    {"path": "D:\\Work\\Demo\\Demo.eww", "name": "Demo", "chain": "ARM",
     "toolchain_id": "tc-...", "opened_at": 0, "pinned": false, "locked_to": null}
  ],
  "settings": {"appearance": {"theme": "light", "accent": "red"}}
}
```

同一工具链有多个版本时，列表中的第一个是默认版本；右键某一行可以设为默认。`locked_to` 是工程级覆盖设置。

## 文件关联说明

注册写入 `HKCU\Software\Classes`（ProgID + `.eww`/`.ewp` 的 OpenWith 和默认值），不需要管理员权限。Windows 10/11 如果已经通过 UserChoice 把扩展名指给其他程序，系统会优先旧关联；此时按钮会提示你到“默认应用”里确认一次，程序不会绕过系统保护。

## 开发与打包

依赖：Python 3.11、PySide6、PyInstaller。

```bash
python IAR_Launcher.py            # 开发运行
python -m unittest tests.test_core
pyinstaller IAR_Launcher.spec --noconfirm --clean
```

打包产物在 `dist/IAR_Launcher/`。`assets/fonts` 会一起打包，界面使用 HarmonyOS Sans SC，不依赖系统安装。

## 目录

```
IAR_Launcher.py          入口（静默/UI 分发）
iar_launcher/core/       配置、工程解析、启动、扫描、文件关联
iar_launcher/ui/         PySide6 主窗口、页面、主题、控件、弹窗
legacy/                  旧版实现（--legacy）
assets/                  图标、HarmonyOS Sans SC 字体及许可
preview/                 HTML 设计预览与字体子集构建脚本
tools/                   离屏截图/验证脚本
tests/                   核心单元测试
```

## 已知限制

- 自动扫描依赖 IAR 卸载注册表项；没有注册表记录时，只能手动添加路径。
- 工程里的 toolchain 名称需要能被识别（ARM/RX/RH850/RL78/RISC-V/MSP430 或自定义名称）；识别失败会提示。
- 文件关联的最终生效仍受 Windows 默认应用策略影响。
- 改主题/主题色会立即写入配置；没有“取消”预览态。
