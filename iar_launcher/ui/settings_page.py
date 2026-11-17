"""设置页：浅色/深色/跟随系统、主题色、配置文件位置。"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .icons import icon
from .theme import ACCENTS
from .widgets import (
    AccentItem,
    Badge,
    Card,
    ElidedLabel,
    HLine,
    SegmentedControl,
    StatusChip,
    make_button,
)


class SettingsPage(QWidget):
    def __init__(self, main, parent=None):
        super().__init__(parent)
        self.main = main
        self.setObjectName("Page")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 22, 28, 16)
        outer.setSpacing(0)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        title = QLabel("设置")
        title.setObjectName("PageTitle")
        subtitle = QLabel("外观与界面偏好，修改后立即生效")
        subtitle.setObjectName("PageSub")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header.addLayout(title_col)
        header.addStretch(1)
        reset = make_button("恢复默认", "ghost", "refresh")
        reset.clicked.connect(self.reset)
        header.addWidget(reset, 0, Qt.AlignmentFlag.AlignTop)
        outer.addLayout(header)
        outer.addSpacing(14)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 3, 2)
        layout.setSpacing(10)

        appearance = Card()
        title_row = QHBoxLayout()
        title_row.setSpacing(7)
        palette_icon = QLabel()
        palette_icon.setPixmap(icon("palette", main.theme.palette["text3"], 15).pixmap(15, 15))
        title_row.addWidget(palette_icon)
        card_title = QLabel("外观")
        card_title.setObjectName("CardTitle")
        title_row.addWidget(card_title)
        title_row.addStretch(1)
        appearance.body.addLayout(title_row)

        theme_label = QLabel("主题")
        theme_label.setObjectName("FieldLabel")
        appearance.body.addSpacing(2)
        appearance.body.addWidget(theme_label)
        self.theme_seg = SegmentedControl(
            [
                ("light", "浅色", "sun"),
                ("dark", "深色", "moon"),
                ("system", "跟随系统", "monitor"),
            ]
        )
        self.theme_seg.set_value(main.theme.mode)
        self.theme_seg.changed.connect(main.theme.set_mode)
        appearance.body.addWidget(self.theme_seg, 0, Qt.AlignmentFlag.AlignLeft)
        hint = QLabel("跟随系统时会随 Windows 的浅色 / 深色模式自动切换。")
        hint.setObjectName("Hint")
        appearance.body.addWidget(hint)

        appearance.body.addWidget(HLine())

        accent_label = QLabel("主题色")
        accent_label.setObjectName("FieldLabel")
        appearance.body.addWidget(accent_label)
        accent_row = QHBoxLayout()
        accent_row.setSpacing(6)
        self.accent_items: dict[str, AccentItem] = {}
        for key, meta in ACCENTS.items():
            item = AccentItem(key, meta["name"], meta["light"]["swatch"])
            item.set_selected(key == main.theme.accent_name)
            item.clicked.connect(main.theme.set_accent)
            accent_row.addWidget(item)
            self.accent_items[key] = item
        accent_row.addStretch(1)
        appearance.body.addLayout(accent_row)
        accent_hint = QLabel("主题色用于主要按钮、选中状态和焦点描边，不改变警告与错误色。")
        accent_hint.setObjectName("Hint")
        appearance.body.addWidget(accent_hint)

        preview = QFrame()
        preview.setObjectName("PreviewStrip")
        preview.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        preview_layout = QHBoxLayout(preview)
        preview_layout.setContentsMargins(11, 8, 11, 8)
        preview_layout.setSpacing(10)
        preview_label = QLabel("预览")
        preview_label.setObjectName("Hint")
        preview_layout.addWidget(preview_label)
        preview_button = make_button("主要按钮", "primary")
        preview_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        preview_layout.addWidget(preview_button)
        preview_layout.addWidget(Badge("ARM"))
        preview_layout.addWidget(StatusChip("可用", "ok"))
        accent_text = QLabel("选中状态")
        accent_text.setObjectName("AccentText")
        preview_layout.addWidget(accent_text)
        preview_layout.addStretch(1)
        appearance.body.addWidget(preview)

        appearance.body.addWidget(HLine())

        titlebar_label = QLabel("窗口标题栏")
        titlebar_label.setObjectName("FieldLabel")
        appearance.body.addWidget(titlebar_label)
        self.titlebar_seg = SegmentedControl(
            [
                ("native", "原生", "monitor"),
                ("custom", "沉浸", "window"),
            ]
        )
        self.titlebar_seg.set_value(main.titlebar_setting())
        self.titlebar_seg.changed.connect(main.set_titlebar_mode)
        appearance.body.addWidget(self.titlebar_seg, 0, Qt.AlignmentFlag.AlignLeft)
        titlebar_hint = QLabel(
            "沉浸模式去掉系统标题栏，由启动器自绘并跟随主题；"
            "拖动、贴边吸附、双击最大化等行为保持不变。仅 Windows 生效。"
        )
        titlebar_hint.setObjectName("Hint")
        titlebar_hint.setWordWrap(True)
        appearance.body.addWidget(titlebar_hint)
        layout.addWidget(appearance)

        data_card = Card()
        data_title_row = QHBoxLayout()
        data_title_row.setSpacing(7)
        folder_icon = QLabel()
        folder_icon.setPixmap(icon("folder", main.theme.palette["text3"], 15).pixmap(15, 15))
        data_title_row.addWidget(folder_icon)
        data_title = QLabel("数据")
        data_title.setObjectName("CardTitle")
        data_title_row.addWidget(data_title)
        data_title_row.addStretch(1)
        data_card.body.addLayout(data_title_row)

        path_row = QHBoxLayout()
        path_col = QVBoxLayout()
        path_col.setSpacing(2)
        path_label = QLabel("配置文件")
        path_label.setObjectName("FieldLabel")
        path_col.addWidget(path_label)
        self.path_value = ElidedLabel(str(main.store.path), Qt.TextElideMode.ElideMiddle)
        self.path_value.setObjectName("MonoPath")
        path_col.addWidget(self.path_value)
        path_row.addLayout(path_col, 1)
        open_dir = make_button("打开目录", "secondary", "folder-open")
        open_dir.clicked.connect(self.open_config_dir)
        path_row.addWidget(open_dir, 0, Qt.AlignmentFlag.AlignBottom)
        data_card.body.addLayout(path_row)
        data_hint = QLabel("主题、主题色与工具链配置都会保存到 config.json，下次启动自动恢复。")
        data_hint.setObjectName("Hint")
        data_hint.setWordWrap(True)
        data_card.body.addWidget(data_hint)
        layout.addWidget(data_card)
        layout.addStretch(1)

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)

        self._palette_icon = palette_icon
        self._folder_icon = folder_icon
        main.theme.changed.connect(self._on_theme_changed)

    def _on_theme_changed(self) -> None:
        theme = self.main.theme
        self.theme_seg.set_value(theme.mode)
        self.theme_seg.refresh_icons(theme.palette["text2"])
        for key, item in self.accent_items.items():
            item.set_selected(key == theme.accent_name)
        self._palette_icon.setPixmap(icon("palette", theme.palette["text3"], 15).pixmap(15, 15))
        self._folder_icon.setPixmap(icon("folder", theme.palette["text3"], 15).pixmap(15, 15))

    def open_config_dir(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.main.store.path.parent)))

    def reset(self) -> None:
        self.main.theme.set_mode("light")
        self.main.theme.set_accent("red")
        self.main.set_titlebar_mode("custom")
        self.titlebar_seg.set_value("custom")
        self.main.toast("ok", "已恢复默认外观", "浅色主题 · 朱红 · 沉浸标题栏")

    def refresh_theme(self) -> None:
        self._on_theme_changed()
