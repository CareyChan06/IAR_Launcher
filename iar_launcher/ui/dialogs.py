"""工具链编辑、自动扫描、工程版本锁定等遮罩弹窗。"""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..core.config import (
    KNOWN_CHAINS,
    ConfigStore,
    RecentProject,
    Toolchain,
    infer_version_from_path,
    product_label,
)
from ..core.discovery import FoundInstall, scan_installed
from .icons import icon
from .theme import ThemeController
from .widgets import Badge, OverlayDialog, make_button, make_icon_button, set_prop


def field_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("FieldLabel")
    return label


def hint_label(text: str = "") -> QLabel:
    label = QLabel(text)
    label.setObjectName("FieldHint")
    label.setWordWrap(True)
    return label


def add_field(layout: QVBoxLayout, label_text: str, widget: QWidget) -> QVBoxLayout:
    box = QVBoxLayout()
    box.setSpacing(5)
    label = QLabel(label_text)
    label.setObjectName("FieldLabel")
    box.addWidget(label)
    box.addWidget(widget)
    layout.addLayout(box)
    return box


class ChainDialog(OverlayDialog):
    def __init__(self, parent, store: ConfigStore, theme: ThemeController, entry: Toolchain | None = None):
        super().__init__(
            parent,
            "编辑工具链" if entry else "添加工具链",
            "修改后立即生效，已打开的项目不受影响。"
            if entry
            else "配置一个 IAR 可执行文件，供对应工具链的工程使用。",
            500,
        )
        self.store = store
        self.theme = theme
        self.entry = entry
        self.result_entry: Toolchain | None = None

        self.chain_combo = QComboBox()
        custom_chains = sorted({item.chain for item in store.toolchains if item.chain not in KNOWN_CHAINS})
        values = list(KNOWN_CHAINS) + [name for name in custom_chains if name]
        for name in values:
            self.chain_combo.addItem(name, name)
        self.chain_combo.addItem("自定义…", "__custom__")
        add_field(self.body_layout, "工具链", self.chain_combo)

        self.custom_wrap = QWidget()
        custom_layout = QVBoxLayout(self.custom_wrap)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        custom_layout.setSpacing(5)
        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("例如 AVR、8051、M68K")
        self.custom_error = QLabel("请输入工具链名称")
        self.custom_error.setObjectName("FieldError")
        self.custom_error.hide()
        custom_layout.addWidget(field_label("自定义工具链名称"))
        custom_layout.addWidget(self.custom_input)
        custom_layout.addWidget(self.custom_error)
        self.custom_wrap.hide()
        self.body_layout.addWidget(self.custom_wrap)

        self.version_input = QLineEdit()
        self.version_input.setPlaceholderText("例如 9.60.3")
        add_field(self.body_layout, "版本备注", self.version_input)

        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText(r"…\common\bin\IarIdePm.exe")
        self.path_input.setStyleSheet("font-family: 'Cascadia Mono', Consolas, monospace; font-size: 11.5px;")
        path_row = QHBoxLayout()
        path_row.setSpacing(7)
        path_row.addWidget(self.path_input, 1)
        browse = make_button("浏览…", "secondary")
        browse.clicked.connect(self._browse)
        path_row.addWidget(browse)
        self.path_hint = hint_label()
        path_group = QWidget()
        path_layout = QVBoxLayout(path_group)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(5)
        path_layout.addLayout(path_row)
        path_layout.addWidget(self.path_hint)
        add_field(self.body_layout, "IarIdePm.exe 路径", path_group)

        self.add_footer("取消", "ghost", self.reject)
        self.add_footer("保存修改" if entry else "添加工具链", "primary", self._save)

        if entry:
            index = self.chain_combo.findData(entry.chain)
            if index >= 0:
                self.chain_combo.setCurrentIndex(index)
            elif entry.chain:
                self.chain_combo.addItem(entry.chain, entry.chain)
                self.chain_combo.setCurrentIndex(self.chain_combo.count() - 1)
            self.version_input.setText(entry.version)
            self.path_input.setText(entry.path)
        self._last_chain = entry.chain if entry else KNOWN_CHAINS[0]
        self._sync_custom(self.chain_combo.currentData())
        self.chain_combo.currentIndexChanged.connect(lambda _: self._sync_custom(self.chain_combo.currentData()))
        self.path_input.textChanged.connect(self._update_hint)
        self.custom_input.textChanged.connect(lambda _: self.custom_error.hide())
        self._update_hint()

    def _sync_custom(self, value: str | None) -> None:
        custom = value == "__custom__"
        self.custom_wrap.setVisible(custom)
        self.custom_error.hide()
        if custom:
            if self._last_chain and self._last_chain not in KNOWN_CHAINS and self._last_chain != "__custom__":
                self.custom_input.setText(self._last_chain)
            QTimer.singleShot(0, self.custom_input.setFocus)
        elif value:
            self._last_chain = value

    def _browse(self) -> None:
        start = self.path_input.text().strip()
        start_dir = str(Path(start).parent) if start else os.environ.get("ProgramFiles", "C:/Program Files")
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 IarIdePm.exe",
            start_dir,
            "IarIdePm.exe (IarIdePm.exe);;可执行文件 (*.exe)",
        )
        if path:
            self.path_input.setText(path)
            if not self.version_input.text().strip():
                self.version_input.setText(infer_version_from_path(path))

    def _update_hint(self) -> None:
        text = self.path_input.text().strip()
        if not text:
            self.path_hint.setText("尚未选择可执行文件")
            set_prop(self.path_hint, "state", "neutral")
            return
        if not text.lower().endswith("iaridepm.exe"):
            self.path_hint.setText("路径应以 IarIdePm.exe 结尾")
            set_prop(self.path_hint, "state", "bad")
            return
        if not Path(text).is_file():
            self.path_hint.setText("文件不存在；保存后会显示为路径失效")
            set_prop(self.path_hint, "state", "bad")
            return
        self.path_hint.setText("已找到 IarIdePm.exe")
        set_prop(self.path_hint, "state", "ok")

    def _save(self) -> None:
        raw = self.chain_combo.currentData()
        chain = self.custom_input.text().strip() if raw == "__custom__" else str(raw)
        version = self.version_input.text().strip()
        path = self.path_input.text().strip()
        if raw == "__custom__" and not chain:
            self.custom_error.show()
            return
        if not path:
            self.path_hint.setText("请填写 IarIdePm.exe 路径")
            set_prop(self.path_hint, "state", "bad")
            return
        if not path.lower().endswith("iaridepm.exe"):
            self.path_hint.setText("路径应以 IarIdePm.exe 结尾")
            set_prop(self.path_hint, "state", "bad")
            return
        if not version:
            version = infer_version_from_path(path) or "未标注"
        if self.entry:
            self.result_entry = self.store.update_toolchain(self.entry.id, chain, version, path)
        else:
            self.result_entry = self.store.add_toolchain(chain, version, path)
        self.accept()


