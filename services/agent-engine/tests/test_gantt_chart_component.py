"""Tests for the Accessible Futuristic Reusable Gantt Chart & Project Roadmap Suite codegen (R-379).

Verifies:
1. Zero runtime dependencies (pure React).
2. "use client" directive present.
3. React forwardRef and explicit displayName across compound exports.
4. Exported canonical TypeScript types & interfaces.
5. Compound and semantic alias exports (GanttChart, ProjectRoadmap, TimelineGantt, GanttTaskBar, GanttTimescale, GanttDependencyLine, default).
6. Timescale zoom view modes ("day", "week", "month").
7. 4 visual styling variants ("default", "card", "glass", "neon").
8. 3 size presets ("sm", "md", "lg").
9. Task progress bar calculation and fill rendering.
10. Milestone marker support (instant event diamond).
11. SVG dependency connector lines and bezier arrowheads.
12. Today vertical indicator line and badge.
13. Synchronized task list sidebar and timeline grid.
14. WAI-ARIA grid and accessibility semantics (role="grid", aria-label="Project Gantt Chart").
15. Imperative handle methods (scrollToToday, zoomIn, zoomOut, exportSvg, getTasks).
16. NextjsWebAdapter emits components/gantt-chart.tsx and codegen package exports render_gantt_chart_component.
17. 100% diff-invariance across ir.description changes.
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_gantt_chart_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TestGanttChartComponent(unittest.TestCase):
    """Test suite for components/gantt-chart.tsx codegen."""

    def setUp(self) -> None:
        self.code = render_gantt_chart_component()
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
        self.assertIn('GanttChart.displayName = "GanttChart"', self.code)
        self.assertIn('ProjectRoadmap.displayName = "ProjectRoadmap"', self.code)
        self.assertIn('TimelineGantt.displayName = "TimelineGantt"', self.code)
        self.assertIn('GanttTaskBar.displayName = "GanttTaskBar"', self.code)
        self.assertIn('GanttTimescale.displayName = "GanttTimescale"', self.code)
        self.assertIn('GanttDependencyLine.displayName = "GanttDependencyLine"', self.code)

    def test_exported_canonical_types(self) -> None:
        """Canonical TypeScript types and interfaces must be exported."""
        self.assertIn("export type GanttViewMode =", self.code)
        self.assertIn("export type GanttVariant =", self.code)
        self.assertIn("export type GanttSize =", self.code)
        self.assertIn("export interface GanttTask", self.code)
        self.assertIn("export interface GanttChartHandle", self.code)
        self.assertIn("export interface GanttChartProps", self.code)

    def test_compound_and_alias_exports(self) -> None:
        """Must export GanttChart, ProjectRoadmap, TimelineGantt, GanttTaskBar, GanttTimescale, GanttDependencyLine, and default."""
        self.assertIn("export const GanttChart =", self.code)
        self.assertIn("export const ProjectRoadmap =", self.code)
        self.assertIn("export const TimelineGantt =", self.code)
        self.assertIn("export const GanttTaskBar", self.code)
        self.assertIn("export const GanttTimescale", self.code)
        self.assertIn("export const GanttDependencyLine", self.code)
        self.assertIn("export default GanttChart;", self.code)

    def test_timescale_zoom_modes(self) -> None:
        """Must support day, week, and month timescale zoom levels."""
        for mode in ["day", "week", "month"]:
            self.assertIn(f'"{mode}"', self.code)

    def test_visual_variants(self) -> None:
        """Must support 4 visual styling variants."""
        for variant in ["default", "card", "glass", "neon"]:
            self.assertIn(f'"{variant}"', self.code)
        self.assertIn("backdropFilter", self.code)
        self.assertIn("rgba(6, 182, 212", self.code)

    def test_size_presets(self) -> None:
        """Must define sm, md, lg size presets."""
        self.assertIn("sm:", self.code)
        self.assertIn("md:", self.code)
        self.assertIn("lg:", self.code)

    def test_task_progress_bar(self) -> None:
        """Must compute and render progress fill width."""
        self.assertIn("progress", self.code)
        self.assertIn("width: `${progress}%`", self.code)

    def test_milestone_marker_rendering(self) -> None:
        """Must support milestone diamond indicators."""
        self.assertIn("isMilestone", self.code)
        self.assertIn('transform: "rotate(45deg)"', self.code)

    def test_dependency_connector_arrows(self) -> None:
        """Must render SVG cubic bezier curve and arrowhead polygon for dependencies."""
        self.assertIn("<svg", self.code)
        self.assertIn("GanttDependencyLine", self.code)
        self.assertIn("<path", self.code)
        self.assertIn("<polygon", self.code)

    def test_today_marker_line(self) -> None:
        """Must render vertical indicator line for current day."""
        self.assertIn("showTodayLine", self.code)
        self.assertIn("TODAY", self.code)

    def test_sidebar_and_timeline_sync(self) -> None:
        """Must render synchronized sidebar with task name and progress."""
        self.assertIn("showSidebar", self.code)
        self.assertIn("sidebarWidth", self.code)
        self.assertIn("Task Details", self.code)

    def test_wai_aria_semantics(self) -> None:
        """Must contain WAI-ARIA grid semantics and task labels."""
        self.assertIn('role="grid"', self.code)
        self.assertIn('aria-label="Project Gantt Chart"', self.code)

    def test_imperative_handle_methods(self) -> None:
        """Must expose imperative handle methods via useImperativeHandle."""
        self.assertIn("useImperativeHandle", self.code)
        self.assertIn("scrollToToday", self.code)
        self.assertIn("zoomIn", self.code)
        self.assertIn("zoomOut", self.code)
        self.assertIn("exportSvg:", self.code)
        self.assertIn("getTasks:", self.code)

    def test_nextjs_adapter_and_codegen_exports(self) -> None:
        """NextjsWebAdapter emits components/gantt-chart.tsx and codegen exposes render function."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        gantt_file = project.get("components/gantt-chart.tsx")
        self.assertIsNotNone(gantt_file, "components/gantt-chart.tsx must be generated")
        self.assertEqual(gantt_file.content, self.code)

        self.assertIn("render_gantt_chart_component", cg.__all__)
        self.assertTrue(callable(cg.render_gantt_chart_component))
        self.assertEqual(cg.render_gantt_chart_component(), self.code)

    def test_diff_invariance(self) -> None:
        """Component code must be 100% diff-invariant across varying IR descriptions."""
        adapter = NextjsWebAdapter()
        ir1 = self.ir
        ir2 = dataclasses.replace(self.ir, description="Modified IR for gantt chart invariance")

        file1 = adapter.generate(ir1).get("components/gantt-chart.tsx")
        file2 = adapter.generate(ir2).get("components/gantt-chart.tsx")

        self.assertIsNotNone(file1)
        self.assertIsNotNone(file2)
        self.assertEqual(file1.content, file2.content)


if __name__ == "__main__":
    unittest.main()
