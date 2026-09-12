"""Tests for the Accessible Futuristic Password Generator Suite (components/password-generator.tsx)."""

from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine import codegen as cg
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_password_generator_component,
)


class TestPasswordGeneratorComponent(unittest.TestCase):
    """Unit tests for the Accessible Futuristic Password Generator Suite (R-410)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_password_generator_component()

    def test_file_generated(self) -> None:
        project = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        self.assertIsNotNone(project.get("components/password-generator.tsx"))

    def test_diff_invariance_and_codegen_export(self) -> None:
        proj1 = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        proj2 = NextjsWebAdapter().generate(example_ir("rideshare-favourites"))
        f1 = proj1.get("components/password-generator.tsx")
        f2 = proj2.get("components/password-generator.tsx")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, render_password_generator_component())

    def test_use_client_directive(self) -> None:
        self.assertTrue(self.source.startswith("'use client';"))

    def test_zero_runtime_dependencies(self) -> None:
        for pkg in re.findall(r"from\s+['\"]([^'\"]+)['\"]", self.source):
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected import: {pkg}",
            )

    def test_forward_ref_and_imperative_handle(self) -> None:
        self.assertIn("forwardRef<PasswordGeneratorHandle, PasswordGeneratorProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        for method in ("generate:", "getValue:", "copy:", "setLength:"):
            self.assertIn(method, self.source)

    def test_typescript_types_present(self) -> None:
        for decl in (
            "export type PasswordGeneratorVariant",
            "export type PasswordGeneratorSize",
            "export interface PasswordGeneratorOptions",
            "export interface PasswordGeneratorHandle",
            "export interface PasswordGeneratorProps",
        ):
            self.assertIn(decl, self.source)

    def test_compound_and_alias_exports(self) -> None:
        for decl in (
            "export const PasswordGenerator =",
            "export const PasswordCreator =",
            "export const SecurePasswordGenerator =",
            "export const PasswordMaker =",
            "export default PasswordGeneratorComponent",
        ):
            self.assertIn(decl, self.source)

    def test_display_names_defined(self) -> None:
        for line in (
            "PasswordGeneratorComponent.displayName = 'PasswordGenerator'",
            "PasswordCreator.displayName = 'PasswordCreator'",
            "SecurePasswordGenerator.displayName = 'SecurePasswordGenerator'",
            "PasswordMaker.displayName = 'PasswordMaker'",
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

    def test_secure_rng(self) -> None:
        for token in ("crypto.getRandomValues", "Uint32Array", "Math.random"):
            self.assertIn(token, self.source)

    def test_charsets(self) -> None:
        self.assertIn("ABCDEFGHIJKLMNOPQRSTUVWXYZ", self.source)
        self.assertIn("0123456789", self.source)
        for token in ("uppercase", "lowercase", "numbers", "symbols"):
            self.assertIn(token, self.source)

    def test_options(self) -> None:
        self.assertIn("length", self.source)
        self.assertIn("excludeAmbiguous", self.source)

    def test_generate_logic(self) -> None:
        self.assertIn("generatePassword", self.source)

    def test_copy_to_clipboard(self) -> None:
        self.assertIn("navigator.clipboard", self.source)
        self.assertIn("writeText", self.source)

    def test_aria_semantics(self) -> None:
        self.assertIn('role="group"', self.source)
        self.assertIn("aria-label", self.source)
        self.assertIn("aria-live", self.source)

    def test_callbacks(self) -> None:
        self.assertIn("onGenerate", self.source)
        self.assertIn("onCopy", self.source)

    def test_package_codegen_export(self) -> None:
        self.assertTrue(hasattr(cg, "render_password_generator_component"))
        self.assertTrue(callable(cg.render_password_generator_component))
        self.assertIn("render_password_generator_component", cg.__all__)


if __name__ == "__main__":
    unittest.main()
