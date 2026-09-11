"""Tests for Task R-353: Generated Accessible Futuristic Reusable Separator Component.

Verifies that NextjsWebAdapter emits an accessible, desktop-grade, zero-dependency, and futuristic
Separator / Divider component (apps/web/components/separator.tsx) supporting:
- WAI-ARIA 1.2 Separator pattern compliance (decorative role="none" vs semantic role="separator" with aria-orientation)
- Horizontal and vertical orientations
- Thickness presets ("thin", "md", "thick") and custom pixel numbers
- Content / text label support along horizontal dividers with flexible alignment ("start", "center", "end")
- 5 futuristic visual styling variants ("neon", "glass", "gradient", "bordered", "minimal")
- Full React ref forwarding (forwardRef<HTMLDivElement, SeparatorProps>)
- 100% diff-invariance across ir.description changes
- Zero external runtime dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_separator_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class SeparatorComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the Separator component."""

    def setUp(self) -> None:
        self.code = render_separator_component()
        self.ir = example_ir("rideshare-favourites")

    def test_separator_is_client_component(self) -> None:
        """Separator must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "Separator must have 'use client' as the first statement.",
        )

    def test_separator_exports_types(self) -> None:
        """Verify export of TypeScript interfaces and union types."""
        self.assertIn("export type SeparatorOrientation", self.code)
        self.assertIn('"horizontal"', self.code)
        self.assertIn('"vertical"', self.code)
        self.assertIn("export type SeparatorVariant", self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"gradient"', self.code)
        self.assertIn('"bordered"', self.code)
        self.assertIn('"minimal"', self.code)
        self.assertIn("export type SeparatorThickness", self.code)
        self.assertIn('"thin"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"thick"', self.code)
        self.assertIn("export type SeparatorLabelAlign", self.code)
        self.assertIn("export interface SeparatorProps", self.code)

    def test_separator_exports_component(self) -> None:
        """Verify Separator component and default export."""
        self.assertIn("export const Separator", self.code)
        self.assertIn('Separator.displayName = "Separator";', self.code)
        self.assertIn("export default Separator;", self.code)

    def test_separator_zero_external_dependencies(self) -> None:
        """Separator uses only React; zero external package imports."""
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
                f"Unexpected external import found in Separator: {line}",
            )

    def test_separator_decorative_mode_semantics(self) -> None:
        """Verify decorative mode emits role='none' and aria-hidden='true'."""
        self.assertIn('role: "none"', self.code)
        self.assertIn('"aria-hidden": true', self.code)

    def test_separator_semantic_mode(self) -> None:
        """Verify non-decorative mode emits role='separator' and aria-orientation."""
        self.assertIn('role: "separator"', self.code)
        self.assertIn('"aria-orientation": orientation', self.code)

    def test_separator_horizontal_orientation(self) -> None:
        """Verify horizontal orientation styles and dimensions."""
        self.assertIn('orientation === "horizontal"', self.code)
        self.assertIn('width: "100%"', self.code)
        self.assertIn("marginTop: ", self.code)
        self.assertIn("marginBottom: ", self.code)

    def test_separator_vertical_orientation(self) -> None:
        """Verify vertical orientation styles and layout."""
        self.assertIn('alignSelf: "stretch"', self.code)
        self.assertIn('display: "inline-block"', self.code)
        self.assertIn('height: "100%"', self.code)

    def test_separator_thickness_presets(self) -> None:
        """Verify thickness presets ('thin', 'md', 'thick')."""
        self.assertIn('case "thick":', self.code)
        self.assertIn("return 4;", self.code)
        self.assertIn('case "md":', self.code)
        self.assertIn("return 2;", self.code)
        self.assertIn('case "thin":', self.code)
        self.assertIn("return 1;", self.code)

    def test_separator_numeric_thickness(self) -> None:
        """Verify custom numeric thickness handling in resolveThickness."""
        self.assertIn('typeof thickness === "number"', self.code)
        self.assertIn("thickness > 0 ? thickness : 1", self.code)

    def test_separator_labeled_divider(self) -> None:
        """Verify labeled divider rendering with flex-grow lines."""
        self.assertIn('data-testid="separator-label"', self.code)
        self.assertIn("content = label ?? children", self.code)
        self.assertIn("flexGrow: 1", self.code)

    def test_separator_label_align(self) -> None:
        """Verify labelAlign positioning ('start', 'center', 'end')."""
        self.assertIn('labelAlign === "start" ? 0 : 1', self.code)
        self.assertIn('labelAlign === "end" ? 0 : 1', self.code)

    def test_separator_visual_variants(self) -> None:
        """Verify 5 visual variants including neon glow and gradient fade."""
        self.assertIn("HORIZONTAL_VARIANT_STYLES", self.code)
        self.assertIn("VERTICAL_VARIANT_STYLES", self.code)
        self.assertIn("rgba(6, 182, 212, 0.6)", self.code)
        self.assertIn("rgba(6, 182, 212, 0.5)", self.code)
        self.assertIn("linear-gradient(90deg,", self.code)
        self.assertIn("linear-gradient(180deg,", self.code)
        self.assertIn("backdropFilter:", self.code)

    def test_separator_forward_ref(self) -> None:
        """Verify React forwardRef implementation."""
        self.assertIn("forwardRef<HTMLDivElement, SeparatorProps>", self.code)
        self.assertIn("ref={ref}", self.code)

    def test_separator_diff_invariance(self) -> None:
        """Ensure code is 100% diff-invariant across IR description changes."""
        adapter = NextjsWebAdapter()
        project1 = adapter.generate(self.ir)
        ir2 = dataclasses.replace(
            self.ir, description="Completely changed description for diff test."
        )
        project2 = adapter.generate(ir2)
        c1 = project1.get("components/separator.tsx").content
        c2 = project2.get("components/separator.tsx").content
        self.assertEqual(
            c1,
            c2,
            "components/separator.tsx must be 100% diff-invariant across ir.description",
        )
        self.assertEqual(c1, self.code)

    def test_separator_emitted_by_adapter_and_exported(self) -> None:
        """NextjsWebAdapter must emit components/separator.tsx and export in cg.__all__."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/separator.tsx")
        self.assertIsNotNone(f, "components/separator.tsx must be generated")
        self.assertEqual(f.content, self.code)
        self.assertIn("render_separator_component", cg.__all__)
        self.assertTrue(callable(cg.render_separator_component))
        self.assertEqual(cg.render_separator_component(), self.code)


if __name__ == "__main__":
    unittest.main()
