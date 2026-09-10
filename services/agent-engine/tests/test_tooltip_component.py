"""Tests for Task R-314: Generated Accessible Reusable Tooltip Component.

Verifies that NextjsWebAdapter emits an accessible, reusable Tooltip component
(apps/web/components/tooltip.tsx) conforming to WAI-ARIA 1.2 Tooltip specifications.
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
from omnistackai_agent_engine.codegen import (
    render_tooltip_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
)


class TooltipComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.code = render_tooltip_component()

    def test_tooltip_component_is_client_component(self) -> None:
        """Tooltip component specifies 'use client' directive."""
        self.assertTrue(self.code.startswith('"use client";'))

    def test_tooltip_component_exports_types_and_component(self) -> None:
        """Tooltip component exports TooltipPosition, TooltipProps, and Tooltip function."""
        self.assertIn('export type TooltipPosition = "top" | "bottom" | "left" | "right";', self.code)
        self.assertIn("export interface TooltipProps {", self.code)
        self.assertIn("content: React.ReactNode;", self.code)
        self.assertIn("position?: TooltipPosition;", self.code)
        self.assertIn("delayMs?: number;", self.code)
        self.assertIn("export function Tooltip(", self.code)
        self.assertIn("export default Tooltip;", self.code)

    def test_tooltip_component_uses_wai_aria_tooltip_semantics(self) -> None:
        """Tooltip element emits role='tooltip' and dynamic id."""
        self.assertIn('role="tooltip"', self.code)
        self.assertIn("id={tooltipId}", self.code)
        self.assertIn("aria-describedby", self.code)

    def test_tooltip_component_handles_hover_and_focus_triggers(self) -> None:
        """Container listens to mouseenter, mouseleave, focus, and blur events."""
        self.assertIn("onMouseEnter={show}", self.code)
        self.assertIn("onMouseLeave={hide}", self.code)
        self.assertIn("onFocus={show}", self.code)
        self.assertIn("onBlur={hide}", self.code)

    def test_tooltip_component_supports_escape_dismiss(self) -> None:
        """Tooltip listens for Escape keydown to dismiss when visible."""
        self.assertIn('e.key === "Escape"', self.code)
        self.assertIn("window.addEventListener", self.code)
        self.assertIn("window.removeEventListener", self.code)

    def test_tooltip_component_has_position_styles(self) -> None:
        """Tooltip computes position styles for top, bottom, left, right."""
        self.assertIn("positionStyles: Record<TooltipPosition, React.CSSProperties>", self.code)
        self.assertIn('bottom: "100%"', self.code)
        self.assertIn('top: "100%"', self.code)
        self.assertIn('right: "100%"', self.code)
        self.assertIn('left: "100%"', self.code)

    def test_adapter_generate_registers_tooltip_component(self) -> None:
        """NextjsWebAdapter.generate outputs components/tooltip.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/tooltip.tsx")
        self.assertIsNotNone(f)
        self.assertEqual(f.content, self.code)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        """render_tooltip_component is 100% diff-invariant across changes to ir.description."""
        ir1 = example_ir("minimal-blog")
        ir2 = dataclasses.replace(ir1, description="Completely changed IR description for R-314")

        adapter = NextjsWebAdapter()
        p1 = adapter.generate(ir1).get("components/tooltip.tsx")
        p2 = adapter.generate(ir2).get("components/tooltip.tsx")

        self.assertIsNotNone(p1)
        self.assertIsNotNone(p2)
        self.assertEqual(p1.content, p2.content)


if __name__ == "__main__":
    unittest.main()
