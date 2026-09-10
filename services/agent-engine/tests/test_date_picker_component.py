"""Tests for Task R-328: Generated Accessible Reusable Date Picker Component.

Verifies that NextjsWebAdapter emits an accessible, reusable Date Picker & Calendar component
(apps/web/components/date-picker.tsx) supporting WAI-ARIA grid and dialog semantics, keyboard
navigation, month/year navigation, date formatting, and trigger popover integration.
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import (
    render_date_picker_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
)


class DatePickerComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.code = render_date_picker_component()

    def test_date_picker_component_is_client_component(self) -> None:
        """Date picker component specifies 'use client' directive."""
        self.assertTrue(self.code.startswith('"use client";'))

    def test_date_picker_component_exports_types_and_components(self) -> None:
        """Date picker component exports types, interfaces, Calendar, and DatePicker."""
        self.assertIn("export type DateFormatter", self.code)
        self.assertIn("export interface CalendarProps", self.code)
        self.assertIn("export interface DatePickerProps", self.code)
        self.assertIn("export function Calendar(", self.code)
        self.assertIn("export const DatePicker =", self.code)
        self.assertIn("export function formatDate(", self.code)
        self.assertIn("export function isSameDay(", self.code)
        self.assertIn("export function isToday(", self.code)
        self.assertIn("export default DatePicker;", self.code)

    def test_calendar_header_controls(self) -> None:
        """Calendar header includes prev/next month and year controls with accessible labels."""
        self.assertIn('aria-label="Previous month"', self.code)
        self.assertIn('aria-label="Next month"', self.code)
        self.assertIn('aria-label="Previous year"', self.code)
        self.assertIn('aria-label="Next year"', self.code)
        self.assertIn('aria-live="polite"', self.code)

    def test_calendar_weekday_headers(self) -> None:
        """Calendar renders weekday header row with abbr tags and full names."""
        self.assertIn("<abbr", self.code)
        self.assertIn('role="columnheader"', self.code)
        self.assertIn("Sunday", self.code)
        self.assertIn("Saturday", self.code)

    def test_calendar_grid_wai_aria_semantics(self) -> None:
        """Calendar grid implements WAI-ARIA grid, row, gridcell, aria-selected, and aria-current."""
        self.assertIn('role="grid"', self.code)
        self.assertIn('role="row"', self.code)
        self.assertIn('role="gridcell"', self.code)
        self.assertIn("aria-selected", self.code)
        self.assertIn('aria-current', self.code)
        self.assertIn("aria-disabled", self.code)

    def test_calendar_keyboard_navigation(self) -> None:
        """Calendar implements keyboard navigation for day and week traversal."""
        self.assertIn("ArrowLeft", self.code)
        self.assertIn("ArrowRight", self.code)
        self.assertIn("ArrowUp", self.code)
        self.assertIn("ArrowDown", self.code)
        self.assertIn("Home", self.code)
        self.assertIn("End", self.code)
        self.assertIn("PageUp", self.code)
        self.assertIn("PageDown", self.code)

    def test_calendar_today_and_clear_actions(self) -> None:
        """Calendar supports today quick selection and optional clear button."""
        self.assertIn("showTodayButton", self.code)
        self.assertIn("showClearButton", self.code)
        self.assertIn("Today", self.code)
        self.assertIn("Clear", self.code)

    def test_date_picker_trigger_wai_aria(self) -> None:
        """DatePicker trigger button has aria-haspopup='dialog', aria-expanded, and SVG icon."""
        self.assertIn('aria-haspopup="dialog"', self.code)
        self.assertIn("aria-expanded", self.code)
        self.assertIn("<svg", self.code)

    def test_date_picker_clearable_affordance(self) -> None:
        """DatePicker supports clearable button affordance with aria-label."""
        self.assertIn("clearable", self.code)
        self.assertIn('aria-label="Clear date"', self.code)

    def test_date_picker_popover_dialog_and_dismiss(self) -> None:
        """DatePicker popover implements role='dialog' and dismisses on Escape and outside click."""
        self.assertIn('role="dialog"', self.code)
        self.assertIn('aria-label="Choose date"', self.code)
        self.assertIn("handleClickOutside", self.code)
        self.assertIn("Escape", self.code)

    def test_codegen_module_exports_render_date_picker_component(self) -> None:
        """render_date_picker_component is exported from omnistackai_agent_engine.codegen."""
        self.assertTrue(hasattr(cg, "render_date_picker_component"))
        self.assertEqual(cg.render_date_picker_component(), self.code)

    def test_adapter_generate_registers_date_picker_component(self) -> None:
        """NextjsWebAdapter.generate outputs components/date-picker.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/date-picker.tsx")
        self.assertIsNotNone(f)
        self.assertEqual(f.content, self.code)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        """render_date_picker_component is 100% diff-invariant across changes to ir.description."""
        ir1 = example_ir("minimal-blog")
        ir2 = dataclasses.replace(ir1, description="Completely changed IR description for R-328")

        adapter = NextjsWebAdapter()
        p1 = adapter.generate(ir1).get("components/date-picker.tsx")
        p2 = adapter.generate(ir2).get("components/date-picker.tsx")

        self.assertIsNotNone(p1)
        self.assertIsNotNone(p2)
        self.assertEqual(p1.content, p2.content)


if __name__ == "__main__":
    unittest.main()
