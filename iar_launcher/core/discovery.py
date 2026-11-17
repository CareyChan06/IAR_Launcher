"""扫描本机 IAR 安装：卸载注册表 + 常见目录，读取 exe 产品名/版本。"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import os
import re
import winreg
from dataclasses import dataclass
from pathlib import Path

from .config import KNOWN_CHAINS, canonical_chain, infer_version_from_path

UNINSTALL_PATHS = (
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
)


@dataclass
class FoundInstall:
    chain: str
    version: str
    path: str
    product_name: str = ""
    source: str = ""

    @property
    def label(self) -> str:
        return f"{self.chain or '未识别'} {self.version}".strip()


def _file_version_strings(path: str) -> dict[str, str]:
    """读取 exe 的 VS_VERSIONINFO（ProductName / FileVersion 等）。"""
    if os.name != "nt":
        return {}
    try:
        version = ctypes.windll.version
        handle = wintypes.DWORD()
        size = version.GetFileVersionInfoSizeW(str(path), ctypes.byref(handle))
        if not size:
            return {}
        buffer = ctypes.create_string_buffer(size)
        if not version.GetFileVersionInfoW(str(path), 0, size, buffer):
            return {}
        pointer = ctypes.c_void_p()
        length = ctypes.c_uint()
        if not version.VerQueryValueW(
            buffer, "\\VarFileInfo\\Translation", ctypes.byref(pointer), ctypes.byref(length)
        ):
            return {}
        translations = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_ushort))
        result: dict[str, str] = {}
        for index in range(max(1, length.value // 4)):
            lang = translations[index * 2]
            codepage = translations[index * 2 + 1]
            prefix = "\\StringFileInfo\\%04x%04x\\" % (lang, codepage)
            for key in ("ProductName", "FileDescription", "FileVersion", "ProductVersion", "CompanyName"):
                value_ptr = ctypes.c_void_p()
                value_len = ctypes.c_uint()
                if version.VerQueryValueW(
                    buffer, prefix + key, ctypes.byref(value_ptr), ctypes.byref(value_len)
                ) and value_len.value:
                    text = ctypes.wstring_at(value_ptr, value_len.value - 1).strip()
                    if text:
                        result[key] = text
        return result
    except Exception:
        return {}


def _file_version_short(path: str) -> str:
    info = _file_version_strings(path)
    value = info.get("FileVersion") or info.get("ProductVersion") or ""
    match = re.match(r"(\d+\.\d+(?:\.\d+)?)", value)
    return match.group(1) if match else ""


def chain_from_text(text: str) -> str:
    lower = (text or "").lower()
    if "risc-v" in lower or "riscv" in lower:
        return "RISC-V"
    if "rh850" in lower:
        return "RH850"
    if "rl78" in lower:
        return "RL78"
    if "msp430" in lower:
        return "MSP430"
    if re.search(r"\bavr\b", lower):
        return "AVR"
    if "renesas rx" in lower or re.search(r"\brx\b", lower) or "ewrx" in lower:
        return "RX"
    if "m16c" in lower or "r8c" in lower:
        return "M16C/R8C"
    if "renesas 78k" in lower or "78k" in lower:
        return "78K"
    if re.search(r"\barm\b", lower) or "ewarm" in lower:
        return "ARM"
    return ""


def _find_exe(base: Path) -> Path | None:
    candidates = [
        base / "common" / "bin" / "IarIdePm.exe",
        base / "bin" / "IarIdePm.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    try:
        children = [child for child in base.iterdir() if child.is_dir()]
    except OSError:
        return None
    for child in children:
        for candidate in (
            child / "common" / "bin" / "IarIdePm.exe",
            child / "bin" / "IarIdePm.exe",
        ):
            if candidate.is_file():
                return candidate
    return None


def _iter_uninstall_entries():
    for hive, subkey in UNINSTALL_PATHS:
        try:
            root = winreg.OpenKey(hive, subkey)
        except OSError:
            continue
        with root:
            try:
                count = winreg.QueryInfoKey(root)[0]
            except OSError:
                continue
            for index in range(count):
                try:
                    name = winreg.EnumKey(root, index)
                    with winreg.OpenKey(root, name) as key:
                        display = _reg_value(key, "DisplayName")
                        if not display or "iar" not in display.lower():
                            continue
                        if "embedded workbench" not in display.lower():
                            continue
                        if "library source" in display.lower():
                            continue
                        location = _reg_value(key, "InstallLocation")
                        if not location:
                            continue
                        yield display, location.strip().strip('"')
                except OSError:
                    continue


def _reg_value(key, name: str) -> str:
    try:
        value, _ = winreg.QueryValueEx(key, name)
        return str(value) if value is not None else ""
    except OSError:
        return ""


def _scan_registry() -> list[FoundInstall]:
    found: list[FoundInstall] = []
    for display, location in _iter_uninstall_entries():
        base = Path(location)
        exe = _find_exe(base)
        if not exe:
            continue
        chain = chain_from_text(display)
        if not chain:
            chain = chain_from_text(_file_version_strings(str(exe)).get("ProductName", ""))
        if not chain:
            chain = chain_from_text(str(base))
        if not chain:
            continue
        version = infer_version_from_path(str(base)) or _file_version_short(str(exe))
        found.append(
            FoundInstall(
                chain=canonical_chain(chain),
                version=version,
                path=str(exe),
                product_name=display,
                source="registry",
            )
        )
    return found


def _scan_directories() -> list[FoundInstall]:
    found: list[FoundInstall] = []
    roots: list[Path] = []
    for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
        value = os.environ.get(env_name)
        if value:
            roots.append(Path(value) / "IAR Systems")
    system_drive = os.environ.get("SystemDrive", "C:")
    roots.append(Path(f"{system_drive}/iar"))
    for root in roots:
        if not root.is_dir():
            continue
        try:
            children = [child for child in root.iterdir() if child.is_dir()]
        except OSError:
            continue
        for child in children:
            exe = _find_exe(child)
            if not exe:
                continue
            info = _file_version_strings(str(exe))
            chain = chain_from_text(info.get("ProductName", "")) or chain_from_text(info.get("FileDescription", ""))
            chain = chain or chain_from_text(str(child))
            if not chain:
                continue
            version = infer_version_from_path(str(child)) or _file_version_short(str(exe))
            found.append(
                FoundInstall(
                    chain=canonical_chain(chain),
                    version=version,
                    path=str(exe),
                    product_name=info.get("ProductName", ""),
                    source="directory",
                )
            )
    return found


def _version_tuple(version: str) -> tuple[int, ...]:
    parts = []
    for piece in re.split(r"[.\-]", version):
        if piece.isdigit():
            parts.append(int(piece))
    return tuple(parts)


def scan_installed() -> list[FoundInstall]:
    merged: dict[str, FoundInstall] = {}
    for item in _scan_registry():
        merged.setdefault(os.path.normcase(os.path.abspath(item.path)), item)
    for item in _scan_directories():
        merged.setdefault(os.path.normcase(os.path.abspath(item.path)), item)

    order = {chain: index for index, chain in enumerate(KNOWN_CHAINS)}
    result = list(merged.values())
    result.sort(
        key=lambda item: (
            order.get(item.chain, len(order)),
            item.chain,
            tuple(-part for part in _version_tuple(item.version)),
        )
    )
    return result
