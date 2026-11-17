"""config.json v2：工具链、最近项目、外观与 v1 迁移。"""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .paths import default_config_path, ensure_parent

SCHEMA_VERSION = 2
KNOWN_CHAINS = ["ARM", "RX", "RH850", "RL78", "RISC-V", "MSP430"]
PRODUCTS = {
    "ARM": "EWARM",
    "RX": "EWRX",
    "RH850": "EWRH850",
    "RL78": "EWRL78",
    "RISC-V": "EW RISC-V",
    "MSP430": "EWMSP430",
}
THEMES = {"light", "dark", "system"}
ACCENTS = {"red", "teal", "blue", "indigo", "violet", "graphite"}
TITLEBAR_MODES = {"native", "custom"}
_VERSION_RE = re.compile(r"(?<![\d.])(\d+\.\d+(?:\.\d+)?)(?![\d.])")


def chain_key(chain: str) -> str:
    value = (chain or "").strip().upper().replace("_", "-")
    aliases = {
        "EWARM": "ARM",
        "IAR ARM": "ARM",
        "EWRX": "RX",
        "RENESAS RX": "RX",
        "EWRH850": "RH850",
        "RENESAS RH850": "RH850",
        "EWRL78": "RL78",
        "RENESAS RL78": "RL78",
        "EW RISCV": "RISC-V",
        "EW RISC-V": "RISC-V",
        "EWMSP430": "MSP430",
    }
    if value in aliases:
        return aliases[value]
    if value in {"RISCV", "RISC-V"}:
        return "RISC-V"
    return value


def canonical_chain(chain: str) -> str:
    key = chain_key(chain)
    if key in KNOWN_CHAINS:
        return key
    return (chain or "").strip()


def product_label(chain: str) -> str:
    key = chain_key(chain)
    return PRODUCTS.get(key, canonical_chain(chain) or chain)


def infer_version_from_path(path: str) -> str:
    text = str(path)
    matches = _VERSION_RE.findall(text)
    return matches[-1] if matches else ""


def _new_id(prefix: str = "tc") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _norm_path(path: str) -> str:
    try:
        return os.path.normcase(os.path.abspath(os.path.expandvars(path)))
    except Exception:
        return os.path.normcase(path)


@dataclass
class Toolchain:
    id: str
    chain: str
    version: str
    path: str
    added_at: float = field(default_factory=time.time)

    @property
    def key(self) -> str:
        return chain_key(self.chain)

    @property
    def available(self) -> bool:
        try:
            return Path(self.path).is_file()
        except OSError:
            return False

    @property
    def product(self) -> str:
        return product_label(self.chain)

    @property
    def label(self) -> str:
        return f"{self.product} {self.version}".strip()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "chain": self.chain,
            "version": self.version,
            "path": self.path,
            "added_at": self.added_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Toolchain":
        chain = canonical_chain(str(data.get("chain", "")))
        path = str(data.get("path", "")).strip()
        version = str(data.get("version", "")).strip() or infer_version_from_path(path)
        return cls(
            id=str(data.get("id") or _new_id()),
            chain=chain,
            version=version,
            path=path,
            added_at=float(data.get("added_at") or time.time()),
        )


