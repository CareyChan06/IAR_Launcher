"""自绘标题栏：左侧留空（整条可拖动），右侧最小化/最大化/关闭按钮，跟随主题。

窗口的拖动、贴边吸附、双击最大化由 winchrome 的 WM_NCHITTEST（HTCAPTION）
接管，这里只负责右侧按钮的点击。
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QToolButton,
    QWidget,
)

from .icons import icon

BAR_HEIGHT = 34
BUTTON_WIDTH = 46
BUTTON_ICON = 14
BUTTON_STROKE = 1.6


class _HoverCloseFilter(QObject):
    """关闭按钮 hover 时切换为白色描边图标（背景由 QSS 染红）。"""

    def __init__(self, button: QToolButton, normal: QIcon, hot: QIcon):
        super().__init__(button)
        self.button = button
        self.normal = normal
        self.hot = hot

    def eventFilter(self, watched, event) -> bool:
        if watched is self.button:
            et = event.type()
            if et == event.Type.Enter:
                self.button.setIcon(self.hot)
            elif et == event.Type.Leave:
                self.button.setIcon(self.normal)
        return False


class TitleBar(QWidget):
    minimize_requested = Signal()
    toggle_maximize_requested = Signal()
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(BAR_HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addStretch(1)

        self._glyph_color = "#5c6e83"
        self._maximized = False
        self.min_button = self._make_button("win-min", "最小化")
        self.max_button = self._make_button("win-max", "最大化")
        self.close_button = self._make_button("x", "关闭", close=True)
        for button in (self.min_button, self.max_button, self.close_button):
            layout.addWidget(button, 0, Qt.AlignmentFlag.AlignTop)

    def _make_button(self, glyph: str, tooltip: str, close: bool = False) -> QToolButton:
        button = QToolButton()
        button.setObjectName("WinClose" if close else "WinButton")
        button.setFixedSize(BUTTON_WIDTH, BAR_HEIGHT)
        button.setIcon(icon(glyph, self._glyph_color, BUTTON_ICON, stroke=BUTTON_STROKE))
        button.setIconSize(QSize(BUTTON_ICON, BUTTON_ICON))
        button.setCursor(Qt.CursorShape.ArrowCursor)
        button.setToolTip(tooltip)
        button.setAutoRaise(True)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if close:
            normal = icon(glyph, self._glyph_color, BUTTON_ICON, stroke=BUTTON_STROKE)
            hot = icon(glyph, "#ffffff", BUTTON_ICON, stroke=BUTTON_STROKE)
            filter_holder = _HoverCloseFilter(button, normal, hot)
            button.installEventFilter(filter_holder)
            button._hover_filter = filter_holder  # 防止被 GC
            button.clicked.connect(self.close_requested.emit)
        elif glyph == "win-min":
            button.clicked.connect(self.minimize_requested.emit)
        else:
            button.clicked.connect(self.toggle_maximize_requested.emit)
        return button

    # ── 状态与主题 ──
    def set_maximized(self, maximized: bool) -> None:
        if maximized == self._maximized:
            return
        self._maximized = maximized
        glyph = "win-restore" if maximized else "win-max"
        tip = "还原" if maximized else "最大化"
        self.max_button.setIcon(icon(glyph, self._glyph_color, BUTTON_ICON, stroke=BUTTON_STROKE))
        self.max_button.setToolTip(tip)

    def refresh(self, palette: dict) -> None:
        self._glyph_color = palette["text2"]
        normal_max = icon(
            "win-restore" if self._maximized else "win-max",
            self._glyph_color,
            BUTTON_ICON,
            stroke=BUTTON_STROKE,
        )
        self.min_button.setIcon(icon("win-min", self._glyph_color, BUTTON_ICON, stroke=BUTTON_STROKE))
        self.max_button.setIcon(normal_max)
        self.close_button.setIcon(icon("x", self._glyph_color, BUTTON_ICON, stroke=BUTTON_STROKE))
        close_filter = getattr(self.close_button, "_hover_filter", None)
        if close_filter is not None:
            close_filter.normal = icon("x", self._glyph_color, BUTTON_ICON, stroke=BUTTON_STROKE)
            close_filter.hot = icon("x", "#ffffff", BUTTON_ICON, stroke=BUTTON_STROKE)

    # ── 供 winchrome 命中测试使用 ──
    def button_zone_width(self) -> int:
        """右侧三个按钮占据的宽度（逻辑像素），该区域不做caption拖动。"""
        return BUTTON_WIDTH * 3