class ScanDialog(OverlayDialog):
    def __init__(self, parent, store: ConfigStore, theme: ThemeController):
        super().__init__(parent, "自动扫描已安装的 IAR", "在注册表与常见安装目录中查找 IarIdePm.exe", 560)
        self.store = store
        self.theme = theme
        self.found: list[FoundInstall] = []
        self._checks: list[tuple[QCheckBox, FoundInstall]] = []
        self.imported = 0

        self.loading = QWidget()
        loading_layout = QVBoxLayout(self.loading)
        loading_layout.setContentsMargins(0, 20, 0, 20)
        loading_layout.setSpacing(10)
        label = QLabel("正在扫描注册表与安装目录…")
        label.setObjectName("Hint")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bar = QProgressBar()
        bar.setRange(0, 0)
        bar.setFixedWidth(220)
        bar.setTextVisible(False)
        bar.setFixedHeight(4)
        loading_layout.addWidget(label)
        loading_layout.addWidget(bar, 0, Qt.AlignmentFlag.AlignHCenter)
        self.body_layout.addWidget(self.loading)

        self.list_wrap = QWidget()
        self.list_layout = QVBoxLayout(self.list_wrap)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(6)
        self.body_layout.addWidget(self.list_wrap)
        self.list_wrap.hide()

        self.note = hint_label("")
        self.body_layout.addWidget(self.note)
        self.add_footer("取消", "ghost", self.reject)
        self.import_button = self.add_footer("导入", "primary", self._import)
        self.import_button.setEnabled(False)
        QTimer.singleShot(80, self._scan)

    def _scan(self) -> None:
        try:
            self.found = scan_installed()
        except Exception as exc:
            self.loading.hide()
            self.note.setText(f"扫描失败：{exc}")
            set_prop(self.note, "state", "bad")
            return
        self.loading.hide()
        self.list_wrap.show()
        configured = {os.path.normcase(os.path.abspath(item.path)) for item in self.store.toolchains}
        if not self.found:
            self.note.setText("没有找到可识别的 IAR 安装。可以点“添加”手动配置。")
            self.import_button.setEnabled(False)
            return
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMaximumHeight(380)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(6)
        for item in self.found:
            row = QFrame()
            row.setObjectName("ScanRow")
            row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.setSpacing(10)
            done = os.path.normcase(os.path.abspath(item.path)) in configured
            check = QCheckBox()
            check.setChecked(True)
            check.setEnabled(not done)
            row_layout.addWidget(check)
            body = QVBoxLayout()
            body.setSpacing(2)
            top = QHBoxLayout()
            top.setSpacing(7)
            top.addWidget(Badge(item.chain, set(KNOWN_CHAINS)))
            name = QLabel(f"{product_label(item.chain)} {item.version}".strip())
            name.setStyleSheet("font-size: 12.5px; font-weight: 500;")
            top.addWidget(name)
            if done:
                tag = QLabel("已配置")
                tag.setProperty("chip", "default")
                top.addWidget(tag)
            top.addStretch(1)
            body.addLayout(top)
            path_label = QLabel(item.path)
            path_label.setObjectName("MonoPath")
            body.addWidget(path_label)
            row_layout.addLayout(body, 1)
            content_layout.addWidget(row)
            self._checks.append((check, item))
            if not done:
                check.stateChanged.connect(lambda _=0: self._update_count())
        content_layout.addStretch(1)
        scroll.setWidget(content)
        self.list_layout.addWidget(scroll)
        self._update_count()

    def _update_count(self) -> None:
        count = sum(1 for check, _item in self._checks if check.isEnabled() and check.isChecked())
        self.import_button.setText(f"导入 {count} 个" if count else "导入")
        self.import_button.setEnabled(count > 0)
        total = len(self.found)
        configured = sum(1 for check, _ in self._checks if not check.isEnabled())
        self.note.setText(f"找到 {total} 个安装，其中 {configured} 个已配置。")

    def _import(self) -> None:
        entries: list[Toolchain] = []
        for check, item in self._checks:
            if check.isEnabled() and check.isChecked():
                entries.append(
                    Toolchain(
                        id="",
                        chain=item.chain,
                        version=item.version,
                        path=item.path,
                    )
                )
        self.imported = self.store.import_toolchains(entries)
        self.accept()


