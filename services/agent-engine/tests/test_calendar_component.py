"""Tests for the Calendar & Event Scheduler Suite codegen (R-366).

Verifies:
1. Zero runtime dependencies (pure React and built-in Date math).
2. "use client" directive present.
3. React forwardRef and explicit displayName.
4. Exported types (CalendarVariant, CalendarSize, CalendarViewMode, CalendarEvent, CalendarProps).
5. Semantic aliases (Scheduler, EventCalendar, default export).
6. 4 visual styling variants ("default", "card", "glass", "neon").
7. 3 size presets ("sm", "md", "lg").
8. WAI-ARIA 1.2 Grid pattern semantics (role="grid", role="row", role="columnheader",
   role="gridcell", aria-selected, aria-current="date").
9. Built-in zero-dependency vector icons (ChevronLeftIcon, ChevronRightIcon, CalendarIcon, ClockIcon).
10. Date math and matrix calculation functions.
11. Multi-view mode support (month and agenda views).
12. Event pills, category colors, and overflow badges.
13. Hidden input form integration when name prop is present.
14. NextjsWebAdapter emits components/calendar.tsx.
15. Codegen package export render_calendar_component in __all__.
16. 100% diff-invariance across ir.description changes.
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_calendar_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TestCalendarComponent(unittest.TestCase):
    """Test suite for components/calendar.tsx codegen."""

    def setUp(self) -> None:
        self.code = render_calendar_component()
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
        """Must use React.forwardRef and set explicit displayName."""
        self.assertIn("forwardRef", self.code)
        self.assertIn('Calendar.displayName = "Calendar"', self.code)
        self.assertIn('Scheduler.displayName = "Scheduler"', self.code)
        self.assertIn('EventCalendar.displayName = "EventCalendar"', self.code)

    def test_exported_types(self) -> None:
        """Must export canonical TypeScript types and interfaces."""
        self.assertIn("export type CalendarVariant =", self.code)
        self.assertIn("export type CalendarSize =", self.code)
        self.assertIn("export type CalendarViewMode =", self.code)
        self.assertIn("export interface CalendarEvent", self.code)
        self.assertIn("export interface CalendarProps", self.code)

    def test_semantic_aliases_and_default_export(self) -> None:
        """Must export Calendar, Scheduler, EventCalendar, and default export."""
        self.assertIn("export const Calendar =", self.code)
        self.assertIn("export const Scheduler = Calendar", self.code)
        self.assertIn("export const EventCalendar = Calendar", self.code)
        self.assertIn("export default Calendar", self.code)

    def test_four_visual_variants(self) -> None:
        """Must support 'default', 'card', 'glass', 'neon' visual variants."""
        for variant in ["default", "card", "glass", "neon"]:
            self.assertIn(f'"{variant}"', self.code)
        self.assertIn("backdropFilter", self.code)  # glass
        self.assertIn("boxShadow", self.code)  # card / neon glow
        self.assertTrue(
            "22d3ee" in self.code or "rgba(6, 182, 212" in self.code,
            "Must feature neon cyan accent styling",
        )

    def test_three_size_presets(self) -> None:
        """Must support 'sm', 'md', and 'lg' size scales."""
        for size in ["sm", "md", "lg"]:
            self.assertIn(f'"{size}"', self.code)
        self.assertIn("SIZE_CONFIGS", self.code)

    def test_wai_aria_grid_pattern(self) -> None:
        """Must implement WAI-ARIA 1.2 Grid pattern semantics."""
        self.assertIn('role="grid"', self.code)
        self.assertIn('role="row"', self.code)
        self.assertIn('role="columnheader"', self.code)
        self.assertIn('role="gridcell"', self.code)
        self.assertIn("aria-selected", self.code)
        self.assertIn("aria-current", self.code)
        self.assertIn('"date"', self.code)

    def test_builtin_vector_icons(self) -> None:
        """Must provide zero-dependency SVG navigation and indicator icons."""
        self.assertIn("ChevronLeftIcon", self.code)
        self.assertIn("ChevronRightIcon", self.code)
        self.assertIn("CalendarIcon", self.code)
        self.assertIn("ClockIcon", self.code)

    def test_date_math_helpers(self) -> None:
        """Must include pure zero-dependency calendar math functions."""
        self.assertIn("function getMonthMatrix", self.code)
        self.assertIn("function isSameDay", self.code)
        self.assertIn("function isToday", self.code)
        self.assertIn("function isSameMonth", self.code)
        self.assertIn("function getDaysInMonth", self.code)
        self.assertIn("function toISODateString", self.code)

    def test_multi_view_mode_and_agenda(self) -> None:
        """Must support month grid and agenda list views."""
        self.assertIn('"month"', self.code)
        self.assertIn('"agenda"', self.code)
        self.assertIn('aria-label="Agenda view"', self.code)
        self.assertIn("No events scheduled", self.code)

    def test_event_pills_and_overflow(self) -> None:
        """Must render event pills and +N more indicator."""
        self.assertIn("dayEvents", self.code)
        self.assertIn("maxEventsPerDay", self.code)
        self.assertIn("+{dayEvents.length - maxEventsPerDay} more", self.code)

    def test_form_integration_hidden_input(self) -> None:
        """Must render hidden input when name prop is supplied."""
        self.assertIn('type="hidden"', self.code)
        self.assertIn("name={name}", self.code)

    def test_adapter_emits_calendar_file(self) -> None:
        """NextjsWebAdapter must generate components/calendar.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/calendar.tsx")
        self.assertIsNotNone(f, "components/calendar.tsx must be emitted")
        self.assertEqual(f.content, self.code)

    def test_package_codegen_exports_render_calendar_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_calendar_component."""
        self.assertTrue(
            hasattr(cg, "render_calendar_component"),
            "render_calendar_component must be exported from codegen package",
        )
        self.assertIn("render_calendar_component", cg.__all__)
        self.assertTrue(callable(cg.render_calendar_component))
        self.assertEqual(cg.render_calendar_component(), self.code)

    def test_diff_invariance_across_description(self) -> None:
        """Component code must be 100% diff-invariant across ir.description changes."""
        modified_ir = dataclasses.replace(
            self.ir,
            description="Completely different prompt description for calendar diff invariance test",
        )
        adapter = NextjsWebAdapter()
        f_a = adapter.generate(self.ir).get("components/calendar.tsx")
        f_b = adapter.generate(modified_ir).get("components/calendar.tsx")
        self.assertIsNotNone(f_a)
        self.assertIsNotNone(f_b)
        self.assertEqual(f_a.content, f_b.content)


if __name__ == "__main__":
    unittest.main()
