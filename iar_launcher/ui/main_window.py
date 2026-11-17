"""主窗口：侧栏导航、页面栈、状态栏、通知与拖放。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, APP_VERSION
from ..core.config import ConfigStore
from ..core.launcher import launch_project
from ..core.paths import asset_dir
from .about_page import AboutPage
from .icons import icon
from .project_page import ProjectPage
from .settings_page import SettingsPage
from .theme import ThemeController
from .titlebar import TitleBar
from .toolchain_page import ToolchainPage
from .widgets import ConfirmDialog, ToastManager, make_button, repolish, set_prop
from .winchrome import IS_WINDOWS, WindowsFrame, apply_titlebar_theme


class MainWindow(QMainWindow):
    PAGE_ORDER = ["projects", "chains", "settings", "about"]

    def __init__(self, store: ConfigStore, theme: ThemeController):
        super().__init__()
        self.store = store
        self.theme = theme
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(str(asset_dir() / "icon.ico")))
        self.setMinimumSize(920, 620)
        self.resize(1024, 680)
        self.setAcceptDrops(True)

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._frame = WindowsFrame(self)
        self.title_bar = TitleBar()
        self.title_bar.minimize_requested.connect(self.showMinimized)
        self.title_bar.toggle_maximize_requested.connect(self._toggle_maximize)
        self.title_bar.close_requested.connect(self.close)
        self.title_bar.setVisible(False)
        root_layout.addWidget(self.title_bar)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        sidebar.setFixedWidth(204)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 16, 12, 12)
        side_layout.setSpacing(2)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        brand_icon = QLabel()
        brand_icon.setFixedSize(34, 34)
        brand_icon.setPixmap(QIcon(str(asset_dir() / "icon.ico")).pixmap(34, 34))
        brand.addWidget(brand_icon)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(1)
        brand_name = QLabel(APP_NAME)
        brand_name.setObjectName("BrandName")
        brand_sub = QLabel("多版本工作区启动器")
        brand_sub.setObjectName("BrandSub")
        brand_text.addWidget(brand_name)
        brand_text.addWidget(brand_sub)
        brand.addLayout(brand_text, 1)
        side_layout.addLayout(brand)
        side_layout.addSpacing(14)

        nav_label = QLabel("工作区")
        nav_label.setObjectName("NavLabel")
        side_layout.addWidget(nav_label)
        side_layout.addSpacing(4)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons: dict[str, QPushButton] = {}
        self._nav_icons = {
            "projects": "folder",
            "chains": "chip",
            "settings": "settings",
            "about": "info",
        }
        for key, text in (
            ("projects", "项目"),
            ("chains", "工具链"),
            ("settings", "设置"),
            ("about", "关于"),
        ):
            button = QPushButton(text)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setIconSize(QSize(17, 17))
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.clicked.connect(lambda checked=False, value=key: self.switch_page(value))
            button.toggled.connect(self._refresh_nav_icons)
            self.nav_group.addButton(button)
            side_layout.addWidget(button)
            self.nav_buttons[key] = button
        side_layout.addStretch(1)

        body_layout.addWidget(sidebar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("PageStack")
        self.pages = {
            "projects": ProjectPage(self),
            "chains": ToolchainPage(self),
            "settings": SettingsPage(self),
            "about": AboutPage(self),
        }
        for key in self.PAGE_ORDER:
            self.stack.addWidget(self.pages[key])
            self.pages[key].setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        body_layout.addWidget(self.stack, 1)
        root_layout.addWidget(body, 1)

        status = QWidget()
        status.setObjectName("StatusBar")
        status.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        status.setFixedHeight(30)
        status_layout = QHBoxLayout(status)
        status_layout.setContentsMargins(14, 0, 14, 0)
        status_layout.setSpacing(8)
        self.health_button = QPushButton()
        self.health_button.setObjectName("HealthButton")
        self.health_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.health_button.setIconSize(QSize(6, 6))
        self.health_button.clicked.connect(lambda: self.switch_page("chains"))
        status_layout.addWidget(self.health_button)
        status_layout.addStretch(1)
        version = QLabel(f"{APP_NAME} v{APP_VERSION}")
        version.setObjectName("VersionLabel")
        status_layout.addWidget(version)
        root_layout.addWidget(status)

        self.toasts = ToastManager(self, bottom_margin=44)
        self.theme.changed.connect(self._on_theme_changed)
        self.switch_page("projects")
        self.refresh_chrome()
        self._apply_titlebar_mode()
        self._center()
        self._first_run_checked = False

    def _center(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen:
            rect = screen.availableGeometry()
            self.move(
                rect.x() + max(0, (rect.width() - self.width()) // 2),
                rect.y() + max(0, (rect.height() - self.height()) // 2),
            )

    # ── 导航 ──
    def switch_page(self, key: str) -> None:
        if key not in self.pages:
            return
        self.stack.setCurrentIndex(self.PAGE_ORDER.index(key))
        self.nav_buttons[key].setChecked(True)
        self._refresh_nav_icons()
        page = self.pages[key]
        page.setFocus(Qt.FocusReason.OtherFocusReason)
        if key == "projects":
            page.refresh()
        elif key == "chains":
            page.refresh()
        elif key == "about":
            page.on_show()

    def _refresh_nav_icons(self, *_args) -> None:
        palette = self.theme.palette
        accent = self.theme.accent["text"]
        for key, button in self.nav_buttons.items():
            color = accent if button.isChecked() else palette["text3"]
            button.setIcon(icon(self._nav_icons[key], color, 17))

    def _on_theme_changed(self) -> None:
        self._refresh_nav_icons()
        self._apply_titlebar_theme()
        self.title_bar.refresh(self.theme.palette)
        self.refresh_chrome()
        self.pages["projects"].refresh_theme()
        self.pages["chains"].refresh_theme()
        self.pages["about"].refresh_theme()

    def _apply_titlebar_theme(self) -> None:
        palette = self.theme.palette
        apply_titlebar_theme(
            self,
            self.theme.resolved == "dark",
            palette["chrome"],
            palette["text"],
            palette["border"],
        )

    # ── 标题栏模式 ──
    def titlebar_setting(self) -> str:
        mode = str(self.store.appearance.get("titlebar", "custom"))
        return mode if mode in {"native", "custom"} else "custom"

    def set_titlebar_mode(self, mode: str) -> None:
        if mode in {"native", "custom"}:
            self.store.set_appearance(titlebar=mode)
            self._apply_titlebar_mode()

    def _apply_titlebar_mode(self) -> None:
        use_custom = IS_WINDOWS and self.titlebar_setting() == "custom"
        flags = self.windowFlags()
        wants = flags | Qt.WindowType.FramelessWindowHint if use_custom else flags & ~Qt.WindowType.FramelessWindowHint
        if wants != flags:
            visible = self.isVisible()
            self.setWindowFlags(wants)
            if visible:
                self.show()
        self.title_bar.setVisible(use_custom)
        self.title_bar.set_maximized(self.isMaximized())
        self._frame.set_active(use_custom)

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def changeEvent(self, event) -> None:  # type: ignore[override]
        super().changeEvent(event)
        if event.type() == event.Type.WindowStateChange:
            self.title_bar.set_maximized(self.isMaximized())

    def nativeEvent(self, event_type, message) -> tuple[bool, int]:  # type: ignore[override]
        handled, result = self._frame.handle(message)
        if handled:
            return True, result
        return super().nativeEvent(event_type, message)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._apply_titlebar_theme()
        self._apply_titlebar_mode()
        if not getattr(self, "_first_run_checked", True):
            self._first_run_checked = True
            QTimer.singleShot(350, self._maybe_first_run)

    def _maybe_first_run(self) -> None:
        if self.store.toolchains:
            return
        scan = ConfirmDialog.ask(
            self,
            "还没有配置工具链",
            "启动器需要至少一个 IarIdePm.exe 路径。要自动扫描本机已安装的 IAR 吗？",
            "",
            "自动扫描",
            danger=False,
        )
        self.switch_page("chains")
        if scan:
            self.pages["chains"].scan()

    # ── 状态栏 ──
    def refresh_chrome(self) -> None:
        good, total = self.store.health()
        projects = len(self.store.recent)
        if total == 0:
            text = f"未配置工具链 · {projects} 个项目"
            state, color, tip = "warn", self.theme.palette["warn"], "尚未配置工具链，点击添加"
        elif good < total:
            text = f"{good}/{total} 个工具链可用 · {projects} 个项目"
            state = "bad" if good == 0 else "warn"
            color = self.theme.palette["danger"] if good == 0 else self.theme.palette["warn"]
            tip = (
                "所有工具链路径都失效了，点击查看"
                if good == 0
                else f"{total - good} 项工具链配置失效，点击查看"
            )
        else:
            text = f"{total} 个工具链可用 · {projects} 个项目"
            state, color, tip = "", self.theme.palette["ok"], "工具链配置正常，点击查看"
        self.health_button.setText(text)
        self.health_button.setIcon(self._dot_icon(color))
        self.health_button.setToolTip(tip)
        self.health_button.setProperty("state", state)
        repolish(self.health_button)

    def _dot_icon(self, color: str) -> QIcon:
        pixmap = QPixmap(12, 12)
        pixmap.setDevicePixelRatio(2)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 12, 12)
        painter.end()
        return QIcon(pixmap)

    # ── 打开工程 ──
    def open_project_path(self, path: str):
        result = launch_project(path, self.store)
        if result.ok:
            self.pages["projects"].refresh()
            self.refresh_chrome()
            label = result.toolchain.label if result.toolchain else "IAR"
            name = result.project.name if result.project else Path(path).stem
            self.toast("ok", f"已启动 {label}", name)
            return result

        action = None
        title = "打开失败"
        if result.code in {"no_chain", "missing_exe"}:
            action = ("去配置", lambda: self.switch_page("chains"))
        if result.code == "no_chain":
            title = "未配置工具链"
        elif result.code == "missing_exe":
            title = "IAR 路径失效"
        elif result.code == "parse":
            title = "无法打开工程"
        elif result.code == "spawn":
            title = "启动 IAR 失败"
        self.toast("error" if result.code in {"parse", "spawn", "missing_exe"} else "warn", title, result.message, action)
        return result

    # ── 通知 ──
    def toast(self, kind: str, title: str, desc: str = "", action=None) -> None:
        self.toasts.show_toast(kind, title, desc, action)

    # ── 拖放 / 激活 ──
    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith((".eww", ".ewp")):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event) -> None:  # type: ignore[override]
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        projects = [path for path in paths if path.lower().endswith((".eww", ".ewp"))]
        if projects:
            event.acceptProposedAction()
            self.open_project_path(projects[0])
        else:
            self.toast("error", "不支持的文件类型", "请拖入 .eww 或 .ewp 工程文件。")

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self.toasts.reposition()

    def activate(self) -> None:
        if self.isMinimized():
            self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()
