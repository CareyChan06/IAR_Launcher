"""主题令牌、QSS 生成与运行时主题控制。"""
from __future__ import annotations

from string import Template

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

from ..core.config import ConfigStore
from ..core.paths import asset_dir

LIGHT = {
    "app": "#eef3f9",
    "main": "#f4f7fb",
    "surface": "#ffffff",
    "surface2": "#f4f7fb",
    "surface3": "#eaf0f7",
    "chrome": "#e9eef4",
    "border": "#d8e1eb",
    "border_strong": "#c4d0dd",
    "text": "#172433",
    "text2": "#5c6e83",
    "text3": "#8495a8",
    "row_hover": "#f7fafd",
    "row_border": "#edf3f9",
    "group_border": "#e6edf5",
    "list_foot": "#fafcfe",
    "note": "#f4f7fb",
    "note_border": "#e6edf5",
    "mode": "#fafcfe",
    "placeholder": "#98a9bd",
    "control": "#c4d0dd",
    "control_hover": "#9fb1c5",
    "nav_hover": "#e2eaf3",
    "nav_count": "#dfe8f1",
    "path": "#7d8ea3",
    "ok": "#11865a",
    "ok_soft": "rgba(17,134,90,0.09)",
    "ok_line": "rgba(17,134,90,0.28)",
    "warn": "#a86a00",
    "warn_soft": "rgba(168,106,0,0.09)",
    "warn_line": "rgba(168,106,0,0.26)",
    "danger": "#c73535",
    "danger_soft": "rgba(199,53,53,0.08)",
    "missing_bg": "#faf8f2",
    "toast": "rgba(255,255,255,0.96)",
    "toast_border": "rgba(196,208,221,0.95)",
    "scrim": "rgba(12,16,22,0.46)",
    "selection": "#f4cfc9",
    "chain": {
        "ARM": ("rgba(199,53,53,0.08)", "#a5372c"),
        "RX": ("rgba(46,89,167,0.09)", "#2e59a7"),
        "RH850": ("rgba(168,106,0,0.09)", "#8a5a12"),
        "RL78": ("rgba(17,134,90,0.09)", "#326d47"),
        "RISC-V": ("rgba(105,70,184,0.09)", "#5a4b96"),
        "MSP430": ("rgba(92,110,131,0.10)", "#4b5566"),
        "CUSTOM": ("rgba(92,110,131,0.10)", "#5c6e83"),
    },
}
DARK = {
    "app": "#090e14",
    "main": "#0b1118",
    "surface": "#0d141e",
    "surface2": "#111a26",
    "surface3": "#162130",
    "chrome": "#090e14",
    "border": "#1c2837",
    "border_strong": "#2a3a4d",
    "text": "#e7eef8",
    "text2": "#b3c2d2",
    "text3": "#8c9eb3",
    "row_hover": "#111a26",
    "row_border": "#15202e",
    "group_border": "#182433",
    "list_foot": "#0a1017",
    "note": "#101924",
    "note_border": "#1b2938",
    "mode": "#101924",
    "placeholder": "#6d7f93",
    "control": "#2a3a4d",
    "control_hover": "#3d5168",
    "nav_hover": "#121c29",
    "nav_count": "#162130",
    "path": "#8c9eb3",
    "ok": "#3fd68c",
    "ok_soft": "rgba(63,214,140,0.10)",
    "ok_line": "rgba(63,214,140,0.28)",
    "warn": "#f2b544",
    "warn_soft": "rgba(242,181,68,0.10)",
    "warn_line": "rgba(242,181,68,0.28)",
    "danger": "#ff6060",
    "danger_soft": "rgba(255,96,96,0.10)",
    "missing_bg": "#1b1a16",
    "toast": "rgba(13,20,30,0.96)",
    "toast_border": "rgba(42,58,77,0.95)",
    "scrim": "rgba(0,0,0,0.58)",
    "selection": "#274c8f",
    "chain": {
        "ARM": ("rgba(255,96,96,0.12)", "#ff8f8f"),
        "RX": ("rgba(79,132,255,0.14)", "#9db9ff"),
        "RH850": ("rgba(242,181,68,0.12)", "#f2c470"),
        "RL78": ("rgba(63,214,140,0.12)", "#6fe0a8"),
        "RISC-V": ("rgba(177,140,255,0.14)", "#c9b0ff"),
        "MSP430": ("rgba(140,158,179,0.12)", "#b3c2d2"),
        "CUSTOM": ("rgba(140,158,179,0.12)", "#b3c2d2"),
    },
}

