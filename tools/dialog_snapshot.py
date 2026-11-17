"""开发用：渲染弹窗与通知的离屏截图。"""
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

from iar_launcher.core.config import ConfigStore, RecentProject
from iar_launcher.core.discovery import scan_installed
from iar_launcher.core.paths import set_config_override
from iar_launcher.ui.app import _load_fonts
from iar_launcher.ui.dialogs import ChainDialog, LockDialog, ScanDialog
from iar_launcher.ui.main_window import MainWindow
from iar_launcher.ui.theme import ThemeController

OUT = ROOT / "preview"
tmp = tempfile.TemporaryDirectory()
base = Path(tmp.name)
config = base / "config.json"
toolchains = []
for item in scan_installed():
    toolchains.append({
        "id": f"tc-{len(toolchains)}",
        "chain": item.chain,
        "version": item.version,
        "path": item.path,
        "added_at": time.time(),
    })
project = RecentProject(str(base / "Demo.eww"), "Demo", "ARM", opened_at=time.time())
config.write_text(json.dumps({
    "schema": 2,
    "toolchains": toolchains,
    "recent_projects": [project.to_dict()],
    "settings": {"appearance": {"theme": "light", "accent": "red"}},
}, ensure_ascii=False), encoding="utf-8")
set_config_override(str(config))

app = QApplication([])
app.setStyle("Fusion")
sans, mono = _load_fonts()
store = ConfigStore()
theme = ThemeController(store, app, sans, mono)
window = MainWindow(store, theme)
window.show()
QTest.qWait(120)

dialog = ChainDialog(window, store, theme, None)
dialog.show()
QTest.qWait(150)
dialog.grab().save(str(OUT / "dialog-chain.png"))
dialog.reject()

dialog = ChainDialog(window, store, theme, None)
dialog.show()
QTest.qWait(80)
dialog.chain_combo.setCurrentIndex(dialog.chain_combo.findData("__custom__"))
QTest.qWait(80)
dialog.grab().save(str(OUT / "dialog-chain-custom.png"))
dialog.reject()

dialog = ScanDialog(window, store, theme)
dialog.show()
QTest.qWait(1200)
dialog.grab().save(str(OUT / "dialog-scan.png"))
dialog.reject()

dialog = LockDialog(window, store, theme, project)
dialog.show()
QTest.qWait(120)
dialog.grab().save(str(OUT / "dialog-lock.png"))
dialog.reject()

window.toast("ok", "已启动 EWARM 9.60.3", "MOTOR_CTRL_F407")
window.toast("warn", "工程文件不存在", "D:\\Work\\MOVED\\MOVED.eww", ("重新定位…", lambda: None))
QTest.qWait(120)
window.grab().save(str(OUT / "app-toast.png"))

print("saved dialog screenshots")
tmp.cleanup()
