# IAR Launcher 配置说明

## 介绍

IAR Launcher 是一个用于根据 .eww 工程文件自动启动对应版本 IAR 开发环境的小工具。

## 配置文件说明

本工具使用 [config.json](./config.json) 文件存储 IAR 路径配置。首次运行时，如果配置文件不存在，程序会自动创建一个默认配置。

### 配置文件结构

```json
{
  "iar_paths": {
    "ARM": "C:\\iar\\ewarm-9.60.3\\common\\bin\\IarIdePm.exe",
    "RX": "C:\\Program Files (x86)\\IAR Systems\\Embedded Workbench 8.4\\common\\bin\\IarIdePm.exe",
    "RH850": "C:\\Program Files (x86)\\IAR Systems\\Embedded Workbench for RH850 3.10\\common\\bin\\IarIdePm.exe",
    "RL78": "C:\\Program Files (x86)\\IAR Systems\\Embedded Workbench for RL78 3.10\\common\\bin\\IarIdePm.exe",
    "RISC-V": "C:\\Program Files\\IAR Systems\\IAR Embedded Workbench for RISC-V\\common\\bin\\IarIdePm.exe"
  },
  "default_config": {
    "check_for_updates": true,
    "show_console_output": false
  }
}
```

### 如何配置

1. 将 [config.json](./config.json) 文件与 IAR_Launcher.exe 放在同一目录下
2. 打开 [config.json](./config.json) 文件
3. 根据你安装的 IAR 版本修改对应的路径：
   - ARM 对应 EWARM (Embedded Workbench for ARM)
   - RX 对应 EWRX (Embedded Workbench for RX)
   - RH850 对应 EWRH850 (Embedded Workbench for RH850)
   - RL78 对应 EWRL78 (Embedded Workbench for RL78)
   - RISC-V 对应 Embedded Workbench for RISC-V
4. 保存文件

### 查找 IAR 可执行文件路径

如果你不知道 IAR 可执行文件的位置，可以按以下方式查找：

1. 在开始菜单搜索 "IAR" 或 "Embedded Workbench"
2. 找到对应的快捷方式，右键选择"属性"
3. 在"目标"字段中可以看到可执行文件的完整路径
4. 路径通常类似于：`C:\Program Files (x86)\IAR Systems\Embedded Workbench...\common\bin\IarIdePm.exe`

## 使用方法

将 .eww 或 .ewp 文件拖放到 IAR_Launcher.exe 上即可自动启动对应版本的 IAR 开发环境。

注意：为了使他人能够自定义IAR路径，需要将 [config.json](./config.json) 文件与 exe 文件放在同一目录下。

## 故障排除

如果出现 "IAR可执行文件不存在" 错误，请检查：

1. [config.json](./config.json) 中的路径是否正确
2. IAR 是否已正确安装
3. 路径中的版本号是否与实际安装的版本一致