"""Tests for the Accessible Futuristic Reusable Heatmap & Activity Contribution Matrix Suite codegen (R-375).

Verifies:
1. Zero runtime dependencies (pure React).
2. "use client" directive present.
3. React forwardRef and explicit displayName across compound exports.
4. Exported canonical TypeScript types & interfaces.
5. Compound and semantic alias exports (Heatmap, ActivityCalendar, ContributionGraph, HeatmapLegend, HeatmapCell, default).
6. 4 visual styling variants ("default", "card", "glass", "neon").
7. 3 size presets ("sm", "md", "lg").
8. 5 color palettes ("emerald", "cyan", "violet", "amber", "rose").
9. Dual layout modes ("calendar" and "grid").
10. Dynamic quantile intensity bucketing (levels 0 to 4).
11. Interactive floating tooltip on hover/focus.
12. Cell selection and keyboard navigation (arrow keys, onCellClick).
13. WAI-ARIA grid accessibility semantics (role="grid", role="gridcell", aria-selected).
14. Integrated legend sub-component (HeatmapLegend).
15. Imperative handle methods (selectCell, clearSelection, getStats, scrollToLatest).
16. NextjsWebAdapter emits components/heatmap.tsx and codegen package exports render_heatmap_component.
17. 100% diff-invariance across ir.description changes.
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_heatmap_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TestHeatmapComponent(unittest.TestCase):
    """Test suite for components/heatmap.tsx codegen."""

    def setUp(self) -> None:
        self.code = render_heatmap_component()
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
        self.assertIn('Heatmap.displayName = "Heatmap"', self.code)
        self.assertIn('ActivityCalendar.displayName = "ActivityCalendar"', self.code)
        self.assertIn('ContributionGraph.displayName = "ContributionGraph"', self.code)
        self.assertIn('HeatmapLegend.displayName = "HeatmapLegend"', self.code)
        self.assertIn('HeatmapCell.displayName = "HeatmapCell"', self.code)

    def test_exported_canonical_types(self) -> None:
        """Canonical TypeScript types must be exported."""
        self.assertIn("export type HeatmapMode =", self.code)
        self.assertIn("export type HeatmapColor =", self.code)
        self.assertIn("export type HeatmapVariant =", self.code)
        self.assertIn("export type HeatmapSize =", self.code)
        self.assertIn("export type HeatmapIntensityLevel =", self.code)
        self.assertIn("export interface HeatmapDatum", self.code)
        self.assertIn("export interface HeatmapStats", self.code)
        self.assertIn("export interface HeatmapHandle", self.code)
        self.assertIn("export interface HeatmapProps", self.code)
        self.assertIn("export interface HeatmapLegendProps", self.code)
        self.assertIn("export interface HeatmapCellProps", self.code)

    def test_compound_and_semantic_exports(self) -> None:
        """Must export Heatmap, ActivityCalendar, ContributionGraph, HeatmapLegend, HeatmapCell, and default export."""
        self.assertIn("export const Heatmap =", self.code)
        self.assertIn("export const ActivityCalendar =", self.code)
        self.assertIn("export const ContributionGraph =", self.code)
        self.assertIn("export const HeatmapLegend =", self.code)
        self.assertIn("export const HeatmapCell =", self.code)
        self.assertIn("export default Heatmap;", self.code)

    def test_visual_variants(self) -> None:
        """Must support 4 visual styling variants."""
        for variant in ["default", "card", "glass", "neon"]:
            self.assertIn(f'"{variant}"', self.code)
        self.assertIn("backdrop-blur-md", self.code)
        self.assertIn("border-cyan-500", self.code)

    def test_size_presets(self) -> None:
        """Must define sm, md, lg size presets."""
        self.assertIn("sm:", self.code)
        self.assertIn("md:", self.code)
        self.assertIn("lg:", self.code)

    def test_color_palettes(self) -> None:
        """Must define 5 distinct color palettes."""
        for palette in ["emerald", "cyan", "violet", "amber", "rose"]:
            self.assertIn(f"{palette}:", self.code)

    def test_dual_layout_modes(self) -> None:
        """Must support both calendar and grid layout modes."""
        self.assertIn('"calendar"', self.code)
        self.assertIn('"grid"', self.code)
        self.assertIn('mode === "calendar"', self.code)
        self.assertIn("calendarWeeks", self.code)
        self.assertIn("gridMatrix", self.code)

    def test_quantile_intensity_bucketing(self) -> None:
        """Must compute intensity levels from 0 to 4 with custom and quantile fallback logic."""
        self.assertIn("calculateLevel", self.code)
        self.assertIn("thresholds", self.code)
        self.assertIn("ratio > 0.75", self.code)

    def test_interactive_tooltip(self) -> None:
        """Must provide floating tooltip on hover/focus with formatting support."""
        self.assertIn('role="tooltip"', self.code)
        self.assertIn("tooltipFormatter", self.code)
        self.assertIn("handleCellMouseEnter", self.code)
        self.assertIn("handleCellMouseLeave", self.code)

    def test_cell_selection_and_keyboard_navigation(self) -> None:
        """Must handle cell selection and keyboard navigation with arrow keys."""
        self.assertIn("handleCellClick", self.code)
        self.assertIn("onCellClick", self.code)
        self.assertIn("handleKeyDown", self.code)
        self.assertIn('"ArrowRight"', self.code)
        self.assertIn('"ArrowLeft"', self.code)

    def test_wai_aria_semantics(self) -> None:
        """Must contain WAI-ARIA grid and gridcell semantics for accessibility."""
        self.assertIn('role="grid"', self.code)
        self.assertIn('role="row"', self.code)
        self.assertIn('role="gridcell"', self.code)
        self.assertIn("aria-selected={isSelected}", self.code)

    def test_legend_subcomponent(self) -> None:
        """Must render HeatmapLegend with configurable labels and intensity markers."""
        self.assertIn("HeatmapLegend", self.code)
        self.assertIn("lessLabel", self.code)
        self.assertIn("moreLabel", self.code)

    def test_imperative_handle_methods(self) -> None:
        """Must expose imperative handle methods via useImperativeHandle."""
        self.assertIn("selectCell", self.code)
        self.assertIn("clearSelection", self.code)
        self.assertIn("getStats", self.code)
        self.assertIn("scrollToLatest", self.code)

    def test_nextjs_adapter_and_codegen_exports(self) -> None:
        """NextjsWebAdapter emits components/heatmap.tsx and codegen exposes render function."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        heatmap_file = project.get("components/heatmap.tsx")
        self.assertIsNotNone(heatmap_file, "components/heatmap.tsx must be generated")
        self.assertEqual(heatmap_file.content, self.code)

        self.assertIn("render_heatmap_component", cg.__all__)
        self.assertTrue(callable(cg.render_heatmap_component))
        self.assertEqual(cg.render_heatmap_component(), self.code)

    def test_diff_invariance(self) -> None:
        """Component code must be 100% diff-invariant across varying IR descriptions."""
        adapter = NextjsWebAdapter()
        ir1 = self.ir
        ir2 = dataclasses.replace(self.ir, description="Modified IR for heatmap invariance")

        file1 = adapter.generate(ir1).get("components/heatmap.tsx")
        file2 = adapter.generate(ir2).get("components/heatmap.tsx")

        self.assertIsNotNone(file1)
        self.assertIsNotNone(file2)
        self.assertEqual(file1.content, file2.content)


if __name__ == "__main__":
    unittest.main()
