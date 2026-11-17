"""通用控件：卡片、按钮、徽标、通知、遮罩弹窗、空状态。"""
from __future__ import annotations

from datetime import datetime
from typing import Callable

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QDesktopServices,
    QFontMetrics,
    QIcon,
    QPixmap,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .icons import icon


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def set_prop(widget: QWidget, name: str, value) -> None:
    widget.setProperty(name, value)
    repolish(widget)


def make_button(
    text: str,
    role: str = "secondary",
    icon_name: str | None = None,
    icon_color: str | None = None,
    parent: QWidget | None = None,
) -> QPushButton:
    button = QPushButton(text, parent)
    button.setProperty("role", role)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    if icon_name:
        button.setIcon(icon(icon_name, icon_color or "#8495a8", 15))
        button.setIconSize(QSize(15, 15))
    return button


def make_icon_button(
    name: str,
    color: str,
    tooltip: str = "",
    size: int = 16,
    parent: QWidget | None = None,
    star: bool = False,
    filled: bool | None = None,
) -> QToolButton:
    button = QToolButton(parent)
    button.setObjectName("StarButton" if star else "IconButton")
    button.setIcon(icon(name, color, size, filled))
    button.setIconSize(QSize(size, size))
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setToolTip(tooltip)
    button.setAutoRaise(True)
    button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return button


class ElidedLabel(QLabel):
    """按宽度省略文本，完整内容放在 tooltip。"""

    def __init__(self, text: str = "", mode: Qt.TextElideMode = Qt.TextElideMode.ElideMiddle, parent=None):
        super().__init__(parent)
        self._full = text
        self._mode = mode
        self.setToolTip(text)
        self.setText(text)

    def setText(self, text: str) -> None:  # type: ignore[override]
        self._full = text or ""
        self.setToolTip(self._full)
        self._update_text()

    def full_text(self) -> str:
        return self._full

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_text()

    def _update_text(self) -> None:
        width = max(20, self.width() - 2)
        metrics = QFontMetrics(self.font())
        super().setText(metrics.elidedText(self._full, self._mode, width))


