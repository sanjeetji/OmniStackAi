"""Tests for the Accessible Futuristic Marquee / Ticker Suite (components/marquee.tsx)."""

from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine import codegen as cg
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_marquee_component,
)


class TestMarqueeComponent(unittest.TestCase):
    """Unit tests for the Accessible Futuristic Marquee / Ticker Suite (R-406)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_marquee_component()

    def test_file_generated(self) -> None:
        project = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        self.assertIsNotNone(project.get("components/marquee.tsx"))

    def test_diff_invariance_and_codegen_export(self) -> None:
        proj1 = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        proj2 = NextjsWebAdapter().generate(example_ir("rideshare-favourites"))
        f1 = proj1.get("components/marquee.tsx")
        f2 = proj2.get("components/marquee.tsx")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, render_marquee_component())

    def test_use_client_directive(self) -> None:
        self.assertTrue(self.source.startswith("'use client';"))

    def test_zero_runtime_dependencies(self) -> None:
        for pkg in re.findall(r"from\s+['\"]([^'\"]+)['\"]", self.source):
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected import: {pkg}",
            )

    def test_forward_ref_and_imperative_handle(self) -> None:
        self.assertIn("forwardRef<MarqueeHandle, MarqueeProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        for method in ("pause:", "resume:", "toggle:", "isPaused:"):
            self.assertIn(method, self.source)

    def test_typescript_types_present(self) -> None:
        for decl in (
            "export type MarqueeVariant",
            "export type MarqueeSize",
            "export type MarqueeDirection",
            "export interface MarqueeHandle",
            "export interface MarqueeProps",
        ):
            self.assertIn(decl, self.source)

    def test_compound_and_alias_exports(self) -> None:
        for decl in (
            "export const Marquee =",
            "export const MarqueeTicker =",
            "export const ScrollingBanner =",
            "export const NewsTicker =",
            "export default MarqueeComponent",
        ):
            self.assertIn(decl, self.source)

    def test_display_names_defined(self) -> None:
        for line in (
            "MarqueeComponent.displayName = 'Marquee'",
            "MarqueeTicker.displayName = 'MarqueeTicker'",
            "ScrollingBanner.displayName = 'ScrollingBanner'",
            "NewsTicker.displayName = 'NewsTicker'",
        ):
            self.assertIn(line, self.source)

    def test_variants_present(self) -> None:
        self.assertIn("'default' | 'card' | 'glass' | 'neon'", self.source)
        for key in ("default: {", "card: {", "glass: {", "neon: {"):
            self.assertIn(key, self.source)

    def test_sizes_present(self) -> None:
        self.assertIn("'sm' | 'md' | 'lg'", self.source)
        for key in ("sm: {", "md: {", "lg: {"):
            self.assertIn(key, self.source)

    def test_directions_present(self) -> None:
        self.assertIn("'left' | 'right' | 'up' | 'down'", self.source)

    def test_keyframes_injection(self) -> None:
        self.assertIn("@keyframes omni-marquee-x", self.source)
        self.assertIn("@keyframes omni-marquee-y", self.source)
        self.assertIn("<style", self.source)

    def test_prefers_reduced_motion(self) -> None:
        self.assertIn("prefers-reduced-motion", self.source)

    def test_pause_on_hover_and_playstate(self) -> None:
        self.assertIn("pauseOnHover", self.source)
        self.assertIn("animationPlayState", self.source)
        self.assertIn("onMouseEnter", self.source)

    def test_seamless_duplicate(self) -> None:
        self.assertIn('aria-hidden="true"', self.source)

    def test_edge_mask(self) -> None:
        self.assertIn("maskImage", self.source)

    def test_controlled_pause_and_duration(self) -> None:
        self.assertIn("paused", self.source)
        self.assertIn("durationSeconds", self.source)

    def test_package_codegen_export(self) -> None:
        self.assertTrue(hasattr(cg, "render_marquee_component"))
        self.assertTrue(callable(cg.render_marquee_component))
        self.assertIn("render_marquee_component", cg.__all__)


if __name__ == "__main__":
    unittest.main()
