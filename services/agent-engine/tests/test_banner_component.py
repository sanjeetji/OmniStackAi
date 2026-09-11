"""Tests for Task R-357: Generated Accessible Futuristic Reusable Announcement Banner & Callout Suite.

Verifies that NextjsWebAdapter emits an accessible, desktop-grade, zero-dependency, and futuristic
Announcement Banner & Callout compound component suite (apps/web/components/banner.tsx) supporting:
- WAI-ARIA live region compliance (role="status" / "alert" / "region", aria-live="polite" / "assertive" / "off")
- 4 layout positions ("top", "bottom", "inline", "floating")
- 6 visual styling variants ("info", "success", "warning", "error", "neon", "gradient")
- 3 size scales ("sm", "md", "lg") with responsive padding, typography, and icon metrics
- Dismissible state with onDismiss callback and accessible close button (aria-label="Dismiss banner")
- Action slot / CTA button container (BannerAction)
- Icon slot container (BannerIcon) and built-in SVG iconography for each variant
- Compound exports: Banner, BannerIcon, BannerAction, BannerCloseButton, AnnouncementBanner, Callout
- React ref forwarding (forwardRef) and displayName for all compound components
- 100% diff-invariance across ir.description changes
- Zero external runtime dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_banner_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class BannerComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the Banner component suite."""

    def setUp(self) -> None:
        self.code = render_banner_component()
        self.ir = example_ir("rideshare-favourites")

    def test_banner_is_client_component(self) -> None:
        """Banner must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "Banner must have 'use client' as the first statement.",
        )

    def test_banner_exports_types(self) -> None:
        """Verify export of TypeScript interfaces and union types."""
        self.assertIn("export type BannerVariant", self.code)
        self.assertIn('"info"', self.code)
        self.assertIn('"success"', self.code)
        self.assertIn('"warning"', self.code)
        self.assertIn('"error"', self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn('"gradient"', self.code)
        self.assertIn("export type BannerPosition", self.code)
        self.assertIn('"top"', self.code)
        self.assertIn('"bottom"', self.code)
        self.assertIn('"inline"', self.code)
        self.assertIn('"floating"', self.code)
        self.assertIn("export type BannerSize", self.code)
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)
        self.assertIn("export interface BannerProps", self.code)
        self.assertIn("export interface BannerCloseButtonProps", self.code)

    def test_banner_compound_exports(self) -> None:
        """Verify export of Banner compound components and semantic aliases."""
        self.assertIn("export const BannerIcon = forwardRef", self.code)
        self.assertIn("export const BannerAction = forwardRef", self.code)
        self.assertIn("export const BannerCloseButton = forwardRef", self.code)
        self.assertIn("export const Banner = forwardRef", self.code)
        self.assertIn("export const AnnouncementBanner = Banner;", self.code)
        self.assertIn("export const Callout = Banner;", self.code)
        self.assertIn("export default Banner;", self.code)

    def test_banner_display_names(self) -> None:
        """Verify displayName assignment for React devtools debugging."""
        self.assertIn('BannerIcon.displayName = "BannerIcon";', self.code)
        self.assertIn('BannerAction.displayName = "BannerAction";', self.code)
        self.assertIn('BannerCloseButton.displayName = "BannerCloseButton";', self.code)
        self.assertIn('Banner.displayName = "Banner";', self.code)

    def test_banner_accessibility_live_regions(self) -> None:
        """Verify WAI-ARIA live region semantics and defaults."""
        self.assertIn("role={effectiveRole}", self.code)
        self.assertIn("aria-live={effectiveAriaLive}", self.code)
        self.assertIn('variant === "error" || variant === "warning" ? "alert" : "status"', self.code)
        self.assertIn('variant === "error" || variant === "warning" ? "assertive" : "polite"', self.code)

    def test_banner_dismissible_close_button(self) -> None:
        """Verify dismissible close button semantics and behavior."""
        self.assertIn('aria-label="Dismiss banner"', self.code)
        self.assertIn("onDismiss?.()", self.code)
        self.assertIn("setVisible(false)", self.code)
        self.assertIn("if (!visible) return null;", self.code)

    def test_banner_position_styles(self) -> None:
        """Verify positioning rules: top, bottom, floating, inline."""
        self.assertIn('"sticky"', self.code)
        self.assertIn('"fixed"', self.code)
        self.assertIn('"translateX(-50%)"', self.code)
        self.assertIn("getPositionStyles", self.code)

    def test_banner_neon_and_cyberpunk_styling(self) -> None:
        """Verify futuristic neon and gradient styling tokens."""
        self.assertIn("0 0 20px rgba(56, 189, 248, 0.25)", self.code)
        self.assertIn("linear-gradient(135deg, #1e1b4b 0%, #0f172a 50%, #064e3b 100%)", self.code)

    def test_banner_size_scales(self) -> None:
        """Verify size scale definitions for sm, md, lg."""
        self.assertIn('sm: { padding: "8px 12px"', self.code)
        self.assertIn('md: { padding: "12px 16px"', self.code)
        self.assertIn('lg: { padding: "16px 20px"', self.code)

    def test_banner_svg_icons(self) -> None:
        """Verify built-in SVGs for status indicators and close button."""
        self.assertIn("InfoIcon", self.code)
        self.assertIn("SuccessIcon", self.code)
        self.assertIn("WarningIcon", self.code)
        self.assertIn("ErrorIcon", self.code)
        self.assertIn("NeonIcon", self.code)
        self.assertIn("CloseIcon", self.code)
        self.assertIn('aria-hidden="true"', self.code)

    def test_banner_zero_runtime_dependencies(self) -> None:
        """Banner component template must not import external third-party libraries."""
        lines = [line.strip() for line in self.code.split("\n") if line.strip().startswith("import ")]
        for line in lines:
            self.assertTrue(
                line.startswith('import React') or 'from "react"' in line,
                f"Unexpected external import detected: {line}",
            )

    def test_banner_adapter_emits_file(self) -> None:
        """NextjsWebAdapter must emit components/banner.tsx in the generated project."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/banner.tsx")
        self.assertIsNotNone(f)
        self.assertEqual(f.content, self.code)

    def test_banner_exported_from_codegen_package(self) -> None:
        """cg.render_banner_component must be exposed at package root."""
        self.assertTrue(callable(cg.render_banner_component))
        self.assertEqual(cg.render_banner_component(), self.code)

    def test_banner_diff_invariance(self) -> None:
        """Diff invariance: changing ir.description must not alter components/banner.tsx."""
        adapter = NextjsWebAdapter()
        project1 = adapter.generate(self.ir)
        f1 = project1.get("components/banner.tsx")

        ir_mutated = dataclasses.replace(
            self.ir,
            description="Completely different description for diff invariance test",
        )
        project2 = adapter.generate(ir_mutated)
        f2 = project2.get("components/banner.tsx")

        self.assertEqual(f1.content, f2.content)

    def test_banner_react_import_single_line(self) -> None:
        """Banner component should have React import on a single line."""
        lines = self.code.split("\n")
        react_import_lines = [l for l in lines if 'from "react"' in l]
        self.assertEqual(len(react_import_lines), 1)
        self.assertTrue(react_import_lines[0].startswith("import React"))


if __name__ == "__main__":
    unittest.main()
