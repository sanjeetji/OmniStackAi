"""PC-020: one place to change a built product's look - name, colours, fonts, corners, style, logo - and
every app follows."""

import base64
import json
import os
import struct
import tempfile
import zlib
from dataclasses import replace
from pathlib import Path
from unittest import TestCase, mock

from omnistackai_agent_engine.application_ir import ApplicationIR, MobileProfile
from omnistackai_agent_engine.studio import brand_kit

FIXTURE = Path(__file__).parent / "fixtures" / "ir" / "hiring_portal.json"


def _png() -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * 4 for _ in range(4))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 4, 8, 2, 0, 0, 0)) + \
        chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def _data_url(data: bytes, kind: str = "png") -> str:
    return f"data:image/{'png' if kind == 'png' else 'svg+xml'};base64," + base64.b64encode(data).decode()


class _Project(TestCase):
    def setUp(self) -> None:
        from omnistackai_agent_engine.intake.build_app import build_app_from_ir

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        ir = ApplicationIR.from_dict(json.loads(FIXTURE.read_text()))
        ir = replace(ir, project_strategy=replace(ir.project_strategy, mobile_profile=MobileProfile.REACT_NATIVE))
        with mock.patch.dict(os.environ, {"OMNISTACKAI_BUILD_VERIFY": "off"}):
            built = build_app_from_ir(ir, Path(self.tmp.name) / "repo", author_name="t", author_email="t@example.com",
                                      prompt="A shop")
        self.repo = Path(built.target_dir)


class ChangingTheBrand(_Project):
    def test_read(self) -> None:
        brand = brand_kit.read_brand(self.repo)
        self.assertEqual(brand["name"], "Hiring Portal")
        self.assertIn("web", brand["apps"])
        self.assertIn("Inter", brand["choices"]["fonts"])

    def test_name_colours_and_a_logo_reach_every_app(self) -> None:
        result = brand_kit.update_brand(self.repo, {"name": "Kaari Studio", "primary_color": "#7C3AED", "font": "Outfit",
                                                    "radius": "xl", "logo": _data_url(_png())})
        document = json.loads((self.repo / "brand.json").read_text())
        self.assertEqual((document["name"], document["primaryColor"], document["fontFamily"], document["borderRadius"]),
                         ("Kaari Studio", "#7c3aed", "Outfit", "xl"))
        self.assertEqual(document["logo"], "/brand-logo.png")
        for path in ("brand/logo.png", "apps/web/public/brand-logo.png", "apps/web/app/icon.png",
                     "apps/admin/public/brand-logo.png", "apps/mobile/assets/icon.png"):
            with self.subTest(path=path):
                self.assertTrue((self.repo / path).exists())
        self.assertFalse((self.repo / "apps/web/app/icon.svg").exists(), "a tab icon is svg or png, never both")
        self.assertGreater(result["renamed_files"], 0)
        pages = "".join(p.read_text(errors="replace") for p in (self.repo / "apps" / "web").rglob("*.tsx")
                        if "node_modules" not in p.parts)
        self.assertNotIn("Hiring Portal", pages)
        self.assertIn("Kaari Studio", pages)
        self.assertTrue(result["commit_sha"])

    def test_bad_input_is_refused_and_nothing_changes(self) -> None:
        before = (self.repo / "brand.json").read_text()
        for changes in ({"primary_color": "red"}, {"font": "Comic Sans"}, {"name": "<script>"}, {"radius": "huge"},
                        {"logo": "data:image/gif;base64,R0lGOD"}, {}):
            with self.subTest(changes=changes), self.assertRaises(brand_kit.BrandError):
                brand_kit.update_brand(self.repo, changes)
        self.assertEqual((self.repo / "brand.json").read_text(), before)

    def test_an_svg_with_a_script_is_not_a_logo(self) -> None:
        with self.assertRaises(brand_kit.BrandError):
            brand_kit.decode_logo(_data_url(b'<svg onload="alert(1)"></svg>', "svg"))
        self.assertEqual(brand_kit.decode_logo(_data_url(b'<svg viewBox="0 0 1 1"><rect/></svg>', "svg")).kind, "svg")

    def test_removing_the_logo(self) -> None:
        brand_kit.update_brand(self.repo, {"logo": _data_url(_png())})
        brand_kit.update_brand(self.repo, {"remove_logo": True})
        self.assertNotIn("logo", json.loads((self.repo / "brand.json").read_text()))
        self.assertFalse((self.repo / "apps/web/public/brand-logo.png").exists())


class TheHeaderReadsTheBrand(_Project):
    def test_the_generated_header_uses_brand_json(self) -> None:
        navbar = (self.repo / "apps/web/components/navbar.tsx").read_text()
        self.assertIn('import { brandLogo, brandName } from "@/lib/brand";', navbar)
        self.assertIn("{brandLogo ? <img src={brandLogo}", navbar)
        self.assertIn('{brandName || "Hiring Portal"}', navbar)
        self.assertIn("export const brandLogo", (self.repo / "apps/web/lib/brand.ts").read_text())

    def test_it_type_checks(self) -> None:
        import subprocess

        cache = Path.home() / ".omnistackai" / "web-typecheck" / "node_modules"
        if not (cache / ".bin" / "tsc").exists():
            self.skipTest("no type-check cache on this machine")
        web = self.repo / "apps" / "web"
        (web / "node_modules").symlink_to(cache)
        brand_kit.update_brand(self.repo, {"logo": _data_url(_png())})
        done = subprocess.run([str(cache / ".bin" / "tsc"), "--noEmit", "--pretty", "false"], cwd=web,
                              capture_output=True, text=True, timeout=600)
        errors = [line for line in done.stdout.splitlines() if "navbar" in line or "lib/brand" in line]
        self.assertEqual(errors, [], done.stdout[-1500:])
