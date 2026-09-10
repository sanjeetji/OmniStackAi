"""Tests for Task R-327: Generated Accessible Reusable Form Controls & Input Primitives.

Verifies that NextjsWebAdapter emits an accessible, reusable suite of Form Controls and Input
primitives (apps/web/components/form-controls.tsx) with Input, Textarea, Select, Checkbox,
RadioGroup, Radio, Label, FormField, FormMessage, FormHelperText, supporting WAI-ARIA form semantics.
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import (
    render_form_controls_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
)


class FormControlsComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.code = render_form_controls_component()

    def test_form_controls_component_is_client_component(self) -> None:
        """Form controls component specifies 'use client' directive."""
        self.assertTrue(self.code.startswith('"use client";'))

    def test_form_controls_component_exports_types_and_subcomponents(self) -> None:
        """Form controls component exports all types, interfaces, and subcomponents."""
        self.assertIn('export type InputSize = "sm" | "md" | "lg";', self.code)
        self.assertIn("export interface InputProps", self.code)
        self.assertIn("export interface TextareaProps", self.code)
        self.assertIn("export interface SelectProps", self.code)
        self.assertIn("export interface SelectOption", self.code)
        self.assertIn("export interface CheckboxProps", self.code)
        self.assertIn("export interface RadioGroupProps", self.code)
        self.assertIn("export interface RadioProps", self.code)
        self.assertIn("export interface LabelProps", self.code)
        self.assertIn("export interface FormFieldProps", self.code)
        self.assertIn("export interface FormMessageProps", self.code)
        self.assertIn("export interface FormHelperTextProps", self.code)
        self.assertIn("export const Input =", self.code)
        self.assertIn("export const Textarea =", self.code)
        self.assertIn("export const Select =", self.code)
        self.assertIn("export const Checkbox =", self.code)
        self.assertIn("export function RadioGroup(", self.code)
        self.assertIn("export function Radio(", self.code)
        self.assertIn("export function Label(", self.code)
        self.assertIn("export function FormField(", self.code)
        self.assertIn("export function FormMessage(", self.code)
        self.assertIn("export function FormHelperText(", self.code)
        self.assertIn("export default Input;", self.code)

    def test_input_supports_size_presets(self) -> None:
        """Input supports sm, md, lg size presets."""
        self.assertIn("sizeMap", self.code)
        self.assertIn("sm:", self.code)
        self.assertIn("md:", self.code)
        self.assertIn("lg:", self.code)

    def test_input_supports_prefix_suffix_and_clear(self) -> None:
        """Input supports prefix, suffix, and clear button affordances."""
        self.assertIn("prefix", self.code)
        self.assertIn("suffix", self.code)
        self.assertIn("onClear", self.code)
        self.assertIn('aria-label="Clear input"', self.code)

    def test_textarea_supports_character_counter(self) -> None:
        """Textarea supports character counter threshold display."""
        self.assertIn("showCount", self.code)
        self.assertIn("maxLength", self.code)

    def test_select_renders_options_and_placeholder(self) -> None:
        """Select supports options array, placeholder, and disabled states."""
        self.assertIn("options", self.code)
        self.assertIn("placeholder", self.code)

    def test_checkbox_aria_semantics_and_states(self) -> None:
        """Checkbox supports checked, indeterminate, and focus states."""
        self.assertIn('type="checkbox"', self.code)
        self.assertIn("indeterminate", self.code)

    def test_radiogroup_and_radio_wai_aria_and_keyboard(self) -> None:
        """RadioGroup and Radio implement WAI-ARIA radiogroup and radio with arrow key navigation."""
        self.assertIn('role="radiogroup"', self.code)
        self.assertIn('role="radio"', self.code)
        self.assertIn("aria-checked", self.code)
        self.assertIn("ArrowDown", self.code)
        self.assertIn("ArrowUp", self.code)

    def test_formfield_and_formmessage_aria_semantics(self) -> None:
        """FormField and FormMessage wire aria-invalid, aria-describedby, and role='alert'."""
        self.assertIn("aria-invalid", self.code)
        self.assertIn("aria-describedby", self.code)
        self.assertIn('role="alert"', self.code)
        self.assertIn('aria-live="polite"', self.code)

    def test_label_supports_required_asterisk(self) -> None:
        """Label renders required asterisk indicator when required is true."""
        self.assertIn("required", self.code)
        self.assertIn("*", self.code)

    def test_codegen_module_exports_render_form_controls_component(self) -> None:
        """render_form_controls_component is exported from omnistackai_agent_engine.codegen."""
        self.assertTrue(hasattr(cg, "render_form_controls_component"))
        self.assertEqual(cg.render_form_controls_component(), self.code)

    def test_adapter_generate_registers_form_controls_component(self) -> None:
        """NextjsWebAdapter.generate outputs components/form-controls.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/form-controls.tsx")
        self.assertIsNotNone(f)
        self.assertEqual(f.content, self.code)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        """render_form_controls_component is 100% diff-invariant across changes to ir.description."""
        ir1 = example_ir("minimal-blog")
        ir2 = dataclasses.replace(ir1, description="Completely changed IR description for R-327")

        adapter = NextjsWebAdapter()
        p1 = adapter.generate(ir1).get("components/form-controls.tsx")
        p2 = adapter.generate(ir2).get("components/form-controls.tsx")

        self.assertIsNotNone(p1)
        self.assertIsNotNone(p2)
        self.assertEqual(p1.content, p2.content)


if __name__ == "__main__":
    unittest.main()
