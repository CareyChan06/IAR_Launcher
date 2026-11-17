"""Windows 标题栏主题（DWM）与沉浸框架（自绘标题栏）。

沉浸模式保留 WS_THICKFRAME/WS_CAPTION 窗口样式，只通过 WM_NCCALCSIZE 把
非客户区“掏空”，再用 WM_NCHITTEST 把顶部条声明为 HTCAPTION、外圈声明为
调整大小带。这样阴影、圆角、贴边吸附、Win+方向键、双击最大化等行为全部
保持原生，仅标题栏本身由应用自绘（VSCode/Chromium 同款方案）。
"""
from __future__ import annotations

import ctypes
import os
import sys
import traceback
from ctypes import wintypes

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor

IS_WINDOWS = sys.platform == "win32"

_DEBUG_LOG = os.environ.get("IAR_FRAME_DEBUG", "")


def _dbg(text: str) -> None:
    if not _DEBUG_LOG:
        return
    try:
        with open(_DEBUG_LOG, "a", encoding="utf-8") as handle:
            handle.write(text + "\n")
    except OSError:
        pass

WM_NCCALCSIZE = 0x0031
WM_NCHITTEST = 0x0084
WM_GETMINMAXINFO = 0x0024

HTCLIENT = 1
HTCAPTION = 2
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17

GWL_STYLE = -16
WS_POPUP = 0x80000000
WS_CHILD = 0x40000000
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_SYSMENU = 0x00080000
SM_CXSIZEFRAME = 32
SM_CXPADDEDBORDER = 92
MONITOR_DEFAULTTONEAREST = 2


class _MINMAXINFO(ctypes.Structure):
    _fields_ = [
        ("ptReserved", wintypes.POINT),
        ("ptMaxSize", wintypes.POINT),
        ("ptMaxPosition", wintypes.POINT),
        ("ptMinTrackSize", wintypes.POINT),
        ("ptMaxTrackSize", wintypes.POINT),
    ]


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_FRAMECHANGED = 0x0020


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_size_t),
        ("lParam", ctypes.c_ssize_t),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


class _NCCALCSIZE_PARAMS(ctypes.Structure):
    _fields_ = [
        ("rgrc", wintypes.RECT * 3),
        ("lppos", ctypes.c_void_p),
    ]


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


