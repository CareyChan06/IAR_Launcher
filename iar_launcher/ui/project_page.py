"""项目页：最近项目、搜索、置顶、清空、右键菜单、版本锁定。"""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QGuiApplication, QKeyEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..core.config import KNOWN_CHAINS, RecentProject, Toolchain
from .dialogs import LockDialog
from .icons import icon
from .widgets import (
    Badge,
    Card,
    ConfirmDialog,
    ElidedLabel,
    EmptyState,
    Tag,
    make_button,
    make_icon_button,
    open_folder,
    pretty_time,
)


class ProjectRow(QFrame):
    open_requested = Signal(object)
    menu_requested = Signal(object, QPoint)
    pin_requested = Signal(object)

    def __init__(self, main, project: RecentProject, parent=None):
        super().__init__(parent)
        self.main = main
        self.project = project
        self.missing = not Path(project.path).is_file()
        self.setObjectName("ProjectRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setProperty("missing", self.missing)
        self.setFixedHeight(56)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        store = main.store
        entry = store.toolchain(project.locked_to) if project.locked_to else store.default_entry(project.chain)
        locked = bool(project.locked_to and entry)
        palette = main.theme.palette

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 7, 12, 7)
        layout.setSpacing(12)

        layout.addWidget(Badge(project.chain, set(KNOWN_CHAINS)))

        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(1)
        name_row = QHBoxLayout()
        name_row.setContentsMargins(0, 0, 0, 0)
        name_row.setSpacing(7)
        name = QLabel(project.name)
        name.setObjectName("ProjectName")
        name_row.addWidget(name)
        if self.missing:
            name_row.addWidget(Tag("需重新定位"))
        name_row.addStretch(1)
        info.addLayout(name_row)
        path = ElidedLabel(project.path, Qt.TextElideMode.ElideMiddle)
        path.setObjectName("ProjectPath")
        path.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        info.addWidget(path)
        layout.addLayout(info, 1)

        meta = QVBoxLayout()
        meta.setContentsMargins(0, 0, 0, 0)
        meta.setSpacing(2)
        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(4)
        meta_row.addStretch(1)
        if self.missing:
            version_text = "未找到"
        elif entry:
            version_text = entry.label
        else:
            version_text = f"{project.chain} 未配置"
        if locked:
            lock = QLabel()
            lock.setPixmap(icon("lock", palette["warn"], 11).pixmap(11, 11))
            lock.setFixedSize(11, 11)
            meta_row.addWidget(lock)
        version = QLabel(version_text)
        version.setObjectName("ProjectMeta")
        version.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        version.setToolTip("已锁定该 IAR 版本" if locked else "按工程工具链自动匹配")
        meta_row.addWidget(version)
        meta.addLayout(meta_row)
        time = QLabel("工程文件已移动" if self.missing else pretty_time(project.opened_at))
        time.setObjectName("ProjectTime")
        time.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        meta.addWidget(time)
        meta_widget = QWidget()
        meta_widget.setLayout(meta)
        meta_widget.setFixedWidth(172)
        layout.addWidget(meta_widget)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(1)
        star_color = "#e8b23a" if project.pinned and main.theme.resolved == "dark" else "#c08a12" if project.pinned else palette["text3"]
        self.star = make_icon_button(
            "star",
            star_color,
            "取消置顶" if project.pinned else "置顶",
            15,
            star=True,
            filled=project.pinned,
        )
        self.star.clicked.connect(lambda: self.pin_requested.emit(self.project))
        actions.addWidget(self.star)
        more = make_icon_button("more", palette["text3"], "更多操作", 16)
        more.clicked.connect(self._show_menu)
        actions.addWidget(more)
        action_widget = QWidget()
        action_widget.setLayout(actions)
        action_widget.setFixedWidth(60)
        layout.addWidget(action_widget)

    def _show_menu(self) -> None:
        self.menu_requested.emit(self.project, self.mapToGlobal(QPoint(self.width() - 4, self.height() - 4)))

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_requested.emit(self.project)
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event) -> None:  # type: ignore[override]
        self.menu_requested.emit(self.project, event.globalPos())

    def keyPressEvent(self, event: QKeyEvent) -> None:  # type: ignore[override]
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.open_requested.emit(self.project)
            return
        if event.key() == Qt.Key.Key_Menu:
            self._show_menu()
            return
        super().keyPressEvent(event)


