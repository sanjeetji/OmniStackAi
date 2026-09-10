"""Tests for Task R-337: Generated Accessible Futuristic Reusable Stat & Metric KPI Card Component.

Verifies that NextjsWebAdapter emits a futuristic, accessible, reusable StatCard component suite
(apps/web/components/stat-card.tsx) supporting:
- StatCardVariant ("default" | "glass" | "bordered" | "glow"), StatTrend ("positive" | "negative" | "neutral")
- Compound subcomponents: StatCard, StatCardHeader, StatCardValue, StatCardDelta, StatCardSparkline, StatCardFooter
- Pure mathematical SVG spline curve (cubic bezier C) sparkline mini-graph with linearGradient fill
- Trend indicator delta badge with directional SVG arrows and screen-reader accessible label
- Glassmorphic backdrop filter and ambient glow border styling
- WAI-ARIA role="region" / role="button", tabIndex, and keyboard Enter/Space activation
- 100% diff-invariance across ir.description changes
- Zero external runtime dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_stat_card_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class StatCardComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.code = render_stat_card_component()

    def test_stat_card_is_client_component(self) -> None:
        """StatCard specifies 'use client' directive."""
        self.assertTrue(self.code.startswith('"use client";'))

    def test_stat_card_exports_types(self) -> None:
        """StatCard exports all required type definitions."""
        self.assertIn(
            'export type StatCardVariant = "default" | "glass" | "bordered" | "glow";',
            self.code,
        )
        self.assertIn(
            'export type StatTrend = "positive" | "negative" | "neutral";',
            self.code,
        )
        self.assertIn("export interface StatCardProps {", self.code)
        self.assertIn("export interface StatCardHeaderProps {", self.code)
        self.assertIn("export interface StatCardValueProps {", self.code)
        self.assertIn("export interface StatCardDeltaProps {", self.code)
        self.assertIn("export interface StatCardSparklineProps {", self.code)
        self.assertIn("export interface StatCardFooterProps {", self.code)

    def test_stat_card_exports_compound_components(self) -> None:
        """StatCard exports all compound subcomponents and default export."""
        self.assertIn("export function StatCard(", self.code)
        self.assertIn("export function StatCardHeader(", self.code)
        self.assertIn("export function StatCardValue(", self.code)
        self.assertIn("export function StatCardDelta(", self.code)
        self.assertIn("export function StatCardSparkline(", self.code)
        self.assertIn("export function StatCardFooter(", self.code)
        self.assertIn("export default StatCard;", self.code)

    def test_stat_card_wai_aria_semantics(self) -> None:
        """StatCard sets role='region' or role='button' with aria-label."""
        self.assertIn('role={isInteractive ? "button" : "region"}', self.code)
        self.assertIn("aria-label={ariaLabel}", self.code)
        self.assertIn("tabIndex={isInteractive ? 0 : undefined}", self.code)

    def test_stat_card_interactive_keyboard_support(self) -> None:
        """StatCard supports Enter and Space keyboard activation when clickable."""
        self.assertIn('e.key === "Enter" || e.key === " "', self.code)
        self.assertIn("e.preventDefault()", self.code)
        self.assertIn("onClick?.(", self.code)

    def test_stat_card_delta_trend_icons_and_accessibility(self) -> None:
        """StatCardDelta includes directional vector arrows and role='status'."""
        self.assertIn("TrendingUpIcon", self.code)
        self.assertIn("TrendingDownIcon", self.code)
        self.assertIn("TrendingFlatIcon", self.code)
        self.assertIn('role="status"', self.code)
        self.assertIn('isPos ? "Increased"', self.code)
        self.assertIn('isNeg ? "Decreased"', self.code)

    def test_stat_card_sparkline_spline_math(self) -> None:
        """StatCardSparkline computes smooth cubic bezier spline curve."""
        self.assertIn("computeSplinePath", self.code)
        self.assertIn("linearGradient", self.code)
        self.assertIn("pathArea", self.code)
        self.assertIn("pathLine", self.code)

    def test_stat_card_sparkline_hover_dot(self) -> None:
        """StatCardSparkline tracks pointer move and renders active coordinate dot."""
        self.assertIn("onPointerMove={handlePointerMove}", self.code)
        self.assertIn("onPointerLeave={handlePointerLeave}", self.code)
        self.assertIn("activePt &&", self.code)

    def test_stat_card_variants(self) -> None:
        """StatCard implements glassmorphism, glow, and bordered variants."""
        self.assertIn('case "glass":', self.code)
        self.assertIn("backdropFilter:", self.code)
        self.assertIn('case "glow":', self.code)
        self.assertIn('case "bordered":', self.code)

    def test_stat_card_value_formatting_slots(self) -> None:
        """StatCardValue supports prefix, suffix, and subtext slots."""
        self.assertIn("prefix &&", self.code)
        self.assertIn("suffix &&", self.code)
        self.assertIn("subtext &&", self.code)

    def test_stat_card_emitted_in_generated_app(self) -> None:
        """NextjsWebAdapter includes components/stat-card.tsx in generated files."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/stat-card.tsx")
        self.assertIsNotNone(f)

    def test_stat_card_content_matches_template(self) -> None:
        """Generated stat-card.tsx content matches render_stat_card_component()."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/stat-card.tsx")
        self.assertIsNotNone(f)
        self.assertEqual(f.content, render_stat_card_component())

    def test_stat_card_diff_invariant(self) -> None:
        """StatCard output is 100% diff-invariant across ir.description changes."""
        ir_b = dataclasses.replace(self.ir, description="Completely different description")
        adapter = NextjsWebAdapter()
        f_a = adapter.generate(self.ir).get("components/stat-card.tsx")
        f_b = adapter.generate(ir_b).get("components/stat-card.tsx")
        self.assertIsNotNone(f_a)
        self.assertIsNotNone(f_b)
        self.assertEqual(f_a.content, f_b.content)

    def test_stat_card_zero_external_dependencies(self) -> None:
        """StatCard uses only React; no external package imports."""
        modules = re.findall(r'from\s+"([^"]+)"', self.code)
        for mod in modules:
            self.assertEqual(mod, "react", f"Unexpected external import: {mod}")

    def test_package_codegen_exports_render_stat_card_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_stat_card_component."""
        self.assertTrue(callable(cg.render_stat_card_component))
        self.assertIn("render_stat_card_component", cg.__all__)
        self.assertEqual(cg.render_stat_card_component(), self.code)


if __name__ == "__main__":
    unittest.main()