class HLine(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Divider")
        self.setFixedHeight(1)


class Card(QFrame):
    def __init__(self, parent=None, margins=(16, 14, 16, 14)):
        super().__init__(parent)
        self.setObjectName("Card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(*margins)
        self.body.setSpacing(8)


class Badge(QLabel):
    def __init__(self, chain: str, known_chains: set[str] | None = None, parent=None):
        super().__init__(chain, parent)
        self.setProperty("badge", "chain")
        self.setProperty("chain", chain if not known_chains or chain in known_chains else "CUSTOM")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(22)
        self.setMinimumWidth(44)
        self.setMaximumWidth(96)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.setToolTip(chain)


class Chip(QLabel):
    def __init__(self, text: str, kind: str = "default", parent=None):
        super().__init__(text, parent)
        self.setProperty("chip", kind)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(17)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)


class Tag(QLabel):
    def __init__(self, text: str, state: str = "warn", parent=None):
        super().__init__(text, parent)
        self.setProperty("tag", state)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


class StatusChip(QLabel):
    def __init__(self, text: str = "", state: str = "neutral", parent=None):
        super().__init__(text, parent)
        self.setObjectName("StatusChip")
        self.setProperty("state", state)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(20)

    def set_state(self, text: str, state: str) -> None:
        self.setText(text)
        set_prop(self, "state", state)


class Dot(QLabel):
    def __init__(self, state: str = "ok", parent=None):
        super().__init__(parent)
        self.setObjectName("Dot")
        self.setFixedSize(6, 6)
        self.set_state(state)

    def set_state(self, state: str) -> None:
        set_prop(self, "state", state)


class SearchField(QLineEdit):
    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self._search_action = self.addAction(icon("search", "#8495a8", 15), QLineEdit.ActionPosition.LeadingPosition)


class EmptyState(QWidget):
    def __init__(
        self,
        title: str,
        text: str,
        icon_name: str = "folder",
        buttons: list[QPushButton] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 40, 20, 40)
        layout.setSpacing(6)
        layout.addStretch(1)

        icon_frame = QFrame()
        icon_frame.setFixedSize(56, 56)
        icon_frame.setStyleSheet("")  # 主题切换时由 QSS 的父级背景兜底
        icon_layout = QVBoxLayout(icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel()
        icon_label.setPixmap(icon(icon_name, "#8495a8", 26).pixmap(26, 26))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(icon_label)
        icon_frame.setObjectName("EmptyIcon")
        layout.addWidget(icon_frame, 0, Qt.AlignmentFlag.AlignHCenter)

        title_label = QLabel(title)
        title_label.setObjectName("EmptyTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        text_label = QLabel(text)
        text_label.setObjectName("EmptyText")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setWordWrap(True)
        # 固定 360px 宽：换行点完全由文案里的 \n 控制（在逗号处断行，不拆词），
        # 超长时才自动兜底换行。stretch 行保证整体水平居中。
        text_label.setFixedWidth(360)
        text_row = QHBoxLayout()
        text_row.setContentsMargins(0, 0, 0, 0)
        text_row.addStretch(1)
        text_row.addWidget(text_label)
        text_row.addStretch(1)
        layout.addLayout(text_row)

        if buttons:
            row = QHBoxLayout()
            row.setSpacing(8)
            row.addStretch(1)
            for button in buttons:
                row.addWidget(button)
            row.addStretch(1)
            layout.addSpacing(8)
            layout.addLayout(row)
        layout.addStretch(1)


class Toast(QFrame):
    closed = Signal(object)

    def __init__(
        self,
        kind: str,
        title: str,
        desc: str = "",
        action: tuple[str, Callable[[], None]] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setFixedWidth(344)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._dismiss)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(11, 10, 10, 10)
        layout.setSpacing(9)

        colors = {
            "ok": ("check", "#11865a"),
            "warn": ("alert", "#a86a00"),
            "error": ("alert", "#c73535"),
            "info": ("info", "#8495a8"),
        }
        icon_name, color = colors.get(kind, colors["info"])
        icon_label = QLabel()
        icon_label.setPixmap(icon(icon_name, color, 17).pixmap(17, 17))
        icon_label.setFixedSize(17, 17)
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("ToastTitle")
        title_label.setWordWrap(True)
        text_col.addWidget(title_label)
        if desc:
            desc_label = QLabel(desc)
            desc_label.setObjectName("ToastDesc")
            desc_label.setWordWrap(True)
            text_col.addWidget(desc_label)
        if action:
            label, callback = action
            action_button = QPushButton(label)
            action_button.setObjectName("ToastAction")
            action_button.setCursor(Qt.CursorShape.PointingHandCursor)
            action_button.clicked.connect(lambda: (callback(), self._dismiss()))
            text_col.addWidget(action_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(text_col, 1)

        close = QToolButton()
        close.setObjectName("ToastClose")
        close.setIcon(icon("x", "#8495a8", 12))
        close.setFixedSize(20, 20)
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.clicked.connect(self._dismiss)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)
        self._timer.start(5200)

    def _dismiss(self) -> None:
        self._timer.stop()
        self.closed.emit(self)
        self.deleteLater()


class ToastManager(QWidget):
    def __init__(self, parent: QWidget, bottom_margin: int = 44):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self._bottom_margin = bottom_margin
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self._layout.addStretch(1)
        self._items: list[Toast] = []
        self.hide()

    def show_toast(self, kind: str, title: str, desc: str = "", action=None) -> None:
        toast = Toast(kind, title, desc, action, self)
        toast.closed.connect(self._remove)
        self._layout.addWidget(toast, 0, Qt.AlignmentFlag.AlignRight)
        self._items.append(toast)
        while len(self._items) > 3:
            oldest = self._items.pop(0)
            oldest._dismiss()
        self._relayout()
        self.show()
        self.raise_()
        QTimer.singleShot(0, self._relayout)

    def _remove(self, toast: Toast) -> None:
        if toast in self._items:
            self._items.remove(toast)
        self._layout.removeWidget(toast)
        toast.hide()
        if not self._items:
            self.hide()
        QTimer.singleShot(0, self._relayout)

    def _relayout(self) -> None:
        if not self._items:
            return
        self._layout.activate()
        height = self._layout.sizeHint().height()
        self.setMinimumSize(344, 0)
        self.setMaximumSize(344, 16777215)
        self.resize(344, max(1, height))
        self.reposition()

    def reposition(self) -> None:
        parent = self.parentWidget()
        if not parent:
            return
        x = max(12, parent.width() - self.width() - 16)
        y = max(12, parent.height() - self.height() - self._bottom_margin)
        self.move(x, y)


class Scrim(QFrame):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Scrim")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class OverlayDialog(QDialog):
    """覆盖在窗口内容区上的模态卡片，替代系统标题栏弹窗。"""

    def __init__(self, parent: QWidget, title: str, subtitle: str = "", width: int = 500):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setModal(True)
        self._card_width = width
        theme = getattr(parent, "theme", None)
        palette = theme.palette if theme is not None else None
        scrim_color = "#070b10" if (theme and theme.resolved == "dark") else "#c9d3df"
        self.setStyleSheet(f"QDialog {{ background: {scrim_color}; }}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scrim = Scrim(self)
        outer.addWidget(self.scrim)

        scrim_layout = QVBoxLayout(self.scrim)
        scrim_layout.setContentsMargins(28, 28, 28, 28)
        scrim_layout.addStretch(1)

        self.card = QFrame()
        self.card.setObjectName("OverlayCard")
        self.card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.card.setFixedWidth(width)
        surface = palette["surface"] if palette else "#ffffff"
        border = palette["border"] if palette else "#d8e1eb"
        self.card.setStyleSheet(
            f"QFrame#OverlayCard {{ background: {surface}; border: 1px solid {border}; border-radius: 12px; }}"
        )
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        head = QHBoxLayout()
        head.setContentsMargins(20, 18, 20, 0)
        head.setSpacing(12)
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("DialogTitle")
        self.title_label.setWordWrap(True)
        title_col.addWidget(self.title_label)
        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setObjectName("DialogSub")
            self.subtitle_label.setWordWrap(True)
            title_col.addWidget(self.subtitle_label)
        else:
            self.subtitle_label = None
        head.addLayout(title_col, 1)
        close = make_icon_button("x", "#8495a8", "关闭", 15)
        close.clicked.connect(self.reject)
        head.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)
        card_layout.addLayout(head)
        card_layout.addSpacing(14)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(20, 0, 20, 16)
        self.body_layout.setSpacing(12)
        card_layout.addWidget(self.body, 1)

        self.footer = QFrame()
        self.footer.setObjectName("DialogFoot")
        self.footer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        if palette:
            self.footer.setStyleSheet(
                "QFrame#DialogFoot {"
                f" background: {palette['list_foot']};"
                f" border-top: 1px solid {palette['row_border']};"
                " border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;"
                "}"
            )
        self.footer_layout = QHBoxLayout(self.footer)
        self.footer_layout.setContentsMargins(20, 12, 20, 12)
        self.footer_layout.setSpacing(8)
        self.footer_layout.addStretch(1)
        card_layout.addWidget(self.footer)

        scrim_layout.addWidget(self.card, 0, Qt.AlignmentFlag.AlignHCenter)
        scrim_layout.addStretch(1)
        self.scrim.setStyleSheet(f"QFrame#Scrim {{ background: {scrim_color}; }}")
        self.scrim.clicked.connect(self.reject)
        self.setMaximumHeight(900)

    def add_footer(self, text: str, role: str, callback: Callable[[], None]) -> QPushButton:
        button = make_button(text, role, parent=self.footer)
        button.clicked.connect(callback)
        self.footer_layout.addWidget(button)
        return button

    def showEvent(self, event) -> None:  # type: ignore[override]
        parent = self.parentWidget()
        if parent:
            origin = parent.mapToGlobal(QPoint(0, 0))
            self.setGeometry(QRect(origin, parent.size()))
            self.setFixedSize(parent.size())
        super().showEvent(event)

    def exec(self) -> int:  # type: ignore[override]
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        return super().exec()


class ConfirmDialog(OverlayDialog):
    def __init__(
        self,
        parent: QWidget,
        title: str,
        message: str,
        detail: str = "",
        confirm_text: str = "确定",
        danger: bool = True,
    ):
        super().__init__(parent, title)
        body = QLabel(message)
        body.setWordWrap(True)
        body.setStyleSheet("font-size: 13px;")
        self.body_layout.addWidget(body)
        if detail:
            detail_label = QLabel(detail)
            detail_label.setObjectName("MonoPath")
            detail_label.setWordWrap(True)
            detail_label.setStyleSheet(
                "font-family: 'Cascadia Mono', Consolas, monospace; font-size: 11px;"
                " padding: 7px 9px; border-radius: 6px;"
            )
            self.body_layout.addWidget(detail_label)
        self.confirmed = False
        self.add_footer("取消", "ghost", self.reject)
        self.add_footer(confirm_text, "danger" if danger else "primary", self._accept)

    def _accept(self) -> None:
        self.confirmed = True
        self.accept()

    @classmethod
    def ask(cls, parent, title, message, detail="", confirm_text="确定", danger=True) -> bool:
        dialog = cls(parent, title, message, detail, confirm_text, danger)
        dialog.exec()
        return dialog.confirmed


class SegmentedControl(QFrame):
    changed = Signal(str)

    def __init__(self, items: list[tuple[str, str, str]], parent=None):
        super().__init__(parent)
        self.setObjectName("Seg")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}
        self._icon_names: dict[str, str] = {}
        for key, text, icon_name in items:
            button = QPushButton(text)
            button.setObjectName("SegBtn")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setIcon(icon(icon_name, "#8495a8", 14))
            button.setIconSize(QSize(14, 14))
            button.clicked.connect(lambda checked=False, value=key: self.changed.emit(value))
            self._group.addButton(button)
            layout.addWidget(button)
            self._buttons[key] = button
            self._icon_names[key] = icon_name

    def set_value(self, key: str) -> None:
        button = self._buttons.get(key)
        if button:
            button.setChecked(True)

    def value(self) -> str:
        for key, button in self._buttons.items():
            if button.isChecked():
                return key
        return ""

    def refresh_icons(self, color: str) -> None:
        for key, button in self._buttons.items():
            button.setIcon(icon(self._icon_names[key], color, 14))


class AccentItem(QFrame):
    clicked = Signal(str)

    def __init__(self, key: str, name: str, color: str, parent=None):
        super().__init__(parent)
        self.key = key
        self._color = color
        self.setObjectName("AccentItem")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(64)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 7, 4, 6)
        layout.setSpacing(6)
        self.circle = QLabel()
        self.circle.setFixedSize(24, 24)
        self.circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.circle.setStyleSheet(f"background: {color}; border-radius: 12px;")
        self.check = QLabel(self.circle)
        self.check.setPixmap(icon("check", "#ffffff", 12).pixmap(12, 12))
        self.check.setFixedSize(12, 12)
        self.check.setGeometry(6, 6, 12, 12)
        self.check.setStyleSheet("background: transparent;")
        self.check.hide()
        layout.addWidget(self.circle, 0, Qt.AlignmentFlag.AlignHCenter)
        label = QLabel(name)
        label.setObjectName("AccentName")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.check.setVisible(selected)
        repolish(self)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)
        super().mouseReleaseEvent(event)