class ProjectPage(QWidget):
    def __init__(self, main, parent=None):
        super().__init__(parent)
        self.main = main
        self._query = ""
        self.setObjectName("Page")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 22, 28, 16)
        outer.setSpacing(0)

        header = QHBoxLayout()
        header.setSpacing(16)
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        title = QLabel("项目")
        title.setObjectName("PageTitle")
        subtitle = QLabel("单击工程，用对应的 IAR 版本直接打开")
        subtitle.setObjectName("PageSub")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header.addLayout(title_col)
        header.addStretch(1)
        self.open_button = make_button("打开工程", "primary", "folder-plus", "#ffffff")
        self.open_button.clicked.connect(self.open_dialog)
        header.addWidget(self.open_button, 0, Qt.AlignmentFlag.AlignTop)
        outer.addLayout(header)
        outer.addSpacing(16)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        from .widgets import SearchField

        self.search = SearchField("搜索工程名、路径或工具链")
        self.search.setFixedWidth(300)
        self.search.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search)
        self.count_label = QLabel("")
        self.count_label.setObjectName("Hint")
        toolbar.addWidget(self.count_label)
        toolbar.addStretch(1)
        self.clear_button = make_button("清空列表", "dangerGhost", "trash")
        self.clear_button.clicked.connect(self.clear_recent)
        toolbar.addWidget(self.clear_button)
        outer.addLayout(toolbar)
        outer.addSpacing(12)

        card = Card(margins=(0, 0, 0, 0))
        card.body.setSpacing(0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        card.body.addWidget(self.scroll, 1)

        footer = QWidget()
        footer.setObjectName("TableFoot")
        footer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(14, 0, 14, 0)
        footer_layout.setSpacing(10)
        hint = QLabel("把 .eww / .ewp 拖到窗口任意位置也能直接打开")
        hint.setObjectName("FootText")
        footer_layout.addWidget(hint)
        footer_layout.addStretch(1)
        right = QLabel("右键查看更多操作")
        right.setObjectName("FootText")
        footer_layout.addWidget(right)
        footer.setFixedHeight(32)
        card.body.addWidget(footer)
        outer.addWidget(card, 1)

        self._content: QWidget | None = None
        self.refresh()

    # ── 数据 ──
    def _visible(self) -> list[RecentProject]:
        query = self._query.strip().lower()
        items = self.main.store.sorted_recent()
        if query:
            items = [
                item
                for item in items
                if query in item.name.lower()
                or query in item.path.lower()
                or query in item.chain.lower()
            ]
        return items

    def refresh(self) -> None:
        store = self.main.store
        items = self._visible()
        pinned_count = sum(1 for item in store.recent if item.pinned)
        self.count_label.setText(
            f"{len(items)} / {len(store.recent)} 个项目"
            if self._query
            else f"{len(store.recent)} 个项目 · 置顶 {pinned_count}"
        )
        self.clear_button.setEnabled(bool(store.recent))

        old = self.scroll.takeWidget()
        content = QWidget()
        content.setObjectName("ListContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if not items:
            if self._query:
                clear = make_button("清除搜索", "secondary", "x")
                clear.clicked.connect(self._clear_search)
                empty = EmptyState(
                    "没有匹配的项目",
                    "换一个工程名、路径或工具链关键字试试。",
                    "search",
                    [clear],
                )
            else:
                open_btn = make_button("打开工程", "primary", "folder-plus", "#ffffff")
                open_btn.clicked.connect(self.open_dialog)
                buttons = [open_btn]
                if not store.toolchains:
                    scan_btn = make_button("去配置工具链", "secondary", "chip")
                    scan_btn.clicked.connect(lambda: self.main.switch_page("chains"))
                    buttons.insert(0, scan_btn)
                empty = EmptyState(
                    "还没有最近项目",
                    "打开一个 .eww 工程后，它会出现在这里并按最近打开时间排序。也可以把工程拖进窗口。",
                    "folder",
                    buttons,
                )
            layout.addWidget(empty, 1)
        else:
            pinned = [item for item in items if item.pinned]
            recent = [item for item in items if not item.pinned]
            if pinned:
                layout.addWidget(self._group_label(f"置顶 · {len(pinned)}"))
                for item in pinned:
                    layout.addWidget(self._make_row(item))
            if recent:
                layout.addWidget(self._group_label(f"最近打开 · {len(recent)}"))
                for item in recent:
                    layout.addWidget(self._make_row(item))
            layout.addStretch(1)
        self.scroll.setWidget(content)
        if old:
            old.deleteLater()
        self._content = content

    def _group_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("GroupLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return label

    def _make_row(self, project: RecentProject) -> ProjectRow:
        row = ProjectRow(self.main, project)
        row.open_requested.connect(self.open_project)
        row.menu_requested.connect(self.show_menu)
        row.pin_requested.connect(self.toggle_pin)
        return row

    # ── 操作 ──
    def _on_search(self, text: str) -> None:
        self._query = text
        self.refresh()

    def _clear_search(self) -> None:
        self.search.clear()

    def open_dialog(self) -> None:
        start = ""
        if self.main.store.recent:
            start = str(Path(self.main.store.recent[0].path).parent)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 IAR 工作区",
            start,
            "IAR 工作区 (*.eww *.ewp);;所有文件 (*.*)",
        )
        if path:
            self.main.open_project_path(path)

    def open_project(self, project: RecentProject) -> None:
        if not Path(project.path).is_file():
            self.main.toast(
                "warn",
                "工程文件不存在",
                project.path,
                ("重新定位…", lambda: self.relocate(project)),
            )
            return
        self.main.open_project_path(project.path)

    def relocate(self, project: RecentProject) -> None:
        start = str(Path(project.path).parent)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "重新选择工程文件",
            start,
            "IAR 工作区 (*.eww *.ewp);;所有文件 (*.*)",
        )
        if not path:
            return
        result = self.main.open_project_path(path)
        if not result.ok:
            return
        new_item = self.main.store.find_recent(path)
        if new_item:
            new_item.pinned = project.pinned
            new_item.locked_to = project.locked_to
            self.main.store.save()
        self.main.store.remove_recent(project.path)
        self.refresh()
        self.main.refresh_chrome()

    def toggle_pin(self, project: RecentProject) -> None:
        pinned = self.main.store.toggle_pin(project.path)
        self.refresh()
        self.main.refresh_chrome()
        self.main.toast("ok", "已置顶" if pinned else "已取消置顶", project.name)

    def clear_recent(self) -> None:
        count = len(self.main.store.recent)
        if not count:
            return
        if not ConfirmDialog.ask(
            self.window(),
            "清空最近项目？",
            "只清除启动器里的记录，不会删除磁盘上的工程文件。",
            f"将移除 {count} 条最近项目记录，以及工程级的版本锁定设置。",
            "清空列表",
        ):
            return
        self.main.store.clear_recent()
        self.refresh()
        self.main.refresh_chrome()
        self.main.toast("ok", "最近项目已清空")

    def show_menu(self, project: RecentProject, global_pos: QPoint) -> None:
        palette = self.main.theme.palette
        menu = QMenu(self)
        color = palette["text2"]
        missing = not Path(project.path).is_file()
        open_action = menu.addAction(icon("folder-open" if missing else "external", color, 14), "重新定位…" if missing else "打开工程")
        folder_action = menu.addAction(icon("folder-open", color, 14), "打开所在文件夹")
        copy_action = menu.addAction(icon("copy", color, 14), "复制工程路径")
        menu.addSeparator()
        lock_action = menu.addAction(icon("lock", color, 14), "指定 IAR 版本…")
        pin_action = menu.addAction(icon("star", color, 14), "取消置顶" if project.pinned else "置顶")
        menu.addSeparator()
        remove_action = menu.addAction(icon("trash", palette["danger"], 14), "从最近列表移除")
        action = menu.exec(global_pos)
        if action is None:
            return
        if action == open_action:
            self.open_project(project)
        elif action == folder_action:
            open_folder(str(Path(project.path).parent))
        elif action == copy_action:
            QGuiApplication.clipboard().setText(project.path)
            self.main.toast("ok", "工程路径已复制", project.path)
        elif action == lock_action:
            self.lock_project(project)
        elif action == pin_action:
            self.toggle_pin(project)
        elif action == remove_action:
            self.main.store.remove_recent(project.path)
            self.refresh()
            self.main.refresh_chrome()
            self.main.toast("ok", "已从最近列表移除", project.name)

    def lock_project(self, project: RecentProject) -> None:
        dialog = LockDialog(self.window(), self.main.store, self.main.theme, project)
        dialog.exec()
        if dialog.saved:
            self.refresh()
            fresh = self.main.store.find_recent(project.path)
            entry = self.main.store.toolchain(fresh.locked_to) if fresh else None
            if entry:
                self.main.toast("ok", "已锁定 IAR 版本", f"{project.name} → {entry.label}")
            else:
                self.main.toast("ok", "已恢复自动匹配", project.name)

    def refresh_theme(self) -> None:
        self.refresh()