ACCENTS = {
    "red": {
        "name": "朱红",
        "light": {"bg": "#c62f26", "hover": "#ad251d", "soft": "#fbeae7", "line": "#f0c8c2", "text": "#a52b22", "swatch": "#c62f26"},
        "dark": {"bg": "#c9382d", "hover": "#dd4a3e", "soft": "rgba(201,56,45,0.18)", "line": "rgba(220,90,80,0.34)", "text": "#f09a90", "swatch": "#c62f26"},
    },
    "teal": {
        "name": "青绿",
        "light": {"bg": "#0f766e", "hover": "#0b5f59", "soft": "#e3f2ef", "line": "#b9ddd6", "text": "#0b5f59", "swatch": "#0f766e"},
        "dark": {"bg": "#0c7c72", "hover": "#119186", "soft": "rgba(18,143,132,0.18)", "line": "rgba(40,170,155,0.34)", "text": "#7fd6c8", "swatch": "#0f766e"},
    },
    "blue": {
        "name": "海蓝",
        "light": {"bg": "#2e59a7", "hover": "#274c8f", "soft": "rgba(46,89,167,0.10)", "line": "rgba(46,89,167,0.36)", "text": "#2e59a7", "swatch": "#2e59a7"},
        "dark": {"bg": "#3a6bd0", "hover": "#3f70d8", "soft": "rgba(79,132,255,0.14)", "line": "rgba(79,132,255,0.34)", "text": "#7aa2ff", "swatch": "#2e59a7"},
    },
    "indigo": {
        "name": "靛蓝",
        "light": {"bg": "#4f46a5", "hover": "#40398a", "soft": "#edeafe", "line": "#cfc9ef", "text": "#453d92", "swatch": "#4f46a5"},
        "dark": {"bg": "#6a5fd0", "hover": "#7c71e0", "soft": "rgba(106,95,208,0.22)", "line": "rgba(140,130,230,0.36)", "text": "#c2baf8", "swatch": "#4f46a5"},
    },
    "violet": {
        "name": "紫罗兰",
        "light": {"bg": "#7c3a8f", "hover": "#673078", "soft": "#f4e9f7", "line": "#e0c9e7", "text": "#6d327e", "swatch": "#7c3a8f"},
        "dark": {"bg": "#9952ad", "hover": "#aa64bf", "soft": "rgba(153,82,173,0.22)", "line": "rgba(190,120,205,0.36)", "text": "#e0b3eb", "swatch": "#7c3a8f"},
    },
    "graphite": {
        "name": "石墨",
        "light": {"bg": "#3f4348", "hover": "#303338", "soft": "#eceef0", "line": "#d0d4d8", "text": "#3a3e43", "swatch": "#3f4348"},
        "dark": {"bg": "#6c7278", "hover": "#7d838a", "soft": "rgba(140,150,160,0.20)", "line": "rgba(160,170,180,0.34)", "text": "#c9cfd5", "swatch": "#3f4348"},
    },
}

