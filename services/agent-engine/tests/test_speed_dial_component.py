"""Tests for Task R-347: Generated Accessible Futuristic Reusable Speed Dial & Floating Action Button Component.

Verifies that NextjsWebAdapter emits an accessible, futuristic, reusable Speed Dial and
Floating Action Button (FAB) component suite (apps/web/components/speed-dial.tsx) supporting:
- Compound suite (SpeedDial, SpeedDial.Trigger, SpeedDial.Action, SpeedDial.Content)
- 4 directional cascades ("up", "down", "left", "right")
- 4 futuristic visual variants ("neon", "glass", "bordered", "minimal")
- 3 size presets ("sm", "md", "lg")
- Primary FAB with 45° rotation toggle animation
- Backdrop overlay support with click-to-dismiss
- Full WAI-ARIA 1.2 menu accessibility semantics (role="menu", role="menuitem", aria-haspopup="menu", aria-expanded)
- Full keyboard navigation (Escape, ArrowUp/Down/Left/Right, Home, End, Tab)
- 100% diff-invariance across ir.description changes
- Zero external runtime dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_speed_dial_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class SpeedDialComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the SpeedDial component."""

    def setUp(self) -> None:
        self.code = render_speed_dial_component()
        self.ir = example_ir("rideshare-favourites")

    def test_speed_dial_is_client_component(self) -> None:
        """SpeedDial must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "SpeedDial must have 'use client' as the first statement.",
        )

    def test_speed_dial_exports_types(self) -> None:
        """Verify export of TypeScript interfaces and union types."""
        self.assertIn("export type SpeedDialDirection", self.code)
        self.assertIn('"up"', self.code)
        self.assertIn('"down"', self.code)
        self.assertIn('"left"', self.code)
        self.assertIn('"right"', self.code)
        self.assertIn("export type SpeedDialVariant", self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"bordered"', self.code)
        self.assertIn('"minimal"', self.code)
        self.assertIn("export type SpeedDialSize", self.code)
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)
        self.assertIn("export interface SpeedDialActionItem", self.code)
        self.assertIn("export interface SpeedDialProps", self.code)
        self.assertIn("export interface SpeedDialTriggerProps", self.code)
        self.assertIn("export interface SpeedDialActionProps", self.code)
        self.assertIn("export interface SpeedDialContentProps", self.code)
        self.assertIn("export interface SpeedDialContextValue", self.code)

    def test_speed_dial_exports_compound_components(self) -> None:
        """Verify SpeedDial compound component and subcomponents."""
        self.assertIn("export const SpeedDialTrigger =", self.code)
        self.assertIn("export const SpeedDialContent =", self.code)
        self.assertIn("export const SpeedDialAction =", self.code)
        self.assertIn("export const SpeedDialRoot =", self.code)
        self.assertIn("SpeedDial.Trigger = SpeedDialTrigger;", self.code)
        self.assertIn("SpeedDial.Action = SpeedDialAction;", self.code)
        self.assertIn("SpeedDial.Content = SpeedDialContent;", self.code)
        self.assertIn("export default SpeedDial;", self.code)

    def test_speed_dial_zero_external_dependencies(self) -> None:
        """SpeedDial uses only React; zero external package imports."""
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
                f"Unexpected external import found in SpeedDial: {line}",
            )

    def test_speed_dial_wai_aria_menu_semantics(self) -> None:
        """Verify WAI-ARIA menu semantics, aria-haspopup, and menuitem roles."""
        self.assertIn('role="menu"', self.code)
        self.assertIn('role="menuitem"', self.code)
        self.assertIn('aria-haspopup="menu"', self.code)
        self.assertIn('aria-expanded={open}', self.code)
        self.assertIn('aria-controls={menuId}', self.code)
        self.assertIn('aria-labelledby={triggerId}', self.code)
        self.assertIn('aria-orientation=', self.code)

    def test_speed_dial_keyboard_navigation_keys(self) -> None:
        """Verify keyboard navigation keys handling."""
        self.assertIn('"Escape"', self.code)
        self.assertIn('"ArrowUp"', self.code)
        self.assertIn('"ArrowDown"', self.code)
        self.assertIn('"ArrowLeft"', self.code)
        self.assertIn('"ArrowRight"', self.code)
        self.assertIn('"Home"', self.code)
        self.assertIn('"End"', self.code)
        self.assertIn('"Tab"', self.code)

    def test_speed_dial_supports_four_directions(self) -> None:
        """Verify cascading layout positions for up, down, left, right directions."""
        self.assertIn("up:", self.code)
        self.assertIn("down:", self.code)
        self.assertIn("left:", self.code)
        self.assertIn("right:", self.code)
        self.assertIn('flexDirection: "column-reverse"', self.code)
        self.assertIn('flexDirection: "column"', self.code)
        self.assertIn('flexDirection: "row-reverse"', self.code)
        self.assertIn('flexDirection: "row"', self.code)

    def test_speed_dial_supports_four_variants(self) -> None:
        """Verify 4 futuristic visual variants."""
        self.assertIn('variant === "neon"', self.code)
        self.assertIn('variant === "glass"', self.code)
        self.assertIn('variant === "bordered"', self.code)
        self.assertIn("minimal", self.code)

    def test_speed_dial_supports_three_sizes(self) -> None:
        """Verify 3 size presets for trigger and action items."""
        self.assertIn('sm: { width: "40px", height: "40px"', self.code)
        self.assertIn('md: { width: "48px", height: "48px"', self.code)
        self.assertIn('lg: { width: "56px", height: "56px"', self.code)
        self.assertIn('sm: { width: "32px", height: "32px"', self.code)
        self.assertIn('md: { width: "40px", height: "40px"', self.code)
        self.assertIn('lg: { width: "48px", height: "48px"', self.code)

    def test_speed_dial_backdrop_overlay(self) -> None:
        """Verify optional backdrop overlay with aria-hidden and dismissal."""
        self.assertIn("backdrop && isOpen &&", self.code)
        self.assertIn('aria-hidden="true"', self.code)
        self.assertIn("backdropFilter:", self.code)

    def test_speed_dial_fab_animation(self) -> None:
        """Verify primary FAB 45-degree rotation toggle animation."""
        self.assertIn('rotate(45deg)', self.code)
        self.assertIn('rotate(0deg)', self.code)
        self.assertIn('transition: "transform 0.25s', self.code)

    def test_speed_dial_close_on_select(self) -> None:
        """Verify closeOnSelect option automatically closes dial on action selection."""
        self.assertIn("closeOnSelect", self.code)
        self.assertIn("onActionTrigger", self.code)
        self.assertIn("triggerRef.current?.focus()", self.code)

    def test_speed_dial_click_outside_dismiss(self) -> None:
        """Verify click outside dismissal handler."""
        self.assertIn("handlePointerDown", self.code)
        self.assertIn("mousedown", self.code)
        self.assertIn("touchstart", self.code)

    def test_speed_dial_diff_invariant(self) -> None:
        """SpeedDial output is 100% diff-invariant across ir.description changes."""
        adapter = NextjsWebAdapter()
        project1 = adapter.generate(self.ir)
        ir2 = dataclasses.replace(
            self.ir, description="Completely changed description for diff test."
        )
        project2 = adapter.generate(ir2)
        sd1 = project1.get("components/speed-dial.tsx").content
        sd2 = project2.get("components/speed-dial.tsx").content
        self.assertEqual(
            sd1,
            sd2,
            "components/speed-dial.tsx must be 100% diff-invariant across ir.description",
        )
        self.assertEqual(sd1, self.code)

    def test_adapter_emits_speed_dial_file(self) -> None:
        """NextjsWebAdapter emits components/speed-dial.tsx in generated project."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/speed-dial.tsx")
        self.assertIsNotNone(f, "components/speed-dial.tsx must be generated")
        self.assertEqual(f.content, self.code)

    def test_package_codegen_exports_render_speed_dial_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_speed_dial_component."""
        self.assertTrue(callable(cg.render_speed_dial_component))
        self.assertEqual(cg.render_speed_dial_component(), self.code)


if __name__ == "__main__":
    unittest.main()
