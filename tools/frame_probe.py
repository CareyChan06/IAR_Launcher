"""开发用：真实桌面上验证沉浸标题栏的点击/双击/拖动/缩放/切换行为。

用法：python tools/frame_probe.py [输出目录]

注入方式：SendInput（MOVE|ABSOLUTE|VIRTUALDESK），按虚拟桌面边界归一化，
兼容多显示器。前台用 ALT 键技巧解除后台进程的 SetForegroundWindow 限制。
每步输出 PASS/FAIL/MANUAL；命中测试（SendMessageW）不依赖真实输入，始终
确定性验证；输入注入不可用时（前台被抢等）标记 MANUAL，由人工点击验证。
"""
from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QPoint, QTimer
from PySide6.QtWidgets import QApplication

from iar_launcher.core.config import ConfigStore
from iar_launcher.ui.app import _load_fonts
from iar_launcher.ui.main_window import MainWindow
from iar_launcher.ui.theme import ThemeController

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()

VK_MENU = 0x12
HTCAPTION, HTCLIENT = 2, 1
HTTOP, HTLEFT, HTRIGHT, HTBOTTOM = 12, 10, 11, 15
HTTOPLEFT, HTTOPRIGHT, HTBOTTOMLEFT, HTBOTTOMRIGHT = 13, 14, 16, 17
SPI_GETWORKAREA = 0x0030


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    _fields_ = [("type", wintypes.DWORD), ("union", _U)]


VS_X = user32.GetSystemMetrics(76)   # 虚拟桌面原点/尺寸（含所有显示器）
VS_Y = user32.GetSystemMetrics(77)
VS_W = user32.GetSystemMetrics(78)
VS_H = user32.GetSystemMetrics(79)


def send_input(x: int, y: int, flags: int) -> int:
    inp = INPUT()
    inp.type = 0
    inp.union.mi.dx, inp.union.mi.dy, inp.union.mi.flags = x, y, flags
    return user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


def move_to(gx: int, gy: int) -> None:
    nx = int((gx - VS_X) * 65535 / max(VS_W - 1, 1))
    ny = int((gy - VS_Y) * 65535 / max(VS_H - 1, 1))
    send_input(nx, ny, 0x0001 | 0x8000 | 0x4000)  # MOVE|ABSOLUTE|VIRTUALDESK


def phys(widget, lx: int, ly: int) -> tuple[int, int]:
    dpr = widget.window().devicePixelRatio()
    g = widget.mapToGlobal(QPoint(lx, ly))
    return int(g.x() * dpr), int(g.y() * dpr)


def click(widget, lx: int | None = None, ly: int | None = None) -> None:
    lx = widget.width() // 2 if lx is None else lx
    ly = widget.height() // 2 if ly is None else ly
    x, y = phys(widget, lx, ly)
    move_to(x, y)
    time.sleep(0.08)
    send_input(0, 0, 0x0002)  # LBUTTONDOWN
    time.sleep(0.06)
    send_input(0, 0, 0x0004)  # LEFTUP


def double_click(widget) -> None:
    click(widget)
    time.sleep(0.06)
    send_input(0, 0, 0x0002)
    time.sleep(0.06)
    send_input(0, 0, 0x0004)