_QSS = Template(
    r"""
QWidget {
    color: $text;
    font-family: "$sans";
    font-size: 13px;
}
QMainWindow, QWidget#Root { background: $app; }
QWidget#Page, QStackedWidget#PageStack { background: $main; }
QToolTip {
    background: $surface; color: $text; border: 1px solid $border_strong;
    padding: 5px 7px; border-radius: 5px;
}
QFrame#Sidebar { background: $chrome; border-right: 1px solid $border; }
QLabel#BrandName { font-size: 15px; font-weight: 700; }
QLabel#BrandSub { font-size: 11.5px; color: $text3; }
QLabel#NavLabel { font-size: 11px; color: $text3; padding-left: 10px; }
QPushButton#NavButton {
    text-align: left; padding: 0 10px; border: 1px solid transparent;
    border-radius: 8px; min-height: 38px; max-height: 38px;
    color: $text2; font-size: 13.5px; font-weight: 500;
}
QPushButton#NavButton:hover { background: $nav_hover; color: $text; }
QPushButton#NavButton:checked { background: $accent_soft; color: $accent_text; }
QPushButton#NavButton:focus { border: 2px solid $accent_bg; }
QLabel#PageTitle { font-size: 20px; font-weight: 700; }
QLabel#PageSub { font-size: 13px; color: $text2; }
QFrame#Card { background: $surface; border: 1px solid $border; border-radius: 12px; }
QLabel#CardTitle { font-size: 13px; font-weight: 600; }
QFrame#Divider { background: $row_border; max-height: 1px; min-height: 1px; border: none; }

QPushButton {
    border: 1px solid transparent; border-radius: 8px;
    padding: 0 13px; min-height: 32px; max-height: 34px;
    background: transparent; color: $text; font-size: 13.5px;
}
QPushButton[role="primary"] { background: $accent_bg; color: #ffffff; font-weight: 500; }
QPushButton[role="primary"]:hover { background: $accent_hover; }
QPushButton[role="primary"]:disabled { background: $border; color: $text3; }
QPushButton[role="primary"]:focus { border: 2px solid #ffffff; padding: 0 12px; }
QPushButton[role="secondary"] { background: $surface; border-color: $border_strong; color: $text; }
QPushButton[role="secondary"]:hover { background: $surface2; border-color: $control_hover; }
QPushButton[role="secondary"]:disabled { color: $text3; border-color: $border; }
QPushButton[role="secondary"]:focus { border: 2px solid $accent_bg; padding: 0 12px; }
QPushButton[role="ghost"] { background: transparent; color: $text2; }
QPushButton[role="ghost"]:hover { background: $surface3; color: $text; }
QPushButton[role="ghost"]:focus { border: 2px solid $accent_bg; padding: 0 12px; }
QPushButton[role="danger"] { background: $danger; color: #ffffff; }
QPushButton[role="danger"]:hover { background: $danger; }
QPushButton[role="dangerGhost"] { background: transparent; color: $danger; }
QPushButton[role="dangerGhost"]:hover { background: $danger_soft; }
QPushButton#LinkButton {
    background: transparent; border: none; color: $text2;
    font-size: 11.5px; padding: 0 6px; min-height: 22px;
}
QPushButton#LinkButton:hover { background: $surface3; color: $text; }
QToolButton#IconButton {
    background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 4px;
}
QToolButton#IconButton:hover { background: $surface3; }
QToolButton#IconButton:focus { border: 2px solid $accent_bg; }
QToolButton#StarButton { background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 4px; }
QToolButton#StarButton:hover { background: $surface3; }

QLineEdit {
    background: $surface; border: 1px solid $border_strong; border-radius: 7px;
    padding: 0 10px; min-height: 32px; max-height: 32px;
    selection-background-color: $accent_bg; selection-color: #ffffff;
}
QLineEdit:hover { border-color: $control_hover; }
QLineEdit:focus { border: 2px solid $accent_bg; padding: 0 9px; }
QLineEdit:disabled { color: $text3; background: $surface2; }
QComboBox {
    background: $surface; border: 1px solid $border_strong; border-radius: 7px;
    padding: 0 30px 0 10px; min-height: 32px; max-height: 32px;
}
QComboBox:hover { border-color: $control_hover; }
QComboBox:focus { border: 2px solid $accent_bg; padding: 0 9px; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox QAbstractItemView {
    background: $surface; border: 1px solid $border_strong; border-radius: 8px;
    padding: 4px; selection-background-color: $accent_soft; selection-color: $accent_text;
}
QCheckBox { spacing: 8px; color: $text2; font-size: 12.5px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border: 1px solid $control; border-radius: 4px;
    background: $surface;
}
QCheckBox::indicator:hover { border-color: $control_hover; }
QCheckBox::indicator:checked {
    background: $accent_bg; border-color: $accent_bg; image: url("$check_icon");
}
QCheckBox::indicator:checked:disabled {
    background: $surface3; border-color: $border_strong; image: none;
}

QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: $scroll; min-height: 28px; border-radius: 5px; }
QScrollBar::handle:vertical:hover { background: $scroll_hover; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:horizontal { background: $scroll; min-width: 28px; border-radius: 5px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QLabel#GroupLabel {
    background: $surface2; color: $text3; font-size: 11.5px;
    padding-left: 14px; min-height: 27px; max-height: 27px;
    border-bottom: 1px solid $group_border;
}
QFrame#ProjectRow { background: transparent; border: none; border-bottom: 1px solid $row_border; }
QFrame#ProjectRow:hover { background: $row_hover; }
QFrame#ProjectRow[missing="true"] { background: $missing_bg; }
QLabel#ProjectName { font-size: 13.5px; font-weight: 600; }
QLabel#ProjectPath { font-family: "$mono"; font-size: 12px; color: $path; }
QLabel#ProjectMeta { font-family: "$mono"; font-size: 12px; color: $text2; }
QLabel#ProjectTime { font-size: 11.5px; color: $text3; }
QLabel#EmptyTitle { font-size: 15px; font-weight: 600; }
QLabel#EmptyText { font-size: 12.5px; color: $text2; }

QLabel[badge="chain"] {
    min-height: 22px; max-height: 22px; padding: 0 7px; border-radius: 6px;
    font-family: "$mono"; font-size: 10.5px; font-weight: 600;
}
QLabel[badge="chain"][chain="ARM"] { background: $chain_arm_bg; color: $chain_arm_fg; }
QLabel[badge="chain"][chain="RX"] { background: $chain_rx_bg; color: $chain_rx_fg; }
QLabel[badge="chain"][chain="RH850"] { background: $chain_rh850_bg; color: $chain_rh850_fg; }
QLabel[badge="chain"][chain="RL78"] { background: $chain_rl78_bg; color: $chain_rl78_fg; }
QLabel[badge="chain"][chain="RISC-V"] { background: $chain_riscv_bg; color: $chain_riscv_fg; }
QLabel[badge="chain"][chain="MSP430"] { background: $chain_msp430_bg; color: $chain_msp430_fg; }
QLabel[badge="chain"][chain="CUSTOM"] { background: $chain_custom_bg; color: $chain_custom_fg; }
QLabel[chip="default"] {
    background: $ok_soft; color: $ok; border-radius: 4px;
    padding: 1px 5px; font-size: 10px; font-weight: 600;
}
QLabel[chip="locked"] {
    background: $surface2; color: $text3; border: 1px solid $border;
    border-radius: 4px; padding: 1px 5px; font-size: 10px;
}
QLabel[tag="warn"] {
    background: $warn_soft; color: $warn; border: 1px solid $warn_line;
    border-radius: 4px; padding: 1px 6px; font-size: 10.5px;
}
QLabel#StatusChip {
    background: $surface2; color: $text2; border: 1px solid $border;
    border-radius: 5px; padding: 1px 7px; font-size: 10.5px;
}
QLabel#StatusChip[state="ok"] { background: $ok_soft; color: $ok; border-color: $ok_line; }
QLabel#StatusChip[state="warn"] { background: $warn_soft; color: $warn; border-color: $warn_line; }
QLabel#StatusChip[state="bad"] { background: $danger_soft; color: $danger; border-color: $danger; }
QLabel#StatusText { font-size: 11.5px; color: $ok; }
QLabel#StatusText[state="bad"] { color: $danger; }
QLabel#Dot { border-radius: 3px; }
QLabel#Dot[state="ok"] { background: $ok; }
QLabel#Dot[state="warn"] { background: $warn; }
QLabel#Dot[state="bad"] { background: $danger; }

QTableWidget {
    background: $surface; border: none; gridline-color: transparent;
    selection-background-color: $row_hover; selection-color: $text;
}
QTableWidget::item { border-bottom: 1px solid $row_border; padding-left: 12px; }
QTableWidget::item:selected { background: $row_hover; color: $text; }
QHeaderView::section {
    background: $surface2; color: $text3; border: none;
    border-bottom: 1px solid $group_border; padding-left: 12px;
    font-size: 11.5px; font-weight: 500;
}
QTableCornerButton::section { background: $surface2; border: none; }
QWidget#TableFoot { background: $list_foot; border-top: 1px solid $row_border; }
QLabel#FootText { font-size: 11.5px; color: $text3; }

QFrame#Toast { background: $toast; border: 1px solid $toast_border; border-radius: 9px; }
QLabel#ToastTitle { font-size: 12.5px; font-weight: 600; }
QLabel#ToastDesc { font-size: 11px; color: $text2; }
QPushButton#ToastAction {
    background: transparent; border: none; color: $accent_text;
    font-size: 11px; font-weight: 600; padding: 2px 0; text-align: left;
}
QToolButton#ToastClose { background: transparent; border: none; border-radius: 4px; padding: 2px; }
QToolButton#ToastClose:hover { background: $surface3; }

QFrame#Scrim { background: $scrim; }
QFrame#OverlayCard { background: $surface; border: 1px solid $border; border-radius: 12px; }
QLabel#DialogTitle { font-size: 16px; font-weight: 600; }
QLabel#DialogSub { font-size: 12px; color: $text3; }
QFrame#DialogFoot { background: $list_foot; border-top: 1px solid $row_border; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; }
QLabel#FieldLabel { font-size: 12px; font-weight: 500; color: $text2; }
QLabel#FieldHint { font-size: 11px; color: $text3; }
QLabel#FieldHint[state="ok"] { color: $ok; }
QLabel#FieldHint[state="bad"] { color: $danger; }
QLabel#FieldError { font-size: 11px; color: $danger; }
QLabel#Hint { font-size: 11.5px; color: $text3; }
QLabel#MonoPath { font-family: "$mono"; font-size: 11px; color: $text2; }
QFrame#Note {
    background: $note; border: 1px solid $note_border; border-radius: 6px;
}
QFrame#ScanRow { background: $mode; border: 1px solid $border; border-radius: 8px; }
QLabel#NoteText { font-size: 11px; color: $text3; }
QRadioButton { spacing: 8px; color: $text2; font-size: 12.5px; }
QRadioButton::indicator {
    width: 15px; height: 15px; border: 1px solid $control; border-radius: 8px;
    background: $surface;
}
QRadioButton::indicator:hover { border-color: $control_hover; }
QRadioButton::indicator:checked { border: 4px solid $accent_bg; background: $surface; }
QProgressBar { background: $surface2; border: none; border-radius: 2px; }
QProgressBar::chunk { background: $accent_bg; border-radius: 2px; }

QFrame#Seg { background: $surface2; border: 1px solid $border; border-radius: 9px; }
QPushButton#SegBtn {
    background: transparent; border: none; border-radius: 6px;
    min-height: 28px; max-height: 28px; padding: 0 12px;
    color: $text2; font-size: 12.5px;
}
QPushButton#SegBtn:hover { color: $text; }
QPushButton#SegBtn:checked { background: $surface; color: $text; font-weight: 500; }
QFrame#AccentItem { background: transparent; border: 1px solid transparent; border-radius: 8px; }
QFrame#AccentItem:hover { background: $surface2; }
QFrame#AccentItem[selected="true"] { background: $surface2; border-color: $border; }
QLabel#AccentName { font-size: 11px; color: $text2; }
QFrame#PreviewStrip { background: $surface2; border: 1px dashed $border_strong; border-radius: 8px; }
QLabel#AccentText { color: $accent_text; font-size: 12px; font-weight: 500; }

QFrame#ModeTile { background: $mode; border: 1px solid $border; border-radius: 8px; }
QLabel#ModeTitle { font-size: 12px; font-weight: 500; }
QLabel#ModeSub { font-size: 11px; color: $text3; }
QFrame#ContactIcon { background: $accent_soft; border-radius: 9px; }
QFrame#EmptyIcon { background: $surface2; border: 1px solid $border; border-radius: 14px; }
QLabel#ContactTitle { font-size: 12.5px; font-weight: 600; }
QLabel#ContactMeta { font-size: 11.5px; color: $text2; }
QLabel#AboutTitle { font-size: 16px; font-weight: 700; }
QPushButton#EmailLink {
    background: transparent; border: none; color: $text2;
    font-size: 11.5px; padding: 0; min-height: 18px; text-align: left;
}
QPushButton#EmailLink:hover { color: $accent_text; }

QWidget#StatusBar { background: $chrome; border-top: 1px solid $border; }
QPushButton#HealthButton {
    background: transparent; border: none; border-radius: 5px;
    color: $text3; font-size: 11.5px; padding: 0 7px; min-height: 22px;
    text-align: left;
}
QPushButton#HealthButton:hover { background: $surface3; color: $text2; }
QPushButton#HealthButton[state="warn"] { color: $warn; }
QPushButton#HealthButton[state="bad"] { color: $danger; }
QLabel#VersionLabel { font-family: "$mono"; font-size: 10.5px; color: $text3; }

QMenu {
    background: $surface; border: 1px solid $border_strong; border-radius: 8px; padding: 4px;
}
QMenu::item {
    padding: 6px 26px 6px 10px; border-radius: 5px; color: $text2; font-size: 12.5px;
}
QMenu::item:selected { background: $surface2; color: $text; }
QMenu::separator { height: 1px; background: $row_border; margin: 4px 6px; }
QMenu::icon { padding-left: 8px; }
"""
)


