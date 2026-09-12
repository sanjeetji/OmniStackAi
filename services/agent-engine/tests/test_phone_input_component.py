"""Tests for the Accessible Futuristic Phone Number Input Suite (components/phone-input.tsx)."""

from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine import codegen as cg
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_phone_input_component,
)


class TestPhoneInputComponent(unittest.TestCase):
    """Unit tests for the Accessible Futuristic Phone Number Input Suite (R-415)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_phone_input_component()

    def test_file_generated(self) -> None:
        project = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        self.assertIsNotNone(project.get("components/phone-input.tsx"))

    def test_diff_invariance_and_codegen_export(self) -> None:
        proj1 = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        proj2 = NextjsWebAdapter().generate(example_ir("rideshare-favourites"))
        f1 = proj1.get("components/phone-input.tsx")
        f2 = proj2.get("components/phone-input.tsx")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, render_phone_input_component())

    def test_use_client_directive(self) -> None:
        self.assertTrue(self.source.startswith("'use client';"))

    def test_zero_runtime_dependencies(self) -> None:
        for pkg in re.findall(r"from\s+['\"]([^'\"]+)['\"]", self.source):
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected import: {pkg}",
            )

    def test_ascii_only_source(self) -> None:
        non_ascii = [c for c in self.source if ord(c) > 126]
        self.assertEqual(non_ascii, [], f"non-ASCII chars present: {non_ascii[:8]}")

    def test_forward_ref_and_imperative_handle(self) -> None:
        self.assertIn("forwardRef<PhoneInputHandle, PhoneInputProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        for method in ("getValue:", "getE164:", "setValue:", "getCountry:", "clear:", "focus:"):
            self.assertIn(method, self.source)

    def test_typescript_types_present(self) -> None:
        for decl in (
            "export type PhoneInputVariant",
            "export type PhoneInputSize",
            "export interface PhoneCountry",
            "export interface PhoneInputHandle",
            "export interface PhoneInputProps",
        ):
            self.assertIn(decl, self.source)

    def test_compound_and_alias_exports(self) -> None:
        for decl in (
            "export const PhoneInput =",
            "export const PhoneNumberInput =",
            "export const TelInput =",
            "export const PhoneField =",
            "export default PhoneInputComponent",
        ):
            self.assertIn(decl, self.source)

    def test_display_names_defined(self) -> None:
        for line in (
            "PhoneInputComponent.displayName = 'PhoneInput'",
            "PhoneNumberInput.displayName = 'PhoneNumberInput'",
            "TelInput.displayName = 'TelInput'",
            "PhoneField.displayName = 'PhoneField'",
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

    def test_countries(self) -> None:
        self.assertIn("DEFAULT_COUNTRIES", self.source)
        self.assertIn("dial", self.source)
        self.assertIn("+1", self.source)

    def test_e164(self) -> None:
        self.assertIn("e164", self.source)

    def test_national_digits(self) -> None:
        self.assertIn("replace", self.source)
        self.assertIn("national", self.source)

    def test_validation(self) -> None:
        self.assertIn("valid", self.source)

    def test_aria_and_inputmode(self) -> None:
        self.assertIn("aria-label", self.source)
        self.assertIn('inputMode="tel"', self.source)

    def test_callbacks_and_controlled(self) -> None:
        for token in ("onChange", "value", "defaultValue", "defaultCountry"):
            self.assertIn(token, self.source)

    def test_package_codegen_export(self) -> None:
        self.assertTrue(hasattr(cg, "render_phone_input_component"))
        self.assertTrue(callable(cg.render_phone_input_component))
        self.assertIn("render_phone_input_component", cg.__all__)


if __name__ == "__main__":
    unittest.main()
