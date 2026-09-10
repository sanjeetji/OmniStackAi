"""Tests for Task R-331: Generated Accessible Reusable Slider & Range Component.

Verifies that NextjsWebAdapter emits an accessible, reusable Slider & Range component
(apps/web/components/slider.tsx) supporting single-value and dual-thumb range modes,
pointer dragging (pointerdown/move/up), full keyboard navigation (Arrows, PageUp, PageDown,
Home, End), tick marks and labels, WAI-ARIA slider pattern semantics, and diff invariance.
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import (
    render_slider_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
)


class SliderComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.code = render_slider_component()

    def test_slider_component_is_client_component(self) -> None:
        """Slider component specifies 'use client' directive."""
        self.assertTrue(self.code.startswith('"use client";'))

    def test_slider_component_exports_types_and_component(self) -> None:
        """Slider component exports types, interfaces, and Slider function."""
        self.assertIn('export type SliderOrientation = "horizontal" | "vertical";', self.code)
        self.assertIn("export type SliderValue = number | [number, number];", self.code)
        self.assertIn("export interface SliderMark", self.code)
        self.assertIn("export interface SliderProps", self.code)
        self.assertIn("export function Slider", self.code)
        self.assertIn("export default Slider;", self.code)

    def test_slider_single_value_and_range_modes(self) -> None:
        """Slider supports both single-value number and dual-thumb range mode."""
        self.assertIn("isRange", self.code)
        self.assertIn("thumbsToRender", self.code)
        self.assertIn("thumbsToRender: (0 | 1)[] = isRange ? [0, 1] : [0];", self.code)

    def test_slider_pointer_drag_event_listeners(self) -> None:
        """Slider handles pointer interactions on track and thumbs with window drag listeners."""
        self.assertIn("onPointerDown={handlePointerDown}", self.code)
        self.assertIn('window.addEventListener("pointermove", handlePointerMove)', self.code)
        self.assertIn('window.addEventListener("pointerup", handlePointerUp)', self.code)
        self.assertIn('window.removeEventListener("pointermove", handlePointerMove)', self.code)
        self.assertIn('window.removeEventListener("pointerup", handlePointerUp)', self.code)

    def test_slider_keyboard_navigation_step_and_page_increments(self) -> None:
        """Slider thumbs handle arrow and page keys for step and large step increments."""
        self.assertIn('case "ArrowRight":', self.code)
        self.assertIn('case "ArrowUp":', self.code)
        self.assertIn('case "ArrowLeft":', self.code)
        self.assertIn('case "ArrowDown":', self.code)
        self.assertIn('case "PageUp":', self.code)
        self.assertIn('case "PageDown":', self.code)
        self.assertIn("Math.max(step * 10, (max - min) / 10)", self.code)

    def test_slider_keyboard_home_end_boundary_snapping(self) -> None:
        """Slider thumbs handle Home and End keys for boundary snapping."""
        self.assertIn('case "Home":', self.code)
        self.assertIn('case "End":', self.code)
        self.assertIn("thumbIdx === 0 ? min : values[0]", self.code)

    def test_slider_wai_aria_slider_semantics(self) -> None:
        """Slider thumbs implement WAI-ARIA slider pattern attributes."""
        self.assertIn('role="slider"', self.code)
        self.assertIn("tabIndex={disabled ? -1 : 0}", self.code)
        self.assertIn("aria-valuenow={val}", self.code)
        self.assertIn("aria-valuemin={isRange && tIdx === 1 ? values[0] : min}", self.code)
        self.assertIn("aria-valuemax={isRange && tIdx === 0 ? values[1] : max}", self.code)
        self.assertIn("aria-orientation={orientation}", self.code)
        self.assertIn("aria-disabled={disabled}", self.code)

    def test_slider_range_dual_thumbs_and_crossover_prevention(self) -> None:
        """Slider range mode clamps thumbs to prevent crossing over."""
        self.assertIn("Math.min(clickVal, isRange ? values[1] : max)", self.code)
        self.assertIn("Math.max(clickVal, values[0])", self.code)

    def test_slider_marks_and_tick_labels(self) -> None:
        """Slider supports rendering tick marks and labels along the track."""
        self.assertIn("resolvedMarks", self.code)
        self.assertIn("m.label", self.code)
        self.assertIn("getPercent(m.value)", self.code)

    def test_slider_value_display_badge_and_formatting(self) -> None:
        """Slider renders formatted value indicator when showValue is true."""
        self.assertIn("showValue", self.code)
        self.assertIn("formatValue", self.code)
        self.assertIn("formatValue(values[0])", self.code)

    def test_slider_exported_from_codegen_package(self) -> None:
        """render_slider_component is exposed at omnistackai_agent_engine.codegen top level."""
        self.assertTrue(callable(cg.render_slider_component))
        self.assertIn("render_slider_component", cg.__all__)
        self.assertEqual(cg.render_slider_component(), self.code)

    def test_slider_registered_in_nextjs_adapter(self) -> None:
        """NextjsWebAdapter registers components/slider.tsx in generated file set."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/slider.tsx")

        self.assertIsNotNone(f)
        self.assertEqual(f.content, self.code)

    def test_slider_is_diff_invariant_across_ir_descriptions(self) -> None:
        """Slider output remains byte-for-byte identical across differing IR descriptions."""
        ir2 = dataclasses.replace(
            self.ir,
            description="Completely different description to test diff invariance",
        )
        adapter = NextjsWebAdapter()
        p1 = adapter.generate(self.ir).get("components/slider.tsx")
        p2 = adapter.generate(ir2).get("components/slider.tsx")

        self.assertIsNotNone(p1)
        self.assertIsNotNone(p2)
        self.assertEqual(p1.content, p2.content)


if __name__ == "__main__":
    unittest.main()
