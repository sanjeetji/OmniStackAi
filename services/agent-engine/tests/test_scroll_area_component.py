"""Tests for Task R-350: Generated Accessible Futuristic Reusable Scroll Area Suite.

Verifies that NextjsWebAdapter emits an accessible, desktop-grade, zero-dependency, and futuristic
Scroll Area / Custom Viewport compound component suite (apps/web/components/scroll-area.tsx) supporting:
- Compound suite (ScrollArea, ScrollArea.Viewport, ScrollArea.Scrollbar, ScrollArea.Thumb, ScrollArea.Corner, useScrollArea)
- Hidden native browser scrollbars with cross-browser styling (scrollbarWidth: none, msOverflowStyle: none)
- Proportional thumb sizing and dynamic offset calculations
- Interactive pointer drag tracking with setPointerCapture and releasePointerCapture
- Direct track-click smooth jump scrolling
- 4 visibility modes ("auto", "always", "scroll", "hover")
- WAI-ARIA 1.2 scrollbar semantics (role="scrollbar", aria-orientation, aria-valuenow, aria-valuemin, aria-valuemax)
- Keyboard viewport navigation (tabIndex={0}, ArrowDown/Up, PageDown/Up, Home/End)
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
from omnistackai_agent_engine.codegen import render_scroll_area_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class ScrollAreaComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the ScrollArea component suite."""

    def setUp(self) -> None:
        self.code = render_scroll_area_component()
        self.ir = example_ir("rideshare-favourites")

    def test_scroll_area_is_client_component(self) -> None:
        """ScrollArea must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "ScrollArea must have 'use client' as the first statement.",
        )

    def test_scroll_area_exports_types(self) -> None:
        """Verify export of TypeScript interfaces and union types."""
        self.assertIn("export type ScrollAreaType", self.code)
        self.assertIn('"auto"', self.code)
        self.assertIn('"always"', self.code)
        self.assertIn('"scroll"', self.code)
        self.assertIn('"hover"', self.code)
        self.assertIn("export type ScrollAreaOrientation", self.code)
        self.assertIn('"vertical"', self.code)
        self.assertIn('"horizontal"', self.code)
        self.assertIn('"both"', self.code)
        self.assertIn("export type ScrollAreaVariant", self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"bordered"', self.code)
        self.assertIn('"minimal"', self.code)
        self.assertIn("export type ScrollAreaSize", self.code)
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)
        self.assertIn("export interface ScrollAreaProps", self.code)
        self.assertIn("export interface ScrollAreaViewportProps", self.code)
        self.assertIn("export interface ScrollAreaScrollbarProps", self.code)
        self.assertIn("export interface ScrollAreaThumbProps", self.code)
        self.assertIn("export interface ScrollAreaCornerProps", self.code)
        self.assertIn("export interface ScrollAreaContextValue", self.code)

    def test_scroll_area_exports_compound_components(self) -> None:
        """Verify ScrollArea compound component and all subcomponents."""
        self.assertIn("export function ScrollArea(", self.code)
        self.assertIn("export function ScrollAreaViewport(", self.code)
        self.assertIn("export function ScrollAreaScrollbar(", self.code)
        self.assertIn("export function ScrollAreaThumb(", self.code)
        self.assertIn("export function ScrollAreaCorner(", self.code)
        self.assertIn("export function useScrollArea()", self.code)
        self.assertIn("ScrollArea.Viewport = ScrollAreaViewport;", self.code)
        self.assertIn("ScrollArea.Scrollbar = ScrollAreaScrollbar;", self.code)
        self.assertIn("ScrollArea.Thumb = ScrollAreaThumb;", self.code)
        self.assertIn("ScrollArea.Corner = ScrollAreaCorner;", self.code)
        self.assertIn("export default ScrollArea;", self.code)

    def test_scroll_area_zero_external_dependencies(self) -> None:
        """ScrollArea uses only React; zero external package imports."""
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
                f"Unexpected external import found in ScrollArea: {line}",
            )

    def test_scroll_area_wai_aria_scrollbar_semantics(self) -> None:
        """Verify WAI-ARIA scrollbar roles and accessibility attributes."""
        self.assertIn('role="scrollbar"', self.code)
        self.assertIn('aria-controls={viewportId}', self.code)
        self.assertIn('aria-orientation={orientation}', self.code)
        self.assertIn('aria-valuenow=', self.code)
        self.assertIn('aria-valuemin={0}', self.code)
        self.assertIn('aria-valuemax=', self.code)

    def test_scroll_area_viewport_keyboard_accessibility(self) -> None:
        """Verify viewport keyboard navigation and focusability."""
        self.assertIn("tabIndex={0}", self.code)
        self.assertIn('"ArrowDown"', self.code)
        self.assertIn('"ArrowUp"', self.code)
        self.assertIn('"PageDown"', self.code)
        self.assertIn('"PageUp"', self.code)
        self.assertIn('"Home"', self.code)
        self.assertIn('"End"', self.code)

    def test_scroll_area_hides_native_scrollbars(self) -> None:
        """Verify CSS properties that hide native scrollbars."""
        self.assertIn('scrollbarWidth: "none"', self.code)
        self.assertIn('msOverflowStyle: "none"', self.code)
        self.assertIn('WebkitOverflowScrolling: "touch"', self.code)

    def test_scroll_area_visibility_modes(self) -> None:
        """Verify 4 visibility types ("auto", "always", "scroll", "hover")."""
        self.assertIn('type === "always"', self.code)
        self.assertIn('type === "hover"', self.code)
        self.assertIn('type === "scroll"', self.code)
        self.assertIn("isHovered || isScrolling", self.code)

    def test_scroll_area_proportional_thumb_sizing(self) -> None:
        """Verify calculation of proportional thumb dimensions."""
        self.assertIn("Math.max(18, ratio * el.clientHeight)", self.code)
        self.assertIn("Math.max(18, ratio * el.clientWidth)", self.code)
        self.assertIn("thumbOffset", self.code)

    def test_scroll_area_pointer_drag_handlers(self) -> None:
        """Verify mouse and touch drag handling with pointer capture."""
        self.assertIn("setPointerCapture", self.code)
        self.assertIn("releasePointerCapture", self.code)
        self.assertIn("handlePointerDown", self.code)
        self.assertIn("handlePointerMove", self.code)
        self.assertIn("handlePointerUp", self.code)

    def test_scroll_area_track_jump_scrolling(self) -> None:
        """Verify direct clicking on the scrollbar track jumps or scrolls smoothly."""
        self.assertIn("handleTrackClick", self.code)
        self.assertIn('behavior: "smooth"', self.code)

    def test_scroll_area_supports_variants(self) -> None:
        """Verify 4 futuristic visual variants."""
        self.assertIn("neon: {", self.code)
        self.assertIn("glass: {", self.code)
        self.assertIn("bordered: {", self.code)
        self.assertIn("minimal: {", self.code)
        self.assertIn("backdropFilter", self.code)

    def test_scroll_area_supports_sizes(self) -> None:
        """Verify 3 size presets for track and thumb thickness."""
        self.assertIn("sm: 4", self.code)
        self.assertIn("md: 8", self.code)
        self.assertIn("lg: 12", self.code)

    def test_scroll_area_diff_invariant(self) -> None:
        """ScrollArea output is 100% diff-invariant across ir.description changes."""
        adapter = NextjsWebAdapter()
        project1 = adapter.generate(self.ir)
        ir2 = dataclasses.replace(
            self.ir, description="Completely changed description for diff test."
        )
        project2 = adapter.generate(ir2)
        sa1 = project1.get("components/scroll-area.tsx").content
        sa2 = project2.get("components/scroll-area.tsx").content
        self.assertEqual(
            sa1,
            sa2,
            "components/scroll-area.tsx must be 100% diff-invariant across ir.description",
        )
        self.assertEqual(sa1, self.code)

    def test_adapter_emits_scroll_area_file(self) -> None:
        """NextjsWebAdapter emits components/scroll-area.tsx in generated project."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/scroll-area.tsx")
        self.assertIsNotNone(f, "components/scroll-area.tsx must be generated")
        self.assertEqual(f.content, self.code)

    def test_package_codegen_exports_render_scroll_area_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_scroll_area_component."""
        self.assertTrue(callable(cg.render_scroll_area_component))
        self.assertEqual(cg.render_scroll_area_component(), self.code)


if __name__ == "__main__":
    unittest.main()
