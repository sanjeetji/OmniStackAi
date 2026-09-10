"""Tests for Task R-316: Generated Accessible Reusable Alert Component.

Verifies that NextjsWebAdapter emits an accessible, reusable compound Alert component
(apps/web/components/alert.tsx) with Alert, AlertTitle, and AlertDescription subcomponents,
supporting WAI-ARIA alert and status semantics.
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import (
    render_alert_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
)


class AlertComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.code = render_alert_component()

    def test_alert_component_is_client_component(self) -> None:
        """Alert component specifies 'use client' directive."""
        self.assertTrue(self.code.startswith('"use client";'))

    def test_alert_component_exports_types_and_subcomponents(self) -> None:
        """Alert component exports AlertVariant, interfaces, and subcomponents."""
        self.assertIn('export type AlertVariant = "info" | "success" | "warning" | "error";', self.code)
        self.assertIn("export interface AlertProps", self.code)
        self.assertIn("export interface AlertTitleProps", self.code)
        self.assertIn("export interface AlertDescriptionProps", self.code)
        self.assertIn("export function Alert(", self.code)
        self.assertIn("export function AlertTitle(", self.code)
        self.assertIn("export function AlertDescription(", self.code)
        self.assertIn("export default Alert;", self.code)

    def test_alert_component_uses_wai_aria_semantics(self) -> None:
        """Alert applies role='alert' for error and role='status' for info/success/warning."""
        self.assertIn('role={variant === "error" ? "alert" : "status"}', self.code)
        self.assertIn('aria-live={variant === "error" ? "assertive" : "polite"}', self.code)

    def test_alert_component_renders_vector_icons(self) -> None:
        """Alert includes built-in accessible vector icons with aria-hidden='true'."""
        self.assertIn('aria-hidden="true"', self.code)
        self.assertIn("<svg", self.code)

    def test_alert_component_supports_dismissible(self) -> None:
        """Alert supports dismissible flag, close button, and onDismiss callback."""
        self.assertIn("dismissible?: boolean;", self.code)
        self.assertIn("onDismiss?: () => void;", self.code)
        self.assertIn('aria-label="Dismiss alert"', self.code)

    def test_alert_component_supports_variants(self) -> None:
        """Alert component defines variant styles for info, success, warning, error."""
        self.assertIn("variantConfig: Record<AlertVariant,", self.code)
        self.assertIn("info:", self.code)
        self.assertIn("success:", self.code)
        self.assertIn("warning:", self.code)
        self.assertIn("error:", self.code)

    def test_alert_component_supports_action_slot(self) -> None:
        """Alert supports custom action button or link slot."""
        self.assertIn("action?: React.ReactNode;", self.code)

    def test_codegen_module_exports_render_alert_component(self) -> None:
        """render_alert_component is exported from omnistackai_agent_engine.codegen."""
        self.assertTrue(hasattr(cg, "render_alert_component"))
        self.assertEqual(cg.render_alert_component(), self.code)

    def test_adapter_generate_registers_alert_component(self) -> None:
        """NextjsWebAdapter.generate outputs components/alert.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/alert.tsx")
        self.assertIsNotNone(f)
        self.assertEqual(f.content, self.code)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        """render_alert_component is 100% diff-invariant across changes to ir.description."""
        ir1 = example_ir("minimal-blog")
        ir2 = dataclasses.replace(ir1, description="Completely changed IR description for R-316")

        adapter = NextjsWebAdapter()
        p1 = adapter.generate(ir1).get("components/alert.tsx")
        p2 = adapter.generate(ir2).get("components/alert.tsx")

        self.assertIsNotNone(p1)
        self.assertIsNotNone(p2)
        self.assertEqual(p1.content, p2.content)


if __name__ == "__main__":
    unittest.main()
