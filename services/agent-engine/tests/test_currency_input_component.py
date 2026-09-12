"""Tests for the Accessible Futuristic Currency / Money Input Suite (components/currency-input.tsx)."""

from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine import codegen as cg
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_currency_input_component,
)


class TestCurrencyInputComponent(unittest.TestCase):
    """Unit tests for the Accessible Futuristic Currency / Money Input Suite (R-409)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_currency_input_component()

    def test_file_generated(self) -> None:
        project = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        self.assertIsNotNone(project.get("components/currency-input.tsx"))

    def test_diff_invariance_and_codegen_export(self) -> None:
        proj1 = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        proj2 = NextjsWebAdapter().generate(example_ir("rideshare-favourites"))
        f1 = proj1.get("components/currency-input.tsx")
        f2 = proj2.get("components/currency-input.tsx")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, render_currency_input_component())

    def test_use_client_directive(self) -> None:
        self.assertTrue(self.source.startswith("'use client';"))

    def test_zero_runtime_dependencies(self) -> None:
        for pkg in re.findall(r"from\s+['\"]([^'\"]+)['\"]", self.source):
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected import: {pkg}",
            )

    def test_forward_ref_and_imperative_handle(self) -> None:
        self.assertIn("forwardRef<CurrencyInputHandle, CurrencyInputProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        for method in ("getValue:", "getFormatted:", "setValue:", "clear:", "focus:"):
            self.assertIn(method, self.source)

    def test_typescript_types_present(self) -> None:
        for decl in (
            "export type CurrencyInputVariant",
            "export type CurrencyInputSize",
            "export interface CurrencyInputHandle",
            "export interface CurrencyInputProps",
        ):
            self.assertIn(decl, self.source)

    def test_compound_and_alias_exports(self) -> None:
        for decl in (
            "export const CurrencyInput =",
            "export const MoneyInput =",
            "export const CurrencyField =",
            "export const PriceInput =",
            "export default CurrencyInputComponent",
        ):
            self.assertIn(decl, self.source)

    def test_display_names_defined(self) -> None:
        for line in (
            "CurrencyInputComponent.displayName = 'CurrencyInput'",
            "MoneyInput.displayName = 'MoneyInput'",
            "CurrencyField.displayName = 'CurrencyField'",
            "PriceInput.displayName = 'PriceInput'",
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

    def test_intl_formatting(self) -> None:
        self.assertIn("Intl.NumberFormat", self.source)
        self.assertIn("style: 'currency'", self.source)
        self.assertIn("currency", self.source)

    def test_locale(self) -> None:
        self.assertIn("locale", self.source)
        self.assertIn("en-US", self.source)

    def test_parsing(self) -> None:
        self.assertIn("parseFloat", self.source)

    def test_min_max_step(self) -> None:
        for token in ("min", "max", "step"):
            self.assertIn(token, self.source)

    def test_aria_and_inputmode(self) -> None:
        self.assertIn("aria-label", self.source)
        self.assertIn("inputMode", self.source)

    def test_callbacks_and_controlled(self) -> None:
        for token in ("onChange", "value", "defaultValue", "allowNegative"):
            self.assertIn(token, self.source)

    def test_package_codegen_export(self) -> None:
        self.assertTrue(hasattr(cg, "render_currency_input_component"))
        self.assertTrue(callable(cg.render_currency_input_component))
        self.assertIn("render_currency_input_component", cg.__all__)


if __name__ == "__main__":
    unittest.main()
