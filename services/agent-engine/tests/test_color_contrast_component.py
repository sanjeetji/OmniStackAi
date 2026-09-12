"""Tests for the Accessible Futuristic Color Contrast Checker Suite (components/color-contrast.tsx)."""

from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine import codegen as cg
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_color_contrast_component,
)


class TestColorContrastComponent(unittest.TestCase):
    """Unit tests for the Accessible Futuristic Color Contrast Checker Suite (R-408)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_color_contrast_component()

    def test_file_generated(self) -> None:
        project = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        self.assertIsNotNone(project.get("components/color-contrast.tsx"))

    def test_diff_invariance_and_codegen_export(self) -> None:
        proj1 = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        proj2 = NextjsWebAdapter().generate(example_ir("rideshare-favourites"))
        f1 = proj1.get("components/color-contrast.tsx")
        f2 = proj2.get("components/color-contrast.tsx")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, render_color_contrast_component())

    def test_use_client_directive(self) -> None:
        self.assertTrue(self.source.startswith("'use client';"))

    def test_zero_runtime_dependencies(self) -> None:
        for pkg in re.findall(r"from\s+['\"]([^'\"]+)['\"]", self.source):
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected import: {pkg}",
            )

    def test_forward_ref_and_imperative_handle(self) -> None:
        self.assertIn("forwardRef<ColorContrastHandle, ColorContrastProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        for method in ("getRatio:", "getResult:", "setColors:", "swap:"):
            self.assertIn(method, self.source)

    def test_typescript_types_present(self) -> None:
        for decl in (
            "export type ColorContrastVariant",
            "export type ColorContrastSize",
            "export interface ContrastResult",
            "export interface ColorContrastHandle",
            "export interface ColorContrastProps",
        ):
            self.assertIn(decl, self.source)

    def test_compound_and_alias_exports(self) -> None:
        for decl in (
            "export const ColorContrast =",
            "export const ContrastChecker =",
            "export const WcagContrast =",
            "export const ContrastRatio =",
            "export default ColorContrastComponent",
        ):
            self.assertIn(decl, self.source)

    def test_display_names_defined(self) -> None:
        for line in (
            "ColorContrastComponent.displayName = 'ColorContrast'",
            "ContrastChecker.displayName = 'ContrastChecker'",
            "WcagContrast.displayName = 'WcagContrast'",
            "ContrastRatio.displayName = 'ContrastRatio'",
        ):
            self.assertIn(line, self.source)

    def test_variants_present(self) -> None:
        self.assertIn("'default' | 'card' | 'glass' | 'neon'", self.source)
        for key in ("default: {", "card: {", "glass: {", "neon: {"):
            self.assertIn(key, self.source)

    def test_sizes_present(self) -> None:
        self.assertIn("'sm' | 'md' | 'lg'", self.source)
        for key in ("sm: {", "md: {", "lg: {"):
            self.assertIn(key, self.source)

    def test_luminance_algorithm(self) -> None:
        for token in ("0.2126", "0.7152", "0.0722", "Math.pow"):
            self.assertIn(token, self.source)

    def test_contrast_ratio(self) -> None:
        self.assertIn("contrastRatio", self.source)
        self.assertIn("0.05", self.source)

    def test_wcag_thresholds(self) -> None:
        for token in ("4.5", "7", "aaNormal", "aaaNormal", "aaLarge"):
            self.assertIn(token, self.source)

    def test_hex_parsing(self) -> None:
        self.assertIn("parseHex", self.source)

    def test_color_inputs(self) -> None:
        self.assertIn('type="color"', self.source)
        self.assertIn("foreground", self.source)
        self.assertIn("background", self.source)

    def test_aria_status(self) -> None:
        self.assertIn('role="status"', self.source)
        self.assertIn("aria-live", self.source)
        self.assertIn("aria-label", self.source)

    def test_callbacks_and_controlled(self) -> None:
        for token in ("onChange", "defaultForeground", "foreground"):
            self.assertIn(token, self.source)

    def test_package_codegen_export(self) -> None:
        self.assertTrue(hasattr(cg, "render_color_contrast_component"))
        self.assertTrue(callable(cg.render_color_contrast_component))
        self.assertIn("render_color_contrast_component", cg.__all__)


if __name__ == "__main__":
    unittest.main()
