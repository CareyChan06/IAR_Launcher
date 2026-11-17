"""应用目录、配置路径与资源定位。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "IAR_Launcher"
_config_override: Path | None = None


def project_root() -> Path:
    """开发环境下的仓库根目录。"""
    return Path(__file__).resolve().parents[2]


def app_dir() -> Path:
    """exe 所在目录；开发环境为仓库根目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return project_root()


def asset_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", app_dir()))
    else:
        base = project_root()
    return base / "assets"


def set_config_override(path: str | os.PathLike[str] | None) -> None:
    """测试/调试用：强制使用指定配置文件。"""
    global _config_override
    _config_override = Path(path).expanduser().resolve() if path else None


def default_config_path() -> Path:
    if _config_override is not None:
        return _config_override

    env = os.environ.get("IAR_LAUNCHER_CONFIG")
    if env:
        return Path(env).expanduser().resolve()

    exe_dir = app_dir()
    candidate = exe_dir / "config.json"
    if candidate.exists():
        return candidate
    try:
        exe_dir.mkdir(parents=True, exist_ok=True)
        probe = exe_dir / ".write_test"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return candidate
    except OSError:
        pass

    local = os.environ.get("LOCALAPPDATA")
    base = Path(local) if local else Path.home() / "AppData" / "Local"
    return base / APP_NAME / "config.json"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
