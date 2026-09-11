"""Tests for the Accessible Futuristic Reusable Org Chart & Hierarchy Flow Diagram Suite codegen (R-374).

Verifies:
1. Zero runtime dependencies (pure React + SVG/CSS connectors).
2. "use client" directive present.
3. React forwardRef and explicit displayName across compound exports.
4. Exported canonical TypeScript types & interfaces.
5. Compound and semantic alias exports (OrgChart, HierarchyTree, OrgNode, default).
6. 4 visual styling variants ("default", "card", "glass", "neon").
7. 3 size presets ("sm", "md", "lg").
8. WAI-ARIA accessibility semantics (role="tree", role="treeitem", aria-expanded, aria-selected).
9. Vertical and horizontal layout orientation support.
10. Recursive tree rendering for parent-child hierarchies.
11. Connector stems and crossbars linking parent and child nodes.
12. Collapsible subtrees with toggle button on connector edge.
13. Direct and total report counts badge calculation.
14. Search filtering and ancestor automatic expansion.
15. Node selection and imperative handle methods (expandAll, collapseAll, selectNode).
16. NextjsWebAdapter emits components/org-chart.tsx and codegen package exports render_org_chart_component.
17. 100% diff-invariance across ir.description changes.
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_org_chart_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TestOrgChartComponent(unittest.TestCase):
    """Test suite for components/org-chart.tsx codegen."""

    def setUp(self) -> None:
        self.code = render_org_chart_component()
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
        self.assertIn('OrgChart.displayName = "OrgChart"', self.code)
        self.assertIn('HierarchyTree.displayName = "HierarchyTree"', self.code)
        self.assertIn('OrgNodeCard.displayName = "OrgNodeCard"', self.code)

    def test_exported_canonical_types(self) -> None:
        """Canonical TypeScript types must be exported."""
        self.assertIn("export type OrgChartOrientation =", self.code)
        self.assertIn("export type OrgChartVariant =", self.code)
        self.assertIn("export type OrgChartSize =", self.code)
        self.assertIn("export interface OrgChartNode", self.code)
        self.assertIn("export interface OrgChartHandle", self.code)
        self.assertIn("export interface OrgChartProps", self.code)
        self.assertIn("export interface OrgNodeCardProps", self.code)

    def test_compound_and_semantic_exports(self) -> None:
        """Must export OrgChart, HierarchyTree, OrgNode, and default export."""
        self.assertIn("export const OrgChart =", self.code)
        self.assertIn("export const HierarchyTree =", self.code)
        self.assertIn("export const OrgNode = OrgNodeCard;", self.code)
        self.assertIn("export default OrgChart;", self.code)

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

    def test_wai_aria_semantics(self) -> None:
        """Must contain WAI-ARIA tree and treeitem semantics for accessibility."""
        self.assertIn('role="tree"', self.code)
        self.assertIn('role="treeitem"', self.code)
        self.assertIn('aria-label="Organization Chart"', self.code)
        self.assertIn("aria-selected={isSelected}", self.code)
        self.assertIn("aria-expanded={hasChildren ? isExpanded : undefined}", self.code)

    def test_vertical_and_horizontal_orientations(self) -> None:
        """Must support vertical and horizontal layout orientations."""
        self.assertIn('"vertical"', self.code)
        self.assertIn('"horizontal"', self.code)
        self.assertIn('orientation === "vertical"', self.code)

    def test_recursive_tree_rendering(self) -> None:
        """Must recursively render child nodes via TreeNode."""
        self.assertIn("function TreeNode", self.code)
        self.assertIn("node.children", self.code)
        self.assertIn("<TreeNode", self.code)

    def test_connector_lines(self) -> None:
        """Must render connector stems and crossbars."""
        self.assertIn("connectorClass", self.code)
        self.assertIn("isFirst", self.code)
        self.assertIn("isLast", self.code)

    def test_collapsible_subtrees(self) -> None:
        """Must allow toggling subtree expansion state."""
        self.assertIn("expandedIds", self.code)
        self.assertIn("onToggleExpand", self.code)
        self.assertIn("ChevronDownIcon", self.code)

    def test_report_count_badges(self) -> None:
        """Must compute and render direct and total report count badges."""
        self.assertIn("countTotalReports", self.code)
        self.assertIn("totalReports", self.code)
        self.assertIn("showReportCount", self.code)

    def test_search_filtering_and_ancestor_expansion(self) -> None:
        """Must support search filtering and ancestor auto-expansion."""
        self.assertIn("searchQuery", self.code)
        self.assertIn("matchedIds", self.code)
        self.assertIn("findAncestors", self.code)
        self.assertIn("SearchIcon", self.code)

    def test_node_selection_and_imperative_handle(self) -> None:
        """Must support node selection and imperative handle methods."""
        self.assertIn("onNodeClick", self.code)
        self.assertIn("selectedId", self.code)
        self.assertIn("expandAll", self.code)
        self.assertIn("collapseAll", self.code)
        self.assertIn("selectNode", self.code)

    def test_nextjs_adapter_and_codegen_exports(self) -> None:
        """NextjsWebAdapter emits components/org-chart.tsx and codegen exposes render function."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        chart_file = project.get("components/org-chart.tsx")
        self.assertIsNotNone(chart_file, "components/org-chart.tsx must be generated")
        self.assertEqual(chart_file.content, self.code)

        self.assertIn("render_org_chart_component", cg.__all__)
        self.assertTrue(callable(cg.render_org_chart_component))
        self.assertEqual(cg.render_org_chart_component(), self.code)

    def test_diff_invariance(self) -> None:
        """Component code must be 100% diff-invariant across varying IR descriptions."""
        adapter = NextjsWebAdapter()
        ir1 = self.ir
        ir2 = dataclasses.replace(self.ir, description="Modified IR for org chart invariance")

        proj1 = adapter.generate(ir1)
        proj2 = adapter.generate(ir2)

        file1 = proj1.get("components/org-chart.tsx")
        file2 = proj2.get("components/org-chart.tsx")

        self.assertIsNotNone(file1)
        self.assertIsNotNone(file2)
        self.assertEqual(file1.content, file2.content)


if __name__ == "__main__":
    unittest.main()
