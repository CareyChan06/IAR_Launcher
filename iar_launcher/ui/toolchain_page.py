"""工具链页：表格、增删改查、自动扫描、导入导出。"""
from __future__ import annotations

import json
import os
from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.config import KNOWN_CHAINS, ConfigStore, Toolchain, toolchains_from_payload
from .dialogs import ChainDialog, ScanDialog
from .icons import icon
from .widgets import (
    Badge,
    Card,
    Chip,
    ConfirmDialog,
    Dot,
    EmptyState,
    make_button,
    make_icon_button,
)


class ToolchainPage(QWidget):
    def __init__(self, main, parent=None):
        super().__init__(parent)
        self.main = main
        self._row_ids: list[str] = []
        self.setObjectName("Page")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 22, 28, 16)
        outer.setSpacing(0)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        title = QLabel("工具链")
        title.setObjectName("PageTitle")
        subtitle = QLabel("为每种工具链配置 IAR 可执行文件，启动时按工程自动匹配")
        subtitle.setObjectName("PageSub")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header.addLayout(title_col)
        header.addStretch(1)
        scan_button = make_button("自动扫描", "secondary", "scan")
        scan_button.clicked.connect(self.scan)
        add_button = make_button("添加", "primary", "plus", "#ffffff")
        add_button.clicked.connect(self.add)
        header.addWidget(scan_button, 0, Qt.AlignmentFlag.AlignTop)
        header.addSpacing(8)
        header.addWidget(add_button, 0, Qt.AlignmentFlag.AlignTop)
        outer.addLayout(header)
        outer.addSpacing(16)

        note_row = QHBoxLayout()
        note_row.setSpacing(7)
        note_icon = QLabel()
        note_icon.setPixmap(icon("info", self.main.theme.palette["text3"], 14).pixmap(14, 14))
        note_row.addWidget(note_icon)
        note = QLabel("同一工具链有多个版本时，默认使用列表中的第一个；右键可将某个版本设为默认，也可在项目上锁定版本。")
        note.setObjectName("Hint")
        note_row.addWidget(note)
        note_row.addStretch(1)
        outer.addLayout(note_row)
        outer.addSpacing(10)

        self.stack = QStackedWidget()
        outer.addWidget(self.stack, 1)

        # 表格
        table_card = Card(margins=(0, 0, 0, 0))
        table_card.body.setSpacing(0)
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["工具链", "版本", "可执行文件", "状态", "操作"])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        header_view = self.table.horizontalHeader()
        header_view.setHighlightSections(False)
        header_view.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header_view.setFixedHeight(34)
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(1, 170)
        self.table.setColumnWidth(3, 112)
        self.table.setColumnWidth(4, 68)
        self.table.cellDoubleClicked.connect(self._edit_row)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._table_menu)
        table_card.body.addWidget(self.table, 1)

        footer = QWidget()
        footer.setObjectName("TableFoot")
        footer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(14, 0, 14, 0)
        footer_layout.setSpacing(6)
        self.foot_label = QLabel("")
        self.foot_label.setObjectName("FootText")
        footer_layout.addWidget(self.foot_label)
        footer_layout.addStretch(1)
        import_button = make_button("导入配置", "ghost")
        import_button.setObjectName("LinkButton")
        import_button.clicked.connect(self.import_config)
        export_button = make_button("导出配置", "ghost")
        export_button.setObjectName("LinkButton")
        export_button.clicked.connect(self.export_config)
        footer_layout.addWidget(import_button)
        footer_layout.addWidget(export_button)
        footer.setFixedHeight(34)
        table_card.body.addWidget(footer)
        self.stack.addWidget(table_card)

        # 空状态
        empty_card = Card(margins=(0, 0, 0, 0))
        scan = make_button("自动扫描本机 IAR", "primary", "scan", "#ffffff")
        scan.clicked.connect(self.scan)
        add = make_button("手动添加", "secondary", "plus")
        add.clicked.connect(self.add)
        empty = EmptyState(
            "还没有配置工具链",
            "先自动扫描本机已安装的 IAR，或手动添加 IarIdePm.exe 路径。",
            "chip",
            [scan, add],
        )
        empty_card.body.addWidget(empty, 1)
        self.stack.addWidget(empty_card)

        self.refresh()

    # ── 刷新 ──
    def refresh(self) -> None:
        store = self.main.store
        entries = store.toolchains
        self.stack.setCurrentIndex(0 if entries else 1)
        good = sum(1 for entry in entries if entry.available)
        self.foot_label.setText(f"{len(entries)} 个条目 · {good} 个可用")
        self.table.setRowCount(0)
        self._row_ids = []
        palette = self.main.theme.palette
        for row, entry in enumerate(entries):
            self.table.insertRow(row)
            self.table.setRowHeight(row, 53)
            self._row_ids.append(entry.id)

            chain_cell = QWidget()
            chain_layout = QHBoxLayout(chain_cell)
            chain_layout.setContentsMargins(12, 0, 4, 0)
            chain_layout.setSpacing(0)
            chain_layout.addWidget(Badge(entry.chain, set(KNOWN_CHAINS)))
            chain_layout.addStretch(1)
            self.table.setCellWidget(row, 0, chain_cell)

            version_cell = QWidget()
            version_layout = QHBoxLayout(version_cell)
            version_layout.setContentsMargins(14, 0, 8, 0)
            version_layout.setSpacing(6)
            version = QLabel(entry.version or "未标注")
            version.setStyleSheet(
                "font-family: 'Cascadia Mono', Consolas, monospace; font-size: 12px; font-weight: 500;"
            )
            version.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            version_layout.addWidget(version)
            if store.is_default(entry):
                version_layout.addWidget(Chip("默认", "default"))
            if any(item.locked_to == entry.id for item in store.recent):
                lock_chip = Chip("已锁定", "locked")
                lock_chip.setToolTip("有工程锁定到此版本")
                version_layout.addWidget(lock_chip)
            version_layout.addStretch(1)
            self.table.setCellWidget(row, 1, version_cell)

            path_item = QTableWidgetItem(entry.path)
            path_item.setToolTip(entry.path)
            path_item.setData(Qt.ItemDataRole.UserRole, entry.id)
            font = QFont("Cascadia Mono")
            font.setPixelSize(11)
            path_item.setFont(font)
            self.table.setItem(row, 2, path_item)

            status_cell = QWidget()
            status_layout = QHBoxLayout(status_cell)
            status_layout.setContentsMargins(14, 0, 8, 0)
            status_layout.setSpacing(6)
            available = entry.available
            status_layout.addWidget(Dot("ok" if available else "bad"))
            status = QLabel("可用" if available else "路径失效")
            status.setObjectName("StatusText")
            if not available:
                status.setProperty("state", "bad")
            status_layout.addWidget(status)
            status_layout.addStretch(1)
            self.table.setCellWidget(row, 3, status_cell)

            action_cell = QWidget()
            action_layout = QHBoxLayout(action_cell)
            action_layout.setContentsMargins(0, 0, 8, 0)
            action_layout.setSpacing(1)
            edit = make_icon_button("pencil", palette["text3"], "编辑", 14)
            edit.clicked.connect(lambda checked=False, entry_id=entry.id: self.edit(entry_id))
            delete = make_icon_button("trash", palette["text3"], "删除", 14)
            delete.clicked.connect(lambda checked=False, entry_id=entry.id: self.delete(entry_id))
            action_layout.addStretch(1)
            action_layout.addWidget(edit)
            action_layout.addWidget(delete)
            self.table.setCellWidget(row, 4, action_cell)

    def refresh_theme(self) -> None:
        self.refresh()

    # ── 操作 ──
    def add(self) -> None:
        dialog = ChainDialog(self.window(), self.main.store, self.main.theme, None)
        if dialog.exec() and dialog.result_entry:
            self.refresh()
            self.main.refresh_chrome()
            self.main.toast("ok", "已添加工具链", dialog.result_entry.label)

    def edit(self, entry_id: str) -> None:
        entry = self.main.store.toolchain(entry_id)
        if not entry:
            return
        dialog = ChainDialog(self.window(), self.main.store, self.main.theme, entry)
        if dialog.exec() and dialog.result_entry:
            self.refresh()
            self.main.refresh_chrome()
            self.main.toast("ok", "工具链已更新", dialog.result_entry.label)

    def _edit_row(self, row: int, _column: int) -> None:
        if 0 <= row < len(self._row_ids):
            self.edit(self._row_ids[row])

    def _table_menu(self, pos: QPoint) -> None:
        row = self.table.indexAt(pos).row()
        if row < 0 or row >= len(self._row_ids):
            return
        entry = self.main.store.toolchain(self._row_ids[row])
        if not entry:
            return
        palette = self.main.theme.palette
        menu = QMenu(self)
        default_action = menu.addAction(icon("check", palette["text2"], 14), "设为默认")
        default_action.setEnabled(not self.main.store.is_default(entry))
        edit_action = menu.addAction(icon("pencil", palette["text2"], 14), "编辑")
        menu.addSeparator()
        delete_action = menu.addAction(icon("trash", palette["danger"], 14), "删除")
        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == default_action:
            self.set_default(entry)
        elif chosen == edit_action:
            self.edit(entry.id)
        elif chosen == delete_action:
            self.delete(entry.id)

    def set_default(self, entry: Toolchain) -> None:
        store = self.main.store
        entries = store.toolchains
        if entry not in entries:
            return
        entries.remove(entry)
        insert_at = next((i for i, item in enumerate(entries) if item.key == entry.key), len(entries))
        entries.insert(insert_at, entry)
        store.save()
        self.refresh()
        self.main.refresh_chrome()
        self.main.toast("ok", "已设为默认版本", entry.label)

    def delete(self, entry_id: str) -> None:
        entry = self.main.store.toolchain(entry_id)
        if not entry:
            return
        used = self.main.store.toolchains_using(entry_id)
        detail = ""
        if used:
            detail = f"有 {used} 个最近项目正在使用此版本，删除后将回退到自动匹配。"
        if not ConfirmDialog.ask(
            self.window(),
            "删除工具链配置？",
            "不会删除 IAR 程序本身，只移除这条启动路径。",
            f"{entry.chain} · {entry.version}\n{entry.path}" + (f"\n\n{detail}" if detail else ""),
            "删除",
        ):
            return
        self.main.store.delete_toolchain(entry_id)
        self.refresh()
        self.main.refresh_chrome()
        self.main.toast("ok", "已删除工具链配置", entry.label)

    def scan(self) -> None:
        dialog = ScanDialog(self.window(), self.main.store, self.main.theme)
        dialog.exec()
        if dialog.imported:
            self.refresh()
            self.main.refresh_chrome()
            self.main.toast("ok", f"已导入 {dialog.imported} 个 IAR 安装")

    def export_config(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出工具链配置",
            str(Path.home() / "iar-launcher-toolchains.json"),
            "JSON (*.json)",
        )
        if not path:
            return
        payload = {
            "schema": 2,
            "toolchains": [entry.to_dict() for entry in self.main.store.toolchains],
        }
        try:
            Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            self.main.toast("error", "导出失败", str(exc))
            return
        self.main.toast("ok", "配置已导出", path)

    def import_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "导入工具链配置",
            str(Path.home()),
            "JSON (*.json);;所有文件 (*.*)",
        )
        if not path:
            return
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            entries = toolchains_from_payload(payload if isinstance(payload, dict) else {})
        except (OSError, json.JSONDecodeError) as exc:
            self.main.toast("error", "导入失败", str(exc))
            return
        if not entries:
            self.main.toast("warn", "没有可导入的工具链", "文件里没有 iar_paths 或 toolchains 字段。")
            return
        if not ConfirmDialog.ask(
            self.window(),
            "导入工具链配置？",
            f"发现 {len(entries)} 个工具链，重复路径会自动跳过。",
            "",
            "导入",
            danger=False,
        ):
            return
        added = self.main.store.import_toolchains(entries)
        self.refresh()
        self.main.refresh_chrome()
        if added:
            self.main.toast("ok", f"已导入 {added} 个工具链")
        else:
            self.main.toast("info", "没有新增工具链", "这些路径都已经配置过了。")
