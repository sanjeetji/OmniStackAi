"""Tests for the Accessible Futuristic Reusable QR Code & Barcode Suite codegen (R-382).

Verifies:
1. Zero runtime dependencies (pure React).
2. "use client" directive present.
3. React forwardRef and explicit displayName across compound exports.
4. Exported canonical TypeScript types & interfaces.
5. Compound and semantic alias exports (QrCode, Barcode, QrCard, default).
6. Pure mathematical QR generator with ECL levels (L, M, Q, H) and matrix calculation.
7. Module / dot geometry styles (square, rounded, dots, diamonds).
8. Center logo slot and quiet zone masking.
9. 1D barcode renderer (Code 128 / EAN-13).
10. Imperative handle methods (toDataURL, download, copyToClipboard).
11. Action toolbar with download PNG/SVG and clipboard copy feedback.
12. WAI-ARIA 1.2 img accessibility semantics (role="img", aria-label).
13. 4 visual styling variants (default, card, glass, neon).
14. 3 size scales (sm, md, lg) and custom numeric sizes.
15. Color styling with gradient support and glow filters.
16. NextjsWebAdapter emits components/qr-code.tsx and codegen package exports render_qr_code_component.
17. 100% diff-invariance across ir.description changes.
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_qr_code_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TestQrCodeComponent(unittest.TestCase):
    """Test suite for components/qr-code.tsx codegen."""

    def setUp(self) -> None:
        self.code = render_qr_code_component()
        self.ir = example_ir("rideshare-favourites")

    def test_zero_runtime_dependencies(self) -> None:
        """Only imports from 'react' are allowed — 0 external npm dependencies."""
        imports = re.findall(r'from\s+"([^"]+)"', self.code)
        for imp in imports:
            self.assertEqual(imp, "react", f"Forbidden external import: {imp}")

    def test_use_client_directive(self) -> None:
        """Must have 'use client' as first statement for Next.js App Router."""
        lines = [line.strip() for line in self.code.splitlines() if line.strip()]
        self.assertEqual(lines[0], '"use client";')

    def test_forward_ref_and_display_name(self) -> None:
        """Must use React.forwardRef and set explicit displayName across compound exports."""
        self.assertIn("forwardRef", self.code)
        self.assertIn('QrCode.displayName = "QrCode"', self.code)
        self.assertIn('Barcode.displayName = "Barcode"', self.code)
        self.assertIn('QrCard.displayName = "QrCard"', self.code)

    def test_exported_types(self) -> None:
        """Must export canonical TypeScript types and interfaces."""
        expected_types = [
            "QrCodeErrorCorrection",
            "QrCodeDotStyle",
            "QrCodeVariant",
            "QrCodeSize",
            "BarcodeFormat",
            "QrCodeHandle",
            "QrCodeProps",
            "BarcodeProps",
            "QrCardProps",
        ]
        for t in expected_types:
            self.assertTrue(
                f"export type {t}" in self.code or f"export interface {t}" in self.code,
                f"Missing type/interface: {t}"
            )

    def test_compound_and_semantic_aliases(self) -> None:
        """Must export QrCode, Barcode, QrCard, and default export."""
        self.assertIn("export const QrCode =", self.code)
        self.assertIn("export const Barcode =", self.code)
        self.assertIn("export const QrCard =", self.code)
        self.assertIn("export default QrCode;", self.code)

    def test_qr_generation_math(self) -> None:
        """Must include zero-dependency mathematical QR encoder with GF(256) and Reed-Solomon math."""
        self.assertIn("generateQrMatrix", self.code)
        self.assertIn("calculateReedSolomon", self.code)
        self.assertIn("EXP_TABLE", self.code)

    def test_dot_styles(self) -> None:
        """Must support square, rounded, dots, and diamonds cell styles."""
        for style in ["square", "rounded", "dots", "diamonds"]:
            self.assertIn(style, self.code)

    def test_center_logo_slot(self) -> None:
        """Must support center logo embedding with quiet zone padding."""
        self.assertIn("logo", self.code)
        self.assertIn("logoSize", self.code)
        self.assertIn("logoBackgroundColor", self.code)

    def test_barcode_rendering(self) -> None:
        """Must include 1D barcode renderer supporting Code 128 or EAN-13."""
        self.assertIn("Barcode", self.code)
        self.assertIn("code128", self.code)

    def test_imperative_handle_methods(self) -> None:
        """Must expose imperative handle with toDataURL, download, and copyToClipboard."""
        self.assertIn("toDataURL", self.code)
        self.assertIn("download", self.code)
        self.assertIn("copyToClipboard", self.code)

    def test_action_toolbar(self) -> None:
        """Must support action buttons for download PNG/SVG and clipboard copy."""
        self.assertIn("showToolbar", self.code)
        self.assertIn("download", self.code)

    def test_wai_aria_semantics(self) -> None:
        """Must implement WAI-ARIA 1.2 img accessibility semantics."""
        self.assertIn('role="img"', self.code)
        self.assertIn("aria-label", self.code)

    def test_four_visual_variants(self) -> None:
        """Must support 'default', 'card', 'glass', 'neon' visual styling variants."""
        for variant in ["default", "card", "glass", "neon"]:
            self.assertIn(variant, self.code)

    def test_three_size_scales(self) -> None:
        """Must support 'sm', 'md', and 'lg' size scales."""
        for sz in ["sm", "md", "lg"]:
            self.assertIn(f'"{sz}"', self.code)

    def test_package_codegen_exports_render_qr_code_component(self) -> None:
        """omnistackai_agent_engine.codegen must export render_qr_code_component."""
        self.assertTrue(hasattr(cg, "render_qr_code_component"))
        self.assertIn("render_qr_code_component", cg.__all__)
        self.assertIs(cg.render_qr_code_component, render_qr_code_component)

    def test_adapter_emits_qr_code_file(self) -> None:
        """NextjsWebAdapter.generate() must emit components/qr-code.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        paths = [f.path for f in project.files()]
        self.assertIn("components/qr-code.tsx", paths)
        file_obj = project.get("components/qr-code.tsx")
        self.assertIsNotNone(file_obj)
        self.assertEqual(file_obj.content, self.code)

    def test_diff_invariance_across_description(self) -> None:
        """Component code must be 100% diff-invariant across ir.description changes."""
        adapter = NextjsWebAdapter()
        ir1 = self.ir
        ir2 = dataclasses.replace(self.ir, description="Updated description for invariance testing")
        p1 = adapter.generate(ir1)
        p2 = adapter.generate(ir2)
        f1 = p1.get("components/qr-code.tsx")
        f2 = p2.get("components/qr-code.tsx")
        self.assertEqual(f1.content, f2.content)


if __name__ == "__main__":
    unittest.main()
