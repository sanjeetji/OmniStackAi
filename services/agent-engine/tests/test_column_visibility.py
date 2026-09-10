"""Tests for Task R-313: Generated Collection Table Column Visibility Dropdown / Selector Controls.

Verifies that NextjsWebAdapter emits interactive, accessible column visibility controls
(dropdown button, menu, checkbox selectors per display field, state guards) in generated
collection screens.
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
    render_screen_page,
)


class ColumnVisibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.screen = next(s for s in self.ir.screens if s.id == "post_list")
        self.page = render_screen_page(self.screen, self.ir)

    def test_collection_screen_declares_visible_columns_state(self) -> None:
        """Page declares visibleColumns state initialized with all display fields set to true."""
        self.assertIn("const [visibleColumns, setVisibleColumns] = useState<Record<string, boolean>>({", self.page)
        self.assertIn('"title": true', self.page)
        self.assertIn('"body": true', self.page)
        self.assertIn('"published": true', self.page)

    def test_collection_screen_declares_show_column_picker_state(self) -> None:
        """Page declares showColumnPicker state initialized to false."""
        self.assertIn("const [showColumnPicker, setShowColumnPicker] = useState<boolean>(false);", self.page)

    def test_collection_screen_toggle_column_function_guards_minimum_one_column(self) -> None:
        """toggleColumn function prevents hiding the last remaining visible column."""
        self.assertIn("const toggleColumn = (colName: string) => {", self.page)
        self.assertIn("currentVisible.length <= 1", self.page)
        self.assertIn("[colName]: !prev[colName]", self.page)

    def test_collection_screen_renders_column_visibility_button(self) -> None:
        """Toolbar renders a Columns button with aria-haspopup and aria-expanded attributes."""
        self.assertIn('aria-haspopup="true"', self.page)
        self.assertIn("aria-expanded={showColumnPicker}", self.page)
        self.assertIn('aria-label="Toggle column visibility"', self.page)
        self.assertIn("Columns", self.page)

    def test_collection_screen_renders_column_picker_dropdown_menu(self) -> None:
        """Dropdown menu renders with role='menu' and aria-label='Column visibility options'."""
        self.assertIn("showColumnPicker && (", self.page)
        self.assertIn('role="menu"', self.page)
        self.assertIn('aria-label="Column visibility options"', self.page)

    def test_collection_screen_renders_checkbox_for_each_display_field(self) -> None:
        """Column picker renders an accessible checkbox input for each display field."""
        self.assertIn('aria-label="Toggle Title column"', self.page)
        self.assertIn('aria-label="Toggle Body column"', self.page)
        self.assertIn('aria-label="Toggle Published column"', self.page)
        self.assertIn('checked={visibleColumns["title"] !== false}', self.page)
        self.assertIn('onChange={() => toggleColumn("title")}', self.page)

    def test_collection_screen_table_headers_conditionally_rendered(self) -> None:
        """Table <th> headers are conditionally rendered based on visibleColumns state."""
        self.assertIn('visibleColumns["title"] !== false && (', self.page)
        self.assertIn('visibleColumns["body"] !== false && (', self.page)
        self.assertIn('visibleColumns["published"] !== false && (', self.page)

    def test_collection_screen_table_cells_conditionally_rendered(self) -> None:
        """Table <td> cells are conditionally rendered based on visibleColumns state."""
        self.assertIn('visibleColumns["title"] !== false && (', self.page)
        self.assertIn('visibleColumns["body"] !== false && (', self.page)
        self.assertIn('visibleColumns["published"] !== false && (', self.page)

    def test_collection_screen_preserves_actions_or_details_and_checkbox_columns(self) -> None:
        """Row selection checkbox and Details/Actions column are always rendered regardless of field columns."""
        self.assertIn('aria-label="Select all"', self.page)
        self.assertIn('>Details</th>', self.page)

    def test_adapter_generate_outputs_column_visibility_controls(self) -> None:
        """NextjsWebAdapter.generate outputs column visibility controls in collection screen."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        screen_file = project.get("app/post_list/page.tsx")
        self.assertIsNotNone(screen_file)
        self.assertIn('aria-label="Toggle column visibility"', screen_file.content)
        self.assertIn('role="menu"', screen_file.content)
        self.assertIn('aria-label="Column visibility options"', screen_file.content)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        """Code generation is 100% diff-invariant across changes to ir.description."""
        ir1 = example_ir("minimal-blog")
        ir2 = dataclasses.replace(ir1, description="A completely different description for R-313")

        s1 = next(s for s in ir1.screens if s.id == "post_list")
        s2 = next(s for s in ir2.screens if s.id == "post_list")
        p1 = render_screen_page(s1, ir1)
        p2 = render_screen_page(s2, ir2)
        self.assertEqual(p1, p2)


if __name__ == "__main__":
    unittest.main()
