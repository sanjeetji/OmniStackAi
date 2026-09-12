"""Tests for the Accessible Futuristic Credit Card Payment Field Suite (components/credit-card.tsx)."""

from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine import codegen as cg
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_credit_card_component,
)


class TestCreditCardComponent(unittest.TestCase):
    """Unit tests for the Accessible Futuristic Credit Card Payment Field Suite (R-407)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_credit_card_component()

    def test_file_generated(self) -> None:
        project = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        self.assertIsNotNone(project.get("components/credit-card.tsx"))

    def test_diff_invariance_and_codegen_export(self) -> None:
        proj1 = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        proj2 = NextjsWebAdapter().generate(example_ir("rideshare-favourites"))
        f1 = proj1.get("components/credit-card.tsx")
        f2 = proj2.get("components/credit-card.tsx")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, render_credit_card_component())

    def test_use_client_directive(self) -> None:
        self.assertTrue(self.source.startswith("'use client';"))

    def test_zero_runtime_dependencies(self) -> None:
        for pkg in re.findall(r"from\s+['\"]([^'\"]+)['\"]", self.source):
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected import: {pkg}",
            )

    def test_forward_ref_and_imperative_handle(self) -> None:
        self.assertIn("forwardRef<CreditCardHandle, CreditCardProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        for method in ("getValue:", "getMeta:", "clear:", "focus:"):
            self.assertIn(method, self.source)

    def test_typescript_types_present(self) -> None:
        for decl in (
            "export type CreditCardVariant",
            "export type CreditCardSize",
            "export type CardBrand",
            "export interface CreditCardValue",
            "export interface CreditCardMeta",
            "export interface CreditCardHandle",
            "export interface CreditCardProps",
        ):
            self.assertIn(decl, self.source)

    def test_compound_and_alias_exports(self) -> None:
        for decl in (
            "export const CreditCard =",
            "export const CreditCardField =",
            "export const PaymentCardField =",
            "export const CardInput =",
            "export default CreditCardComponent",
        ):
            self.assertIn(decl, self.source)

    def test_display_names_defined(self) -> None:
        for line in (
            "CreditCardComponent.displayName = 'CreditCard'",
            "CreditCardField.displayName = 'CreditCardField'",
            "PaymentCardField.displayName = 'PaymentCardField'",
            "CardInput.displayName = 'CardInput'",
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

    def test_brands_present(self) -> None:
        self.assertIn("'visa' | 'mastercard' | 'amex' | 'discover' | 'unknown'", self.source)

    def test_luhn_validation(self) -> None:
        self.assertIn("luhnValid", self.source)
        self.assertIn("% 10", self.source)

    def test_brand_detection(self) -> None:
        self.assertIn("detectBrand", self.source)
        self.assertIn("/^4/", self.source)

    def test_formatting(self) -> None:
        self.assertIn("formatNumber", self.source)
        self.assertIn("formatExpiry", self.source)

    def test_validation_meta(self) -> None:
        for token in ("numberValid", "expiryValid", "cvcValid", "complete"):
            self.assertIn(token, self.source)

    def test_aria_and_inputmode(self) -> None:
        self.assertIn("aria-invalid", self.source)
        self.assertIn("aria-label", self.source)
        self.assertIn("inputMode", self.source)

    def test_callbacks_and_controlled(self) -> None:
        for token in ("onChange", "onComplete", "value", "defaultValue"):
            self.assertIn(token, self.source)

    def test_package_codegen_export(self) -> None:
        self.assertTrue(hasattr(cg, "render_credit_card_component"))
        self.assertTrue(callable(cg.render_credit_card_component))
        self.assertIn("render_credit_card_component", cg.__all__)


if __name__ == "__main__":
    unittest.main()
