"""Tests for Task R-342: Generated Accessible Futuristic Reusable Segmented Control & Mode Switcher Component.

Verifies that NextjsWebAdapter emits an accessible, futuristic, reusable SegmentedControl compound component
suite (apps/web/components/segmented-control.tsx) supporting:
- SegmentedControl compound component with sliding pill indicator animation
- Options support labels, icons, disabled state, and notification badges
- 4 futuristic visual variants ("neon", "glass", "pills", "minimal")
- 3 size presets ("sm", "md", "lg")
- Controlled and uncontrolled operation modes
- Full keyboard navigation (ArrowLeft/ArrowRight cycling, Home/End jump)
- Full WAI-ARIA accessibility semantics (role="radiogroup", role="radio", aria-checked, aria-disabled)
- 100% diff-invariance across ir.description changes
- Zero external runtime dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_segmented_control_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class SegmentedControlComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the SegmentedControl component."""

    def setUp(self) -> None:
        self.code = render_segmented_control_component()
        self.ir = example_ir("rideshare-favourites")

    def test_segmented_control_component_is_client_component(self) -> None:
        """The SegmentedControl component must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "SegmentedControl must have 'use client' as the first statement.",
        )

    def test_segmented_control_component_exports_types(self) -> None:
        """Verify export of TypeScript interfaces and union types."""
        self.assertIn("export type SegmentedControlVariant", self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"pills"', self.code)
        self.assertIn('"minimal"', self.code)
        self.assertIn("export type SegmentedControlSize", self.code)
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)
        self.assertIn("export type SegmentedControlOrientation", self.code)
        self.assertIn("export interface SegmentedControlOption", self.code)
        self.assertIn("export interface SegmentedControlProps", self.code)
        self.assertIn("export interface SegmentedControlOptionItemProps", self.code)

    def test_segmented_control_component_exports_compound(self) -> None:
        """Verify SegmentedControl compound component and default export."""
        self.assertIn("export const SegmentedControl =", self.code)
        self.assertIn("(SegmentedControl as any).Option = SegmentedControlOptionItem;", self.code)
        self.assertIn("export default SegmentedControl;", self.code)

    def test_segmented_control_zero_external_dependencies(self) -> None:
        """SegmentedControl uses only React; zero external package imports."""
        import_lines = [
            line for line in self.code.splitlines() if line.startswith("import ")
        ]
        self.assertTrue(len(import_lines) >= 1)
        for line in import_lines:
            self.assertIn(
                'from "react"',
                line,
                f"Unexpected external import in SegmentedControl component: {line}",
            )

    def test_segmented_control_wai_aria_radiogroup_semantics(self) -> None:
        """Verify WAI-ARIA radiogroup and radio attributes."""
        self.assertIn('role="radiogroup"', self.code)
        self.assertIn('role="radio"', self.code)
        self.assertIn("aria-checked={isSelected}", self.code)
        self.assertIn("aria-disabled={isDisabled}", self.code)
        self.assertIn("aria-label={option.ariaLabel}", self.code)
        self.assertIn("tabIndex={tabIndex}", self.code)

    def test_segmented_control_keyboard_navigation(self) -> None:
        """Verify Arrow and Home/End keydown navigation support."""
        self.assertIn('"ArrowLeft"', self.code)
        self.assertIn('"ArrowRight"', self.code)
        self.assertIn('"ArrowUp"', self.code)
        self.assertIn('"ArrowDown"', self.code)
        self.assertIn('"Home"', self.code)
        self.assertIn('"End"', self.code)

    def test_segmented_control_sliding_pill_indicator(self) -> None:
        """Verify animated indicator element with bounding rect tracking."""
        self.assertIn("/* Animated Sliding Pill Indicator */", self.code)
        self.assertIn("getBoundingClientRect()", self.code)
        self.assertIn("cubic-bezier(0.4, 0, 0.2, 1)", self.code)

    def test_segmented_control_option_badges_and_icons(self) -> None:
        """Verify badge and icon rendering slots."""
        self.assertIn("{option.icon && (", self.code)
        self.assertIn("{option.badge !== undefined && (", self.code)

    def test_segmented_control_size_presets(self) -> None:
        """Verify height and padding presets for sm, md, and lg sizes."""
        self.assertIn('containerHeight: "28px"', self.code)
        self.assertIn('containerHeight: "36px"', self.code)
        self.assertIn('containerHeight: "44px"', self.code)

    def test_segmented_control_hidden_form_input(self) -> None:
        """Verify hidden input field support for form submissions."""
        self.assertIn('<input', self.code)
        self.assertIn('type="hidden"', self.code)
        self.assertIn('name={name}', self.code)

    def test_segmented_control_exported_in_codegen_init(self) -> None:
        """Verify render_segmented_control_component is exported in omnistackai_agent_engine.codegen."""
        self.assertTrue(callable(getattr(cg, "render_segmented_control_component", None)))
        self.assertIn("render_segmented_control_component", cg.__all__)

    def test_segmented_control_emitted_by_adapter(self) -> None:
        """Verify NextjsWebAdapter emits components/segmented-control.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/segmented-control.tsx")
        self.assertIsNotNone(f, "components/segmented-control.tsx must be generated")
        self.assertEqual(f.content, self.code)

    def test_segmented_control_diff_invariance(self) -> None:
        """Verify 100% diff-invariance across ApplicationIR description changes."""
        mutated_ir = dataclasses.replace(
            self.ir,
            description="Completely mutated description with unpredictable tokens",
        )
        adapter = NextjsWebAdapter()
        f1 = adapter.generate(self.ir).get("components/segmented-control.tsx")
        f2 = adapter.generate(mutated_ir).get("components/segmented-control.tsx")

        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(self.code, f1.content)
        self.assertEqual(f1.content, f2.content)

    def test_segmented_control_controlled_and_uncontrolled_modes(self) -> None:
        """Verify controlled value and defaultValue state management."""
        self.assertIn("value: controlledValue", self.code)
        self.assertIn("defaultValue", self.code)
        self.assertIn("isControlled ? controlledValue : uncontrolledValue", self.code)

    def test_segmented_control_orientation_support(self) -> None:
        """Verify horizontal and vertical orientation flexibility."""
        self.assertIn('orientation === "vertical" ? "column" : "row"', self.code)


if __name__ == "__main__":
    unittest.main()
