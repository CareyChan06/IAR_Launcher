"""关于页：应用信息、联系我们、系统集成、启动方式。"""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, APP_VERSION, AUTHOR, EMAIL
from ..core import association
from ..core.paths import asset_dir
from .icons import icon
from .widgets import (
    Card,
    ModeTile,
    StatusChip,
    make_button,
    make_icon_button,
    repolish,
)


class AboutPage(QWidget):
    def __init__(self, main, parent=None):
        super().__init__(parent)
        self.main = main
        self.setObjectName("Page")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 28, 14)
        outer.setSpacing(0)

        title = QLabel("关于")
        title.setObjectName("PageTitle")
        subtitle = QLabel("系统集成、启动方式与联系方式")
        subtitle.setObjectName("PageSub")
        outer.addWidget(title)
        outer.addSpacing(4)
        outer.addWidget(subtitle)
        outer.addSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 3, 2)
        layout.setSpacing(10)

        hero = Card()
        hero.body.setSpacing(0)
        hero_row = QHBoxLayout()
        hero_row.setSpacing(13)
        app_icon = QLabel()
        app_icon.setFixedSize(42, 42)
        pixmap = QIcon(str(asset_dir() / "icon.ico")).pixmap(42, 42)
        app_icon.setPixmap(pixmap)
        hero_row.addWidget(app_icon)
        hero_text = QVBoxLayout()
        hero_text.setSpacing(2)
        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        app_title = QLabel(APP_NAME)
        app_title.setObjectName("AboutTitle")
        name_row.addWidget(app_title)
        version = StatusChip(f"v{APP_VERSION}")
        name_row.addWidget(version)
        name_row.addStretch(1)
        hero_text.addLayout(name_row)
        tagline = QLabel("根据 .eww 工程的工具链，自动选用对应版本的 IAR 打开")
        tagline.setObjectName("PageSub")
        hero_text.addWidget(tagline)
        hero_row.addLayout(hero_text, 1)
        hero.body.addLayout(hero_row)
        layout.addWidget(hero)

        contact = Card()
        contact.body.setSpacing(8)
        contact_title_row = QHBoxLayout()
        contact_title_row.setSpacing(7)
        self.contact_icon = QLabel()
        contact_title_row.addWidget(self.contact_icon)
        contact_title = QLabel("联系我们")
        contact_title.setObjectName("CardTitle")
        contact_title_row.addWidget(contact_title)
        contact_title_row.addStretch(1)
        contact.body.addLayout(contact_title_row)
        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)
        author = QLabel(f"作者  {AUTHOR}")
        author.setObjectName("ContactMeta")
        meta_row.addWidget(author)
        meta_row.addWidget(self._dot())
        email = make_button(EMAIL, "ghost")
        email.setObjectName("EmailLink")
        repolish(email)
        email.setCursor(Qt.CursorShape.PointingHandCursor)
        email.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(f"mailto:{EMAIL}")))
        meta_row.addWidget(email)
        copy = make_icon_button("copy", main.theme.palette["text3"], "复制邮箱", 13)
        copy.clicked.connect(self.copy_email)
        meta_row.addWidget(copy)
        meta_row.addStretch(1)
        contact.body.addLayout(meta_row)
        layout.addWidget(contact)

        integration = Card()
        integration.body.setSpacing(10)
        integ_title_row = QHBoxLayout()
        integ_title_row.setSpacing(7)
        self.link_icon = QLabel()
        integ_title_row.addWidget(self.link_icon)
        integ_title = QLabel("系统集成")
        integ_title.setObjectName("CardTitle")
        integ_title_row.addWidget(integ_title)
        integ_title_row.addStretch(1)
        integration.body.addLayout(integ_title_row)

        assoc_row = QHBoxLayout()
        assoc_row.setSpacing(12)
        assoc_text = QVBoxLayout()
        assoc_text.setSpacing(2)
        assoc_title_row = QHBoxLayout()
        assoc_title_row.setSpacing(8)
        assoc_title = QLabel(".eww / .ewp 默认打开方式")
        assoc_title.setStyleSheet("font-size: 13px; font-weight: 500;")
        assoc_title_row.addWidget(assoc_title)
        self.assoc_chip = StatusChip("未关联")
        assoc_title_row.addWidget(self.assoc_chip)
        assoc_title_row.addStretch(1)
        assoc_text.addLayout(assoc_title_row)
        desc = QLabel("注册到当前用户，不需要管理员权限。")
        desc.setObjectName("Hint")
        assoc_text.addWidget(desc)
        assoc_row.addLayout(assoc_text, 1)
        self.register_button = make_button("注册为默认打开方式", "secondary", "link")
        self.register_button.clicked.connect(self.register_association)
        assoc_row.addWidget(self.register_button)
        integration.body.addLayout(assoc_row)

        note_frame = QFrame()
        note_frame.setObjectName("Note")
        note_frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        note_layout = QVBoxLayout(note_frame)
        note_layout.setContentsMargins(9, 7, 9, 7)
        note = QLabel(
            "Windows 已记住旧关联时，注册后可能仍需在“默认应用”里确认一次，程序会检测并提示。"
        )
        note.setObjectName("NoteText")
        note.setWordWrap(True)
        note_layout.addWidget(note)
        integration.body.addWidget(note_frame)
        settings_link = make_button("打开系统默认应用设置", "ghost")
        settings_link.setObjectName("LinkButton")
        settings_link.clicked.connect(self.open_default_apps)
        integration.body.addWidget(settings_link, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(integration)

        modes = Card()
        modes.body.setSpacing(8)
        mode_title_row = QHBoxLayout()
        mode_title_row.setSpacing(7)
        monitor = QLabel()
        monitor.setPixmap(icon("monitor", main.theme.palette["text3"], 15).pixmap(15, 15))
        mode_title_row.addWidget(monitor)
        mode_title = QLabel("启动方式")
        mode_title.setObjectName("CardTitle")
        mode_title_row.addWidget(mode_title)
        mode_title_row.addStretch(1)
        modes.body.addLayout(mode_title_row)
        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)
        mode_row.addWidget(ModeTile("mouse", "双击本程序", "打开主界面"), 1)
        mode_row.addWidget(ModeTile("folder", "双击 .eww", "静默启动"), 1)
        mode_row.addWidget(ModeTile("external", "拖到图标", "静默启动"), 1)
        mode_row.addWidget(ModeTile("terminal", "--ui 参数", "强制显示界面"), 1)
        modes.body.addLayout(mode_row)
        layout.addWidget(modes)
        layout.addStretch(1)

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        self._monitor_icon = monitor
        self.refresh_theme()
        self.refresh_assoc()

    @staticmethod
    def _dot() -> QLabel:
        label = QLabel("·")
        label.setObjectName("Hint")
        return label

    def refresh_theme(self) -> None:
        text3 = self.main.theme.palette["text3"]
        self.contact_icon.setPixmap(icon("mail", text3, 15).pixmap(15, 15))
        self.link_icon.setPixmap(icon("link", text3, 15).pixmap(15, 15))
        self._monitor_icon.setPixmap(icon("monitor", text3, 15).pixmap(15, 15))
        self.refresh_assoc()

    def refresh_assoc(self) -> None:
        if not getattr(sys, "frozen", False):
            self.assoc_chip.set_state("开发模式", "neutral")
            self.register_button.setText("打包后可用")
            self.register_button.setEnabled(False)
            return
        status = association.query_status()
        self.assoc_chip.setToolTip(status.get("detail", ""))
        if status["state"] == "ours":
            self.assoc_chip.set_state("已关联", "ok")
            self.register_button.setText("重新注册")
            self.register_button.setEnabled(True)
        elif status["state"] == "other":
            self.assoc_chip.set_state("被其他程序占用", "warn")
            self.register_button.setText("重新注册")
            self.register_button.setEnabled(True)
        elif status["state"] == "partial":
            self.assoc_chip.set_state("部分关联", "warn")
            self.register_button.setText("注册为默认打开方式")
            self.register_button.setEnabled(True)
        else:
            self.assoc_chip.set_state("未关联", "neutral")
            self.register_button.setText("注册为默认打开方式")
            self.register_button.setEnabled(True)

    def register_association(self) -> None:
        exe = association.app_executable()
        if not exe:
            self.main.toast("info", "开发模式下不可注册", "打包为 exe 后可在当前用户注册 .eww / .ewp 关联。")
            return
        ok, message = association.register(exe)
        self.refresh_assoc()
        status = association.query_status()
        self.main.toast("ok" if ok and status["state"] != "other" else "warn", "文件关联", message)

    def open_default_apps(self) -> None:
        if not association.open_default_apps():
            self.main.toast("error", "无法打开默认应用设置", "请手动打开 Windows 设置 → 应用 → 默认应用。")

    def copy_email(self) -> None:
        QGuiApplication.clipboard().setText(EMAIL)
        self.main.toast("ok", "邮箱已复制", EMAIL)

    def on_show(self) -> None:
        self.refresh_assoc()
