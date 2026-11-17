"""开发用：离屏渲染各页面截图，便于核对 PySide6 实现。"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from iar_launcher.core.config import ConfigStore
from iar_launcher.core.paths import set_config_override, asset_dir
from iar_launcher.core.discovery import scan_installed
from iar_launcher.ui.app import _load_fonts
from iar_launcher.ui.main_window import MainWindow
from iar_launcher.ui.theme import ThemeController

OUT = ROOT / "preview"

tmp = tempfile.TemporaryDirectory()
base = Path(tmp.name)
config_path = base / "config.json"

toolchains = []
for item in scan_installed():
    toolchains.append({
        "id": f"tc-{len(toolchains)}",
        "chain": item.chain,
        "version": item.version,
        "path": item.path,
        "added_at": time.time(),
    })
# 伪造两条失效路径，展示状态
for chain, version, path in [
    ("RH850", "3.10", r"C:\IAR\RH850 3.10\common\bin\IarIdePm.exe"),
    ("RL78", "3.10", r"C:\IAR\RL78 3.10\common\bin\IarIdePm.exe"),
]:
    toolchains.append({
        "id": f"tc-{len(toolchains)}",
        "chain": chain,
        "version": version,
        "path": path,
        "added_at": time.time(),
    })

projects = []
for name, chain in [("MOTOR_CTRL_F407", "ARM"), ("SENSOR_HUB_RX65", "RX"), ("PANEL_RL78_G13", "RL78")]:
    folder = base / name
    folder.mkdir()
    ewp = folder / f"{name}.ewp"
    ewp.write_text(f"<project><configuration><toolchain><name>{chain}</name></toolchain></configuration></project>", encoding="utf-8")
    eww = folder / f"{name}.eww"
    eww.write_text(f"<workspace><project><path>$WS_DIR$\\{name}.ewp</path></project></workspace>", encoding="utf-8")
    projects.append({
        "path": str(eww),
        "name": name,
        "chain": chain,
        "toolchain_id": None,
        "opened_at": time.time() - len(projects) * 3700,
        "pinned": len(projects) < 2,
        "locked_to": None,
    })
projects.append({
    "path": str(base / "MOVED" / "MOVED.eww"),
    "name": "MSP430_LEGACY_DONGLE",
    "chain": "MSP430",
    "toolchain_id": None,
    "opened_at": time.time() - 86400 * 3,
    "pinned": False,
    "locked_to": None,
})

payload = {
    "schema": 2,
    "toolchains": toolchains,
    "recent_projects": projects,
    "settings": {"appearance": {"theme": "light", "accent": "red", "titlebar": "custom"}},
}
config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
set_config_override(str(config_path))

app = QApplication([])
app.setStyle("Fusion")
sans, mono = _load_fonts()
store = ConfigStore()
theme = ThemeController(store, app, sans, mono)
window = MainWindow(store, theme)
window.show()
QTest.qWait(150)

OUT.mkdir(exist_ok=True)
for key, name in [("projects", "app-projects"), ("chains", "app-chains"), ("settings", "app-settings"), ("about", "app-about")]:
    window.switch_page(key)
    QTest.qWait(80)
    window.grab().save(str(OUT / f"{name}.png"))

theme.set_mode("dark")
theme.set_accent("blue")
window.switch_page("chains")
QTest.qWait(100)
window.grab().save(str(OUT / "app-chains-dark.png"))
window.switch_page("settings")
QTest.qWait(80)
window.grab().save(str(OUT / "app-settings-dark.png"))

print("saved screenshots")
tmp.cleanup()