@dataclass
class RecentProject:
    path: str
    name: str
    chain: str
    toolchain_id: str | None = None
    opened_at: float = field(default_factory=time.time)
    pinned: bool = False
    locked_to: str | None = None

    @property
    def key(self) -> str:
        return _norm_path(self.path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "chain": self.chain,
            "toolchain_id": self.toolchain_id,
            "opened_at": self.opened_at,
            "pinned": self.pinned,
            "locked_to": self.locked_to,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecentProject":
        return cls(
            path=str(data.get("path", "")),
            name=str(data.get("name") or Path(str(data.get("path", ""))).stem),
            chain=canonical_chain(str(data.get("chain", ""))),
            toolchain_id=data.get("toolchain_id") or None,
            opened_at=float(data.get("opened_at") or 0),
            pinned=bool(data.get("pinned")),
            locked_to=data.get("locked_to") or None,
        )


def toolchains_from_payload(payload: dict[str, Any]) -> list[Toolchain]:
    """从 v2 或 v1 配置内容中提取工具链，用于导入/迁移。"""
    entries: list[Toolchain] = []
    if isinstance(payload.get("toolchains"), list):
        for item in payload["toolchains"]:
            if isinstance(item, dict) and item.get("path"):
                entries.append(Toolchain.from_dict(item))
    elif isinstance(payload.get("iar_paths"), dict):
        for chain, path in payload["iar_paths"].items():
            if not path:
                continue
            entries.append(
                Toolchain(
                    id=_new_id("mig"),
                    chain=canonical_chain(str(chain)),
                    version=infer_version_from_path(str(path)),
                    path=str(path),
                )
            )
    return entries


class ConfigStore:
    def __init__(self, path: str | os.PathLike[str] | None = None, create: bool = True):
        self.path = Path(path).resolve() if path else default_config_path()
        self.toolchains: list[Toolchain] = []
        self.recent: list[RecentProject] = []
        self.settings: dict[str, Any] = {}
        self.migrated = False
        self.load(create=create)

    # ── 读写 ──
    def load(self, create: bool = True) -> None:
        if not self.path.exists():
            self.toolchains = []
            self.recent = []
            self.settings = {
            "appearance": {"theme": "light", "accent": "red", "titlebar": "custom"}
        }
            if create:
                self.save()
            return

        raw_text = self.path.read_text(encoding="utf-8")
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"config.json 不是有效的 JSON：{exc}") from exc

        if not isinstance(payload, dict):
            raise ValueError("config.json 顶层必须是对象")

        is_v1 = payload.get("schema", 1) < SCHEMA_VERSION and "iar_paths" in payload
        if is_v1:
            backup = self.path.with_name(self.path.name + ".v1.bak")
            if not backup.exists():
                try:
                    backup.write_text(raw_text, encoding="utf-8")
                except OSError:
                    pass
            self.migrated = True

        self.toolchains = toolchains_from_payload(payload)
        self.recent = [
            RecentProject.from_dict(item)
            for item in payload.get("recent_projects", [])
            if isinstance(item, dict) and item.get("path")
        ]
        settings = payload.get("settings")
        if not isinstance(settings, dict):
            settings = {}
            if isinstance(payload.get("default_config"), dict):
                settings.update(payload["default_config"])
        appearance = settings.get("appearance")
        if not isinstance(appearance, dict):
            appearance = {}
        theme = str(appearance.get("theme", "light"))
        accent = str(appearance.get("accent", "red"))
        titlebar = str(appearance.get("titlebar", "custom"))
        settings["appearance"] = {
            "theme": theme if theme in THEMES else "light",
            "accent": accent if accent in ACCENTS else "red",
            "titlebar": titlebar if titlebar in TITLEBAR_MODES else "custom",
        }
        self.settings = settings
        if is_v1:
            self.save()

    def save(self) -> None:
        ensure_parent(self.path)
        payload = {
            "schema": SCHEMA_VERSION,
            "toolchains": [entry.to_dict() for entry in self.toolchains],
            "recent_projects": [item.to_dict() for item in self.recent],
            "settings": self.settings,
        }
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    # ── 外观 ──
    @property
    def appearance(self) -> dict[str, str]:
        return self.settings.setdefault(
            "appearance", {"theme": "light", "accent": "red", "titlebar": "custom"}
        )

    def set_appearance(
        self,
        theme: str | None = None,
        accent: str | None = None,
        titlebar: str | None = None,
    ) -> None:
        if theme in THEMES:
            self.appearance["theme"] = theme
        if accent in ACCENTS:
            self.appearance["accent"] = accent
        if titlebar in TITLEBAR_MODES:
            self.appearance["titlebar"] = titlebar
        self.save()

    # ── 工具链 ──
    def toolchain(self, entry_id: str | None) -> Toolchain | None:
        if not entry_id:
            return None
        return next((entry for entry in self.toolchains if entry.id == entry_id), None)

    def entries_for_chain(self, chain: str) -> list[Toolchain]:
        key = chain_key(chain)
        return [entry for entry in self.toolchains if entry.key == key]

    def default_entry(self, chain: str) -> Toolchain | None:
        entries = self.entries_for_chain(chain)
        return entries[0] if entries else None

    def is_default(self, entry: Toolchain) -> bool:
        default = self.default_entry(entry.chain)
        return bool(default and default.id == entry.id)

    def add_toolchain(self, chain: str, version: str, path: str) -> Toolchain:
        entry = Toolchain(
            id=_new_id(),
            chain=canonical_chain(chain),
            version=version.strip() or infer_version_from_path(path),
            path=path.strip(),
        )
        self.toolchains.append(entry)
        self.save()
        return entry

    def update_toolchain(self, entry_id: str, chain: str, version: str, path: str) -> Toolchain | None:
        entry = self.toolchain(entry_id)
        if not entry:
            return None
        entry.chain = canonical_chain(chain)
        entry.version = version.strip() or infer_version_from_path(path)
        entry.path = path.strip()
        self.save()
        return entry

    def delete_toolchain(self, entry_id: str) -> None:
        self.toolchains = [entry for entry in self.toolchains if entry.id != entry_id]
        for item in self.recent:
            if item.locked_to == entry_id:
                item.locked_to = None
            if item.toolchain_id == entry_id:
                item.toolchain_id = None
        self.save()

    def toolchains_using(self, entry_id: str) -> int:
        count = 0
        for item in self.recent:
            if item.locked_to == entry_id:
                count += 1
            elif not item.locked_to and self.default_entry(item.chain) and self.default_entry(item.chain).id == entry_id:
                count += 1
        return count

    def import_toolchains(self, entries: list[Toolchain]) -> int:
        existing = {_norm_path(entry.path) for entry in self.toolchains}
        added = 0
        for entry in entries:
            key = _norm_path(entry.path)
            if not entry.path or key in existing:
                continue
            entry.id = _new_id("imp")
            self.toolchains.append(entry)
            existing.add(key)
            added += 1
        if added:
            self.save()
        return added

    def health(self) -> tuple[int, int]:
        good = sum(1 for entry in self.toolchains if entry.available)
        return good, len(self.toolchains)

    # ── 最近项目 ──
    def find_recent(self, path: str) -> RecentProject | None:
        key = _norm_path(path)
        return next((item for item in self.recent if item.key == key), None)

    def touch_recent(self, project, toolchain: Toolchain) -> RecentProject:
        key = _norm_path(str(project.path))
        item = next((entry for entry in self.recent if entry.key == key), None)
        now = time.time()
        if item is None:
            item = RecentProject(
                path=str(project.path),
                name=project.name,
                chain=project.chain,
                toolchain_id=toolchain.id,
                opened_at=now,
            )
            self.recent.append(item)
        else:
            item.name = project.name
            item.chain = project.chain
            item.toolchain_id = toolchain.id
            item.opened_at = now
        self.recent.sort(key=lambda entry: entry.opened_at, reverse=True)
        self.recent = self.recent[:60]
        self.save()
        return item

    def update_recent(self, path: str, **changes: Any) -> RecentProject | None:
        item = self.find_recent(path)
        if not item:
            return None
        for name, value in changes.items():
            if hasattr(item, name):
                setattr(item, name, value)
        self.save()
        return item

    def remove_recent(self, path: str) -> None:
        key = _norm_path(path)
        self.recent = [item for item in self.recent if item.key != key]
        self.save()

    def clear_recent(self) -> None:
        self.recent = []
        self.save()

    def set_lock(self, path: str, entry_id: str | None) -> None:
        item = self.find_recent(path)
        if item:
            item.locked_to = entry_id or None
            self.save()

    def toggle_pin(self, path: str) -> bool:
        item = self.find_recent(path)
        if not item:
            return False
        item.pinned = not item.pinned
        self.save()
        return item.pinned

    def sorted_recent(self) -> list[RecentProject]:
        return sorted(self.recent, key=lambda item: (0 if item.pinned else 1, -item.opened_at))
