"""Tests for Task R-332: Generated Accessible Reusable Progress & Spinner Component.

Verifies that NextjsWebAdapter emits an accessible, reusable Progress and Spinner component suite
(apps/web/components/progress.tsx) supporting linear ProgressBar (determinate/indeterminate, striped,
animated), CircularProgress (SVG stroke calculations, center value/label), and Spinner (role="status",
aria-live="polite", sr-only label), with WAI-ARIA compliance, semantic color variants, and diff invariance.
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import (
    render_progress_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
)


class ProgressComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.code = render_progress_component()

    def test_progress_component_is_client_component(self) -> None:
        """Progress component specifies 'use client' directive."""
        self.assertTrue(self.code.startswith('"use client";'))

    def test_progress_component_exports_types_and_components(self) -> None:
        """Progress component exports types, interfaces, ProgressBar, CircularProgress, and Spinner."""
        self.assertIn('export type ProgressVariant = "default" | "primary" | "success" | "warning" | "error" | "info";', self.code)
        self.assertIn('export type ProgressSize = "sm" | "md" | "lg";', self.code)
        self.assertIn("export interface ProgressBarProps", self.code)
        self.assertIn("export interface CircularProgressProps", self.code)
        self.assertIn("export interface SpinnerProps", self.code)
        self.assertIn("export function ProgressBar(", self.code)
        self.assertIn("export function CircularProgress(", self.code)
        self.assertIn("export function Spinner(", self.code)
        self.assertIn("export { ProgressBar as Progress };", self.code)
        self.assertIn("export default ProgressBar;", self.code)

    def test_progress_bar_determinate_mode_aria_attributes(self) -> None:
        """ProgressBar determinate mode binds WAI-ARIA progressbar attributes."""
        self.assertIn('role="progressbar"', self.code)
        self.assertIn("aria-valuenow={isIndeterminate ? undefined : clampedValue}", self.code)
        self.assertIn("aria-valuemin={min}", self.code)
        self.assertIn("aria-valuemax={max}", self.code)
        self.assertIn("aria-valuetext={isIndeterminate ? undefined : formattedValue}", self.code)

    def test_progress_bar_indeterminate_mode_omits_valuenow(self) -> None:
        """ProgressBar indeterminate mode sets undefined for aria-valuenow per WAI-ARIA spec."""
        self.assertIn("const isIndeterminate = value === undefined || value === null;", self.code)
        self.assertIn("isIndeterminate ? undefined : clampedValue", self.code)
        self.assertIn("omni-progress-indeterminate", self.code)

    def test_progress_bar_supports_labels_and_value_formatting(self) -> None:
        """ProgressBar renders optional label, showValue flag, and formatValue hook."""
        self.assertIn("formatValue?: (value: number, max: number) => string;", self.code)
        self.assertIn("formatValue(clampedValue!, max)", self.code)
        self.assertIn("aria-labelledby={ariaLabelledBy}", self.code)
        self.assertIn("showValue && !isIndeterminate", self.code)

    def test_progress_bar_striped_and_animated_classes(self) -> None:
        """ProgressBar supports striped gradient and animated progress stripes."""
        self.assertIn("striped = false", self.code)
        self.assertIn("animated = false", self.code)
        self.assertIn("linear-gradient(45deg,", self.code)
        self.assertIn("omni-progress-stripes", self.code)

    def test_progress_bar_sizes_and_semantic_variants(self) -> None:
        """ProgressBar maps size presets and semantic color variants."""
        self.assertIn("const VARIANT_COLORS: Record<ProgressVariant, string>", self.code)
        self.assertIn("const SIZE_HEIGHTS: Record<ProgressSize, number>", self.code)
        self.assertIn('default: "var(--primary, #2563eb)"', self.code)
        self.assertIn('success: "var(--success, #16a34a)"', self.code)
        self.assertIn('error: "var(--destructive, #dc2626)"', self.code)

    def test_circular_progress_svg_stroke_calculations(self) -> None:
        """CircularProgress renders SVG circles with mathematical circumference and offset."""
        self.assertIn("const radius = (dimension - strokeWidth) / 2;", self.code)
        self.assertIn("const circumference = 2 * Math.PI * radius;", self.code)
        self.assertIn("strokeDasharray={circumference}", self.code)
        self.assertIn("strokeDashoffset={offset}", self.code)

    def test_circular_progress_determinate_and_indeterminate_modes(self) -> None:
        """CircularProgress handles determinate -90deg rotation and indeterminate spinning sweep."""
        self.assertIn('"rotate(-90deg)"', self.code)
        self.assertIn('"omni-progress-spin 1.4s linear infinite"', self.code)

    def test_spinner_accessibility_live_region(self) -> None:
        """Spinner renders with role='status', aria-live='polite', and sr-only label text."""
        self.assertIn('role="status"', self.code)
        self.assertIn('aria-live="polite"', self.code)
        self.assertIn('label = "Loading..."', self.code)
        self.assertIn('clip: "rect(0, 0, 0, 0)"', self.code)

    def test_adapter_generates_components_progress_tsx(self) -> None:
        """NextjsWebAdapter outputs components/progress.tsx in the generated project."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        progress_file = project.get("components/progress.tsx")
        self.assertIsNotNone(progress_file)
        self.assertEqual(progress_file.content, self.code)

    def test_package_codegen_exports_render_progress_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_progress_component."""
        self.assertTrue(callable(cg.render_progress_component))
        self.assertIn("render_progress_component", cg.__all__)
        self.assertEqual(cg.render_progress_component(), self.code)

    def test_diff_invariance_across_ir_description(self) -> None:
        """render_progress_component is 100% diff-invariant across changes to ir.description."""
        modified_ir = dataclasses.replace(
            self.ir,
            description="Completely different description to test diff-invariance",
        )
        adapter = NextjsWebAdapter()
        original_file = adapter.generate(self.ir).get("components/progress.tsx")
        modified_file = adapter.generate(modified_ir).get("components/progress.tsx")

        self.assertIsNotNone(original_file)
        self.assertIsNotNone(modified_file)
        self.assertEqual(original_file.content, modified_file.content)
