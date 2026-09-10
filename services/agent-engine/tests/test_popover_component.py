"""Tests for Task R-323: Generated Accessible Reusable Popover Component.

Verifies that NextjsWebAdapter emits an accessible, reusable compound Popover component
(apps/web/components/popover.tsx) supporting WAI-ARIA dialog semantics, placement positioning,
click-outside and Escape dismiss, controlled/uncontrolled state, and diff invariance.
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import (
    render_popover_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
    _POPOVER_COMPONENT,
)


class PopoverComponentTests(unittest.TestCase):
    """Assertions ensuring the emitted Popover component conforms to enterprise WAI-ARIA standards."""

    def setUp(self) -> None:
        self.code = _POPOVER_COMPONENT

    def test_popover_component_is_client_component(self) -> None:
        """Popover component must start with 'use client' directive."""
        self.assertTrue(
            self.code.strip().startswith('"use client";')
            or self.code.strip().startswith("'use client';")
        )

    def test_popover_component_exports_types_and_compound_components(self) -> None:
        """Popover must export types, interfaces, and compound subcomponents."""
        self.assertIn("export function Popover(", self.code)
        self.assertIn("export function PopoverTrigger(", self.code)
        self.assertIn("export function PopoverContent(", self.code)
        self.assertIn("export function PopoverClose(", self.code)
        self.assertIn("export function PopoverArrow(", self.code)
        self.assertIn("export type PopoverAlign", self.code)
        self.assertIn("export type PopoverSide", self.code)
        self.assertIn("export interface PopoverProps", self.code)
        self.assertIn("export interface PopoverTriggerProps", self.code)
        self.assertIn("export interface PopoverContentProps", self.code)
        self.assertIn("export interface PopoverCloseProps", self.code)

    def test_popover_component_uses_wai_aria_dialog_semantics(self) -> None:
        """Popover elements must emit WAI-ARIA dialog roles and state attributes."""
        self.assertIn('aria-haspopup="dialog"', self.code)
        self.assertIn('aria-expanded={isOpen}', self.code)
        self.assertIn('role="dialog"', self.code)
        self.assertIn('aria-modal="true"', self.code)
        self.assertIn("aria-controls={contentId}", self.code)
        self.assertIn("aria-labelledby={triggerId}", self.code)

    def test_popover_component_supports_placements_and_alignments(self) -> None:
        """Popover must support align ('start' | 'end' | 'center') and side ('top' | 'bottom' | 'left' | 'right')."""
        self.assertIn('"start"', self.code)
        self.assertIn('"end"', self.code)
        self.assertIn('"center"', self.code)
        self.assertIn('"top"', self.code)
        self.assertIn('"bottom"', self.code)
        self.assertIn('"left"', self.code)
        self.assertIn('"right"', self.code)

    def test_popover_component_supports_controlled_and_uncontrolled_modes(self) -> None:
        """Popover must support controlled (open, onOpenChange) and uncontrolled (defaultOpen) modes."""
        self.assertIn("open?: boolean", self.code)
        self.assertIn("defaultOpen?: boolean", self.code)
        self.assertIn("onOpenChange?: (open: boolean) => void", self.code)
        self.assertIn("isControlled ? controlledOpen : uncontrolledOpen", self.code)

    def test_popover_component_handles_click_outside_dismiss(self) -> None:
        """Popover must attach mousedown listener to dismiss on outside click."""
        self.assertIn("mousedown", self.code)
        self.assertIn("setIsOpen(false)", self.code)

    def test_popover_component_handles_escape_dismiss_and_focus_restoration(self) -> None:
        """Popover must listen for Escape key to close and restore focus to trigger."""
        self.assertIn('"Escape"', self.code)
        self.assertIn("triggerRef.current?.focus()", self.code)

    def test_popover_close_button_has_accessible_label(self) -> None:
        """PopoverClose must emit accessible aria-label."""
        self.assertIn('aria-label="Close popover"', self.code)

    def test_popover_arrow_renders_pointing_indicator(self) -> None:
        """PopoverArrow must render a visual pointer indicator with aria-hidden='true'."""
        self.assertIn('aria-hidden="true"', self.code)
        self.assertIn("PopoverArrow", self.code)

    def test_adapter_generate_registers_popover_component_and_diff_invariance(self) -> None:
        """NextjsWebAdapter.generate outputs components/popover.tsx and maintains diff-invariance."""
        ir1 = example_ir("minimal-blog")
        ir2 = dataclasses.replace(ir1, description="Completely changed IR description for R-323")

        adapter = NextjsWebAdapter()
        p1 = adapter.generate(ir1).get("components/popover.tsx")
        p2 = adapter.generate(ir2).get("components/popover.tsx")

        self.assertIsNotNone(p1)
        self.assertIsNotNone(p2)
        self.assertEqual(p1.content, self.code)
        self.assertEqual(p1.content, p2.content)

    def test_codegen_module_exports_render_popover_component(self) -> None:
        """render_popover_component is exported from omnistackai_agent_engine.codegen."""
        self.assertTrue(hasattr(cg, "render_popover_component"))
        self.assertEqual(cg.render_popover_component(), self.code)


if __name__ == "__main__":
    unittest.main()
