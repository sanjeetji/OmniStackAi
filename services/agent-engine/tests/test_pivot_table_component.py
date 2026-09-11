"""Tests for the Accessible Futuristic Reusable Pivot Table Suite codegen (R-377).

Verifies:
1. Zero runtime dependencies (pure React).
2. "use client" directive present.
3. React forwardRef and explicit displayName across compound exports.
4. Exported canonical TypeScript types & interfaces.
5. Compound and semantic alias exports (PivotTable, CrossTab, MatrixTable, PivotCell, PivotHeader, default).
6. 4 visual styling variants ("default", "card", "glass", "neon").
7. 3 size presets ("sm", "md", "lg").
8. Aggregation operations (sum, avg, count, min, max).
9. Multi-dimensional row and column grouping logic.
10. Collapsible and expandable hierarchy levels.
11. Subtotals and grand totals calculation.
12. Built-in search filtering across dimensions.
13. Interactive sorting by dimension or metric values.
14. WAI-ARIA table/grid accessibility semantics (role="table", role="row", role="columnheader", role="rowheader", role="gridcell", aria-expanded).
15. Imperative handle methods (expandAllRows, collapseAllRows, exportCsv, getAggregatedData).
16. NextjsWebAdapter emits components/pivot-table.tsx and codegen package exports render_pivot_table_component.
17. 100% diff-invariance across ir.description changes.
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_pivot_table_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TestPivotTableComponent(unittest.TestCase):
    """Test suite for components/pivot-table.tsx codegen."""

    def setUp(self) -> None:
        self.code = render_pivot_table_component()
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
        self.assertIn('PivotTable.displayName = "PivotTable"', self.code)
        self.assertIn('CrossTab.displayName = "CrossTab"', self.code)
        self.assertIn('MatrixTable.displayName = "MatrixTable"', self.code)
        self.assertIn('PivotCell.displayName = "PivotCell"', self.code)
        self.assertIn('PivotHeader.displayName = "PivotHeader"', self.code)

    def test_exported_canonical_types(self) -> None:
        """Canonical TypeScript types must be exported."""
        self.assertIn("export type PivotAggregator =", self.code)
        self.assertIn("export type PivotVariant =", self.code)
        self.assertIn("export type PivotSize =", self.code)
        self.assertIn("export interface PivotValueField", self.code)
        self.assertIn("export interface PivotCellCoord", self.code)
        self.assertIn("export interface PivotTableHandle", self.code)
        self.assertIn("export interface PivotCellProps", self.code)
        self.assertIn("export interface PivotHeaderProps", self.code)
        self.assertIn("export interface PivotTableProps", self.code)

    def test_compound_and_semantic_exports(self) -> None:
        """Must export PivotTable, CrossTab, MatrixTable, PivotCell, PivotHeader, and default export."""
        self.assertIn("export const PivotTable =", self.code)
        self.assertIn("export const CrossTab =", self.code)
        self.assertIn("export const MatrixTable =", self.code)
        self.assertIn("export const PivotCell =", self.code)
        self.assertIn("export const PivotHeader =", self.code)
        self.assertIn("export default PivotTable;", self.code)

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

    def test_aggregation_functions(self) -> None:
        """Must support mathematical operations: sum, avg, count, min, max."""
        self.assertIn("computeAggregation", self.code)
        for agg in ["sum", "avg", "count", "min", "max"]:
            self.assertIn(f'"{agg}"', self.code)

    def test_multi_dimensional_grouping(self) -> None:
        """Must support hierarchical row and column dimension grouping."""
        self.assertIn("rowTree", self.code)
        self.assertIn("columnKeys", self.code)
        self.assertIn("matrix", self.code)

    def test_collapsible_row_hierarchy(self) -> None:
        """Must allow collapsing and expanding row groups with chevrons."""
        self.assertIn("collapsedRows", self.code)
        self.assertIn("toggleCollapse", self.code)
        self.assertIn("ChevronDownIcon", self.code)
        self.assertIn("ChevronRightIcon", self.code)

    def test_subtotals_and_grand_totals(self) -> None:
        """Must compute and render subtotals and grand totals."""
        self.assertIn("showSubtotals", self.code)
        self.assertIn("showGrandTotals", self.code)
        self.assertIn('"__GRAND_TOTAL__"', self.code)
        self.assertIn("Grand Total", self.code)

    def test_search_filtering(self) -> None:
        """Must support search filtering across dimensions."""
        self.assertIn("searchQuery", self.code)
        self.assertIn("filteredData", self.code)
        self.assertIn("SearchIcon", self.code)

    def test_interactive_sorting(self) -> None:
        """Must support sorting rows by column values."""
        self.assertIn("handleSort", self.code)
        self.assertIn("sortCol", self.code)
        self.assertIn("sortDir", self.code)
        self.assertIn("sortedFlatRows", self.code)

    def test_wai_aria_semantics(self) -> None:
        """Must contain WAI-ARIA table, row, and header semantics."""
        self.assertIn('role="table"', self.code)
        self.assertIn('role="row"', self.code)
        self.assertIn('role="columnheader"', self.code)
        self.assertIn('role="rowheader"', self.code)
        self.assertIn('role="gridcell"', self.code)
        self.assertIn("aria-expanded=", self.code)

    def test_imperative_handle_methods(self) -> None:
        """Must expose imperative handle methods via useImperativeHandle."""
        self.assertIn("useImperativeHandle", self.code)
        self.assertIn("expandAllRows:", self.code)
        self.assertIn("collapseAllRows:", self.code)
        self.assertIn("exportCsv:", self.code)
        self.assertIn("getAggregatedData:", self.code)

    def test_nextjs_adapter_and_codegen_exports(self) -> None:
        """NextjsWebAdapter emits components/pivot-table.tsx and codegen exposes render function."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        table_file = project.get("components/pivot-table.tsx")
        self.assertIsNotNone(table_file, "components/pivot-table.tsx must be generated")
        self.assertEqual(table_file.content, self.code)

        self.assertIn("render_pivot_table_component", cg.__all__)
        self.assertTrue(callable(cg.render_pivot_table_component))
        self.assertEqual(cg.render_pivot_table_component(), self.code)

    def test_diff_invariance(self) -> None:
        """Component code must be 100% diff-invariant across varying IR descriptions."""
        adapter = NextjsWebAdapter()
        ir1 = self.ir
        ir2 = dataclasses.replace(self.ir, description="Modified IR for pivot table invariance")

        file1 = adapter.generate(ir1).get("components/pivot-table.tsx")
        file2 = adapter.generate(ir2).get("components/pivot-table.tsx")

        self.assertIsNotNone(file1)
        self.assertIsNotNone(file2)
        self.assertEqual(file1.content, file2.content)


if __name__ == "__main__":
    unittest.main()
