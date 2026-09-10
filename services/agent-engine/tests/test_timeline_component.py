"""Tests for Task R-336: Generated Accessible Reusable Timeline / Activity Feed Component.

Verifies that NextjsWebAdapter emits an accessible, reusable Timeline component
(apps/web/components/timeline.tsx) supporting:
- TimelineVariant, TimelineItemStatus, TimelineItem, TimelineProps types
- Default, compact, and centered layout variants
- Built-in status icons: completed (check), error (x), warning (alert), active (dot), pending (clock)
- statusColor / statusBg helpers for all five statuses
- Vertical connector between items with green fill for completed steps
- role="list" on the root, role="listitem" on each item
- icon override slot and action slot
- timestamp rendered as <time> element
- 100% diff-invariance across ir.description changes
- Zero external dependencies
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_timeline_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TimelineComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.code = render_timeline_component()

    def test_timeline_is_client_component(self) -> None:
        """Timeline specifies 'use client' directive."""
        self.assertTrue(self.code.startswith('"use client";'))

    def test_timeline_exports_types(self) -> None:
        """Timeline exports all required types."""
        self.assertIn(
            'export type TimelineVariant = "default" | "compact" | "centered";',
            self.code,
        )
        self.assertIn("export type TimelineItemStatus =", self.code)
        self.assertIn('"pending"', self.code)
        self.assertIn('"active"', self.code)
        self.assertIn('"completed"', self.code)
        self.assertIn('"error"', self.code)
        self.assertIn('"warning"', self.code)
        self.assertIn("export interface TimelineItem {", self.code)
        self.assertIn("export interface TimelineProps {", self.code)

    def test_timeline_exports_main_function(self) -> None:
        """Timeline exports Timeline function and default export."""
        self.assertIn("export function Timeline(", self.code)
        self.assertIn("export default Timeline;", self.code)

    def test_timeline_wai_aria_list(self) -> None:
        """Timeline root uses role='list' and aria-label."""
        self.assertIn('role="list"', self.code)
        self.assertIn("aria-label={label}", self.code)

    def test_timeline_wai_aria_listitem(self) -> None:
        """Each timeline item uses role='listitem'."""
        self.assertIn('role="listitem"', self.code)

    def test_timeline_status_icons(self) -> None:
        """Timeline includes built-in SVG icons for all five statuses."""
        self.assertIn("CheckCircleIcon", self.code)
        self.assertIn("XCircleIcon", self.code)
        self.assertIn("AlertCircleIcon", self.code)
        self.assertIn("ActiveDotIcon", self.code)
        self.assertIn("ClockIcon", self.code)

    def test_timeline_status_icon_dispatch(self) -> None:
        """StatusIcon dispatches correctly to each icon type."""
        self.assertIn('case "completed":', self.code)
        self.assertIn('case "error":', self.code)
        self.assertIn('case "warning":', self.code)
        self.assertIn('case "active":', self.code)

    def test_timeline_status_color_helper(self) -> None:
        """statusColor returns correct CSS custom property for each status."""
        self.assertIn("function statusColor(status: TimelineItemStatus): string", self.code)
        self.assertIn("--color-success,", self.code)
        self.assertIn("--color-primary,", self.code)
        self.assertIn("--color-danger,", self.code)
        self.assertIn("--color-warning,", self.code)

    def test_timeline_status_bg_helper(self) -> None:
        """statusBg returns alpha-channel background for each status."""
        self.assertIn("function statusBg(status: TimelineItemStatus): string", self.code)
        self.assertIn("--color-success-alpha,", self.code)
        self.assertIn("--color-primary-alpha,", self.code)
        self.assertIn("--color-danger-alpha,", self.code)
        self.assertIn("--color-warning-alpha,", self.code)

    def test_timeline_vertical_connector(self) -> None:
        """Timeline renders a vertical connector between items."""
        self.assertIn("!isLast", self.code)
        self.assertIn("minHeight:", self.code)
        # Connector fills green for completed steps
        self.assertIn('status === "completed"', self.code)

    def test_timeline_compact_variant(self) -> None:
        """Compact variant reduces vertical spacing."""
        self.assertIn('variant === "compact"', self.code)
        self.assertIn("isCompact", self.code)
        self.assertIn("isCompact ? 8 : 20", self.code)  # paddingBottom difference

    def test_timeline_centered_variant(self) -> None:
        """Centered variant renders alternating left/right layout."""
        self.assertIn('variant === "centered"', self.code)
        self.assertIn("isCentered", self.code)
        self.assertIn("index % 2 === 1", self.code)
        self.assertIn("isRight", self.code)

    def test_timeline_timestamp_as_time_element(self) -> None:
        """Timestamp is rendered inside a <time> element."""
        self.assertIn("<time", self.code)
        self.assertIn("{item.timestamp}", self.code)

    def test_timeline_action_slot(self) -> None:
        """Timeline item exposes an action slot."""
        self.assertIn("item.action", self.code)

    def test_timeline_icon_override_slot(self) -> None:
        """Timeline item accepts a custom icon override."""
        self.assertIn("item.icon !== undefined", self.code)

    def test_timeline_emitted_in_generated_app(self) -> None:
        """NextjsWebAdapter includes components/timeline.tsx in generated files."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/timeline.tsx")
        self.assertIsNotNone(f)

    def test_timeline_content_matches_template(self) -> None:
        """Generated timeline.tsx content matches render_timeline_component()."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/timeline.tsx")
        self.assertIsNotNone(f)
        self.assertEqual(f.content, render_timeline_component())

    def test_timeline_diff_invariant(self) -> None:
        """Timeline output is identical regardless of ir.description."""
        ir_b = dataclasses.replace(self.ir, description="Completely different description")
        adapter = NextjsWebAdapter()
        f_a = adapter.generate(self.ir).get("components/timeline.tsx")
        f_b = adapter.generate(ir_b).get("components/timeline.tsx")
        self.assertIsNotNone(f_a)
        self.assertIsNotNone(f_b)
        self.assertEqual(f_a.content, f_b.content)

    def test_timeline_zero_external_dependencies(self) -> None:
        """Timeline uses only React; no external package imports."""
        import re
        modules = re.findall(r'from\s+"([^"]+)"', self.code)
        for mod in modules:
            self.assertEqual(mod, "react", f"Unexpected external import: {mod}")

    def test_package_codegen_exports_render_timeline_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_timeline_component."""
        self.assertTrue(callable(cg.render_timeline_component))
        self.assertIn("render_timeline_component", cg.__all__)
        self.assertEqual(cg.render_timeline_component(), self.code)


if __name__ == "__main__":
    unittest.main()
