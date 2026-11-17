"""启动 IAR / 记录最近项目。静默模式只依赖标准库。"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import ConfigStore, Toolchain
from .project import ProjectInfo, ProjectParseError, parse_project


@dataclass
class LaunchResult:
    ok: bool
    message: str = ""
    project: ProjectInfo | None = None
    toolchain: Toolchain | None = None
    code: str = ""


def resolve_toolchain(store: ConfigStore, project: ProjectInfo) -> Toolchain | None:
    recent = store.find_recent(str(project.launch_path))
    if recent and recent.locked_to:
        locked = store.toolchain(recent.locked_to)
        if locked:
            return locked
    return store.default_entry(project.chain)


def launch_project(path: str | os.PathLike[str], store: ConfigStore | None = None) -> LaunchResult:
    try:
        project = parse_project(path)
    except ProjectParseError as exc:
        return LaunchResult(False, str(exc), code="parse")

    store = store or ConfigStore()
    entry = resolve_toolchain(store, project)
    if entry is None:
        chain = project.chain or "未知"
        return LaunchResult(
            False,
            f"未配置 {chain} 工具链。请在“工具链”页添加对应版本的 IarIdePm.exe。",
            project=project,
            code="no_chain",
        )
    exe = Path(entry.path)
    if not exe.is_file():
        return LaunchResult(
            False,
            f"{entry.label} 的 IarIdePm.exe 不存在：\n{entry.path}",
            project=project,
            toolchain=entry,
            code="missing_exe",
        )

    try:
        subprocess.Popen(
            [str(exe), str(project.launch_path)],
            cwd=str(exe.parent),
            close_fds=True,
        )
    except OSError as exc:
        return LaunchResult(
            False,
            f"启动 {entry.label} 失败：{exc}",
            project=project,
            toolchain=entry,
            code="spawn",
        )

    try:
        store.touch_recent(project, entry)
    except OSError:
        # 配置文件不可写不应阻止 IAR 启动。
        pass
    return LaunchResult(True, "已启动", project=project, toolchain=entry)
