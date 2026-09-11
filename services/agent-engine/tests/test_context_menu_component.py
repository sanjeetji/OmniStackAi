"""Tests for Task R-348: Generated Accessible Futuristic Reusable Context Menu Suite.

Verifies that NextjsWebAdapter emits an accessible, desktop-class, zero-dependency, and futuristic
Context Menu compound component suite (apps/web/components/context-menu.tsx) supporting:
- Compound suite (ContextMenu, ContextMenu.Trigger, ContextMenu.Content, ContextMenu.Item,
  ContextMenu.CheckboxItem, ContextMenu.RadioGroup, ContextMenu.RadioItem, ContextMenu.Separator,
  ContextMenu.Label, ContextMenu.Sub, ContextMenu.SubTrigger, ContextMenu.SubContent)
- Viewport boundary collision prevention and clamping (window.innerWidth / window.innerHeight)
- Nested submenus with edge-flipping support
- Checkbox and radio items with custom vector indicators
- Shortcut key badges (<kbd>) and destructive item styling
- Full WAI-ARIA 1.2 menu accessibility semantics (role="menu", role="menuitem", etc.)
- Full keyboard navigation (Escape, ArrowDown/Up, ArrowRight/Left, Home, End, Tab)
- 4 futuristic visual variants ("neon", "glass", "bordered", "minimal")
- 3 size presets ("sm", "md", "lg")
- 100% diff-invariance across ir.description changes
- Zero external runtime dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_context_menu_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class ContextMenuComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the ContextMenu component suite."""

    def setUp(self) -> None:
        self.code = render_context_menu_component()
        self.ir = example_ir("rideshare-favourites")

    def test_context_menu_is_client_component(self) -> None:
        """ContextMenu must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "ContextMenu must have 'use client' as the first statement.",
        )

    def test_context_menu_exports_types(self) -> None:
        """Verify export of TypeScript interfaces and union types."""
        self.assertIn("export type ContextMenuVariant", self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"bordered"', self.code)
        self.assertIn('"minimal"', self.code)
        self.assertIn("export type ContextMenuSize", self.code)
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)
        self.assertIn("export interface ContextMenuProps", self.code)
        self.assertIn("export interface ContextMenuTriggerProps", self.code)
        self.assertIn("export interface ContextMenuContentProps", self.code)
        self.assertIn("export interface ContextMenuItemProps", self.code)
        self.assertIn("export interface ContextMenuCheckboxItemProps", self.code)
        self.assertIn("export interface ContextMenuRadioGroupProps", self.code)
        self.assertIn("export interface ContextMenuRadioItemProps", self.code)
        self.assertIn("export interface ContextMenuSeparatorProps", self.code)
        self.assertIn("export interface ContextMenuLabelProps", self.code)
        self.assertIn("export interface ContextMenuSubProps", self.code)
        self.assertIn("export interface ContextMenuSubTriggerProps", self.code)
        self.assertIn("export interface ContextMenuSubContentProps", self.code)
        self.assertIn("export interface ContextMenuContextValue", self.code)

    def test_context_menu_exports_compound_components(self) -> None:
        """Verify ContextMenu compound component and all subcomponents."""
        self.assertIn("export const ContextMenuTrigger =", self.code)
        self.assertIn("export const ContextMenuContent =", self.code)
        self.assertIn("export const ContextMenuItem =", self.code)
        self.assertIn("export const ContextMenuCheckboxItem =", self.code)
        self.assertIn("export const ContextMenuRadioGroup =", self.code)
        self.assertIn("export const ContextMenuRadioItem =", self.code)
        self.assertIn("export const ContextMenuSeparator =", self.code)
        self.assertIn("export const ContextMenuLabel =", self.code)
        self.assertIn("export const ContextMenuSub =", self.code)
        self.assertIn("export const ContextMenuSubTrigger =", self.code)
        self.assertIn("export const ContextMenuSubContent =", self.code)
        self.assertIn("ContextMenu.Trigger = ContextMenuTrigger;", self.code)
        self.assertIn("ContextMenu.Content = ContextMenuContent;", self.code)
        self.assertIn("ContextMenu.Item = ContextMenuItem;", self.code)
        self.assertIn("ContextMenu.CheckboxItem = ContextMenuCheckboxItem;", self.code)
        self.assertIn("ContextMenu.RadioGroup = ContextMenuRadioGroup;", self.code)
        self.assertIn("ContextMenu.RadioItem = ContextMenuRadioItem;", self.code)
        self.assertIn("ContextMenu.Separator = ContextMenuSeparator;", self.code)
        self.assertIn("ContextMenu.Label = ContextMenuLabel;", self.code)
        self.assertIn("ContextMenu.Sub = ContextMenuSub;", self.code)
        self.assertIn("ContextMenu.SubTrigger = ContextMenuSubTrigger;", self.code)
        self.assertIn("ContextMenu.SubContent = ContextMenuSubContent;", self.code)
        self.assertIn("export default ContextMenu;", self.code)

    def test_context_menu_zero_external_dependencies(self) -> None:
        """ContextMenu uses only React; zero external package imports."""
        import_lines = [
            line.strip()
            for line in self.code.splitlines()
            if line.strip().startswith("import ")
        ]
        self.assertTrue(len(import_lines) >= 1)
        for line in import_lines:
            self.assertIn(
                'from "react"',
                line,
                f"Unexpected external import found in ContextMenu: {line}",
            )

    def test_context_menu_wai_aria_menu_semantics(self) -> None:
        """Verify WAI-ARIA menu roles and accessibility attributes."""
        self.assertIn('role="menu"', self.code)
        self.assertIn('role="menuitem"', self.code)
        self.assertIn('role="menuitemcheckbox"', self.code)
        self.assertIn('role="menuitemradio"', self.code)
        self.assertIn('role="separator"', self.code)
        self.assertIn('role="group"', self.code)
        self.assertIn('aria-orientation="vertical"', self.code)
        self.assertIn('aria-checked={checked}', self.code)
        self.assertIn('aria-haspopup="menu"', self.code)
        self.assertIn('aria-expanded=', self.code)

    def test_context_menu_keyboard_navigation(self) -> None:
        """Verify full keyboard navigation handling."""
        self.assertIn('"Escape"', self.code)
        self.assertIn('"ArrowDown"', self.code)
        self.assertIn('"ArrowUp"', self.code)
        self.assertIn('"ArrowRight"', self.code)
        self.assertIn('"ArrowLeft"', self.code)
        self.assertIn('"Home"', self.code)
        self.assertIn('"End"', self.code)
        self.assertIn('"Tab"', self.code)
        self.assertIn('"Enter"', self.code)

    def test_context_menu_viewport_boundary_clamping(self) -> None:
        """Verify viewport boundary collision prevention calculations."""
        self.assertIn("window.innerWidth", self.code)
        self.assertIn("window.innerHeight", self.code)
        self.assertIn("getBoundingClientRect", self.code)
        self.assertIn("position: \"fixed\"", self.code)

    def test_context_menu_submenus(self) -> None:
        """Verify nested submenu support with Sub, SubTrigger, and SubContent."""
        self.assertIn("ContextMenuSubContext", self.code)
        self.assertIn("onMouseEnter={() => setOpen(true)}", self.code)
        self.assertIn("onMouseLeave={() => setOpen(false)}", self.code)
        self.assertIn('left: "100%"', self.code)

    def test_context_menu_checkbox_and_radio_items(self) -> None:
        """Verify CheckboxItem and RadioItem indicators and selection state."""
        self.assertIn("onCheckedChange", self.code)
        self.assertIn("onValueChange", self.code)
        self.assertIn("points=\"20 6 9 17 4 12\"", self.code)
        self.assertIn("borderRadius: \"50%\"", self.code)

    def test_context_menu_shortcuts_and_kbd(self) -> None:
        """Verify keyboard shortcut indicator element."""
        self.assertIn("<kbd", self.code)
        self.assertIn("{shortcut}", self.code)

    def test_context_menu_destructive_item(self) -> None:
        """Verify destructive item variant styling."""
        self.assertIn("destructive ? \"#ef4444\" : \"inherit\"", self.code)

    def test_context_menu_supports_variants(self) -> None:
        """Verify 4 futuristic visual variants."""
        self.assertIn('variant === "neon"', self.code)
        self.assertIn('variant === "glass"', self.code)
        self.assertIn('variant === "bordered"', self.code)
        self.assertIn("minimal", self.code)

    def test_context_menu_supports_sizes(self) -> None:
        """Verify 3 size presets."""
        self.assertIn('sm: { minWidth: "160px"', self.code)
        self.assertIn('md: { minWidth: "190px"', self.code)
        self.assertIn('lg: { minWidth: "220px"', self.code)

    def test_context_menu_diff_invariant(self) -> None:
        """ContextMenu output is 100% diff-invariant across ir.description changes."""
        adapter = NextjsWebAdapter()
        project1 = adapter.generate(self.ir)
        ir2 = dataclasses.replace(
            self.ir, description="Completely changed description for diff test."
        )
        project2 = adapter.generate(ir2)
        cm1 = project1.get("components/context-menu.tsx").content
        cm2 = project2.get("components/context-menu.tsx").content
        self.assertEqual(
            cm1,
            cm2,
            "components/context-menu.tsx must be 100% diff-invariant across ir.description",
        )
        self.assertEqual(cm1, self.code)

    def test_adapter_emits_context_menu_file(self) -> None:
        """NextjsWebAdapter emits components/context-menu.tsx in generated project."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/context-menu.tsx")
        self.assertIsNotNone(f, "components/context-menu.tsx must be generated")
        self.assertEqual(f.content, self.code)

    def test_package_codegen_exports_render_context_menu_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_context_menu_component."""
        self.assertTrue(callable(cg.render_context_menu_component))
        self.assertEqual(cg.render_context_menu_component(), self.code)


if __name__ == "__main__":
    unittest.main()
