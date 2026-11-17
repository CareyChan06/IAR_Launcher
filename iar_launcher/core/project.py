"""解析 .eww / .ewp，提取工具链和启动目标。"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from .config import canonical_chain


class ProjectParseError(Exception):
    pass


@dataclass
class ProjectInfo:
    path: Path          # 用户选择的文件（eww 或 ewp）
    name: str
    chain: str
    eww_path: Path | None
    ewp_path: Path
    launch_path: Path   # 真正传给 IarIdePm 的文件


def _clean_relative(value: str) -> str:
    text = value.strip().strip('"')
    for token in ("$WS_DIR$\\", "$WS_DIR$/", "$WS_DIR$"):
        if text.startswith(token):
            text = text[len(token):]
    return text.lstrip("\\/")


def _toolchain_from_ewp(ewp: Path) -> str:
    try:
        root = ET.parse(str(ewp)).getroot()
    except ET.ParseError as exc:
        raise ProjectParseError(f"工程文件不是有效的 XML：{exc}") from exc
    except OSError as exc:
        raise ProjectParseError(f"无法读取工程文件：{exc}") from exc

    for configuration in root.findall(".//configuration"):
        toolchain = configuration.find("toolchain/name")
        if toolchain is not None and toolchain.text and toolchain.text.strip():
            return canonical_chain(toolchain.text)
    for toolchain in root.findall(".//toolchain/name"):
        if toolchain.text and toolchain.text.strip():
            return canonical_chain(toolchain.text)
    raise ProjectParseError("无法从 ewp 文件中识别 toolchain，请检查工程配置")


def parse_project(path: str | os.PathLike[str]) -> ProjectInfo:
    source = Path(path).expanduser()
    try:
        source = source.resolve()
    except OSError:
        pass
    if not source.exists():
        raise ProjectParseError(f"工程文件不存在：{source}")
    suffix = source.suffix.lower()

    if suffix == ".ewp":
        chain = _toolchain_from_ewp(source)
        return ProjectInfo(
            path=source,
            name=source.stem,
            chain=chain,
            eww_path=None,
            ewp_path=source,
            launch_path=source,
        )

    if suffix != ".eww":
        raise ProjectParseError("请选择 .eww 或 .ewp 文件")

    try:
        root = ET.parse(str(source)).getroot()
    except ET.ParseError as exc:
        raise ProjectParseError(f"工作区文件不是有效的 XML：{exc}") from exc
    except OSError as exc:
        raise ProjectParseError(f"无法读取工作区文件：{exc}") from exc

    project_path = None
    for project in root.findall(".//project"):
        node = project.find("path")
        if node is not None and node.text and node.text.strip():
            project_path = node.text.strip()
            break
    if not project_path:
        raise ProjectParseError("无法从 eww 文件中找到 ewp 路径")

    relative = _clean_relative(project_path)
    ewp = Path(relative)
    if not ewp.is_absolute():
        ewp = source.parent / relative
    try:
        ewp = ewp.resolve()
    except OSError:
        pass
    if not ewp.exists():
        raise ProjectParseError(f"找不到 ewp 文件：{ewp}")

    chain = _toolchain_from_ewp(ewp)
    return ProjectInfo(
        path=source,
        name=source.stem,
        chain=chain,
        eww_path=source,
        ewp_path=ewp,
        launch_path=source,
    )
