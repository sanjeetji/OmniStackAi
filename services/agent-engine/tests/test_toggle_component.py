"""Tests for Task R-320: Generated Accessible Reusable Toggle Switch Component.

Verifies that NextjsWebAdapter emits an accessible, reusable Toggle Switch component
(apps/web/components/toggle.tsx) supporting WAI-ARIA 1.2 switch semantics, keyboard navigation,
multiple size presets, controlled and uncontrolled modes, and diff invariance.
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import (
    render_toggle_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
)


class ToggleComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.code = render_toggle_component()

    def test_toggle_component_is_client_component(self) -> None:
        """Toggle component must start with 'use client' directive."""
        self.assertTrue(self.code.startswith('"use client";'))

    def test_toggle_component_exports_types_and_components(self) -> None:
        """Toggle component must export ToggleSize, ToggleProps, Toggle, and ToggleSwitch."""
        self.assertIn('export type ToggleSize = "sm" | "md" | "lg";', self.code)
        self.assertIn("export interface ToggleProps", self.code)
        self.assertIn("export function Toggle(", self.code)
        self.assertIn("export const ToggleSwitch = Toggle;", self.code)
        self.assertIn("export default Toggle;", self.code)

    def test_toggle_component_uses_wai_aria_switch_semantics(self) -> None:
        """Toggle element must emit role='switch', aria-checked, and tabIndex."""
        self.assertIn('role="switch"', self.code)
        self.assertIn("aria-checked={isChecked}", self.code)
        self.assertIn("tabIndex={disabled ? -1 : 0}", self.code)

    def test_toggle_component_handles_keyboard_events(self) -> None:
        """Toggle must listen for Space and Enter key presses to toggle state."""
        self.assertIn('e.key === " " || e.key === "Spacebar" || e.key === "Enter"', self.code)
        self.assertIn("e.preventDefault()", self.code)

    def test_toggle_component_supports_sizes(self) -> None:
        """Toggle must define dimensions for sm, md, and lg sizes."""
        self.assertIn("SIZE_CONFIG", self.code)
        self.assertIn("trackWidth: 32", self.code)
        self.assertIn("trackWidth: 44", self.code)
        self.assertIn("trackWidth: 56", self.code)

    def test_toggle_component_supports_labels_and_descriptions(self) -> None:
        """Toggle must bind label and description with aria-labelledby and aria-describedby."""
        self.assertIn("useId()", self.code)
        self.assertIn("aria-labelledby={label ? labelId : undefined}", self.code)
        self.assertIn("aria-describedby={description ? descId : (ariaDescribedBy || undefined)}", self.code)

    def test_toggle_component_supports_controlled_and_uncontrolled_modes(self) -> None:
        """Toggle must support both controlled (checked, onChange) and uncontrolled (defaultChecked)."""
        self.assertIn("const isControlled = checked !== undefined;", self.code)
        self.assertIn("defaultChecked = false", self.code)
        self.assertIn("onChange?.(nextState);", self.code)

    def test_toggle_component_handles_disabled_state(self) -> None:
        """Toggle must handle disabled state with styling and aria-disabled."""
        self.assertIn("aria-disabled={disabled}", self.code)
        self.assertIn('cursor: disabled ? "not-allowed" : "pointer"', self.code)

    def test_toggle_component_supports_form_integration(self) -> None:
        """Toggle must render a hidden input when name is provided for HTML form submission."""
        self.assertIn('<input', self.code)
        self.assertIn('type="hidden"', self.code)
        self.assertIn('name={name}', self.code)
        self.assertIn('value={isChecked ? "true" : "false"}', self.code)

    def test_codegen_module_exports_render_toggle_component(self) -> None:
        """render_toggle_component is exported from omnistackai_agent_engine.codegen."""
        self.assertTrue(hasattr(cg, "render_toggle_component"))
        self.assertEqual(cg.render_toggle_component(), self.code)

    def test_adapter_generate_registers_toggle_component_and_diff_invariance(self) -> None:
        """NextjsWebAdapter.generate outputs components/toggle.tsx and maintains diff-invariance."""
        ir1 = example_ir("minimal-blog")
        ir2 = dataclasses.replace(ir1, description="Completely changed IR description for R-320")

        adapter = NextjsWebAdapter()
        p1 = adapter.generate(ir1).get("components/toggle.tsx")
        p2 = adapter.generate(ir2).get("components/toggle.tsx")

        self.assertIsNotNone(p1)
        self.assertIsNotNone(p2)
        self.assertEqual(p1.content, self.code)
        self.assertEqual(p1.content, p2.content)


if __name__ == "__main__":
    unittest.main()
