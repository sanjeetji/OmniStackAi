"""
R-383: Accessible Futuristic Reusable Spreadsheet & Inline-Editable Data Sheet Suite
Unit tests for render_spreadsheet_component and the generated components/spreadsheet.tsx.
"""
from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_spreadsheet_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter, _SPREADSHEET_COMPONENT


class TestSpreadsheetComponent(unittest.TestCase):
    """Test suite for components/spreadsheet.tsx codegen (R-383)."""

    def setUp(self) -> None:
        self.code = render_spreadsheet_component()
        self.ir = example_ir("rideshare-favourites")
        project = NextjsWebAdapter().generate(self.ir)
        self.file = project.get("components/spreadsheet.tsx")

    # ------------------------------------------------------------------
    # 1. File is generated at the correct path
    # ------------------------------------------------------------------
    def test_file_generated(self):
        """components/spreadsheet.tsx must be emitted by NextjsWebAdapter."""
        ir = example_ir("minimal-blog")
        project = NextjsWebAdapter().generate(ir)
        paths = project.paths()
        self.assertIn("components/spreadsheet.tsx", paths)

    # ------------------------------------------------------------------
    # 2. Zero external npm dependencies (only 'react' imports allowed)
    # ------------------------------------------------------------------
    def test_zero_runtime_dependencies(self):
        """Only imports from 'react' are allowed — 0 external npm dependencies."""
        imports = re.findall(r'from\s+"([^"]+)"', self.code)
        for pkg in imports:
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Forbidden external import detected: {pkg}",
            )

    # ------------------------------------------------------------------
    # 3. TypeScript type interfaces present
    # ------------------------------------------------------------------
    def test_typescript_types_present(self):
        """All required TypeScript type exports must be present."""
        required_types = [
            "SpreadsheetVariant",
            "SpreadsheetSize",
            "CellType",
            "CellValue",
            "CellCoord",
            "CellRange",
            "ColumnDef",
            "RowData",
            "SpreadsheetHandle",
            "SpreadsheetProps",
            "SpreadsheetToolbarProps",
            "SpreadsheetCellProps",
        ]
        for t in required_types:
            self.assertIn(t, self.code, f"Missing TypeScript type: {t}")

    # ------------------------------------------------------------------
    # 4. All 4 variants present
    # ------------------------------------------------------------------
    def test_variants_present(self):
        """All four visual variants must be implemented: default, card, glass, neon."""
        for variant in ("default", "card", "glass", "neon"):
            self.assertIn(f'case "{variant}"', self.code, f"Missing variant: {variant}")

    # ------------------------------------------------------------------
    # 5. All 3 size scales present
    # ------------------------------------------------------------------
    def test_sizes_present(self):
        """All three size scales must be configured: sm, md, lg."""
        for size in ("sm", "md", "lg"):
            self.assertIn(f'"{size}"', self.code, f"Missing size: {size}")

    # ------------------------------------------------------------------
    # 6. Compound exports present
    # ------------------------------------------------------------------
    def test_compound_exports(self):
        """All compound and semantic alias exports must be present."""
        exports = [
            "export const Spreadsheet",
            "export const DataSheet",
            "export const InlineGrid",
            "export const SpreadsheetToolbar",
            "export const SpreadsheetCell",
        ]
        for exp in exports:
            self.assertIn(exp, self.code, f"Missing export: {exp}")

    # ------------------------------------------------------------------
    # 7. Default export present
    # ------------------------------------------------------------------
    def test_default_export(self):
        """A default export must be present."""
        self.assertIn("export default SpreadsheetComponent", self.code)

    # ------------------------------------------------------------------
    # 8. WAI-ARIA grid semantics present
    # ------------------------------------------------------------------
    def test_aria_grid_semantics(self):
        """WAI-ARIA 1.2 grid semantics must be present."""
        for attr in ('role="grid"', 'role="row"', 'role="columnheader"', 'role="gridcell"', 'aria-selected'):
            self.assertIn(attr, self.code, f"Missing ARIA attribute: {attr}")

    # ------------------------------------------------------------------
    # 9. forwardRef and useImperativeHandle present
    # ------------------------------------------------------------------
    def test_forward_ref_and_imperative_handle(self):
        """forwardRef and useImperativeHandle must be used for the imperative handle API."""
        self.assertIn("forwardRef", self.code)
        self.assertIn("useImperativeHandle", self.code)

    # ------------------------------------------------------------------
    # 10. Formula engine present
    # ------------------------------------------------------------------
    def test_formula_engine(self):
        """Formula engine must support =SUM, =AVG, =COUNT, =MIN, =MAX, =IF."""
        for symbol in ("=SUM", "=AVG", "=COUNT", "=MIN", "=MAX", "=IF", "evaluateFormula"):
            self.assertIn(symbol, self.code, f"Missing formula support: {symbol}")

    # ------------------------------------------------------------------
    # 11. Keyboard navigation present
    # ------------------------------------------------------------------
    def test_keyboard_navigation(self):
        """Arrow key navigation, Tab, Home, End, PageUp, PageDown must be implemented."""
        for key in ("ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight",
                    "Tab", "Home", "End", "PageUp", "PageDown"):
            self.assertIn(f'"{key}"', self.code, f"Missing keyboard key: {key}")

    # ------------------------------------------------------------------
    # 12. Multi-cell range selection present
    # ------------------------------------------------------------------
    def test_range_selection(self):
        """Multi-cell range selection with Shift+Click and Shift+Arrow must be implemented."""
        self.assertIn("CellRange", self.code)
        self.assertIn("isCellInRange", self.code)
        self.assertIn("e.shiftKey", self.code)
        self.assertIn("setRange", self.code)

    # ------------------------------------------------------------------
    # 13. Column freeze support present
    # ------------------------------------------------------------------
    def test_column_freeze(self):
        """Column freeze (sticky positioning) must be implemented."""
        self.assertIn("frozen", self.code)
        self.assertIn('"sticky"', self.code)

    # ------------------------------------------------------------------
    # 14. Undo/Redo history stack present
    # ------------------------------------------------------------------
    def test_undo_redo(self):
        """Undo/Redo history stack with Ctrl+Z/Ctrl+Y must be implemented."""
        self.assertIn("historyIdx", self.code)
        self.assertIn("pushHistory", self.code)
        self.assertIn('"z"', self.code)   # Ctrl+Z
        self.assertIn('"y"', self.code)   # Ctrl+Y

    # ------------------------------------------------------------------
    # 15. CSV export present
    # ------------------------------------------------------------------
    def test_csv_export(self):
        """CSV export (exportCsv) and import (csvToRows) must be implemented."""
        self.assertIn("exportCsv", self.code)
        self.assertIn("rowsToCsv", self.code)
        self.assertIn("csvToRows", self.code)

    # ------------------------------------------------------------------
    # 16. displayName on all compound exports
    # ------------------------------------------------------------------
    def test_display_names(self):
        """All compound exports must have explicit displayName properties."""
        display_names = [
            'SpreadsheetComponent.displayName = "Spreadsheet"',
            'SpreadsheetToolbarInner.displayName = "SpreadsheetToolbar"',
            'SpreadsheetCellInner.displayName = "SpreadsheetCell"',
            'DataSheet.displayName = "DataSheet"',
            'InlineGrid.displayName = "InlineGrid"',
        ]
        for dn in display_names:
            self.assertIn(dn, self.code, f"Missing displayName: {dn}")

    # ------------------------------------------------------------------
    # 17. Diff-invariant across ir.description
    # ------------------------------------------------------------------
    def test_diff_invariance_across_description(self):
        """Generated spreadsheet content must be identical regardless of ir.description."""
        ir_a = example_ir("rideshare-favourites")
        ir_b = example_ir("minimal-blog")
        project_a = NextjsWebAdapter().generate(ir_a)
        project_b = NextjsWebAdapter().generate(ir_b)
        content_a = project_a.get("components/spreadsheet.tsx")
        content_b = project_b.get("components/spreadsheet.tsx")
        self.assertIsNotNone(content_a)
        self.assertIsNotNone(content_b)
        self.assertEqual(
            content_a.content,
            content_b.content,
            "components/spreadsheet.tsx must be diff-invariant across ir.description changes",
        )


if __name__ == "__main__":
    unittest.main()
