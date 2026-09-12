"""Tests for the Accessible Futuristic Cookie Consent & Preferences Manager Suite (components/cookie-consent.tsx)."""

from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine import codegen as cg
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_cookie_consent_component,
)


class TestCookieConsentComponent(unittest.TestCase):
    """Unit tests for the Accessible Futuristic Cookie Consent & Preferences Manager Suite (R-402)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_cookie_consent_component()

    def test_file_generated(self) -> None:
        project = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        self.assertIsNotNone(project.get("components/cookie-consent.tsx"))

    def test_diff_invariance_and_codegen_export(self) -> None:
        proj1 = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        proj2 = NextjsWebAdapter().generate(example_ir("rideshare-favourites"))
        f1 = proj1.get("components/cookie-consent.tsx")
        f2 = proj2.get("components/cookie-consent.tsx")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, render_cookie_consent_component())

    def test_use_client_directive(self) -> None:
        self.assertTrue(self.source.startswith("'use client';"))

    def test_zero_runtime_dependencies(self) -> None:
        for pkg in re.findall(r"from\s+['\"]([^'\"]+)['\"]", self.source):
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected import: {pkg}",
            )

    def test_forward_ref_and_imperative_handle(self) -> None:
        self.assertIn("forwardRef<CookieConsentHandle, CookieConsentProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        for method in ("open:", "close:", "accept:", "reject:", "getConsent:", "reset:"):
            self.assertIn(method, self.source)

    def test_typescript_types_present(self) -> None:
        for decl in (
            "export type CookieConsentVariant",
            "export type CookieConsentSize",
            "export type CookieConsentPosition",
            "export interface ConsentCategory",
            "export interface CookieConsentHandle",
            "export interface CookieConsentProps",
        ):
            self.assertIn(decl, self.source)

    def test_compound_and_alias_exports(self) -> None:
        for decl in (
            "export const CookieConsent =",
            "export const ConsentBanner =",
            "export const CookieBanner =",
            "export const ConsentManager =",
            "export default CookieConsentComponent",
        ):
            self.assertIn(decl, self.source)

    def test_display_names_defined(self) -> None:
        for line in (
            "CookieConsentComponent.displayName = 'CookieConsent'",
            "ConsentBanner.displayName = 'ConsentBanner'",
            "CookieBanner.displayName = 'CookieBanner'",
            "ConsentManager.displayName = 'ConsentManager'",
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

    def test_positions_present(self) -> None:
        for token in ("'bottom'", "'top'", "'bottom-left'", "'bottom-right'", "'center'"):
            self.assertIn(token, self.source)

    def test_localstorage_persistence(self) -> None:
        for token in ("localStorage", "getItem", "setItem", "storageKey"):
            self.assertIn(token, self.source)

    def test_ssr_safe_mounting(self) -> None:
        self.assertIn("mounted", self.source)

    def test_categories_and_required(self) -> None:
        for token in ("categories", "required", "ConsentState"):
            self.assertIn(token, self.source)

    def test_switch_aria_semantics(self) -> None:
        self.assertIn('role="region"', self.source)
        self.assertIn("aria-label", self.source)
        self.assertIn('role="switch"', self.source)
        self.assertIn("aria-checked", self.source)

    def test_callbacks(self) -> None:
        for token in ("onAccept", "onReject", "onChange"):
            self.assertIn(token, self.source)

    def test_policy_link(self) -> None:
        self.assertIn("policyUrl", self.source)

    def test_package_codegen_export(self) -> None:
        self.assertTrue(hasattr(cg, "render_cookie_consent_component"))
        self.assertTrue(callable(cg.render_cookie_consent_component))
        self.assertIn("render_cookie_consent_component", cg.__all__)


if __name__ == "__main__":
    unittest.main()