def build_qss(theme: str, accent: str, sans: str, mono: str) -> str:
    palette = DARK if theme == "dark" else LIGHT
    colors = ACCENTS.get(accent, ACCENTS["red"])[theme]
    chain = palette["chain"]
    values = dict(palette)
    values.update(
        {
            "sans": sans,
            "mono": mono,
            "accent_bg": colors["bg"],
            "accent_hover": colors["hover"],
            "accent_soft": colors["soft"],
            "accent_line": colors["line"],
            "accent_text": colors["text"],
            "scroll": palette["control"],
            "scroll_hover": palette["control_hover"],
            "check_icon": (asset_dir() / "icons" / "check-white.png").as_posix(),
            "chain_arm_bg": chain["ARM"][0],
            "chain_arm_fg": chain["ARM"][1],
            "chain_rx_bg": chain["RX"][0],
            "chain_rx_fg": chain["RX"][1],
            "chain_rh850_bg": chain["RH850"][0],
            "chain_rh850_fg": chain["RH850"][1],
            "chain_rl78_bg": chain["RL78"][0],
            "chain_rl78_fg": chain["RL78"][1],
            "chain_riscv_bg": chain["RISC-V"][0],
            "chain_riscv_fg": chain["RISC-V"][1],
            "chain_msp430_bg": chain["MSP430"][0],
            "chain_msp430_fg": chain["MSP430"][1],
            "chain_custom_bg": chain["CUSTOM"][0],
            "chain_custom_fg": chain["CUSTOM"][1],
        }
    )
    return _QSS.substitute(values)


