"""Tests for Task R-322: Generated Accessible Reusable Dropdown Menu Component.

Verifies that NextjsWebAdapter emits an accessible, reusable compound Dropdown Menu component
(apps/web/components/dropdown-menu.tsx) supporting WAI-ARIA 1.2 menu semantics, keyboard navigation,
placement positioning, compound subcomponents, and diff invariance.
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import (
    render_dropdown_menu_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
    _DROPDOWN_MENU_COMPONENT,
)


class DropdownMenuComponentTests(unittest.TestCase):
    """Assertions ensuring the emitted Dropdown Menu component conforms to enterprise WAI-ARIA standards."""

    def setUp(self) -> None:
        self.code = _DROPDOWN_MENU_COMPONENT

    def test_dropdown_menu_component_is_client_component(self) -> None:
        """Dropdown Menu component must start with 'use client' directive."""
        self.assertTrue(
            self.code.strip().startswith('"use client";')
            or self.code.strip().startswith("'use client';")
        )

    def test_dropdown_menu_component_exports_types_and_compound_components(self) -> None:
        """Dropdown Menu must export types, interfaces, and compound subcomponents."""
        self.assertIn("export function DropdownMenu(", self.code)
        self.assertIn("export function DropdownMenuTrigger(", self.code)
        self.assertIn("export function DropdownMenuContent(", self.code)
        self.assertIn("export function DropdownMenuItem(", self.code)
        self.assertIn("export function DropdownMenuSeparator(", self.code)
        self.assertIn("export function DropdownMenuLabel(", self.code)
        self.assertIn("export type DropdownMenuAlign", self.code)
        self.assertIn("export type DropdownMenuSide", self.code)
        self.assertIn("export interface DropdownMenuProps", self.code)
        self.assertIn("export interface DropdownMenuTriggerProps", self.code)
        self.assertIn("export interface DropdownMenuContentProps", self.code)
        self.assertIn("export interface DropdownMenuItemProps", self.code)

    def test_dropdown_menu_component_uses_wai_aria_menu_semantics(self) -> None:
        """Dropdown Menu elements must emit WAI-ARIA 1.2 menu roles and state attributes."""
        self.assertIn('aria-haspopup="menu"', self.code)
        self.assertIn('aria-expanded={isOpen}', self.code)
        self.assertIn('role="menu"', self.code)
        self.assertIn('role="menuitem"', self.code)
        self.assertIn('role="separator"', self.code)
        self.assertIn("aria-controls={contentId}", self.code)
        self.assertIn("aria-labelledby={triggerId}", self.code)

    def test_dropdown_menu_component_supports_keyboard_navigation(self) -> None:
        """Dropdown Menu must support ArrowDown, ArrowUp, Home, End, Escape, and Enter/Space."""
        self.assertIn('"ArrowDown"', self.code)
        self.assertIn('"ArrowUp"', self.code)
        self.assertIn('"Home"', self.code)
        self.assertIn('"End"', self.code)
        self.assertIn('"Escape"', self.code)
        self.assertIn('"Enter"', self.code)
        self.assertIn('" "', self.code)

    def test_dropdown_menu_component_supports_placements_and_alignments(self) -> None:
        """Dropdown Menu must support align ('start' | 'end' | 'center') and side ('top' | 'bottom' | 'left' | 'right')."""
        self.assertIn('"start"', self.code)
        self.assertIn('"end"', self.code)
        self.assertIn('"center"', self.code)
        self.assertIn('"top"', self.code)
        self.assertIn('"bottom"', self.code)
        self.assertIn('"left"', self.code)
        self.assertIn('"right"', self.code)

    def test_dropdown_menu_component_supports_disabled_items(self) -> None:
        """DropdownMenuItem must handle disabled state with aria-disabled and focus skipping."""
        self.assertIn("aria-disabled={disabled", self.code)
        self.assertIn("disabled", self.code)

    def test_dropdown_menu_component_supports_destructive_items(self) -> None:
        """DropdownMenuItem must support destructive variant styling for hazardous actions."""
        self.assertIn("destructive?: boolean", self.code)
        self.assertIn("destructive", self.code)

    def test_dropdown_menu_component_handles_click_outside_and_escape_dismiss(self) -> None:
        """DropdownMenu must attach listeners to dismiss on outside click or Escape key."""
        self.assertIn("mousedown", self.code)
        self.assertIn("setIsOpen(false)", self.code)

    def test_dropdown_menu_component_supports_shortcut_and_icons(self) -> None:
        """DropdownMenuItem must support optional shortcut text badge and icon slot."""
        self.assertIn("shortcut?: string", self.code)
        self.assertIn("icon?: React.ReactNode", self.code)

    def test_adapter_generate_registers_dropdown_menu_component_and_diff_invariance(self) -> None:
        """NextjsWebAdapter.generate outputs components/dropdown-menu.tsx and maintains diff-invariance."""
        ir1 = example_ir("minimal-blog")
        ir2 = dataclasses.replace(ir1, description="Completely changed IR description for R-322")

        adapter = NextjsWebAdapter()
        p1 = adapter.generate(ir1).get("components/dropdown-menu.tsx")
        p2 = adapter.generate(ir2).get("components/dropdown-menu.tsx")

        self.assertIsNotNone(p1)
        self.assertIsNotNone(p2)
        self.assertEqual(p1.content, self.code)
        self.assertEqual(p1.content, p2.content)

    def test_codegen_module_exports_render_dropdown_menu_component(self) -> None:
        """render_dropdown_menu_component is exported from omnistackai_agent_engine.codegen."""
        self.assertTrue(hasattr(cg, "render_dropdown_menu_component"))
        self.assertEqual(cg.render_dropdown_menu_component(), self.code)


if __name__ == "__main__":
    unittest.main()
