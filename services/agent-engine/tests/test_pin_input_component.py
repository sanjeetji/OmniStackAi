"""Tests for Task R-346: Generated Accessible Futuristic Reusable PIN & OTP Code Input Component.

Verifies that NextjsWebAdapter emits an accessible, futuristic, reusable PIN & OTP Code Input
component suite (apps/web/components/pin-input.tsx) supporting:
- Compound suite (PinInput, PinInput.Group, PinInput.Slot, PinInput.Separator)
- 4 futuristic visual variants ("neon", "glass", "bordered", "minimal")
- 3 size presets ("sm", "md", "lg")
- Multi-slot discrete character input with auto-advance and Backspace auto-retreat
- Smart clipboard paste auto-distribution across slots
- Input types ("numeric", "alphanumeric", "password") and masking support
- Native browser autofill integration (autocomplete="one-time-code")
- Full keyboard navigation (ArrowLeft/ArrowRight, Backspace, Delete, Home, End)
- Full WAI-ARIA 1.2 accessibility semantics (role="group", aria-label, slot labeling, aria-hidden separator)
- 100% diff-invariance across ir.description changes
- Zero external runtime dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_pin_input_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class PinInputComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the PinInput component."""

    def setUp(self) -> None:
        self.code = render_pin_input_component()
        self.ir = example_ir("rideshare-favourites")

    def test_pin_input_component_is_client_component(self) -> None:
        """The PinInput component must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "PinInput must have 'use client' as the first statement.",
        )

    def test_pin_input_component_exports_types(self) -> None:
        """Verify export of TypeScript interfaces and union types."""
        self.assertIn("export type PinInputVariant", self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"bordered"', self.code)
        self.assertIn('"minimal"', self.code)
        self.assertIn("export type PinInputSize", self.code)
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)
        self.assertIn("export type PinInputType", self.code)
        self.assertIn('"numeric"', self.code)
        self.assertIn('"alphanumeric"', self.code)
        self.assertIn('"password"', self.code)
        self.assertIn("export interface PinInputContextValue", self.code)
        self.assertIn("export interface PinInputSlotProps", self.code)
        self.assertIn("export interface PinInputSeparatorProps", self.code)
        self.assertIn("export interface PinInputGroupProps", self.code)
        self.assertIn("export interface PinInputProps", self.code)

    def test_pin_input_component_exports_compound(self) -> None:
        """Verify PinInput compound component and subcomponents."""
        self.assertIn("export const PinInput =", self.code)
        self.assertIn("export const PinInputSlot =", self.code)
        self.assertIn("export function PinInputGroup", self.code)
        self.assertIn("export function PinInputSeparator", self.code)
        self.assertIn("PinInput.Group = PinInputGroup;", self.code)
        self.assertIn("PinInput.Slot = PinInputSlot;", self.code)
        self.assertIn("PinInput.Separator = PinInputSeparator;", self.code)
        self.assertIn("export default PinInput;", self.code)

    def test_pin_input_zero_external_dependencies(self) -> None:
        """PinInput uses only React; zero external package imports."""
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
                f"Unexpected external import found in PinInput: {line}",
            )

    def test_pin_input_wai_aria_group_semantics(self) -> None:
        """Verify WAI-ARIA group semantics and slot accessibility labelling."""
        self.assertIn('role="group"', self.code)
        self.assertIn('aria-label={ariaLabel}', self.code)
        self.assertIn('digit ${index + 1} of ${length}', self.code)
        self.assertIn('aria-hidden="true"', self.code)

    def test_pin_input_keyboard_navigation(self) -> None:
        """Verify full keyboard navigation handling."""
        self.assertIn('"Backspace"', self.code)
        self.assertIn('"ArrowLeft"', self.code)
        self.assertIn('"ArrowRight"', self.code)
        self.assertIn('"Delete"', self.code)
        self.assertIn('"Home"', self.code)
        self.assertIn('"End"', self.code)

    def test_pin_input_auto_advance_and_retreat(self) -> None:
        """Verify auto-advance on valid char and retreat on Backspace."""
        self.assertIn("inputsRef.current[index + 1]?.focus()", self.code)
        self.assertIn("inputsRef.current[index - 1]?.focus()", self.code)

    def test_pin_input_paste_handling(self) -> None:
        """Verify smart clipboard paste distribution."""
        self.assertIn("e.clipboardData.getData", self.code)
        self.assertIn("handlePaste", self.code)
        self.assertIn("Math.min(filtered.length, length)", self.code)

    def test_pin_input_supports_numeric_and_alphanumeric_validation(self) -> None:
        """Verify character validation modes."""
        self.assertIn('type === "numeric"', self.code)
        self.assertIn('type === "alphanumeric"', self.code)
        self.assertIn('autoComplete="one-time-code"', self.code)

    def test_pin_input_mask_and_password_support(self) -> None:
        """Verify masking options and hidden form input."""
        self.assertIn('mask || type === "password" ? "password" : "text"', self.code)
        self.assertIn('<input type="hidden" name={name}', self.code)

    def test_pin_input_supports_variants(self) -> None:
        """Verify 4 futuristic visual variants."""
        self.assertIn('variant === "neon"', self.code)
        self.assertIn('variant === "glass"', self.code)
        self.assertIn('variant === "bordered"', self.code)

    def test_pin_input_supports_sizes(self) -> None:
        """Verify 3 size presets."""
        self.assertIn("sm: { width: 34", self.code)
        self.assertIn("md: { width: 44", self.code)
        self.assertIn("lg: { width: 54", self.code)

    def test_pin_input_diff_invariant(self) -> None:
        """PinInput output is 100% diff-invariant across ir.description changes."""
        adapter = NextjsWebAdapter()
        project1 = adapter.generate(self.ir)
        ir2 = dataclasses.replace(
            self.ir, description="Completely changed description for diff test."
        )
        project2 = adapter.generate(ir2)
        pi1 = project1.get("components/pin-input.tsx").content
        pi2 = project2.get("components/pin-input.tsx").content
        self.assertEqual(
            pi1,
            pi2,
            "components/pin-input.tsx must be 100% diff-invariant across ir.description",
        )
        self.assertEqual(pi1, self.code)

    def test_adapter_emits_pin_input_file(self) -> None:
        """NextjsWebAdapter emits components/pin-input.tsx in generated project."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/pin-input.tsx")
        self.assertIsNotNone(f, "components/pin-input.tsx must be generated")
        self.assertEqual(f.content, self.code)

    def test_package_codegen_exports_render_pin_input_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_pin_input_component."""
        self.assertTrue(callable(cg.render_pin_input_component))
        self.assertEqual(cg.render_pin_input_component(), self.code)


if __name__ == "__main__":
    unittest.main()
