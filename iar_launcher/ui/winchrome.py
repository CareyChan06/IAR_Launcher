"""Windows 原生标题栏跟随应用主题（DWM）。"""
from __future__ import annotations

import ctypes

from PySide6.QtGui import QColor


def _colorref(color: str) -> int:
    value = QColor(color)
    return value.red() | (value.green() << 8) | (value.blue() << 16)


def apply_titlebar_theme(widget, dark: bool, chrome: str, text: str, border: str) -> None:
    """在 Windows 10/11 上设置沉浸式深色标题栏与标题栏颜色。"""
    try:
        hwnd = int(widget.winId())
        dwm = ctypes.windll.dwmapi
        value = ctypes.c_int(1 if dark else 0)
        for attribute in (20, 19):  # Win11 / Win10 1809+
            if dwm.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)
            ) == 0:
                break
        for attribute, color in ((35, chrome), (36, text), (34, border)):
            value = ctypes.c_uint(_colorref(color))
            dwm.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value))
    except Exception:
        # 非 Windows 或旧系统：保持系统默认标题栏。
        pass
