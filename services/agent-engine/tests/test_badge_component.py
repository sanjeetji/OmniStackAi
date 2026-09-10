"""Tests for Task R-312: Generated Accessible Reusable Badge & Status Pill Component.

Verifies that NextjsWebAdapter emits a dedicated, accessible, reusable Badge
component (apps/web/components/badge.tsx) supporting semantic status variants,
dot indicators, sizing, and clean WAI-ARIA role="status" compliance.
"""

from __future__ import annotations

import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_badge_component,
)


class BadgeComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.code = render_badge_component()
        self.ir = example_ir("minimal-blog")

    def test_render_badge_component_returns_string(self) -> None:
        self.assertIsInstance(self.code, str)
        self.assertGreater(len(self.code), 100)

    def test_badge_component_is_client_component(self) -> None:
        self.assertTrue(self.code.startswith('"use client";'))

    def test_badge_component_exports_types(self) -> None:
        self.assertIn("export type BadgeVariant =", self.code)
        self.assertIn('"success"', self.code)
        self.assertIn('"warning"', self.code)
        self.assertIn('"error"', self.code)
        self.assertIn('"info"', self.code)
        self.assertIn('"neutral"', self.code)
        self.assertIn("export type BadgeSize =", self.code)
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn("export interface BadgeProps", self.code)

    def test_badge_component_exports_badge_function_and_default(self) -> None:
        self.assertIn("export function Badge(", self.code)
        self.assertIn("export default Badge;", self.code)

    def test_badge_component_has_status_role(self) -> None:
        self.assertIn('role="status"', self.code)
        self.assertIn("aria-label={ariaLabel}", self.code)

    def test_badge_component_supports_variants(self) -> None:
        self.assertIn("VARIANT_STYLES", self.code)
        # Success colors
        self.assertIn("#dcfce7", self.code)
        self.assertIn("#166534", self.code)
        # Warning colors
        self.assertIn("#fef3c7", self.code)
        self.assertIn("#92400e", self.code)
        # Error colors
        self.assertIn("#fee2e2", self.code)
        self.assertIn("#991b1b", self.code)
        # Info colors
        self.assertIn("#eff6ff", self.code)
        self.assertIn("#1d4ed8", self.code)

    def test_badge_component_supports_sizes(self) -> None:
        self.assertIn('size === "sm"', self.code)
        self.assertIn("fontSize: isSm ? 11 : 12", self.code)

    def test_badge_component_renders_dot_indicator(self) -> None:
        self.assertIn("dot && (", self.code)
        self.assertIn('aria-hidden="true"', self.code)
        self.assertIn('borderRadius: "50%"', self.code)

    def test_badge_component_supports_pulse(self) -> None:
        self.assertIn("pulse", self.code)

    def test_adapter_registers_badge_component(self) -> None:
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        badge_file = project.get("components/badge.tsx")
        self.assertIsNotNone(badge_file)
        self.assertEqual(badge_file.content, self.code)

    def test_codegen_module_exports_render_badge_component(self) -> None:
        import omnistackai_agent_engine.codegen as cg

        self.assertTrue(hasattr(cg, "render_badge_component"))
        self.assertEqual(cg.render_badge_component(), self.code)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        code1 = render_badge_component()
        code2 = render_badge_component()
        self.assertEqual(code1, code2)


if __name__ == "__main__":
    unittest.main()
