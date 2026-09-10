"""Tests for Task R-329: Generated Accessible Reusable Data Grid / Table Component.

Verifies that NextjsWebAdapter emits an accessible, reusable Data Grid component
(apps/web/components/data-grid.tsx) supporting generic typed columns, sortable headers
with aria-sort, row selection checkboxes with select-all, display density presets,
sticky headers, striped rows, loading skeleton state, and diff invariance.
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import (
    render_data_grid_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
)


class DataGridComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.code = render_data_grid_component()

    def test_data_grid_component_is_client_component(self) -> None:
        """Data grid component specifies 'use client' directive."""
        self.assertTrue(self.code.startswith('"use client";'))

    def test_data_grid_component_exports_types_and_component(self) -> None:
        """Data grid component exports types, interfaces, and DataGrid function."""
        self.assertIn('export type SortDirection = "asc" | "desc" | null;', self.code)
        self.assertIn("export interface SortState", self.code)
        self.assertIn('export type DataGridDensity = "compact" | "comfortable" | "spacious";', self.code)
        self.assertIn("export interface ColumnDef", self.code)
        self.assertIn("export interface DataGridProps", self.code)
        self.assertIn("export function DataGrid", self.code)
        self.assertIn("export default DataGrid;", self.code)

    def test_data_grid_density_presets(self) -> None:
        """Data grid supports compact, comfortable, and spacious density presets."""
        self.assertIn("densityPaddingMap", self.code)
        self.assertIn("densityFontSizeMap", self.code)
        self.assertIn("compact:", self.code)
        self.assertIn("comfortable:", self.code)
        self.assertIn("spacious:", self.code)

    def test_data_grid_sortable_columns_and_aria_sort(self) -> None:
        """Data grid implements column sorting with aria-sort, toggle cycle, and SVG indicators."""
        self.assertIn("aria-sort", self.code)
        self.assertIn("ascending", self.code)
        self.assertIn("descending", self.code)
        self.assertIn("handleSortToggle", self.code)
        self.assertIn("<svg", self.code)

    def test_data_grid_row_selection_checkboxes(self) -> None:
        """Data grid implements select-all header checkbox, row checkboxes, and indeterminate state."""
        self.assertIn("selectable", self.code)
        self.assertIn('aria-label="Select all rows"', self.code)
        self.assertIn("headerCheckboxRef", self.code)
        self.assertIn("indeterminate", self.code)
        self.assertIn("onSelectionChange", self.code)

    def test_data_grid_row_aria_selected(self) -> None:
        """Data grid marks selected rows with aria-selected and background highlight."""
        self.assertIn("aria-selected", self.code)
        self.assertIn("currentSelection.includes", self.code)

    def test_data_grid_sticky_header(self) -> None:
        """Data grid supports stickyHeader with position sticky on thead."""
        self.assertIn("stickyHeader", self.code)
        self.assertIn("stickyHeader ? 10 : undefined", self.code)

    def test_data_grid_striped_and_hoverable(self) -> None:
        """Data grid supports striped alternating rows and hoverable row transitions."""
        self.assertIn("striped", self.code)
        self.assertIn("hoverable", self.code)
        self.assertIn("transition: \"background-color 0.15s ease\"", self.code)

    def test_data_grid_loading_skeleton_state(self) -> None:
        """Data grid supports loading skeleton state with role='status' and aria-busy."""
        self.assertIn("loading", self.code)
        self.assertIn("loadingRows", self.code)
        self.assertIn('aria-busy={loading}', self.code)
        self.assertIn('role="status"', self.code)
        self.assertIn("animation: \"pulse", self.code)

    def test_data_grid_empty_state(self) -> None:
        """Data grid renders emptyState fallback when no records are present."""
        self.assertIn("emptyState", self.code)
        self.assertIn("No records found", self.code)

    def test_codegen_module_exports_render_data_grid_component(self) -> None:
        """render_data_grid_component is exported from omnistackai_agent_engine.codegen."""
        self.assertTrue(hasattr(cg, "render_data_grid_component"))
        self.assertEqual(cg.render_data_grid_component(), self.code)

    def test_adapter_generate_registers_data_grid_component(self) -> None:
        """NextjsWebAdapter.generate outputs components/data-grid.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/data-grid.tsx")
        self.assertIsNotNone(f)
        self.assertEqual(f.content, self.code)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        """render_data_grid_component is 100% diff-invariant across changes to ir.description."""
        ir1 = example_ir("minimal-blog")
        ir2 = dataclasses.replace(ir1, description="Completely changed IR description for R-329")

        adapter = NextjsWebAdapter()
        p1 = adapter.generate(ir1).get("components/data-grid.tsx")
        p2 = adapter.generate(ir2).get("components/data-grid.tsx")

        self.assertIsNotNone(p1)
        self.assertIsNotNone(p2)
        self.assertEqual(p1.content, p2.content)


if __name__ == "__main__":
    unittest.main()
