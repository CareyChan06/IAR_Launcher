"""HKCU 文件关联（尽力而为，不绕过 Windows UserChoice）。"""
from __future__ import annotations

import ctypes
import os
import sys
import winreg
from pathlib import Path

PROG_ID = "IARLauncher.eww"
EXTS = (".eww", ".ewp")
USER_CHOICE = r"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{ext}\UserChoice"
CLASSES = r"Software\Classes"


def app_executable() -> str | None:
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).resolve())
    return None


def _set_default(key_path: str, value: str) -> None:
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, value)


def _set_value(key_path: str, name: str, value: str) -> None:
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)


def _query_default(key_path: str) -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            value, _ = winreg.QueryValueEx(key, "")
            return str(value or "")
    except OSError:
        return ""


def _query_value(key_path: str, name: str) -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            value, _ = winreg.QueryValueEx(key, name)
            return str(value or "")
    except OSError:
        return ""


def _command_target(prog_id: str) -> str:
    command = _query_default(f"{CLASSES}\\{prog_id}\\shell\\open\\command").strip()
    if not command:
        return ""
    if command.startswith('"'):
        end = command.find('"', 1)
        return command[1:end] if end > 0 else ""
    return command.split(" ", 1)[0]


def _prog_id_is_ours(prog_id: str) -> bool:
    if prog_id == PROG_ID:
        return True
    exe = app_executable()
    if not exe:
        return False
    target = _command_target(prog_id)
    if not target:
        return False
    try:
        return os.path.normcase(os.path.abspath(target)) == os.path.normcase(os.path.abspath(exe))
    except OSError:
        return False


def _notify_shell() -> None:
    try:
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
    except Exception:
        pass


def register(exe_path: str) -> tuple[bool, str]:
    exe = str(Path(exe_path).resolve())
    if not Path(exe).is_file():
        return False, f"可执行文件不存在：{exe}"

    try:
        base = f"{CLASSES}\\{PROG_ID}"
        _set_default(base, "IAR Workspace")
        _set_default(f"{base}\\DefaultIcon", f'"{exe}",0')
        _set_default(f"{base}\\shell\\open\\command", f'"{exe}" "%1"')
        for ext in EXTS:
            ext_key = f"{CLASSES}\\{ext}"
            _set_default(ext_key, PROG_ID)
            _set_value(ext_key + r"\OpenWithProgids", PROG_ID, "")
        _notify_shell()
    except OSError as exc:
        return False, f"写入注册表失败：{exc}"

    status = query_status()
    if status["state"] == "ours":
        return True, "已注册到当前用户"
    if status["state"] in {"other", "partial"}:
        return (
            True,
            f"已写入注册表，但 Windows 仍保留部分旧关联（{status['detail']}）。"
            "请在“默认应用”里把 .eww / .ewp 改成 IAR Launcher。",
        )
    return True, "已注册到当前用户"


def query_status() -> dict[str, str]:
    details: list[str] = []
    states: list[str] = []
    for ext in EXTS:
        user_prog = _query_value(USER_CHOICE.format(ext=ext), "ProgId")
        if user_prog:
            if _prog_id_is_ours(user_prog):
                states.append("ours")
            else:
                states.append("other")
                details.append(user_prog)
            continue
        default = _query_default(f"{CLASSES}\\{ext}")
        if default == PROG_ID:
            states.append("ours")
        elif default:
            states.append("other")
            details.append(default)
        else:
            states.append("unset")

    unique = set(states)
    if unique == {"ours"}:
        return {"state": "ours", "detail": "已关联 .eww 和 .ewp"}
    if "other" in unique:
        if "ours" in unique:
            return {"state": "partial", "detail": "、".join(sorted(set(details)))}
        return {"state": "other", "detail": "、".join(sorted(set(details))) or "其他程序"}
    if "unset" in unique and "ours" not in unique:
        return {"state": "unset", "detail": "尚未关联"}
    return {"state": "partial", "detail": "部分关联"}


def open_default_apps() -> bool:
    try:
        os.startfile("ms-settings:defaultapps")
        return True
    except OSError:
        return False
