"""Tests for the Accessible Futuristic Data Visualization & SVG Chart Suite codegen (R-370).

Verifies:
1. Zero runtime dependencies (pure React).
2. "use client" directive present.
3. React forwardRef and explicit displayName across all compound exports.
4. Exported canonical TypeScript types & interfaces.
5. Semantic aliases (BarChart, LineChart, AreaChart, DonutChart, PieChart, Sparkline, default).
6. 4 visual styling variants ("default", "card", "glass", "neon").
7. 3 size presets ("sm", "md", "lg").
8. WAI-ARIA 1.2 accessibility semantics (role="img", role="region", sr-only data table).
9. Pure SVG rendering elements (<svg>, <rect>, <path>, <circle>, <linearGradient>).
10. Bar chart rendering with rounded corners and value labels.
11. Line and Area chart smooth bezier curve math and gradient fills.
12. Donut and Pie chart trigonometry and center readout.
13. Sparkline compact mode.
14. Interactive tooltip and series legend toggling.
15. NextjsWebAdapter emits components/chart.tsx.
16. Codegen package export render_chart_component in __all__.
17. 100% diff-invariance across ir.description changes.
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_chart_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TestChartComponent(unittest.TestCase):
    """Test suite for components/chart.tsx codegen."""

    def setUp(self) -> None:
        self.code = render_chart_component()
        self.ir = example_ir("rideshare-favourites")

    def test_zero_runtime_dependencies(self) -> None:
        """Only imports from 'react' are allowed — 0 external npm dependencies."""
        imports = re.findall(r'from\s+"([^"]+)"', self.code)
        for imp in imports:
            self.assertEqual(imp, "react", f"Forbidden external import: {imp}")

    def test_use_client_directive(self) -> None:
        """Must have 'use client' as first statement for Next.js App Router."""
        lines = [line.strip() for line in self.code.splitlines() if line.strip()]
        self.assertEqual(lines[0], '"use client";')

    def test_forward_ref_and_display_name(self) -> None:
        """Must use React.forwardRef and set explicit displayName across compound exports."""
        self.assertIn("forwardRef", self.code)
        self.assertIn('Chart.displayName = "Chart"', self.code)
        self.assertIn('BarChart.displayName = "BarChart"', self.code)
        self.assertIn('LineChart.displayName = "LineChart"', self.code)
        self.assertIn('AreaChart.displayName = "AreaChart"', self.code)
        self.assertIn('DonutChart.displayName = "DonutChart"', self.code)
        self.assertIn('PieChart.displayName = "PieChart"', self.code)
        self.assertIn('Sparkline.displayName = "Sparkline"', self.code)

    def test_exported_types(self) -> None:
        """Must export canonical TypeScript types and interfaces."""
        expected_types = [
            "ChartType",
            "ChartVariant",
            "ChartSize",
            "ChartCurve",
            "ChartDataPoint",
            "ChartSeries",
            "ChartTooltipData",
            "ChartProps",
        ]
        for t in expected_types:
            self.assertTrue(
                f"export type {t}" in self.code or f"export interface {t}" in self.code,
                f"Missing exported type/interface: {t}",
            )

    def test_semantic_aliases_and_default_export(self) -> None:
        """Must export Chart, BarChart, LineChart, AreaChart, DonutChart, PieChart, Sparkline, and default."""
        self.assertIn("export const Chart", self.code)
        self.assertIn("export const BarChart", self.code)
        self.assertIn("export const LineChart", self.code)
        self.assertIn("export const AreaChart", self.code)
        self.assertIn("export const DonutChart", self.code)
        self.assertIn("export const PieChart", self.code)
        self.assertIn("export const Sparkline", self.code)
        self.assertIn("export default Chart;", self.code)

    def test_four_visual_variants(self) -> None:
        """Must support 'default', 'card', 'glass', 'neon' visual variants."""
        self.assertIn('"default"', self.code)
        self.assertIn('"card"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"neon"', self.code)
        # Neon cyan accent and glass blur
        self.assertTrue(
            "#06b6d4" in self.code or "rgba(6, 182, 212" in self.code,
            "Missing neon cyan glow styling",
        )
        self.assertIn("backdropFilter", self.code)

    def test_three_size_presets(self) -> None:
        """Must support 'sm', 'md', and 'lg' size scales."""
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)
        self.assertIn("SIZE_CONFIG", self.code)

    def test_wai_aria_semantics_and_screen_reader_table(self) -> None:
        """Must implement WAI-ARIA 1.2 graphics semantics and accessible screen-reader table."""
        self.assertIn('role="region"', self.code)
        self.assertIn('role="img"', self.code)
        self.assertIn("aria-label", self.code)
        self.assertIn('className="sr-only"', self.code)
        self.assertIn("<table>", self.code)
        self.assertIn("<caption>", self.code)

    def test_pure_svg_rendering_elements(self) -> None:
        """Must use native SVG elements for pure mathematical rendering."""
        self.assertIn("<svg", self.code)
        self.assertIn("<rect", self.code)
        self.assertIn("<path", self.code)
        self.assertIn("<circle", self.code)
        self.assertIn("<linearGradient", self.code)

    def test_bar_chart_rendering(self) -> None:
        """Must render bars with rounded corners and value labels."""
        self.assertIn("renderBars", self.code)
        self.assertIn("chart-bars", self.code)
        self.assertIn("barWidth", self.code)

    def test_line_and_area_chart_bezier_curving(self) -> None:
        """Must compute smooth curve paths and area fills."""
        self.assertIn("renderLinesOrAreas", self.code)
        self.assertIn("generateSmoothPath", self.code)
        self.assertIn("areaPathD", self.code)

    def test_donut_and_pie_trigonometry(self) -> None:
        """Must implement polar-to-cartesian coordinate trigonometry and center cutout."""
        self.assertIn("polarToCartesian", self.code)
        self.assertIn("describeDonutSlice", self.code)
        self.assertIn("donutHoleRatio", self.code)
        self.assertIn("chart-center-readout", self.code)

    def test_sparkline_mode(self) -> None:
        """Must support ultra-compact sparkline rendering."""
        self.assertIn('"sparkline"', self.code)
        self.assertIn("sparklineHeight", self.code)

    def test_interactive_tooltip_and_legend_toggling(self) -> None:
        """Must include interactive tooltip positioning and click-to-toggle series logic."""
        self.assertIn("activeTooltip", self.code)
        self.assertIn("chart-tooltip", self.code)
        self.assertIn("hiddenSeries", self.code)
        self.assertIn("toggleSeries", self.code)

    def test_adapter_emits_chart_file(self) -> None:
        """NextjsWebAdapter must generate components/chart.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/chart.tsx")
        self.assertIsNotNone(f, "components/chart.tsx must be emitted")
        self.assertEqual(f.content, self.code)

    def test_package_codegen_exports_render_chart_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_chart_component."""
        self.assertIn("render_chart_component", cg.__all__)
        self.assertTrue(callable(cg.render_chart_component))
        self.assertEqual(cg.render_chart_component(), self.code)

    def test_diff_invariance_across_description(self) -> None:
        """Component code must be 100% diff-invariant across ir.description changes."""
        ir_mod = dataclasses.replace(self.ir, description="Completely changed description")
        adapter = NextjsWebAdapter()
        f1 = adapter.generate(self.ir).get("components/chart.tsx")
        f2 = adapter.generate(ir_mod).get("components/chart.tsx")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)


if __name__ == "__main__":
    unittest.main()
