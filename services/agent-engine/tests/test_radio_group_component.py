"""Tests for Task R-355: Generated Accessible Futuristic Reusable Radio Group Suite.

Verifies that NextjsWebAdapter emits an accessible, desktop-grade, zero-dependency, and futuristic
Radio Group compound component suite (apps/web/components/radio-group.tsx) supporting:
- WAI-ARIA 1.2 Radio Group pattern compliance (role="radiogroup", role="radio", aria-checked, aria-orientation, aria-disabled)
- Full arrow-key keyboard navigation with roving focus and wrap-around (ArrowDown/Right -> next, ArrowUp/Left -> prev)
- Layout orientations: vertical (default) and horizontal flex layouts
- 4 futuristic visual styling variants ("default", "card", "pill", "neon")
- 3 size scales ("sm", "md", "lg") with responsive radio circle, dot, and typography dimensions
- Controlled (value, onValueChange) and uncontrolled (defaultValue) state management
- Form integration via hidden input element
- Composite options prop convenience rendering alongside custom child items
- React ref forwarding (forwardRef) for group container and radio item buttons
- 100% diff-invariance across ir.description changes
- Zero external runtime dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_radio_group_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class RadioGroupComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the Radio Group component suite."""

    def setUp(self) -> None:
        self.code = render_radio_group_component()
        self.ir = example_ir("rideshare-favourites")

    def test_radio_group_is_client_component(self) -> None:
        """RadioGroup must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "RadioGroup must have 'use client' as the first statement.",
        )

    def test_radio_group_exports_types(self) -> None:
        """Verify export of TypeScript interfaces and union types."""
        self.assertIn("export type RadioGroupOrientation", self.code)
        self.assertIn('"vertical"', self.code)
        self.assertIn('"horizontal"', self.code)
        self.assertIn("export type RadioGroupVariant", self.code)
        self.assertIn('"default"', self.code)
        self.assertIn('"card"', self.code)
        self.assertIn('"pill"', self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn("export type RadioGroupSize", self.code)
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)
        self.assertIn("export interface RadioOption", self.code)
        self.assertIn("export interface RadioGroupProps", self.code)
        self.assertIn("export interface RadioGroupItemProps", self.code)
        self.assertIn("export interface RadioGroupContextValue", self.code)

    def test_radio_group_exports_components(self) -> None:
        """Verify RadioGroup, RadioGroupItem, Radio, and useRadioGroup exports."""
        self.assertIn("export const RadioGroup", self.code)
        self.assertIn('RadioGroup.displayName = "RadioGroup";', self.code)
        self.assertIn("export const RadioGroupItem", self.code)
        self.assertIn('RadioGroupItem.displayName = "RadioGroupItem";', self.code)
        self.assertIn("export const Radio = RadioGroupItem;", self.code)
        self.assertIn("export function useRadioGroup()", self.code)
        self.assertIn("export default RadioGroup;", self.code)

    def test_radio_group_zero_external_dependencies(self) -> None:
        """RadioGroup uses only React; zero external package imports."""
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
                f"Unexpected external import found in RadioGroup: {line}",
            )

    def test_radio_group_wai_aria_semantics(self) -> None:
        """Verify WAI-ARIA 1.2 radiogroup and radio attributes."""
        self.assertIn('role="radiogroup"', self.code)
        self.assertIn('role="radio"', self.code)
        self.assertIn("aria-checked={isChecked}", self.code)
        self.assertIn("aria-orientation={orientation}", self.code)
        self.assertIn("aria-disabled={disabled || undefined}", self.code)

    def test_radio_group_arrow_key_navigation(self) -> None:
        """Verify arrow key navigation with wrap-around in handleKeyDown."""
        self.assertIn('e.key === "ArrowDown" || e.key === "ArrowRight"', self.code)
        self.assertIn('e.key === "ArrowUp" || e.key === "ArrowLeft"', self.code)
        self.assertIn("e.preventDefault()", self.code)
        self.assertIn("itemsRef.current.get(nextVal)?.focus()", self.code)

    def test_radio_group_roving_focus_registration(self) -> None:
        """Verify item registration mechanism for roving focus."""
        self.assertIn("itemsRef = useRef<Map<string, HTMLButtonElement>>", self.code)
        self.assertIn("registerItem", self.code)
        self.assertIn("unregisterItem", self.code)

    def test_radio_group_visual_variants(self) -> None:
        """Verify 4 visual styling variants (default, card, pill, neon)."""
        self.assertIn('ctx.variant === "card"', self.code)
        self.assertIn('ctx.variant === "pill"', self.code)
        self.assertIn('ctx.variant === "neon"', self.code)
        self.assertIn("0 0 10px rgba(56, 189, 248, 0.5)", self.code)

    def test_radio_group_size_scales(self) -> None:
        """Verify 3 size scales for circle, dot, and typography."""
        self.assertIn('ctx.size === "sm" ? 16 : ctx.size === "lg" ? 24 : 20', self.code)
        self.assertIn('ctx.size === "sm" ? 6 : ctx.size === "lg" ? 10 : 8', self.code)

    def test_radio_group_orientations(self) -> None:
        """Verify vertical and horizontal flex layouts."""
        self.assertIn('orientation === "horizontal" ? "row" : "column"', self.code)
        self.assertIn('orientation === "horizontal" ? "center" : "stretch"', self.code)

    def test_radio_group_options_prop_support(self) -> None:
        """Verify options array mapping to RadioGroupItem."""
        self.assertIn("options.map((opt) => (", self.code)
        self.assertIn("label={opt.label}", self.code)
        self.assertIn("description={opt.description}", self.code)

    def test_radio_group_form_integration(self) -> None:
        """Verify hidden input rendering for native form submissions."""
        self.assertIn('type="hidden"', self.code)
        self.assertIn("name={name}", self.code)
        self.assertIn("value={currentValue ?? \"\"}", self.code)

    def test_radio_group_compound_attachment(self) -> None:
        """Verify forwardRef implementation on both group and item."""
        self.assertIn("forwardRef<HTMLDivElement, RadioGroupProps>", self.code)
        self.assertIn("forwardRef<HTMLButtonElement, RadioGroupItemProps>", self.code)

    def test_radio_group_diff_invariance(self) -> None:
        """Ensure code is 100% diff-invariant across IR description changes."""
        adapter = NextjsWebAdapter()
        project1 = adapter.generate(self.ir)
        ir2 = dataclasses.replace(
            self.ir, description="Completely changed description for diff test."
        )
        project2 = adapter.generate(ir2)
        c1 = project1.get("components/radio-group.tsx").content
        c2 = project2.get("components/radio-group.tsx").content
        self.assertEqual(
            c1,
            c2,
            "components/radio-group.tsx must be 100% diff-invariant across ir.description",
        )
        self.assertEqual(c1, self.code)

    def test_radio_group_emitted_by_adapter_and_exported(self) -> None:
        """NextjsWebAdapter must emit components/radio-group.tsx and export in cg.__all__."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/radio-group.tsx")
        self.assertIsNotNone(f, "components/radio-group.tsx must be generated")
        self.assertEqual(f.content, self.code)
        self.assertIn("render_radio_group_component", cg.__all__)
        self.assertTrue(callable(cg.render_radio_group_component))
        self.assertEqual(cg.render_radio_group_component(), self.code)


if __name__ == "__main__":
    unittest.main()
