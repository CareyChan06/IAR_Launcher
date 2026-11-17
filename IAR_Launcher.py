"""IAR Launcher 入口。

无参数 / --ui      → 显示 PySide6 界面
<eww|ewp>           → 静默启动，不加载 Qt
--legacy <文件>     → 运行旧版实现
--config <路径>     → 指定 config.json（测试/便携用）
"""
from __future__ import annotations

import ctypes
import sys
from pathlib import Path

# 允许从快捷方式、任意工作目录启动。
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))


def _message(text: str, title: str = "IAR Launcher", flags: int = 0x10) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(0, text, title, flags)
    except Exception:
        print(f"{title}: {text}", file=sys.stderr)


def _parse_args(argv: list[str]) -> tuple[list[str], bool, str | None, bool]:
    paths: list[str] = []
    ui = False
    config_path: str | None = None
    legacy = False
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--legacy":
            legacy = True
        elif arg == "--ui":
            ui = True
        elif arg == "--config" and index + 1 < len(argv):
            config_path = argv[index + 1]
            index += 1
        elif arg.startswith("--config="):
            config_path = arg.split("=", 1)[1]
        elif arg.startswith("--"):
            pass
        else:
            paths.append(arg)
        index += 1
    return paths, ui, config_path, legacy


def main() -> int:
    paths, ui, config_path, legacy = _parse_args(sys.argv[1:])

    if legacy:
        sys.argv = [sys.argv[0]] + paths
        try:
            from legacy.iar_launcher_v1 import main as legacy_main

            legacy_main()
            return 0
        except Exception as exc:
            _message(f"旧版启动失败：\n{exc}")
            return 1

    if config_path:
        from iar_launcher.core.paths import set_config_override

        set_config_override(config_path)

    if paths and not ui:
        try:
            from iar_launcher.core.launcher import launch_project

            for path in paths:
                result = launch_project(path)
                if not result.ok:
                    _message(result.message)
                    return 1
            return 0
        except Exception as exc:
            _message(f"启动失败：\n{exc}")
            return 1

    try:
        from iar_launcher.ui.app import run

        return run()
    except Exception as exc:
        _message(f"界面启动失败：\n{exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
