"""Tests for Task R-352: Generated Accessible Futuristic Reusable Aspect Ratio Component.

Verifies that NextjsWebAdapter emits an accessible, desktop-grade, zero-dependency, and futuristic
Aspect Ratio viewport container component (apps/web/components/aspect-ratio.tsx) supporting:
- Zero Cumulative Layout Shift (CLS) space reservation via padding-bottom percentage calculation
- Modern CSS aspectRatio layout engine acceleration
- Absolute full-bleed child container (position: absolute, inset: 0, 100% width and height)
- Ratio presets ("16/9", "4/3", "1/1", "21/9", "9/16", "3/2", "2/3") and direct numeric ratios
- 4 futuristic visual variants ("neon", "glass", "bordered", "minimal")
- Overflow clipping control (overflowHidden: boolean)
- Full React ref forwarding (forwardRef<HTMLDivElement, AspectRatioProps>)
- 100% diff-invariance across ir.description changes
- Zero external runtime dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_aspect_ratio_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class AspectRatioComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the Aspect Ratio viewport container component."""

    def setUp(self) -> None:
        self.code = render_aspect_ratio_component()
        self.ir = example_ir("rideshare-favourites")

    def test_aspect_ratio_is_client_component(self) -> None:
        """AspectRatio must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "AspectRatio must have 'use client' as the first statement.",
        )

    def test_aspect_ratio_exports_types(self) -> None:
        """Verify export of TypeScript interfaces and union types."""
        self.assertIn("export type AspectRatioPreset", self.code)
        self.assertIn('"16/9"', self.code)
        self.assertIn('"4/3"', self.code)
        self.assertIn('"1/1"', self.code)
        self.assertIn('"21/9"', self.code)
        self.assertIn('"9/16"', self.code)
        self.assertIn('"3/2"', self.code)
        self.assertIn('"2/3"', self.code)
        self.assertIn("export type AspectRatioVariant", self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"bordered"', self.code)
        self.assertIn('"minimal"', self.code)
        self.assertIn("export interface AspectRatioProps", self.code)

    def test_aspect_ratio_exports_component(self) -> None:
        """Verify AspectRatio component and default export."""
        self.assertIn("export const AspectRatio", self.code)
        self.assertIn('AspectRatio.displayName = "AspectRatio";', self.code)
        self.assertIn("export default AspectRatio;", self.code)

    def test_aspect_ratio_zero_external_dependencies(self) -> None:
        """AspectRatio uses only React; zero external package imports."""
        import_lines = [
            line.strip()
            for line in self.code.splitlines()
            if line.strip().startswith("import ")
        ]
        self.assertTrue(len(import_lines) >= 1)
        for line in import_lines:
            self.assertIn(
                'from "react"',
                line,
                f"Unexpected external import found in AspectRatio: {line}",
            )

    def test_aspect_ratio_numeric_ratio_support(self) -> None:
        """Verify direct numeric aspect ratio support in parseRatio."""
        self.assertIn("function parseRatio", self.code)
        self.assertIn('typeof ratio === "number"', self.code)
        self.assertIn("ratio > 0 ? ratio : 16 / 9", self.code)

    def test_aspect_ratio_preset_ratio_support(self) -> None:
        """Verify string preset parsing via slash delimiter."""
        self.assertIn('typeof ratio === "string"', self.code)
        self.assertIn('ratio.split("/")', self.code)
        self.assertIn("parts[0] / parts[1]", self.code)

    def test_aspect_ratio_padding_bottom_calculation(self) -> None:
        """Verify paddingBottom calculation fallback for zero CLS space reservation."""
        self.assertIn("paddingBottom = `${(1 / numericRatio) * 100}%`", self.code)
        self.assertIn("paddingBottom,", self.code)

    def test_aspect_ratio_css_aspect_ratio_property(self) -> None:
        """Verify modern CSS aspectRatio property acceleration in container style."""
        self.assertIn("aspectRatio: `${numericRatio}`", self.code)

    def test_aspect_ratio_absolute_child_container(self) -> None:
        """Verify full-bleed absolute child container inside the ratio viewport."""
        self.assertIn('data-testid="aspect-ratio-content"', self.code)
        self.assertIn('position: "absolute"', self.code)
        self.assertIn("inset: 0", self.code)
        self.assertIn('width: "100%"', self.code)
        self.assertIn('height: "100%"', self.code)

    def test_aspect_ratio_overflow_control(self) -> None:
        """Verify overflowHidden prop controls container overflow clipping."""
        self.assertIn("overflowHidden = true", self.code)
        self.assertIn('overflow: overflowHidden ? "hidden" : "visible"', self.code)

    def test_aspect_ratio_futuristic_variants(self) -> None:
        """Verify 4 futuristic styling variants and neon cyan glow."""
        self.assertIn("VARIANT_STYLES", self.code)
        self.assertIn("rgba(6, 182, 212, 0.4)", self.code)
        self.assertIn("rgba(6, 182, 212, 0.25)", self.code)
        self.assertIn("backdropFilter:", self.code)

    def test_aspect_ratio_custom_class_and_style(self) -> None:
        """Verify custom className and inline style merging."""
        self.assertIn("className={`relative w-full ${className}`.trim()}", self.code)
        self.assertIn("...variantStyle,", self.code)
        self.assertIn("...style,", self.code)

    def test_aspect_ratio_forward_ref(self) -> None:
        """Verify forwardRef implementation on the outer container."""
        self.assertIn("forwardRef<HTMLDivElement, AspectRatioProps>", self.code)
        self.assertIn("ref={ref}", self.code)

    def test_aspect_ratio_diff_invariance(self) -> None:
        """Ensure code is 100% diff-invariant across IR description changes."""
        adapter = NextjsWebAdapter()
        project1 = adapter.generate(self.ir)
        ir2 = dataclasses.replace(
            self.ir, description="Completely changed description for diff test."
        )
        project2 = adapter.generate(ir2)
        c1 = project1.get("components/aspect-ratio.tsx").content
        c2 = project2.get("components/aspect-ratio.tsx").content
        self.assertEqual(
            c1,
            c2,
            "components/aspect-ratio.tsx must be 100% diff-invariant across ir.description",
        )
        self.assertEqual(c1, self.code)

    def test_aspect_ratio_emitted_by_adapter(self) -> None:
        """NextjsWebAdapter must emit components/aspect-ratio.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/aspect-ratio.tsx")
        self.assertIsNotNone(f, "components/aspect-ratio.tsx must be generated")
        self.assertEqual(f.content, self.code)

    def test_aspect_ratio_exported_in_codegen_module(self) -> None:
        """Verify render_aspect_ratio_component is exported in cg.__all__ and callable."""
        self.assertIn("render_aspect_ratio_component", cg.__all__)
        self.assertTrue(callable(cg.render_aspect_ratio_component))
        rendered = cg.render_aspect_ratio_component()
        self.assertEqual(rendered, self.code)


if __name__ == "__main__":
    unittest.main()
