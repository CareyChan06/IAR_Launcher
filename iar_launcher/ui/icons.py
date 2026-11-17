"""SVG 图标工厂（与 HTML 预览同一套线条图标）。"""
from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

PATHS = {
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
    "folder-plus": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/><path d="M12 11.5v6M9 14.5h6"/>',
    "folder-open": '<path d="M3 8V6a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v1"/><path d="M3 9h18l-2.2 9.1a2 2 0 0 1-1.9 1.5H5.9a2 2 0 0 1-1.9-1.5Z"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.6-3.6"/>',
    "star": '<path d="m12 3 2.7 5.5 6 .9-4.3 4.2 1 6-5.4-2.8-5.4 2.8 1-6L3.3 9.4l6-.9Z"/>',
    "more": '<circle cx="5" cy="12" r="1.3" fill="{color}" stroke="none"/><circle cx="12" cy="12" r="1.3" fill="{color}" stroke="none"/><circle cx="19" cy="12" r="1.3" fill="{color}" stroke="none"/>',
    "trash": '<path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/><path d="M10 11v5M14 11v5"/>',
    "x": '<path d="M6 6l12 12M18 6 6 18"/>',
    "check": '<path d="m5 13 4 4L19 7"/>',
    "alert": '<path d="M12 3 2.7 20h18.6Z"/><path d="M12 9.5v4.5M12 17.1h.01"/>',
    "lock": '<rect x="4.5" y="10" width="15" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    "scan": '<path d="M19.1 4.9A10 10 0 1 0 21 12"/><path d="M15.5 8.5A5 5 0 1 0 17 12"/><path d="m12 12 7-7"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "pencil": '<path d="M4 20h4L20 8l-4-4L4 16Z"/><path d="m14 6 4 4"/>',
    "chevron": '<path d="m6 9 6 6 6-6"/>',
    "chip": '<rect x="7" y="7" width="10" height="10" rx="2"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    "copy": '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
    "external": '<path d="M14 3h7v7"/><path d="M21 3 11 13"/><path d="M18 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h5"/>',
    "monitor": '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
    "terminal": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="m7 9 3 3-3 3M13 15h4"/>',
    "mouse": '<rect x="6" y="3" width="12" height="18" rx="6"/><path d="M12 7v4"/>',
    "settings": '<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="9" cy="6" r="2"/><circle cx="15" cy="12" r="2"/><circle cx="8" cy="18" r="2"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "moon": '<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z"/>',
    "palette": '<circle cx="12" cy="12" r="9"/><circle cx="8" cy="9" r="1.1" fill="{color}" stroke="none"/><circle cx="12" cy="7" r="1.1" fill="{color}" stroke="none"/><circle cx="16" cy="9" r="1.1" fill="{color}" stroke="none"/><path d="M12 21a3 3 0 0 1 0-6h3a4 4 0 0 0 0-8"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    "refresh": '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    "min": '<path d="M5 12h14"/>',
    "max": '<rect x="5" y="5" width="14" height="14" rx="1"/>',
    "win-min": '<path d="M4.5 12h15"/>',
    "win-max": '<rect x="5.5" y="5.5" width="13" height="13" rx="1.2"/>',
    "win-restore": '<rect x="8" y="4.5" width="11.5" height="11.5" rx="1.2"/><path d="M4.5 8.5v9a2 2 0 0 0 2 2h9"/>',
    "window": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 8.5h18"/>',
    "link": '<path d="M10 13.5a4.5 4.5 0 0 0 6.36 0l2.5-2.5a4.5 4.5 0 0 0-6.36-6.36L11.1 6.4"/><path d="M14 10.5a4.5 4.5 0 0 0-6.36 0l-2.5 2.5a4.5 4.5 0 0 0 6.36 6.36l1.39-1.4"/>',
}
FILL_PATHS = {"star"}
FILLED = {"star", "moon"}


def _color(value: str) -> str:
    return value if value.startswith("#") else value


@lru_cache(maxsize=1024)
def icon(
    name: str,
    color: str = "#8495a8",
    size: int = 16,
    filled: bool | None = None,
    stroke: float = 1.8,
) -> QIcon:
    paths = PATHS.get(name, "")
    paths = paths.replace("{color}", color)
    if filled is None:
        filled = name in FILL_PATHS
    fill = color if filled else "none"
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
        f'fill="{fill}" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">'
        f"{paths}</svg>"
    )
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    screen = QGuiApplication.primaryScreen()
    ratio = screen.devicePixelRatio() if screen else 1.0
    pixmap = QPixmap(int(size * ratio), int(size * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    if renderer.isValid():
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
    return QIcon(pixmap)
