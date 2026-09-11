"""Tests for Task R-359: Generated Accessible Futuristic Reusable Bottom Navigation Bar Primitive.

Verifies that NextjsWebAdapter emits an accessible, mobile-first, zero-dependency, and futuristic
Bottom Navigation Bar compound component suite (apps/web/components/bottom-nav.tsx) supporting:
- WAI-ARIA 1.2 Tabs pattern compliance:
  - Nav container emits role="tablist", aria-orientation="horizontal"
  - Each item button emits role="tab", aria-selected, aria-disabled, aria-controls
- Keyboard navigation:
  - ArrowRight / ArrowLeft / ArrowUp / ArrowDown traversal with wrap-around
  - Home / End jump navigation
- 4 futuristic visual styling variants ("default", "glass", "card", "neon")
- 3 size scales ("sm", "md", "lg") with responsive heights and font metrics
- Optional floating-action-button (FAB) slot with centre gap
- Full-screen backdrop tint (backdropOpen) for FAB menus
- Badge support: dot indicator (boolean) and count chip (number | string)
- Disabled item support with aria-disabled and pointer-events
- Controlled and uncontrolled selection modes
- Active pill indicator transition
- React ref forwarding (forwardRef) and explicit displayName
- 100% diff-invariance across ir.description changes
- Zero external runtime npm dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_bottom_nav_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class BottomNavComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the BottomNav component suite."""

    def setUp(self) -> None:
        self.code = render_bottom_nav_component()
        self.ir = example_ir("rideshare-favourites")

    # ------------------------------------------------------------------
    # Basic structure
    # ------------------------------------------------------------------

    def test_bottom_nav_is_client_component(self) -> None:
        """BottomNav must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "BottomNav must have 'use client' as the first statement.",
        )

    def test_bottom_nav_exports_types(self) -> None:
        """Verify export of TypeScript union types and interfaces."""
        self.assertIn("export type BottomNavVariant", self.code)
        self.assertIn('"default"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"card"', self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn("export type BottomNavSize", self.code)
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)
        self.assertIn("export interface BottomNavItem", self.code)
        self.assertIn("export interface BottomNavProps", self.code)

    def test_bottom_nav_exports_component_and_display_name(self) -> None:
        """Verify BottomNav export, forwardRef, displayName, and default export."""
        self.assertIn("export const BottomNav = forwardRef", self.code)
        self.assertIn('BottomNav.displayName = "BottomNav";', self.code)
        self.assertIn("export default BottomNav;", self.code)

    # ------------------------------------------------------------------
    # WAI-ARIA semantics
    # ------------------------------------------------------------------

    def test_bottom_nav_wai_aria_tablist(self) -> None:
        """Nav must expose role=tablist with aria-orientation=horizontal."""
        self.assertIn('role="tablist"', self.code)
        self.assertIn('aria-orientation="horizontal"', self.code)

    def test_bottom_nav_wai_aria_tab_buttons(self) -> None:
        """Each item button must carry the WAI-ARIA tab role and attributes."""
        self.assertIn('role="tab"', self.code)
        self.assertIn("aria-selected={isActive}", self.code)
        self.assertIn("aria-disabled={item.disabled}", self.code)
        self.assertIn("aria-controls={panelId}", self.code)

    def test_bottom_nav_accessible_label(self) -> None:
        """Items must propagate aria-label (with override support)."""
        self.assertIn("aria-label={item.ariaLabel ?? item.label}", self.code)

    def test_bottom_nav_nav_landmark(self) -> None:
        """The root element must be a <nav> landmark with aria-label."""
        self.assertIn('<nav ref={ref}', self.code)
        self.assertIn('aria-label="Main navigation"', self.code)

    # ------------------------------------------------------------------
    # Keyboard navigation
    # ------------------------------------------------------------------

    def test_bottom_nav_keyboard_arrow_right(self) -> None:
        """ArrowRight must move focus to the next enabled tab."""
        self.assertIn('"ArrowRight"', self.code)

    def test_bottom_nav_keyboard_arrow_left(self) -> None:
        """ArrowLeft must move focus to the previous enabled tab."""
        self.assertIn('"ArrowLeft"', self.code)

    def test_bottom_nav_keyboard_arrow_up_down(self) -> None:
        """ArrowUp / ArrowDown must also navigate (vertical alias)."""
        self.assertIn('"ArrowUp"', self.code)
        self.assertIn('"ArrowDown"', self.code)

    def test_bottom_nav_keyboard_home_end(self) -> None:
        """Home / End must jump to first / last enabled tab."""
        self.assertIn('"Home"', self.code)
        self.assertIn('"End"', self.code)

    # ------------------------------------------------------------------
    # Visual variants
    # ------------------------------------------------------------------

    def test_bottom_nav_glass_variant(self) -> None:
        """Glass variant must use backdropFilter and translucent background."""
        self.assertIn("backdropFilter", self.code)
        self.assertIn("rgba(255,255,255,0.72)", self.code)

    def test_bottom_nav_neon_variant(self) -> None:
        """Neon variant must use cyan glow and dark background."""
        self.assertIn("rgba(56,189,248,0.15)", self.code)
        self.assertIn("rgba(9,13,22,0.97)", self.code)
        self.assertIn('"#38bdf8"', self.code)

    def test_bottom_nav_card_variant(self) -> None:
        """Card variant must use top border-radius for a floating-card look."""
        self.assertIn('"20px 20px 0 0"', self.code)

    # ------------------------------------------------------------------
    # Size scales
    # ------------------------------------------------------------------

    def test_bottom_nav_size_sm(self) -> None:
        """sm size must set height to 52px."""
        self.assertIn('height: "52px"', self.code)

    def test_bottom_nav_size_md(self) -> None:
        """md size must set height to 60px."""
        self.assertIn('height: "60px"', self.code)

    def test_bottom_nav_size_lg(self) -> None:
        """lg size must set height to 72px."""
        self.assertIn('height: "72px"', self.code)

    # ------------------------------------------------------------------
    # Badge support
    # ------------------------------------------------------------------

    def test_bottom_nav_badge_chip(self) -> None:
        """BadgeChip helper must be present for count/dot badge rendering."""
        self.assertIn("BadgeChip", self.code)
        self.assertIn("item.badge !== undefined", self.code)
        self.assertIn("item.badge !== false", self.code)

    # ------------------------------------------------------------------
    # FAB slot
    # ------------------------------------------------------------------

    def test_bottom_nav_fab_slot(self) -> None:
        """Optional FAB slot must split items around a centre gap."""
        self.assertIn("hasFab", self.code)
        self.assertIn("leftItems", self.code)
        self.assertIn("rightItems", self.code)
        self.assertIn('width: "72px"', self.code)

    # ------------------------------------------------------------------
    # Backdrop
    # ------------------------------------------------------------------

    def test_bottom_nav_backdrop(self) -> None:
        """Backdrop tint must be rendered when backdropOpen is true."""
        self.assertIn("backdropOpen", self.code)
        self.assertIn('aria-hidden="true"', self.code)
        self.assertIn("onBackdropClose", self.code)

    # ------------------------------------------------------------------
    # Controlled / uncontrolled modes
    # ------------------------------------------------------------------

    def test_bottom_nav_controlled_mode(self) -> None:
        """Controlled mode uses activeKey prop; uncontrolled uses internal state."""
        self.assertIn("isControlled", self.code)
        self.assertIn("controlledActiveKey", self.code)
        self.assertIn("internalKey", self.code)
        self.assertIn("setInternalKey", self.code)

    # ------------------------------------------------------------------
    # Active pill indicator
    # ------------------------------------------------------------------

    def test_bottom_nav_active_pill(self) -> None:
        """An active pill indicator must animate in / out with opacity."""
        self.assertIn("pillStyle", self.code)
        self.assertIn("opacity: isActive ? 1 : 0", self.code)

    # ------------------------------------------------------------------
    # Zero external dependencies
    # ------------------------------------------------------------------

    def test_bottom_nav_zero_runtime_dependencies(self) -> None:
        """BottomNav template must not import external third-party libraries."""
        lines = [
            line.strip()
            for line in self.code.split("\n")
            if line.strip().startswith("import ")
        ]
        for line in lines:
            self.assertTrue(
                line.startswith("import React") or 'from "react"' in line,
                f"Unexpected external import detected: {line}",
            )

    # ------------------------------------------------------------------
    # Adapter wiring
    # ------------------------------------------------------------------

    def test_bottom_nav_adapter_emits_file(self) -> None:
        """NextjsWebAdapter must emit components/bottom-nav.tsx in the generated project."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/bottom-nav.tsx")
        self.assertIsNotNone(f)
        self.assertEqual(f.content, self.code)

    def test_bottom_nav_exported_from_codegen_package(self) -> None:
        """cg.render_bottom_nav_component must be exposed at package root."""
        self.assertTrue(callable(cg.render_bottom_nav_component))
        self.assertEqual(cg.render_bottom_nav_component(), self.code)

    # ------------------------------------------------------------------
    # Diff invariance
    # ------------------------------------------------------------------

    def test_bottom_nav_diff_invariance(self) -> None:
        """Diff invariance: changing ir.description must not alter components/bottom-nav.tsx."""
        adapter = NextjsWebAdapter()
        project1 = adapter.generate(self.ir)
        f1 = project1.get("components/bottom-nav.tsx")

        ir_mutated = dataclasses.replace(
            self.ir,
            description="Completely different description for diff invariance test",
        )
        project2 = adapter.generate(ir_mutated)
        f2 = project2.get("components/bottom-nav.tsx")

        self.assertEqual(f1.content, f2.content)


if __name__ == "__main__":
    unittest.main()
