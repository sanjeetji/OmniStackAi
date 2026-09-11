"""Tests for Task R-349: Generated Accessible Futuristic Reusable Hover Card Suite.

Verifies that NextjsWebAdapter emits an accessible, desktop-grade, zero-dependency, and futuristic
Hover Card / Preview Card compound component suite (apps/web/components/hover-card.tsx) supporting:
- Compound suite (HoverCard, HoverCard.Trigger, HoverCard.Content, HoverCard.Arrow, useHoverCard)
- Viewport boundary collision prevention and clamping (window.innerWidth / window.innerHeight)
- Smooth pointer transit and cursor coordination without premature dismissal
- Configurable entrance and exit delay timers (openDelay, closeDelay)
- Directional positioning across 4 sides ("top", "bottom", "left", "right") and 3 aligns ("start", "center", "end")
- Directional SVG pointer arrow notch
- Full WAI-ARIA 1.2 dialog accessibility semantics (role="dialog", aria-haspopup="dialog", etc.)
- Full keyboard navigation (Escape key dismissal with trigger focus restoration)
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
from omnistackai_agent_engine.codegen import render_hover_card_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class HoverCardComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the HoverCard component suite."""

    def setUp(self) -> None:
        self.code = render_hover_card_component()
        self.ir = example_ir("rideshare-favourites")

    def test_hover_card_is_client_component(self) -> None:
        """HoverCard must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "HoverCard must have 'use client' as the first statement.",
        )

    def test_hover_card_exports_types(self) -> None:
        """Verify export of TypeScript interfaces and union types."""
        self.assertIn("export type HoverCardSide", self.code)
        self.assertIn('"top"', self.code)
        self.assertIn('"bottom"', self.code)
        self.assertIn('"left"', self.code)
        self.assertIn('"right"', self.code)
        self.assertIn("export type HoverCardAlign", self.code)
        self.assertIn('"start"', self.code)
        self.assertIn('"center"', self.code)
        self.assertIn('"end"', self.code)
        self.assertIn("export type HoverCardVariant", self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"bordered"', self.code)
        self.assertIn('"minimal"', self.code)
        self.assertIn("export type HoverCardSize", self.code)
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)
        self.assertIn("export interface HoverCardProps", self.code)
        self.assertIn("export interface HoverCardTriggerProps", self.code)
        self.assertIn("export interface HoverCardContentProps", self.code)
        self.assertIn("export interface HoverCardArrowProps", self.code)
        self.assertIn("export interface HoverCardContextValue", self.code)

    def test_hover_card_exports_compound_components(self) -> None:
        """Verify HoverCard compound component and all subcomponents."""
        self.assertIn("export function HoverCard(", self.code)
        self.assertIn("export function HoverCardTrigger(", self.code)
        self.assertIn("export function HoverCardContent(", self.code)
        self.assertIn("export function HoverCardArrow(", self.code)
        self.assertIn("export function useHoverCard()", self.code)
        self.assertIn("HoverCard.Trigger = HoverCardTrigger;", self.code)
        self.assertIn("HoverCard.Content = HoverCardContent;", self.code)
        self.assertIn("HoverCard.Arrow = HoverCardArrow;", self.code)
        self.assertIn("export default HoverCard;", self.code)

    def test_hover_card_zero_external_dependencies(self) -> None:
        """HoverCard uses only React; zero external package imports."""
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
                f"Unexpected external import found in HoverCard: {line}",
            )

    def test_hover_card_wai_aria_dialog_semantics(self) -> None:
        """Verify WAI-ARIA dialog roles and accessibility attributes."""
        self.assertIn('role="dialog"', self.code)
        self.assertIn('"aria-haspopup": "dialog"', self.code)
        self.assertIn('"aria-expanded": isOpen', self.code)
        self.assertIn('"aria-controls": isOpen ? contentId : undefined', self.code)
        self.assertIn('aria-labelledby={triggerId}', self.code)
        self.assertIn('tabIndex={-1}', self.code)

    def test_hover_card_keyboard_navigation(self) -> None:
        """Verify Escape key closes card and restores trigger focus."""
        self.assertIn('e.key === "Escape"', self.code)
        self.assertIn("setIsOpen(false)", self.code)
        self.assertIn("triggerRef.current?.focus()", self.code)

    def test_hover_card_delay_timers(self) -> None:
        """Verify openDelay and closeDelay timer configuration and clearance."""
        self.assertIn("openDelay = 300", self.code)
        self.assertIn("closeDelay = 200", self.code)
        self.assertIn("openTimerRef", self.code)
        self.assertIn("closeTimerRef", self.code)
        self.assertIn("clearTimeout", self.code)

    def test_hover_card_pointer_transit(self) -> None:
        """Verify pointer enter and leave handlers on both trigger and content."""
        self.assertIn("handleOpen", self.code)
        self.assertIn("handleClose", self.code)
        self.assertIn("onPointerEnter", self.code)
        self.assertIn("onPointerLeave", self.code)

    def test_hover_card_viewport_collision_clamping(self) -> None:
        """Verify collision avoidance flipping and viewport clamping calculations."""
        self.assertIn("window.innerWidth", self.code)
        self.assertIn("window.innerHeight", self.code)
        self.assertIn("getBoundingClientRect", self.code)
        self.assertIn("avoidCollisions", self.code)
        self.assertIn("Math.max(8, Math.min(left, viewportWidth - contentRect.width - 8))", self.code)
        self.assertIn("Math.max(8, Math.min(top, viewportHeight - contentRect.height - 8))", self.code)

    def test_hover_card_directional_sides(self) -> None:
        """Verify side placement calculations."""
        self.assertIn('chosenSide === "bottom"', self.code)
        self.assertIn('chosenSide === "top"', self.code)
        self.assertIn('chosenSide === "right"', self.code)
        self.assertIn('chosenSide === "left"', self.code)

    def test_hover_card_alignments(self) -> None:
        """Verify alignment cross-axis calculations."""
        self.assertIn('align === "start"', self.code)
        self.assertIn('align === "end"', self.code)
        self.assertIn("(triggerRect.width - contentRect.width) / 2", self.code)

    def test_hover_card_supports_variants(self) -> None:
        """Verify 4 futuristic visual variants."""
        self.assertIn("neon: {", self.code)
        self.assertIn("glass: {", self.code)
        self.assertIn("bordered: {", self.code)
        self.assertIn("minimal: {", self.code)
        self.assertIn("backdropFilter", self.code)

    def test_hover_card_supports_sizes(self) -> None:
        """Verify 3 size presets."""
        self.assertIn("sm: { width: \"100%\", maxWidth: 260", self.code)
        self.assertIn("md: { width: \"100%\", maxWidth: 320", self.code)
        self.assertIn("lg: { width: \"100%\", maxWidth: 400", self.code)

    def test_hover_card_diff_invariant(self) -> None:
        """HoverCard output is 100% diff-invariant across ir.description changes."""
        adapter = NextjsWebAdapter()
        project1 = adapter.generate(self.ir)
        ir2 = dataclasses.replace(
            self.ir, description="Completely changed description for diff test."
        )
        project2 = adapter.generate(ir2)
        hc1 = project1.get("components/hover-card.tsx").content
        hc2 = project2.get("components/hover-card.tsx").content
        self.assertEqual(
            hc1,
            hc2,
            "components/hover-card.tsx must be 100% diff-invariant across ir.description",
        )
        self.assertEqual(hc1, self.code)

    def test_adapter_emits_hover_card_file(self) -> None:
        """NextjsWebAdapter emits components/hover-card.tsx in generated project."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/hover-card.tsx")
        self.assertIsNotNone(f, "components/hover-card.tsx must be generated")
        self.assertEqual(f.content, self.code)

    def test_package_codegen_exports_render_hover_card_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_hover_card_component."""
        self.assertTrue(callable(cg.render_hover_card_component))
        self.assertEqual(cg.render_hover_card_component(), self.code)


if __name__ == "__main__":
    unittest.main()