class WindowsFrame:
    """挂在 QMainWindow.nativeEvent 上的原生框架控制器。"""

    def __init__(self, window):
        self.window = window
        self.active = False

    # ── 开关 ──
    def set_active(self, on: bool) -> None:
        on = bool(on and IS_WINDOWS)
        changed = on != self.active
        self.active = on
        if IS_WINDOWS and (changed or on):
            self._refresh_frame()

    def _refresh_frame(self) -> None:
        """Qt 的 FramelessWindowHint 会去掉全部原生样式；这里把
        WS_THICKFRAME 等加回去（非客户区已被 NCCALCSIZE 掏空），
        从而保住阴影、贴边吸附、Win+方向键、Aero 预览等原生行为。"""
        try:
            hwnd = int(self.window.winId())
            user32 = ctypes.windll.user32
            if self.active:
                # 必须在无符号 32 位空间做位运算：带 WS_POPUP 的样式作为
                # Python 负数参与 ~ 运算会产生超界值（ctypes OverflowError）。
                style = user32.GetWindowLongW(hwnd, GWL_STYLE) & 0xFFFFFFFF
                style &= 0xFFFFFFFF & ~(WS_POPUP | WS_CHILD | WS_CAPTION)
                style |= WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU
                user32.SetWindowLongW(
                    hwnd, GWL_STYLE,
                    ctypes.c_long(style if style < 0x80000000 else style - 0x100000000),
                )
            user32.SetWindowPos(
                hwnd, 0, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED,
            )
        except Exception:
            if _DEBUG_LOG:
                _dbg(f"refresh_frame failed: {traceback.format_exc()}")

    # ── 几何工具 ──
    def _border(self) -> int:
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(SM_CXSIZEFRAME) + user32.GetSystemMetrics(SM_CXPADDEDBORDER)

    # ── 消息处理：返回 (handled, result) ──
    def handle(self, message: int) -> tuple[bool, int]:
        if not self.active:
            return False, 0
        try:
            msg = ctypes.cast(int(message), ctypes.POINTER(_MSG)).contents
        except Exception:
            return False, 0
        if _DEBUG_LOG:
            _dbg(f"msg 0x{msg.message:04X} hwnd={int(msg.hwnd) if msg.hwnd else 0}")

        if msg.message == WM_NCCALCSIZE:
            if msg.wParam != 1:
                return False, 0
            # 客户区 = 整个窗口矩形（非客户区完全掏空），
            # 边缘调整大小与 caption 判定全部由 WM_NCHITTEST 自己声明。
            return True, 0
        if msg.message == WM_NCHITTEST:
            return self._on_nchittest(msg)
        if msg.message == WM_GETMINMAXINFO:
            return self._on_getminmaxinfo(msg)
        return False, 0

    # 最大化范围 = 显示器工作区（不遮任务栏），配合无内缩的客户区正好铺满。
    def _on_getminmaxinfo(self, msg: _MSG) -> tuple[bool, int]:
        try:
            user32 = ctypes.windll.user32
            info = ctypes.cast(msg.lParam, ctypes.POINTER(_MINMAXINFO)).contents
            hwnd = int(msg.hwnd)
            mon = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
            mi = _MONITORINFO()
            mi.cbSize = ctypes.sizeof(_MONITORINFO)
            if not mon or not user32.GetMonitorInfoW(mon, ctypes.byref(mi)):
                return False, 0
            work, area = mi.rcWork, mi.rcMonitor
            info.ptMaxPosition.x = work.left - area.left
            info.ptMaxPosition.y = work.top - area.top
            info.ptMaxSize.x = work.right - work.left
            info.ptMaxSize.y = work.bottom - work.top
            # 我们自己截获了 WM_GETMINMAXINFO，Qt 的 setMinimumSize 不会再生效，
            # 最小跟踪尺寸必须在这里同步给系统（逻辑像素 × DPR）。
            dpr = self.window.devicePixelRatioF()
            info.ptMinTrackSize.x = max(1, int(self.window.minimumWidth() * dpr))
            info.ptMinTrackSize.y = max(1, int(self.window.minimumHeight() * dpr))
            _dbg(f"minmaxinfo max=({info.ptMaxSize.x},{info.ptMaxSize.y}) pos=({info.ptMaxPosition.x},{info.ptMaxPosition.y}) min=({info.ptMinTrackSize.x},{info.ptMinTrackSize.y})")
            return True, 0
        except Exception:
            return False, 0

    # 外圈 = 调整大小带；顶部标题条 = HTCAPTION（拖动/吸附/双击最大化全原生）。
    def _on_nchittest(self, msg: _MSG) -> tuple[bool, int]:
        try:
            user32 = ctypes.windll.user32
            hwnd = int(msg.hwnd)
            lp = int(msg.lParam) & 0xFFFFFFFF  # 低16位=x，高16位=y（有符号）
            x = ctypes.c_short(lp & 0xFFFF).value
            y = ctypes.c_short((lp >> 16) & 0xFFFF).value
            rect = wintypes.RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return False, 0
            b = self._border()
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            if self.active and not (style & WS_THICKFRAME):
                # 自愈：Qt 可能在窗口操作中把样式重置回 frameless，
                # 延迟补一次（同步改样式会递归触发命中测试）。
                QTimer.singleShot(0, self._refresh_frame)
            # 注意：WS_MAXIMIZE 与 WS_MAXIMIZEBOX 值相同（0x00010000），
            # 用样式位判断最大化永远为真，必须用 IsZoomed。
            maximized = bool(user32.IsZoomed(hwnd))

            if not maximized:
                left = x < rect.left + b
                right = x >= rect.right - b
                top = y < rect.top + b
                bottom = y >= rect.bottom - b
                if top and left:
                    _dbg(f"hit HTTOPLEFT {x},{y}")
                    return True, HTTOPLEFT
                if top and right:
                    _dbg(f"hit HTTOPRIGHT {x},{y}")
                    return True, HTTOPRIGHT
                if bottom and left:
                    _dbg(f"hit HTBOTTOMLEFT {x},{y}")
                    return True, HTBOTTOMLEFT
                if bottom and right:
                    _dbg(f"hit HTBOTTOMRIGHT {x},{y}")
                    return True, HTBOTTOMRIGHT
                if top:
                    _dbg(f"hit HTTOP {x},{y}")
                    return True, HTTOP
                if bottom:
                    _dbg(f"hit HTBOTTOM {x},{y}")
                    return True, HTBOTTOM
                if left:
                    _dbg(f"hit HTLEFT {x},{y}")
                    return True, HTLEFT
                if right:
                    _dbg(f"hit HTRIGHT {x},{y}")
                    return True, HTRIGHT

            bar = getattr(self.window, "title_bar", None)
            if bar is not None and bar.isVisible():
                dpr = self.window.devicePixelRatioF()
                bar_h = int(bar.height() * dpr)
                zone = int(bar.button_zone_width() * dpr)
                if rect.top + b <= y < rect.top + bar_h and x < rect.right - zone:
                    _dbg(f"hit HTCAPTION {x},{y} band=({rect.top + b},{rect.top + bar_h}) zone_x={rect.right - zone}")
                    return True, HTCAPTION
                _dbg(f"miss caption {x},{y} rect={rect.left},{rect.top},{rect.right},{rect.bottom} band=({rect.top + b},{rect.top + bar_h}) zone_x={rect.right - zone}")
            return False, 0
        except Exception:
            return False, 0