class LockDialog(OverlayDialog):
    def __init__(self, parent, store: ConfigStore, theme: ThemeController, project: RecentProject):
        super().__init__(parent, f"为「{project.name}」指定 IAR 版本", "仅对该工程生效，会覆盖工程文件里的工具链设置。", 540)
        self.store = store
        self.project = project
        self.saved = False

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMaximumHeight(360)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._auto = QRadioButton("自动匹配  ·  使用工程文件里的 toolchain 设置")
        self._auto.setChecked(not project.locked_to)
        layout.addWidget(self._auto)
        self._radios: list[tuple[QRadioButton, Toolchain]] = []
        for entry in store.toolchains:
            label = f"{entry.chain} {entry.version}  ·  {entry.path}"
            radio = QRadioButton(label)
            radio.setToolTip(entry.path)
            if project.locked_to == entry.id:
                radio.setChecked(True)
            layout.addWidget(radio)
            self._radios.append((radio, entry))
        layout.addStretch(1)
        scroll.setWidget(content)
        self.body_layout.addWidget(scroll)

        self.add_footer("取消", "ghost", self.reject)
        self.add_footer("保存", "primary", self._save)

    def _save(self) -> None:
        selected = None
        for radio, entry in self._radios:
            if radio.isChecked():
                selected = entry.id
                break
        if self._auto.isChecked():
            selected = None
        self.store.set_lock(self.project.path, selected)
        self.saved = True
        self.accept()
