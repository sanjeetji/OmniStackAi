"""Tests for Task R-343: Generated Accessible Futuristic Reusable Carousel & Slider Showcase Component.

Verifies that NextjsWebAdapter emits an accessible, futuristic, reusable Carousel compound component
suite (apps/web/components/carousel.tsx) supporting:
- Carousel compound component suite (Carousel, Carousel.Content, Carousel.Slide, Carousel.Previous,
  Carousel.Next, Carousel.Indicators, Carousel.Progress, Carousel.AutoplayToggle)
- 4 futuristic visual variants ("neon", "glass", "cards", "minimal")
- Transitions ("slide", "fade") and orientations ("horizontal", "vertical")
- Touch / swipe gesture handling (onTouchStart, onTouchEnd with delta threshold)
- Autoplay with configurable interval, pause on hover/focus, and accessible play/pause toggle
- Full keyboard navigation per WAI-ARIA Carousel Pattern (ArrowLeft/Right, ArrowUp/Down, Home, End)
- Full WAI-ARIA accessibility semantics (role="region", aria-roledescription="carousel",
  role="group", aria-roledescription="slide", aria-label, aria-hidden, aria-live)
- Indicator modes: dots, fraction, progress, none
- 100% diff-invariance across ir.description changes
- Zero external runtime dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_carousel_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class CarouselComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the Carousel component."""

    def setUp(self) -> None:
        self.code = render_carousel_component()
        self.ir = example_ir("rideshare-favourites")

    def test_carousel_component_is_client_component(self) -> None:
        """The Carousel component must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "Carousel must have 'use client' as the first statement.",
        )

    def test_carousel_component_exports_types(self) -> None:
        """Verify export of TypeScript interfaces and union types."""
        self.assertIn("export type CarouselVariant", self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"cards"', self.code)
        self.assertIn('"minimal"', self.code)
        self.assertIn("export type CarouselTransition", self.code)
        self.assertIn('"slide"', self.code)
        self.assertIn('"fade"', self.code)
        self.assertIn("export type CarouselOrientation", self.code)
        self.assertIn("export type CarouselIndicatorType", self.code)
        self.assertIn("export interface CarouselContextValue", self.code)
        self.assertIn("export interface CarouselProps", self.code)
        self.assertIn("export interface CarouselContentProps", self.code)
        self.assertIn("export interface CarouselSlideProps", self.code)
        self.assertIn("export interface CarouselPreviousProps", self.code)
        self.assertIn("export interface CarouselNextProps", self.code)
        self.assertIn("export interface CarouselIndicatorsProps", self.code)
        self.assertIn("export interface CarouselProgressProps", self.code)
        self.assertIn("export interface CarouselAutoplayToggleProps", self.code)

    def test_carousel_component_exports_compound(self) -> None:
        """Verify Carousel compound component and subcomponent attachments."""
        self.assertIn("export const Carousel =", self.code)
        self.assertIn("export const CarouselContent =", self.code)
        self.assertIn("export const CarouselSlide =", self.code)
        self.assertIn("export const CarouselPrevious =", self.code)
        self.assertIn("export const CarouselNext =", self.code)
        self.assertIn("export const CarouselIndicators =", self.code)
        self.assertIn("export const CarouselProgress =", self.code)
        self.assertIn("export const CarouselAutoplayToggle =", self.code)
        self.assertIn("(Carousel as any).Content = CarouselContent;", self.code)
        self.assertIn("(Carousel as any).Slide = CarouselSlide;", self.code)
        self.assertIn("(Carousel as any).Previous = CarouselPrevious;", self.code)
        self.assertIn("(Carousel as any).Next = CarouselNext;", self.code)
        self.assertIn("(Carousel as any).Indicators = CarouselIndicators;", self.code)
        self.assertIn("(Carousel as any).Progress = CarouselProgress;", self.code)
        self.assertIn("(Carousel as any).AutoplayToggle = CarouselAutoplayToggle;", self.code)
        self.assertIn("export default Carousel;", self.code)

    def test_carousel_zero_external_dependencies(self) -> None:
        """Carousel uses only React; zero external package imports."""
        import_lines = [
            line for line in self.code.splitlines() if line.startswith("import ")
        ]
        self.assertTrue(len(import_lines) >= 1)
        for line in import_lines:
            self.assertIn(
                'from "react"',
                line,
                f"Unexpected external import in Carousel component: {line}",
            )

    def test_carousel_wai_aria_carousel_semantics(self) -> None:
        """Verify WAI-ARIA carousel pattern roles and attributes."""
        self.assertIn('role="region"', self.code)
        self.assertIn('aria-roledescription="carousel"', self.code)
        self.assertIn('role="group"', self.code)
        self.assertIn('aria-roledescription="slide"', self.code)
        self.assertIn("aria-hidden={!isSelected}", self.code)
        self.assertIn('aria-live={isPlaying ? "off" : "polite"}', self.code)
        self.assertIn('aria-label="Previous slide"', self.code)
        self.assertIn('aria-label="Next slide"', self.code)

    def test_carousel_keyboard_navigation(self) -> None:
        """Verify Arrow and Home/End keyboard navigation support."""
        self.assertIn('"ArrowLeft"', self.code)
        self.assertIn('"ArrowRight"', self.code)
        self.assertIn('"ArrowUp"', self.code)
        self.assertIn('"ArrowDown"', self.code)
        self.assertIn('"Home"', self.code)
        self.assertIn('"End"', self.code)

    def test_carousel_touch_swipe_gesture_handling(self) -> None:
        """Verify touch start/end detection and delta calculation."""
        self.assertIn("onTouchStart={handleTouchStart}", self.code)
        self.assertIn("onTouchEnd={handleTouchEnd}", self.code)
        self.assertIn("e.changedTouches[0].clientX", self.code)
        self.assertIn("Math.abs(deltaX) > 40", self.code)

    def test_carousel_autoplay_and_pause_controls(self) -> None:
        """Verify autoplay interval timer, hover/focus pause, and toggle button."""
        self.assertIn("autoplayInterval", self.code)
        self.assertIn("pauseOnHover", self.code)
        self.assertIn("pauseOnFocus", self.code)
        self.assertIn("toggleAutoplay", self.code)
        self.assertIn("CarouselAutoplayToggle", self.code)
        self.assertIn("aria-pressed={isPlaying}", self.code)

    def test_carousel_indicators_and_progress(self) -> None:
        """Verify dot indicators, fraction count, and progress bar modes."""
        self.assertIn('role="tablist"', self.code)
        self.assertIn('role="tab"', self.code)
        self.assertIn('role="progressbar"', self.code)
        self.assertIn('omnistack-carousel-fraction', self.code)
        self.assertIn('selectedIndex + 1', self.code)

    def test_carousel_visual_variants_and_transitions(self) -> None:
        """Verify neon, glass, cards, and minimal styling presets and slide/fade transitions."""
        self.assertIn("ROOT_VARIANT_STYLES", self.code)
        self.assertIn("BUTTON_VARIANT_STYLES", self.code)
        self.assertIn("rgba(6, 182, 212", self.code)  # Neon cyan
        self.assertIn("backdropFilter", self.code)  # Glass
        self.assertIn("scale(0.92)", self.code)  # Cards 3D
        self.assertIn("translateX", self.code)  # Slide transition
        self.assertIn("opacity 0.4s", self.code)  # Fade transition

    def test_carousel_controlled_and_uncontrolled_modes(self) -> None:
        """Verify controlled selectedIndex and defaultIndex management."""
        self.assertIn("selectedIndex: controlledIndex", self.code)
        self.assertIn("defaultIndex", self.code)
        self.assertIn("isControlled ? controlledIndex : internalIndex", self.code)
        self.assertIn("onSelect", self.code)

    def test_carousel_exported_in_codegen_init(self) -> None:
        """Verify render_carousel_component is exported in omnistackai_agent_engine.codegen."""
        self.assertTrue(callable(getattr(cg, "render_carousel_component", None)))
        self.assertIn("render_carousel_component", cg.__all__)

    def test_carousel_emitted_by_adapter(self) -> None:
        """Verify NextjsWebAdapter emits components/carousel.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/carousel.tsx")
        self.assertIsNotNone(f, "components/carousel.tsx must be generated")
        self.assertEqual(f.content, self.code)

    def test_carousel_diff_invariance(self) -> None:
        """Verify 100% diff-invariance across ApplicationIR description changes."""
        mutated_ir = dataclasses.replace(
            self.ir,
            description="Completely mutated description with unpredictable tokens",
        )
        adapter = NextjsWebAdapter()
        f1 = adapter.generate(self.ir).get("components/carousel.tsx")
        f2 = adapter.generate(mutated_ir).get("components/carousel.tsx")

        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(self.code, f1.content)
        self.assertEqual(f1.content, f2.content)

    def test_carousel_loop_and_bounds_handling(self) -> None:
        """Verify loop mode modulo wrapping and non-loop bounded indexing."""
        self.assertIn("nextIndex % slidesCount + slidesCount) % slidesCount", self.code)
        self.assertIn("Math.max(0, Math.min(slidesCount - 1, nextIndex))", self.code)


if __name__ == "__main__":
    unittest.main()