class ModeTile(QFrame):
    def __init__(self, icon_name: str, title: str, subtitle: str, parent=None):
        super().__init__(parent)
        self.setObjectName("ModeTile")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(9, 8, 9, 8)
        layout.setSpacing(7)
        icon_label = QLabel()
        icon_label.setPixmap(icon(icon_name, "#8c9eb3", 14).pixmap(14, 14))
        icon_label.setFixedSize(14, 14)
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(1)
        title_label = QLabel(title)
        title_label.setObjectName("ModeTitle")
        sub_label = QLabel(subtitle)
        sub_label.setObjectName("ModeSub")
        text_col.addWidget(title_label)
        text_col.addWidget(sub_label)
        layout.addLayout(text_col, 1)


def pretty_time(timestamp: float) -> str:
    if not timestamp:
        return "—"
    now = datetime.now()
    dt = datetime.fromtimestamp(timestamp)
    delta = now - dt
    seconds = max(0, int(delta.total_seconds()))
    if seconds < 60:
        return "刚刚"
    if seconds < 3600:
        return f"{seconds // 60} 分钟前"
    if dt.date() == now.date():
        return f"今天 {dt:%H:%M}"
    if (now.date() - dt.date()).days == 1:
        return f"昨天 {dt:%H:%M}"
    if dt.year == now.year:
        return f"{dt.month}月{dt.day}日"
    return dt.strftime("%Y-%m-%d")


def open_folder(path: str) -> None:
    try:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
    except Exception:
        pass
