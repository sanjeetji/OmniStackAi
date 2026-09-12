"""Tests for the Accessible Futuristic Masked / Pattern Input Suite (components/masked-input.tsx)."""

from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine import codegen as cg
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_masked_input_component,
)


class TestMaskedInputComponent(unittest.TestCase):
    """Unit tests for the Accessible Futuristic Masked / Pattern Input Suite (R-404)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_masked_input_component()

    def test_file_generated(self) -> None:
        project = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        self.assertIsNotNone(project.get("components/masked-input.tsx"))

    def test_diff_invariance_and_codegen_export(self) -> None:
        proj1 = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        proj2 = NextjsWebAdapter().generate(example_ir("rideshare-favourites"))
        f1 = proj1.get("components/masked-input.tsx")
        f2 = proj2.get("components/masked-input.tsx")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, render_masked_input_component())

    def test_use_client_directive(self) -> None:
        self.assertTrue(self.source.startswith("'use client';"))

    def test_zero_runtime_dependencies(self) -> None:
        for pkg in re.findall(r"from\s+['\"]([^'\"]+)['\"]", self.source):
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected import: {pkg}",
            )

    def test_forward_ref_and_imperative_handle(self) -> None:
        self.assertIn("forwardRef<MaskedInputHandle, MaskedInputProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        for method in ("getValue:", "getRawValue:", "setValue:", "clear:", "focus:"):
            self.assertIn(method, self.source)

    def test_typescript_types_present(self) -> None:
        for decl in (
            "export type MaskedInputVariant",
            "export type MaskedInputSize",
            "export type MaskedInputPreset",
            "export interface MaskedInputHandle",
            "export interface MaskedInputProps",
        ):
            self.assertIn(decl, self.source)

    def test_compound_and_alias_exports(self) -> None:
        for decl in (
            "export const MaskedInput =",
            "export const InputMask =",
            "export const PatternInput =",
            "export const FormattedInput =",
            "export default MaskedInputComponent",
        ):
            self.assertIn(decl, self.source)

    def test_display_names_defined(self) -> None:
        for line in (
            "MaskedInputComponent.displayName = 'MaskedInput'",
            "InputMask.displayName = 'InputMask'",
            "PatternInput.displayName = 'PatternInput'",
            "FormattedInput.displayName = 'FormattedInput'",
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

    def test_presets_present(self) -> None:
        self.assertIn("'phone' | 'date' | 'card' | 'time' | 'ssn'", self.source)
        self.assertIn("PRESET_MASKS", self.source)

    def test_masking_logic(self) -> None:
        self.assertIn("applyMask", self.source)
        self.assertIn("mask", self.source)
        self.assertIn("[0-9]", self.source)

    def test_raw_and_formatted(self) -> None:
        for token in ("raw", "formatted", "complete"):
            self.assertIn(token, self.source)

    def test_caret_handling(self) -> None:
        self.assertIn("setSelectionRange", self.source)

    def test_aria_and_inputmode(self) -> None:
        self.assertIn("aria-label", self.source)
        self.assertIn("inputMode", self.source)

    def test_callbacks(self) -> None:
        self.assertIn("onChange", self.source)
        self.assertIn("onComplete", self.source)

    def test_controlled_and_uncontrolled(self) -> None:
        self.assertIn("value", self.source)
        self.assertIn("defaultValue", self.source)

    def test_package_codegen_export(self) -> None:
        self.assertTrue(hasattr(cg, "render_masked_input_component"))
        self.assertTrue(callable(cg.render_masked_input_component))
        self.assertIn("render_masked_input_component", cg.__all__)


if __name__ == "__main__":
    unittest.main()
