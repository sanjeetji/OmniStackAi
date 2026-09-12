"""Tests for the Accessible Futuristic Password Strength Meter & Requirements Suite (components/password-strength.tsx)."""

from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine import codegen as cg
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_password_strength_component,
)


class TestPasswordStrengthComponent(unittest.TestCase):
    """Unit tests for the Accessible Futuristic Password Strength Meter & Requirements Suite (R-403)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_password_strength_component()

    def test_file_generated(self) -> None:
        project = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        self.assertIsNotNone(project.get("components/password-strength.tsx"))

    def test_diff_invariance_and_codegen_export(self) -> None:
        proj1 = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        proj2 = NextjsWebAdapter().generate(example_ir("rideshare-favourites"))
        f1 = proj1.get("components/password-strength.tsx")
        f2 = proj2.get("components/password-strength.tsx")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, render_password_strength_component())

    def test_use_client_directive(self) -> None:
        self.assertTrue(self.source.startswith("'use client';"))

    def test_zero_runtime_dependencies(self) -> None:
        for pkg in re.findall(r"from\s+['\"]([^'\"]+)['\"]", self.source):
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected import: {pkg}",
            )

    def test_forward_ref_and_imperative_handle(self) -> None:
        self.assertIn("forwardRef<PasswordStrengthHandle, PasswordStrengthProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        for method in ("getValue:", "setValue:", "getStrength:", "clear:", "focus:"):
            self.assertIn(method, self.source)

    def test_typescript_types_present(self) -> None:
        for decl in (
            "export type PasswordStrengthVariant",
            "export type PasswordStrengthSize",
            "export type PasswordStrengthLevel",
            "export interface PasswordRule",
            "export interface PasswordStrengthResult",
            "export interface PasswordStrengthHandle",
            "export interface PasswordStrengthProps",
        ):
            self.assertIn(decl, self.source)

    def test_compound_and_alias_exports(self) -> None:
        for decl in (
            "export const PasswordStrength =",
            "export const PasswordStrengthMeter =",
            "export const PasswordInput =",
            "export const PasswordField =",
            "export default PasswordStrengthComponent",
        ):
            self.assertIn(decl, self.source)

    def test_display_names_defined(self) -> None:
        for line in (
            "PasswordStrengthComponent.displayName = 'PasswordStrength'",
            "PasswordStrengthMeter.displayName = 'PasswordStrengthMeter'",
            "PasswordInput.displayName = 'PasswordInput'",
            "PasswordField.displayName = 'PasswordField'",
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

    def test_levels_present(self) -> None:
        self.assertIn("'empty' | 'weak' | 'fair' | 'good' | 'strong'", self.source)

    def test_strength_scoring(self) -> None:
        for token in ("score", "minLength", ".test(", "rules"):
            self.assertIn(token, self.source)

    def test_requirements_checklist(self) -> None:
        self.assertIn("showRequirements", self.source)
        self.assertIn("passed", self.source)

    def test_show_hide_toggle(self) -> None:
        self.assertIn("showToggle", self.source)
        self.assertIn("aria-pressed", self.source)
        self.assertIn("'password'", self.source)

    def test_aria_semantics(self) -> None:
        self.assertIn('role="status"', self.source)
        self.assertIn("aria-live", self.source)
        self.assertIn("aria-describedby", self.source)
        self.assertIn("useId(", self.source)

    def test_callbacks(self) -> None:
        self.assertIn("onChange", self.source)
        self.assertIn("onStrengthChange", self.source)

    def test_controlled_and_uncontrolled(self) -> None:
        self.assertIn("value", self.source)
        self.assertIn("defaultValue", self.source)

    def test_package_codegen_export(self) -> None:
        self.assertTrue(hasattr(cg, "render_password_strength_component"))
        self.assertTrue(callable(cg.render_password_strength_component))
        self.assertIn("render_password_strength_component", cg.__all__)


if __name__ == "__main__":
    unittest.main()