def system_is_dark() -> bool:
    try:
        hints = QGuiApplication.styleHints()
        scheme = hints.colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return True
        if scheme == Qt.ColorScheme.Light:
            return False
    except Exception:
        pass
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return int(value) == 0
    except Exception:
        return False


class ThemeController(QObject):
    changed = Signal()

    def __init__(self, store: ConfigStore, app: QApplication, sans: str, mono: str):
        super().__init__()
        self.store = store
        self.app = app
        self.sans = sans
        self.mono = mono
        self.mode = store.appearance.get("theme", "light")
        self.accent_name = store.appearance.get("accent", "red")
        if self.mode not in {"light", "dark", "system"}:
            self.mode = "light"
        if self.accent_name not in ACCENTS:
            self.accent_name = "red"
        self.resolved = self._resolve()
        self.palette = DARK if self.resolved == "dark" else LIGHT
        self.accent = ACCENTS[self.accent_name][self.resolved]
        self.apply()

    def _resolve(self) -> str:
        if self.mode == "system":
            return "dark" if system_is_dark() else "light"
        return self.mode

    def apply(self, persist: bool = False) -> None:
        self.resolved = self._resolve()
        self.palette = DARK if self.resolved == "dark" else LIGHT
        self.accent = ACCENTS[self.accent_name][self.resolved]
        self.app.setStyleSheet(build_qss(self.resolved, self.accent_name, self.sans, self.mono))
        pal = QPalette()
        pal.setColor(QPalette.ColorRole.Window, QColor(self.palette["app"]))
        pal.setColor(QPalette.ColorRole.Base, QColor(self.palette["surface"]))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor(self.palette["surface2"]))
        pal.setColor(QPalette.ColorRole.Text, QColor(self.palette["text"]))
        pal.setColor(QPalette.ColorRole.WindowText, QColor(self.palette["text"]))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor(self.palette["text"]))
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(self.palette["placeholder"]))
        pal.setColor(QPalette.ColorRole.Highlight, QColor(self.accent["bg"]))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(self.palette["surface"]))
        pal.setColor(QPalette.ColorRole.ToolTipText, QColor(self.palette["text"]))
        self.app.setPalette(pal)
        if persist:
            self.store.set_appearance(self.mode, self.accent_name)
        self.changed.emit()

    def set_mode(self, mode: str) -> None:
        if mode in {"light", "dark", "system"} and mode != self.mode:
            self.mode = mode
            self.apply(persist=True)

    def set_accent(self, name: str) -> None:
        if name in ACCENTS and name != self.accent_name:
            self.accent_name = name
            self.apply(persist=True)

    def on_system_change(self, *_args) -> None:
        if self.mode == "system":
            self.apply()
