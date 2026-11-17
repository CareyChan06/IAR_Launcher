from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from iar_launcher.core.config import (
    ConfigStore,
    RecentProject,
    Toolchain,
    chain_key,
    infer_version_from_path,
)
from iar_launcher.core.discovery import chain_from_text
from iar_launcher.core.project import ProjectParseError, parse_project


class ProjectParsingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.app = self.root / "App"
        self.app.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _write_ewp(self, name="Demo.ewp", chain="ARM"):
        ewp = self.app / name
        ewp.write_text(
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f"<project><configuration><name>Debug</name>"
            f"<toolchain><name>{chain}</name></toolchain>"
            f"</configuration></project>",
            encoding="utf-8",
        )
        return ewp

    def test_eww_with_ws_dir(self):
        self._write_ewp(chain="RX")
        eww = self.root / "Workspace.eww"
        eww.write_text(
            '<?xml version="1.0"?><workspace><project>'
            "<path>$WS_DIR$\\App\\Demo.ewp</path></project></workspace>",
            encoding="utf-8",
        )
        info = parse_project(eww)
        self.assertEqual(info.chain, "RX")
        self.assertEqual(info.launch_path, eww.resolve())
        self.assertEqual(info.ewp_path.name, "Demo.ewp")

    def test_eww_with_slash_token(self):
        self._write_ewp(chain="RISC-V")
        eww = self.root / "Workspace.eww"
        eww.write_text(
            "<workspace><project><path>$WS_DIR$/App/Demo.ewp</path></project></workspace>",
            encoding="utf-8",
        )
        self.assertEqual(parse_project(eww).chain, "RISC-V")

    def test_ewp_direct(self):
        ewp = self._write_ewp(chain="RL78")
        info = parse_project(ewp)
        self.assertEqual(info.chain, "RL78")
        self.assertEqual(info.launch_path, ewp.resolve())

    def test_missing_ewp(self):
        eww = self.root / "Workspace.eww"
        eww.write_text(
            "<workspace><project><path>$WS_DIR$\\Missing.ewp</path></project></workspace>",
            encoding="utf-8",
        )
        with self.assertRaises(ProjectParseError):
            parse_project(eww)


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "config.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_migrates_v1(self):
        v1 = {
            "iar_paths": {
                "ARM": r"C:\iar\ewarm-9.60.3\common\bin\IarIdePm.exe",
                "RH850": r"C:\IAR\RH850 3.10\common\bin\IarIdePm.exe",
            },
            "default_config": {"check_for_updates": True, "show_console_output": False},
        }
        self.path.write_text(json.dumps(v1), encoding="utf-8")
        store = ConfigStore(self.path)
        self.assertTrue(store.migrated)
        self.assertTrue(self.path.with_name("config.json.v1.bak").exists())
        self.assertEqual(len(store.toolchains), 2)
        self.assertEqual(store.toolchains[0].version, "9.60.3")
        self.assertEqual(store.toolchains[1].version, "3.10")
        reloaded = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(reloaded["schema"], 2)
        self.assertEqual(len(reloaded["toolchains"]), 2)

    def test_toolchain_crud_and_health(self):
        store = ConfigStore(self.path)
        missing = store.add_toolchain("RX", "8.4", str(Path(self.tmp.name) / "missing.exe"))
        self.assertFalse(missing.available)
        good_exe = Path(self.tmp.name) / "IarIdePm.exe"
        good_exe.write_bytes(b"")
        good = store.add_toolchain("ARM", "9.60.3", str(good_exe))
        self.assertTrue(good.available)
        self.assertEqual(store.health(), (1, 2))
        self.assertIs(store.default_entry("ARM"), good)
        store.set_appearance("dark", "teal")
        self.assertEqual(store.appearance["theme"], "dark")
        self.assertEqual(store.appearance["accent"], "teal")
        self.assertEqual(store.toolchains_using(good.id), 0)
        store.delete_toolchain(good.id)
        self.assertIsNone(store.toolchain(good.id))

    def test_recent_pin_and_lock(self):
        store = ConfigStore(self.path)
        exe = Path(self.tmp.name) / "IarIdePm.exe"
        exe.write_bytes(b"")
        arm = store.add_toolchain("ARM", "9.60.3", str(exe))

        class P:
            path = str(Path(self.tmp.name) / "Demo.eww")
            name = "Demo"
            chain = "ARM"

        store.touch_recent(P, arm)
        self.assertEqual(len(store.recent), 1)
        self.assertTrue(store.toggle_pin(P.path))
        store.set_lock(P.path, arm.id)
        self.assertEqual(store.find_recent(P.path).locked_to, arm.id)
        self.assertEqual(store.toolchains_using(arm.id), 1)
        store.remove_recent(P.path)
        self.assertEqual(store.recent, [])

    def test_sorted_recent_pins_first(self):
        store = ConfigStore(self.path)
        store.recent = [
            RecentProject("C:/a.eww", "A", "ARM", opened_at=10),
            RecentProject("C:/b.eww", "B", "RX", opened_at=20, pinned=True),
        ]
        self.assertEqual([item.name for item in store.sorted_recent()], ["B", "A"])


class DiscoveryTests(unittest.TestCase):
    def test_chain_from_text(self):
        cases = {
            "IAR Embedded Workbench for Arm": "ARM",
            "IAR Embedded Workbench for Renesas RX": "RX",
            "IAR Embedded Workbench for RH850": "RH850",
            "IAR Embedded Workbench for Renesas RL78": "RL78",
            "IAR Embedded Workbench for RISC-V": "RISC-V",
            "IAR Embedded Workbench for MSP430 7.10": "MSP430",
            "IAR Embedded Workbench for AVR": "AVR",
            "IAR Embedded Workbench for Renesas M16C and R8C": "M16C/R8C",
        }
        for text, expected in cases.items():
            self.assertEqual(chain_from_text(text), expected, text)

    def test_version_inference(self):
        self.assertEqual(
            infer_version_from_path(r"C:\iar\ewarm-9.60.3\common\bin\IarIdePm.exe"), "9.60.3"
        )
        self.assertEqual(
            infer_version_from_path(r"C:\Program Files (x86)\IAR Systems\Embedded Workbench 8.4\common\bin\IarIdePm.exe"),
            "8.4",
        )
        self.assertEqual(infer_version_from_path(r"C:\IAR\no-version\IarIdePm.exe"), "")

    def test_chain_key_aliases(self):
        self.assertEqual(chain_key("Renesas RX"), "RX")
        self.assertEqual(chain_key("EWARM"), "ARM")
        self.assertEqual(chain_key("risc-v"), "RISC-V")


if __name__ == "__main__":
    unittest.main()
