"""Tests for Task R-363: Generated Accessible Futuristic Reusable Tour & Onboarding Spotlight Guide Suite.

Verifies that NextjsWebAdapter emits an accessible, desktop-and-mobile-grade, zero-dependency,
and futuristic Tour & Onboarding Spotlight Guide compound component suite (apps/web/components/tour.tsx) supporting:
- Compound subcomponents:
  - Tour (root provider & overlay orchestrator)
  - TourCard (positioned popover card)
  - TourHeader (title, step counter, skip/close button)
  - TourBody (description content slot)
  - TourFooter (progress dots, back/prev, next/finish buttons)
  - TourDots (interactive step progress indicator)
  - Spotlight, Walkthrough, OnboardingTour (semantic aliases)
- Dynamic element spotlight:
  - Bounding rectangle calculation with resize & scroll tracking
  - SVG mask cutout (<mask id="..."> with black hole overlay)
  - Neon variant glowing cyan stroke and drop shadow
  - Viewport boundary collision clamping
- Step navigation & flow:
  - nextStep, prevStep, goToStep, startTour, endTour, skipTour
  - Controlled and uncontrolled step and open state
  - Smooth scrollIntoView target scrolling
- WAI-ARIA 1.2 Dialog semantics:
  - role="dialog", aria-modal="true", aria-label="Tour Guide"
  - Interactive dot aria-label="Go to step N"
  - Close button aria-label="Close tour"
- Keyboard navigation:
  - ArrowRight to advance, ArrowLeft to go back, Escape to skip/dismiss
- 4 futuristic visual styling variants ("default", "card", "glass", "neon")
- 3 size scales ("sm", "md", "lg") with responsive widths and font metrics
- Built-in SVG vector icons (XIcon, ArrowLeftIcon, ArrowRightIcon, CheckIcon, HelpCircleIcon)
- React ref forwarding (forwardRef) and explicit displayName on all subcomponents
- 100% diff-invariance across ir.description changes
- Zero external runtime npm dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_tour_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TourComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the Tour component suite."""

    def setUp(self) -> None:
        self.code = render_tour_component()
        self.ir = example_ir("rideshare-favourites")

    # ------------------------------------------------------------------
    # Basic structure
    # ------------------------------------------------------------------

    def test_tour_is_client_component(self) -> None:
        """Tour must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "Tour must have 'use client' as the first statement.",
        )

    def test_tour_exports_types(self) -> None:
        """Verify export of TypeScript union types and interfaces."""
        self.assertIn("export type TourVariant", self.code)
        self.assertIn('"default"', self.code)
        self.assertIn('"card"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"neon"', self.code)

        self.assertIn("export type TourSize", self.code)
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)

        self.assertIn("export type TourPlacement", self.code)
        self.assertIn('"top"', self.code)
        self.assertIn('"bottom"', self.code)
        self.assertIn('"left"', self.code)
        self.assertIn('"right"', self.code)
        self.assertIn('"center"', self.code)

        self.assertIn("export interface TourStep", self.code)
        self.assertIn("export interface TourContextValue", self.code)
        self.assertIn("export interface TourProps", self.code)
        self.assertIn("export interface TourCardProps", self.code)
        self.assertIn("export interface TourHeaderProps", self.code)
        self.assertIn("export interface TourBodyProps", self.code)
        self.assertIn("export interface TourFooterProps", self.code)
        self.assertIn("export interface TourDotsProps", self.code)
        self.assertIn("export interface TourSpotlightProps", self.code)

    def test_tour_exports_components_and_display_name(self) -> None:
        """Verify all subcomponent exports, forwardRef, displayName, and default export."""
        self.assertIn("export const Tour = forwardRef", self.code)
        self.assertIn('Tour.displayName = "Tour";', self.code)

        self.assertIn("export const TourCard = forwardRef", self.code)
        self.assertIn('TourCard.displayName = "TourCard";', self.code)

        self.assertIn("export const TourHeader = forwardRef", self.code)
        self.assertIn('TourHeader.displayName = "TourHeader";', self.code)

        self.assertIn("export const TourBody = forwardRef", self.code)
        self.assertIn('TourBody.displayName = "TourBody";', self.code)

        self.assertIn("export const TourDots = forwardRef", self.code)
        self.assertIn('TourDots.displayName = "TourDots";', self.code)

        self.assertIn("export const TourFooter = forwardRef", self.code)
        self.assertIn('TourFooter.displayName = "TourFooter";', self.code)

        self.assertIn("export const Spotlight = Tour;", self.code)
        self.assertIn('Spotlight.displayName = "Spotlight";', self.code)

        self.assertIn("export const Walkthrough = Tour;", self.code)
        self.assertIn('Walkthrough.displayName = "Walkthrough";', self.code)

        self.assertIn("export const OnboardingTour = Tour;", self.code)
        self.assertIn('OnboardingTour.displayName = "OnboardingTour";', self.code)

        self.assertIn("export default Tour;", self.code)

    def test_tour_compound_attachments(self) -> None:
        """Verify compound subcomponent property attachments."""
        self.assertIn("(Tour as any).Card = TourCard;", self.code)
        self.assertIn("(Tour as any).Header = TourHeader;", self.code)
        self.assertIn("(Tour as any).Body = TourBody;", self.code)
        self.assertIn("(Tour as any).Footer = TourFooter;", self.code)
        self.assertIn("(Tour as any).Dots = TourDots;", self.code)

    # ------------------------------------------------------------------
    # Context & Hook
    # ------------------------------------------------------------------

    def test_tour_context_and_hook(self) -> None:
        """Verify TourContext and useTour custom hook."""
        self.assertIn("export const TourContext = createContext", self.code)
        self.assertIn("export function useTour(): TourContextValue", self.code)
        self.assertIn("useTour must be used within a <Tour /> component.", self.code)

    # ------------------------------------------------------------------
    # WAI-ARIA and Semantics
    # ------------------------------------------------------------------

    def test_tour_dialog_semantics(self) -> None:
        """Overlay container must declare dialog semantics."""
        self.assertIn('role="dialog"', self.code)
        self.assertIn('aria-modal="true"', self.code)
        self.assertIn('aria-label="Tour Guide"', self.code)

    def test_tour_interactive_button_aria(self) -> None:
        """Buttons must carry clear accessible labels."""
        self.assertIn('aria-label="Close tour"', self.code)
        self.assertIn("aria-label={`Go to step ${i + 1}`}", self.code)

    # ------------------------------------------------------------------
    # Keyboard Navigation
    # ------------------------------------------------------------------

    def test_tour_keyboard_navigation(self) -> None:
        """Tour must handle ArrowRight, ArrowLeft, and Escape keys."""
        self.assertIn('e.key === "Escape"', self.code)
        self.assertIn('e.key === "ArrowRight"', self.code)
        self.assertIn('e.key === "ArrowLeft"', self.code)
        self.assertIn("e.preventDefault()", self.code)

    # ------------------------------------------------------------------
    # Spotlight Mask & Calculations
    # ------------------------------------------------------------------

    def test_tour_spotlight_mask_and_cutout(self) -> None:
        """SVG mask cutout must create a transparent window over target element."""
        self.assertIn('data-tour="spotlight"', self.code)
        self.assertIn("<mask id={maskId}>", self.code)
        self.assertIn('fill="white"', self.code)
        self.assertIn('fill="black"', self.code)
        self.assertIn("mask={`url(#${maskId})`}", self.code)

    def test_tour_neon_spotlight_glow(self) -> None:
        """Neon variant must draw a cyan glowing outline around the spotlight."""
        self.assertIn('variant === "neon"', self.code)
        self.assertIn('stroke="#06b6d4"', self.code)
        self.assertIn("drop-shadow(0 0 8px rgba(6, 182, 212, 0.7))", self.code)

    def test_tour_card_clamping(self) -> None:
        """Popover card coordinates must be clamped within viewport bounds."""
        self.assertIn("Math.max(16, Math.min(window.innerWidth", self.code)
        self.assertIn("Math.max(16, Math.min(window.innerHeight", self.code)

    # ------------------------------------------------------------------
    # Visual Variants and Sizes
    # ------------------------------------------------------------------

    def test_tour_variant_styles(self) -> None:
        """Verify variant styles for card, glass, neon, and default."""
        self.assertIn("getTourCardStyles", self.code)
        self.assertIn('"#1e293b"', self.code)
        self.assertIn('"rgba(15, 23, 42, 0.85)"', self.code)
        self.assertIn('backdropFilter: "blur(16px)"', self.code)
        self.assertIn('"#030712"', self.code)
        self.assertIn("rgba(6, 182, 212, 0.6)", self.code)

    def test_tour_size_presets(self) -> None:
        """Verify dimension definitions for sm, md, and lg sizes."""
        self.assertIn("TOUR_SIZES", self.code)
        self.assertIn("width: 280", self.code)
        self.assertIn("width: 340", self.code)
        self.assertIn("width: 400", self.code)

    # ------------------------------------------------------------------
    # Subcomponent Data Attributes
    # ------------------------------------------------------------------

    def test_tour_data_attributes(self) -> None:
        """Verify data-* attributes for subcomponents."""
        self.assertIn('data-tour="overlay"', self.code)
        self.assertIn('data-tour="card"', self.code)
        self.assertIn('data-tour="header"', self.code)
        self.assertIn('data-tour="title"', self.code)
        self.assertIn('data-tour="counter"', self.code)
        self.assertIn('data-tour="close-button"', self.code)
        self.assertIn('data-tour="body"', self.code)
        self.assertIn('data-tour="dots"', self.code)
        self.assertIn('data-tour="dot"', self.code)
        self.assertIn('data-tour="footer"', self.code)
        self.assertIn('data-tour="prev-button"', self.code)
        self.assertIn('data-tour="next-button"', self.code)

    # ------------------------------------------------------------------
    # Vector Icons
    # ------------------------------------------------------------------

    def test_tour_vector_icons(self) -> None:
        """Verify inline vector icons."""
        self.assertIn("function XIcon", self.code)
        self.assertIn("function ArrowLeftIcon", self.code)
        self.assertIn("function ArrowRightIcon", self.code)
        self.assertIn("function CheckIcon", self.code)
        self.assertIn("function HelpCircleIcon", self.code)

    # ------------------------------------------------------------------
    # Codegen & Adapter integration
    # ------------------------------------------------------------------

    def test_adapter_emits_tour_file(self) -> None:
        """NextjsWebAdapter emits components/tour.tsx in generated project."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/tour.tsx")
        self.assertIsNotNone(f, "components/tour.tsx must be emitted")
        self.assertEqual(f.content, self.code)

    def test_package_codegen_exports_render_tour_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_tour_component."""
        self.assertTrue(
            hasattr(cg, "render_tour_component"),
            "render_tour_component must be exported from codegen package",
        )
        self.assertIn("render_tour_component", cg.__all__)
        self.assertTrue(callable(cg.render_tour_component))
        self.assertEqual(cg.render_tour_component(), self.code)

    def test_tour_zero_external_dependencies(self) -> None:
        """Tour uses only React; zero external package imports."""
        modules = re.findall(r'from\s+"([^"]+)"', self.code)
        for mod in modules:
            self.assertEqual(mod, "react", f"Unexpected external import: {mod}")

    def test_tour_diff_invariant(self) -> None:
        """Tour output is 100% diff-invariant across ir.description changes."""
        modified_ir = dataclasses.replace(
            self.ir,
            description="Completely different prompt description for tour diff invariance test",
        )
        adapter = NextjsWebAdapter()
        f_a = adapter.generate(self.ir).get("components/tour.tsx")
        f_b = adapter.generate(modified_ir).get("components/tour.tsx")
        self.assertIsNotNone(f_a)
        self.assertIsNotNone(f_b)
        self.assertEqual(
            f_a.content,
            f_b.content,
            "components/tour.tsx must be 100% diff-invariant across ir.description changes",
        )


if __name__ == "__main__":
    unittest.main()
