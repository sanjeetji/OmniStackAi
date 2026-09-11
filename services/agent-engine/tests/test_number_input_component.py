"""Tests for Task R-360: Generated Accessible Futuristic Reusable Number Input & Numeric Stepper Primitive.

Verifies that NextjsWebAdapter emits an accessible, desktop-grade, zero-dependency, and futuristic
Number Input & Numeric Stepper compound component suite (apps/web/components/number-input.tsx) supporting:
- WAI-ARIA spinbutton pattern:
  - Input emits role="spinbutton", aria-valuenow, aria-valuemin, aria-valuemax
  - aria-invalid, aria-required, aria-describedby for labels/errors
- Keyboard navigation:
  - ArrowUp increments value
  - ArrowDown decrements value
- Stepper buttons:
  - Increment button: aria-label="Increment", tabIndex=-1
  - Decrement button: aria-label="Decrement", tabIndex=-1
  - Disabled at min/max boundaries
- min / max / step / precision constraints
- 3 value format modes: "plain", "currency", "percentage" (via Intl.NumberFormat)
- 4 futuristic visual styling variants ("default", "card", "glass", "neon")
- 3 size scales ("sm", "md", "lg") with responsive heights
- hideControls prop to suppress stepper buttons
- leftSection / rightSection slot nodes
- label, helperText, and error message with accessible ARIA linkage
- Required field asterisk affordance
- Controlled and uncontrolled selection modes
- React ref forwarding (forwardRef) and explicit displayName
- 100% diff-invariance across ir.description changes
- Zero external runtime npm dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_number_input_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class NumberInputComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the NumberInput component suite."""

    def setUp(self) -> None:
        self.code = render_number_input_component()
        self.ir = example_ir("rideshare-favourites")

    # ------------------------------------------------------------------
    # Basic structure
    # ------------------------------------------------------------------

    def test_number_input_is_client_component(self) -> None:
        """NumberInput must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "NumberInput must have 'use client' as the first statement.",
        )

    def test_number_input_exports_types(self) -> None:
        """Verify export of TypeScript union types and interfaces."""
        self.assertIn("export type NumberInputVariant", self.code)
        self.assertIn('"default"', self.code)
        self.assertIn('"card"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn("export type NumberInputSize", self.code)
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)
        self.assertIn("export type NumberInputFormat", self.code)
        self.assertIn('"plain"', self.code)
        self.assertIn('"currency"', self.code)
        self.assertIn('"percentage"', self.code)
        self.assertIn("export interface NumberInputProps", self.code)

    def test_number_input_exports_component_and_display_name(self) -> None:
        """Verify NumberInput export, forwardRef, displayName, and default export."""
        self.assertIn("export const NumberInput = forwardRef", self.code)
        self.assertIn('NumberInput.displayName = "NumberInput";', self.code)
        self.assertIn("export default NumberInput;", self.code)

    # ------------------------------------------------------------------
    # WAI-ARIA spinbutton
    # ------------------------------------------------------------------

    def test_number_input_wai_aria_spinbutton_role(self) -> None:
        """Input element must carry role=spinbutton."""
        self.assertIn('role="spinbutton"', self.code)

    def test_number_input_wai_aria_value_attributes(self) -> None:
        """aria-valuenow, aria-valuemin, aria-valuemax must be present."""
        self.assertIn("aria-valuenow={", self.code)
        self.assertIn("aria-valuemin={min}", self.code)
        self.assertIn("aria-valuemax={max}", self.code)

    def test_number_input_wai_aria_invalid_and_required(self) -> None:
        """aria-invalid and aria-required must be applied."""
        self.assertIn("aria-invalid={Boolean(error)}", self.code)
        self.assertIn("aria-required={required}", self.code)

    def test_number_input_wai_aria_describedby(self) -> None:
        """aria-describedby links to error and helper text IDs."""
        self.assertIn("aria-describedby={ariaDescribedBy}", self.code)
        self.assertIn("errorId", self.code)
        self.assertIn("helperId", self.code)

    # ------------------------------------------------------------------
    # Keyboard navigation
    # ------------------------------------------------------------------

    def test_number_input_keyboard_arrow_up_increments(self) -> None:
        """ArrowUp must trigger increment."""
        self.assertIn('"ArrowUp"', self.code)
        self.assertIn("handleIncrement", self.code)

    def test_number_input_keyboard_arrow_down_decrements(self) -> None:
        """ArrowDown must trigger decrement."""
        self.assertIn('"ArrowDown"', self.code)
        self.assertIn("handleDecrement", self.code)

    # ------------------------------------------------------------------
    # Stepper buttons
    # ------------------------------------------------------------------

    def test_number_input_increment_button(self) -> None:
        """Increment stepper button must have aria-label and tabIndex=-1."""
        self.assertIn('aria-label="Increment"', self.code)
        self.assertIn("ChevronUpIcon", self.code)

    def test_number_input_decrement_button(self) -> None:
        """Decrement stepper button must have aria-label and tabIndex=-1."""
        self.assertIn('aria-label="Decrement"', self.code)
        self.assertIn("ChevronDownIcon", self.code)

    def test_number_input_stepper_boundary_disabled(self) -> None:
        """Stepper buttons must disable at min/max boundaries."""
        self.assertIn("atMin", self.code)
        self.assertIn("atMax", self.code)

    def test_number_input_hide_controls(self) -> None:
        """hideControls prop must suppress the stepper buttons."""
        self.assertIn("hideControls", self.code)
        self.assertIn("!hideControls", self.code)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------

    def test_number_input_clamp_helper(self) -> None:
        """A clamp() helper must enforce min/max boundaries."""
        self.assertIn("function clamp(", self.code)
        self.assertIn("Math.max(min, out)", self.code)
        self.assertIn("Math.min(max, out)", self.code)

    def test_number_input_precision(self) -> None:
        """precision prop must be used in toFixed calls."""
        self.assertIn("toFixed(precision)", self.code)

    def test_number_input_step(self) -> None:
        """step prop must be applied in increment/decrement logic."""
        self.assertIn("cur + step", self.code)
        self.assertIn("cur - step", self.code)

    # ------------------------------------------------------------------
    # Formatters
    # ------------------------------------------------------------------

    def test_number_input_format_currency(self) -> None:
        """Currency format must use Intl.NumberFormat with style=currency."""
        self.assertIn('style: "currency"', self.code)
        self.assertIn("Intl.NumberFormat", self.code)

    def test_number_input_format_percentage(self) -> None:
        """Percentage format must use Intl.NumberFormat with style=percent."""
        self.assertIn('style: "percent"', self.code)

    def test_number_input_format_plain(self) -> None:
        """Plain format must also use Intl.NumberFormat (locale-aware)."""
        self.assertIn("minimumFractionDigits: precision", self.code)
        self.assertIn("maximumFractionDigits: precision", self.code)

    # ------------------------------------------------------------------
    # Visual variants
    # ------------------------------------------------------------------

    def test_number_input_glass_variant(self) -> None:
        """Glass variant must use backdropFilter and translucent background."""
        self.assertIn("backdropFilter", self.code)
        self.assertIn("rgba(255,255,255,0.65)", self.code)

    def test_number_input_neon_variant(self) -> None:
        """Neon variant must use cyan glow and dark background."""
        self.assertIn("rgba(56,189,248,0.35)", self.code)
        self.assertIn("rgba(9,13,22,0.97)", self.code)

    # ------------------------------------------------------------------
    # Size scales
    # ------------------------------------------------------------------

    def test_number_input_size_sm(self) -> None:
        """sm size must set height to 32px."""
        self.assertIn('height: "32px"', self.code)

    def test_number_input_size_md(self) -> None:
        """md size must set height to 38px."""
        self.assertIn('height: "38px"', self.code)

    def test_number_input_size_lg(self) -> None:
        """lg size must set height to 44px."""
        self.assertIn('height: "44px"', self.code)

    # ------------------------------------------------------------------
    # Label / helper / error
    # ------------------------------------------------------------------

    def test_number_input_label(self) -> None:
        """Label must link to the input via htmlFor."""
        self.assertIn("htmlFor={inputId}", self.code)

    def test_number_input_error_role_alert(self) -> None:
        """Error message must use role=alert and aria-live=polite."""
        self.assertIn('role="alert"', self.code)
        self.assertIn('aria-live="polite"', self.code)

    def test_number_input_required_asterisk(self) -> None:
        """Required prop must render a visible asterisk for sighted users."""
        self.assertIn("required &&", self.code)
        self.assertIn("aria-hidden", self.code)

    # ------------------------------------------------------------------
    # Controlled / uncontrolled
    # ------------------------------------------------------------------

    def test_number_input_controlled_and_uncontrolled(self) -> None:
        """Controlled and uncontrolled modes must coexist."""
        self.assertIn("isControlled", self.code)
        self.assertIn("controlledValue", self.code)
        self.assertIn("internalValue", self.code)
        self.assertIn("setInternalValue", self.code)

    # ------------------------------------------------------------------
    # Display / raw text toggle
    # ------------------------------------------------------------------

    def test_number_input_focus_shows_raw_text(self) -> None:
        """When focused, the raw numeric text (not formatted) must be shown."""
        self.assertIn("focused", self.code)
        self.assertIn("rawText", self.code)
        self.assertIn("displayValue", self.code)

    # ------------------------------------------------------------------
    # Input attributes
    # ------------------------------------------------------------------

    def test_number_input_input_mode_decimal(self) -> None:
        """inputMode=decimal enables the numeric keyboard on mobile."""
        self.assertIn('inputMode="decimal"', self.code)

    def test_number_input_tabular_nums(self) -> None:
        """Tabular nums ensure digit alignment."""
        self.assertIn('"tabular-nums"', self.code)

    # ------------------------------------------------------------------
    # Zero external dependencies
    # ------------------------------------------------------------------

    def test_number_input_zero_runtime_dependencies(self) -> None:
        """NumberInput template must not import external third-party libraries."""
        lines = [
            line.strip()
            for line in self.code.split("\n")
            if line.strip().startswith("import ")
        ]
        for line in lines:
            self.assertTrue(
                line.startswith("import React") or 'from "react"' in line,
                f"Unexpected external import detected: {line}",
            )

    # ------------------------------------------------------------------
    # Adapter wiring
    # ------------------------------------------------------------------

    def test_number_input_adapter_emits_file(self) -> None:
        """NextjsWebAdapter must emit components/number-input.tsx in the generated project."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/number-input.tsx")
        self.assertIsNotNone(f)
        self.assertEqual(f.content, self.code)

    def test_number_input_exported_from_codegen_package(self) -> None:
        """cg.render_number_input_component must be exposed at package root."""
        self.assertTrue(callable(cg.render_number_input_component))
        self.assertEqual(cg.render_number_input_component(), self.code)

    # ------------------------------------------------------------------
    # Diff invariance
    # ------------------------------------------------------------------

    def test_number_input_diff_invariance(self) -> None:
        """Diff invariance: changing ir.description must not alter components/number-input.tsx."""
        adapter = NextjsWebAdapter()
        project1 = adapter.generate(self.ir)
        f1 = project1.get("components/number-input.tsx")

        ir_mutated = dataclasses.replace(
            self.ir,
            description="Completely different description for diff invariance test",
        )
        project2 = adapter.generate(ir_mutated)
        f2 = project2.get("components/number-input.tsx")

        self.assertEqual(f1.content, f2.content)


if __name__ == "__main__":
    unittest.main()
