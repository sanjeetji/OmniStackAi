"""Tests for Task R-321: Generated Accessible Reusable Accordion Component.

Verifies that NextjsWebAdapter emits an accessible, reusable compound Accordion component
(apps/web/components/accordion.tsx) supporting WAI-ARIA 1.2 accordion semantics, single/multiple
modes, collapsible behavior, animated chevron icons, visual variants, and diff invariance.
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import (
    render_accordion_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
)


class AccordionComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.code = render_accordion_component()

    def test_accordion_component_is_client_component(self) -> None:
        """Accordion component must start with 'use client' directive."""
        self.assertTrue(self.code.startswith('"use client";'))

    def test_accordion_component_exports_types_and_compound_components(self) -> None:
        """Accordion component must export types, interfaces, and compound subcomponents."""
        self.assertIn('export type AccordionType = "single" | "multiple";', self.code)
        self.assertIn('export type AccordionVariant = "default" | "bordered" | "separated";', self.code)
        self.assertIn("export interface AccordionProps", self.code)
        self.assertIn("export interface AccordionItemProps", self.code)
        self.assertIn("export interface AccordionTriggerProps", self.code)
        self.assertIn("export interface AccordionContentProps", self.code)
        self.assertIn("export function Accordion(", self.code)
        self.assertIn("export function AccordionItem(", self.code)
        self.assertIn("export function AccordionTrigger(", self.code)
        self.assertIn("export function AccordionContent(", self.code)
        self.assertIn("export default Accordion;", self.code)

    def test_accordion_component_uses_wai_aria_accordion_semantics(self) -> None:
        """Accordion elements must emit WAI-ARIA 1.2 accordion roles and state attributes."""
        self.assertIn("aria-expanded={isOpen}", self.code)
        self.assertIn("aria-controls={contentId}", self.code)
        self.assertIn('role="region"', self.code)
        self.assertIn("aria-labelledby={triggerId}", self.code)
        self.assertIn("hidden={!isOpen}", self.code)

    def test_accordion_component_supports_single_and_multiple_modes(self) -> None:
        """Accordion must support both single active item and multiple expandable items."""
        self.assertIn('type === "single"', self.code)
        self.assertIn('type === "multiple"', self.code)

    def test_accordion_component_supports_collapsible_behavior(self) -> None:
        """Accordion in single mode must support collapsible toggle."""
        self.assertIn("collapsible = true", self.code)

    def test_accordion_component_supports_controlled_and_uncontrolled_modes(self) -> None:
        """Accordion must support controlled (value, onValueChange) and uncontrolled (defaultValue)."""
        self.assertIn("const isControlled = value !== undefined;", self.code)
        self.assertIn("defaultValue", self.code)
        self.assertIn("onValueChange?.(", self.code)

    def test_accordion_component_includes_animated_chevron_icon(self) -> None:
        """AccordionTrigger must render a rotating chevron icon with aria-hidden='true'."""
        self.assertIn('aria-hidden="true"', self.code)
        self.assertIn('rotate(180deg)', self.code)
        self.assertIn('<svg', self.code)

    def test_accordion_component_supports_variants(self) -> None:
        """Accordion must support default, bordered, and separated styling variants."""
        self.assertIn('"default"', self.code)
        self.assertIn('"bordered"', self.code)
        self.assertIn('"separated"', self.code)

    def test_accordion_component_handles_disabled_items(self) -> None:
        """AccordionItem must support disabled state disabling trigger button."""
        self.assertIn("disabled?: boolean;", self.code)
        self.assertIn("disabled={disabled}", self.code)
        self.assertIn('"not-allowed"', self.code)

    def test_codegen_module_exports_render_accordion_component(self) -> None:
        """render_accordion_component is exported from omnistackai_agent_engine.codegen."""
        self.assertTrue(hasattr(cg, "render_accordion_component"))
        self.assertEqual(cg.render_accordion_component(), self.code)

    def test_adapter_generate_registers_accordion_component_and_diff_invariance(self) -> None:
        """NextjsWebAdapter.generate outputs components/accordion.tsx and maintains diff-invariance."""
        ir1 = example_ir("minimal-blog")
        ir2 = dataclasses.replace(ir1, description="Completely changed IR description for R-321")

        adapter = NextjsWebAdapter()
        p1 = adapter.generate(ir1).get("components/accordion.tsx")
        p2 = adapter.generate(ir2).get("components/accordion.tsx")

        self.assertIsNotNone(p1)
        self.assertIsNotNone(p2)
        self.assertEqual(p1.content, self.code)
        self.assertEqual(p1.content, p2.content)


if __name__ == "__main__":
    unittest.main()
