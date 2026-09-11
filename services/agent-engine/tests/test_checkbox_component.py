"""Tests for Task R-356: Generated Accessible Futuristic Reusable Checkbox & Checkbox Group Primitive.

Verifies that NextjsWebAdapter emits an accessible, desktop-grade, zero-dependency, and futuristic
Checkbox & Checkbox Group compound component suite (apps/web/components/checkbox.tsx) supporting:
- WAI-ARIA 1.2 Checkbox pattern compliance (role="checkbox", role="group", aria-checked="mixed" / boolean, aria-disabled)
- Tri-state / indeterminate support with dedicated SVG minus vector and checkmark vector
- Keyboard navigation (Space key toggling state with preventDefault)
- 4 futuristic visual styling variants ("default", "card", "pill", "neon")
- 3 size scales ("sm", "md", "lg") with responsive box, icon, and typography dimensions
- Controlled (checked, onCheckedChange) and uncontrolled (defaultChecked) state management
- CheckboxGroup compound container with multiple selection array management (value, onValueChange)
- Form integration via hidden input element
- React ref forwarding (forwardRef) and displayName for Checkbox and CheckboxGroup
- Subcomponent aliasing (CheckboxItem = Checkbox) and useCheckboxGroup context hook
- 100% diff-invariance across ir.description changes
- Zero external runtime dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_checkbox_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class CheckboxComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the Checkbox component suite."""

    def setUp(self) -> None:
        self.code = render_checkbox_component()
        self.ir = example_ir("rideshare-favourites")

    def test_checkbox_is_client_component(self) -> None:
        """Checkbox must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "Checkbox must have 'use client' as the first statement.",
        )

    def test_checkbox_exports_types(self) -> None:
        """Verify export of TypeScript interfaces and union types."""
        self.assertIn("export type CheckboxVariant", self.code)
        self.assertIn('"default"', self.code)
        self.assertIn('"card"', self.code)
        self.assertIn('"pill"', self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn("export type CheckboxSize", self.code)
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)
        self.assertIn("export type CheckedState", self.code)
        self.assertIn('boolean | "indeterminate"', self.code)
        self.assertIn("export interface CheckboxProps", self.code)
        self.assertIn("export interface CheckboxGroupProps", self.code)
        self.assertIn("export interface CheckboxGroupContextValue", self.code)

    def test_checkbox_exports_components(self) -> None:
        """Verify Checkbox, CheckboxGroup, CheckboxItem, and useCheckboxGroup exports."""
        self.assertIn("export const Checkbox", self.code)
        self.assertIn('Checkbox.displayName = "Checkbox";', self.code)
        self.assertIn("export const CheckboxItem = Checkbox;", self.code)
        self.assertIn("export const CheckboxGroup", self.code)
        self.assertIn('CheckboxGroup.displayName = "CheckboxGroup";', self.code)
        self.assertIn("export function useCheckboxGroup()", self.code)
        self.assertIn("export default Checkbox;", self.code)

    def test_checkbox_zero_external_dependencies(self) -> None:
        """Checkbox uses only React; zero external package imports."""
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
                f"Unexpected external import found in Checkbox: {line}",
            )

    def test_checkbox_wai_aria_semantics(self) -> None:
        """Verify WAI-ARIA 1.2 checkbox and group attributes."""
        self.assertIn('role="checkbox"', self.code)
        self.assertIn('role="group"', self.code)
        self.assertIn("aria-checked={ariaChecked}", self.code)
        self.assertIn('isIndeterminate ? "mixed" : isChecked', self.code)
        self.assertIn("aria-disabled={isDisabled || undefined}", self.code)
        self.assertIn("aria-required={required || undefined}", self.code)
        self.assertIn("aria-orientation={orientation}", self.code)

    def test_checkbox_space_key_toggle(self) -> None:
        """Verify Space key toggling with event.preventDefault()."""
        self.assertIn('e.key === " "', self.code)
        self.assertIn("e.preventDefault()", self.code)
        self.assertIn("toggle()", self.code)

    def test_checkbox_tri_state_svg_indicators(self) -> None:
        """Verify custom SVG checkmark and minus indicators."""
        self.assertIn('<polyline points="20 6 9 17 4 12" />', self.code)
        self.assertIn('<line x1="5" y1="12" x2="19" y2="12" />', self.code)
        self.assertIn("isIndeterminate", self.code)

    def test_checkbox_visual_variants(self) -> None:
        """Verify 4 visual styling variants (default, card, pill, neon)."""
        self.assertIn('effectiveVariant === "card"', self.code)
        self.assertIn('effectiveVariant === "pill"', self.code)
        self.assertIn('effectiveVariant === "neon"', self.code)
        self.assertIn("0 0 10px rgba(56, 189, 248, 0.5)", self.code)

    def test_checkbox_size_scales(self) -> None:
        """Verify 3 size scales for box, icon, and typography."""
        self.assertIn('effectiveSize === "sm" ? 14 : effectiveSize === "lg" ? 22 : 18', self.code)
        self.assertIn('effectiveSize === "sm" ? 10 : effectiveSize === "lg" ? 14 : 12', self.code)
        self.assertIn('effectiveSize === "sm" ? 12 : effectiveSize === "lg" ? 16 : 14', self.code)

    def test_checkbox_group_array_management(self) -> None:
        """Verify multi-select array management inside CheckboxGroup."""
        self.assertIn("group.value.includes(value)", self.code)
        self.assertIn("group.value.filter((v) => v !== value)", self.code)
        self.assertIn("group.onValueChange(next)", self.code)

    def test_checkbox_options_prop_support(self) -> None:
        """Verify options array mapping in CheckboxGroup."""
        self.assertIn("options.map((opt) => (", self.code)
        self.assertIn("label={opt.label}", self.code)
        self.assertIn("description={opt.description}", self.code)

    def test_checkbox_form_integration(self) -> None:
        """Verify hidden input rendering for native form submissions."""
        self.assertIn('type="hidden"', self.code)
        self.assertIn("name={effectiveName}", self.code)
        self.assertIn('value={isChecked ? value : ""}', self.code)

    def test_checkbox_compound_attachment(self) -> None:
        """Verify forwardRef implementation on both Checkbox and CheckboxGroup."""
        self.assertIn("forwardRef<HTMLButtonElement, CheckboxProps>", self.code)
        self.assertIn("forwardRef<HTMLDivElement, CheckboxGroupProps>", self.code)

    def test_checkbox_diff_invariance(self) -> None:
        """Ensure code is 100% diff-invariant across IR description changes."""
        adapter = NextjsWebAdapter()
        project1 = adapter.generate(self.ir)
        ir2 = dataclasses.replace(
            self.ir, description="Completely changed description for diff test."
        )
        project2 = adapter.generate(ir2)
        c1 = project1.get("components/checkbox.tsx").content
        c2 = project2.get("components/checkbox.tsx").content
        self.assertEqual(
            c1,
            c2,
            "components/checkbox.tsx must be 100% diff-invariant across ir.description",
        )
        self.assertEqual(c1, self.code)

    def test_checkbox_emitted_by_adapter_and_exported(self) -> None:
        """NextjsWebAdapter must emit components/checkbox.tsx and export in cg.__all__."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/checkbox.tsx")
        self.assertIsNotNone(f, "components/checkbox.tsx must be generated")
        self.assertEqual(f.content, self.code)
        self.assertIn("render_checkbox_component", cg.__all__)
        self.assertTrue(callable(cg.render_checkbox_component))
        self.assertEqual(cg.render_checkbox_component(), self.code)


if __name__ == "__main__":
    unittest.main()
