"""PySide6 应用启动、字体加载与单实例。"""
from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox

from .. import APP_NAME
from ..core.config import ConfigStore
from ..core.paths import asset_dir, default_config_path
from .main_window import MainWindow
from .theme import ThemeController

SERVER_NAME = "IAR_Launcher_UI_v1"


def _load_fonts() -> tuple[str, str]:
    font_dir = asset_dir() / "fonts"
    candidates = [
        "HarmonyOS_Sans_SC_Regular.ttf",
        "HarmonyOS_Sans_SC_Medium.ttf",
        "HarmonyOS_Sans_SC_Bold.ttf",
    ]
    families: list[str] = []
    for name in candidates:
        path = font_dir / name
        if not path.is_file():
            continue
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id >= 0:
            families.extend(QFontDatabase.applicationFontFamilies(font_id))
    sans = families[0] if families else "Microsoft YaHei UI"
    if not any("harmonyos" in family.lower() for family in families):
        sans = "Microsoft YaHei UI"
    mono = "Cascadia Mono" if "Cascadia Mono" in QFontDatabase.families() else "Consolas"
    return sans, mono


def _notify_existing() -> bool:
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if not socket.waitForConnected(350):
        return False
    socket.write(b"activate")
    socket.waitForBytesWritten(350)
    socket.disconnectFromServer()
    return True


def run() -> int:
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("carey_chan.IARLauncher")
    except Exception:
        pass
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName("carey_chan")
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon(str(asset_dir() / "icon.ico")))

    sans, mono = _load_fonts()
    font = QFont(sans)
    font.setPointSizeF(9.75)
    app.setFont(font)

    if _notify_existing():
        return 0

    try:
        store = ConfigStore()
    except ValueError as exc:
        QMessageBox.critical(
            None,
            "配置文件读取失败",
            f"{exc}\n\n请修复或删除配置文件后重试。\n{default_config_path()}",
        )
        return 1

    theme = ThemeController(store, app, sans, mono)
    try:
        QGuiApplication.styleHints().colorSchemeChanged.connect(theme.on_system_change)
    except AttributeError:
        pass

    QLocalServer.removeServer(SERVER_NAME)
    server = QLocalServer()
    if not server.listen(SERVER_NAME):
        # 极少数情况下命名管道仍被占用：仍然启动，只是不启用单实例。
        server = None

    window = MainWindow(store, theme)
    window.show()

    if server is not None:
        def on_new_connection() -> None:
            socket = server.nextPendingConnection()
            if socket is not None:
                window.activate()
                socket.disconnected.connect(socket.deleteLater)

        server.newConnection.connect(on_new_connection)
        app.aboutToQuit.connect(server.close)

    return app.exec()