def drag_to(x: int, y: int, dx: int, dy: int) -> None:
    move_to(x, y)
    time.sleep(0.1)
    send_input(0, 0, 0x0002)
    time.sleep(0.15)
    for step in range(1, 7):
        move_to(x + dx * step // 6, y + dy * step // 6)
        time.sleep(0.05)
    move_to(x + dx, y + dy)
    time.sleep(0.1)
    send_input(0, 0, 0x0004)
    time.sleep(0.2)


def hit_test(hwnd: int, gx: int, gy: int) -> int:
    lp = ((gy & 0xFFFF) << 16) | (gx & 0xFFFF)
    return user32.SendMessageW(hwnd, 0x0084, 0, lp)


app = QApplication(sys.argv)
app.setStyle("Fusion")
sans, mono = _load_fonts()
store = ConfigStore()
theme = ThemeController(store, app, sans, mono)
window = MainWindow(store, theme)
window._first_run_checked = True
window.show()

passed: list[str] = []


def report(name: str, ok: bool, detail: str = "") -> None:
    line = f"{'PASS' if ok else 'FAIL'} {name} {detail}".rstrip()
    passed.append(line)
    print(line, flush=True)


def manual(name: str, detail: str = "") -> None:
    line = f"MANUAL {name} {detail}".rstrip()
    passed.append(line)
    print(line, flush=True)


def focus() -> bool:
    """强制把窗口带到前台并确认；返回注入是否可用（窗口确实可见在最前）。"""
    hwnd = int(window.winId())
    user32.keybd_event(VK_MENU, 0, 0, 0)
    user32.SetForegroundWindow(hwnd)
    user32.keybd_event(VK_MENU, 0, 2, 0)
    window.raise_()
    window.activateWindow()
    time.sleep(0.3)
    cx = int((window.x() + window.width() // 2) * window.devicePixelRatio())
    cy = int((window.y() + window.height() // 2) * window.devicePixelRatio())
    under = int(user32.WindowFromPoint(wintypes.POINT(cx, cy)) or 0)
    return under == hwnd


def reset_position() -> None:
    if window.isMaximized() or window.isMinimized():
        window.showNormal()
    window.move(300, 80)
    time.sleep(0.1)


def caption_point() -> tuple[int, int]:
    """标题条上确定属于 HTCAPTION 的一点：按钮区之外、边框带之下。"""
    lx = max(20, (window.width() - window.title_bar.button_zone_width()) // 2)
    ly = window.title_bar.height() // 2
    return phys(window.title_bar, lx, ly)


def work_area() -> wintypes.RECT:
    rc = wintypes.RECT()
    user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rc), 0)
    return rc


def run_steps() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "preview")

    # 0. 初始状态截图
    reset_position()
    ok_front = focus()
    window.grab().save(str(Path(out) / "probe-client.png"))

    # 1. 命中测试（确定性，无需真实输入）：四角/四边/caption/按钮区
    hwnd = int(window.winId())
    b = window._frame._border()
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    cx = (rect.left + rect.right) // 2
    checks = [
        ("hit top-left corner", hit_test(hwnd, rect.left + 2, rect.top + 2), HTTOPLEFT),
        ("hit top-right corner", hit_test(hwnd, rect.right - 2, rect.top + 2), HTTOPRIGHT),
        ("hit bottom-left corner", hit_test(hwnd, rect.left + 2, rect.bottom - 2), HTBOTTOMLEFT),
        ("hit bottom-right corner", hit_test(hwnd, rect.right - 2, rect.bottom - 2), HTBOTTOMRIGHT),
        ("hit top edge", hit_test(hwnd, cx, rect.top + b // 2), HTTOP),
        ("hit left edge", hit_test(hwnd, rect.left + b // 2, (rect.top + rect.bottom) // 2), HTLEFT),
        ("hit right edge", hit_test(hwnd, rect.right - b // 2, (rect.top + rect.bottom) // 2), HTRIGHT),
        ("hit bottom edge", hit_test(hwnd, cx, rect.bottom - b // 2), HTBOTTOM),
        ("hit caption band", hit_test(hwnd, *caption_point()), HTCAPTION),
        ("hit center client", hit_test(hwnd, cx, rect.bottom - 100), HTCLIENT),
    ]
    btn_x, btn_y = phys(window.title_bar.close_button,
                        window.title_bar.close_button.width() // 2,
                        window.title_bar.close_button.height() // 2)
    checks.append(("hit close button zone", hit_test(hwnd, btn_x, btn_y), HTCLIENT))
    for name, got, want in checks:
        report(name, got == want, f"got={got} want={want}")

    if not ok_front:
        manual("front-window acquisition failed; click tests need manual run",
               "请手动验证：最小化/双击最大化/拖动/边缘缩放/最大化按钮/关闭按钮")
        print("SUMMARY: HIT-TEST DONE, INPUT MANUAL")
        app.quit()
        return

    # 2. 最小化按钮
    focus()
    click(window.title_bar.min_button)
    time.sleep(0.4)
    ok = window.isMinimized()
    report("min_button", ok)
    window.showNormal()
    focus()

    # 3. 双击标题条最大化 / 再双击还原；最大化范围 = 工作区（不遮任务栏）
    double_click(window.title_bar)
    time.sleep(0.5)
    ok1 = window.isMaximized()
    if ok1:
        window.grab().save(str(Path(out) / "probe-maximized-client.png"))
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        wa = work_area()
        fit = (abs(rect.left - wa.left) <= 2 and abs(rect.top - wa.top) <= 2
               and abs(rect.right - wa.right) <= 2 and abs(rect.bottom - wa.bottom) <= 2)
        report("maximize fits work area (no taskbar cover)", fit,
               f"rect=({rect.left},{rect.top},{rect.right},{rect.bottom}) work=({wa.left},{wa.top},{wa.right},{wa.bottom})")
    double_click(window.title_bar)
    time.sleep(0.5)
    ok2 = not window.isMaximized()
    report("caption double-click maximize/restore", ok1 and ok2, f"max={ok1} restore={ok2}")

    # 4. 拖动标题条
    reset_position()
    focus()
    before = (window.x(), window.y())
    x, y = caption_point()
    drag_to(x, y, 120, 60)
    after = (window.x(), window.y())
    report(
        "caption drag",
        abs(after[0] - before[0] - 120) <= 4 and abs(after[1] - before[1] - 60) <= 4,
        f"{before} -> {after}",
    )

    # 5. 右边缘拖动调整宽度
    reset_position()
    focus()
    before_w = window.width()
    dpr = window.devicePixelRatio()
    x, y = int((window.x() + window.width() + 4) * dpr), int((window.y() + window.height() // 2) * dpr)
    drag_to(x, y, 80, 0)
    after_w = window.width()
    report("edge resize", after_w >= before_w + 60, f"{before_w} -> {after_w}")

    # 6. 最大化按钮 + 图标切换
    reset_position()
    focus()
    click(window.title_bar.max_button)
    time.sleep(0.5)
    ok = window.isMaximized() and window.title_bar._maximized
    report("max button + glyph", ok)
    click(window.title_bar.max_button)  # 还原（restore 图标）
    time.sleep(0.5)
    report("restore button", not window.isMaximized())

    # 7. 切换到原生标题栏
    reset_position()
    window.set_titlebar_mode("native")
    time.sleep(0.6)
    report("toggle native", not window.title_bar.isVisible())
    window.grab().save(str(Path(out) / "probe-native-client.png"))

    # 8. 切回沉浸并确认 caption 仍有效
    window.set_titlebar_mode("custom")
    time.sleep(0.6)
    ok_visible = window.title_bar.isVisible() and window._frame.active
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    cap_ok = hit_test(hwnd, (rect.left + rect.right) // 2,
                      rect.top + window.title_bar.height() // 2 + 2) == HTCAPTION
    report("toggle custom + caption hit", ok_visible and cap_ok, f"visible={ok_visible} caption={cap_ok}")

    # 9. 关闭按钮
    focus()
    click(window.title_bar.close_button)
    time.sleep(0.5)
    report("close_button", not window.isVisible())

    fails = [l for l in passed if l.startswith("FAIL")]
    print("SUMMARY:", "ALL PASS" if not fails else f"{len(fails)} FAIL")
    app.quit()


QTimer.singleShot(1200, run_steps)
QTimer.singleShot(25000, app.quit)  # 安全兜底
app.exec()
