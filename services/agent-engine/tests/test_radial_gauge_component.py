"""Tests for Task R-341: Generated Accessible Futuristic Reusable Radial Gauge & Activity Rings Component.

Verifies that NextjsWebAdapter emits an accessible, futuristic, reusable RadialGauge compound component
suite (apps/web/components/radial-gauge.tsx) supporting:
- Pure SVG arc trigonometry without external chart libraries (polarToCartesian, describeArc)
- Single radial gauge mode with angle sweeps (240°, 270°, 360°), threshold transitions, target markers
- Concentric multi-ring activity mode (RadialGauge.Rings / ActivityRings) with nested radii and legends
- 4 futuristic visual variants ("neon", "glass", "gradient", "minimal")
- Center readout slot with formatted values, units, labels, or custom content
- WAI-ARIA accessibility semantics (role="meter", aria-valuenow, aria-valuemin, aria-valuemax, aria-label)
- 100% diff-invariance across ir.description changes
- Zero external runtime dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_radial_gauge_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class RadialGaugeComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the RadialGauge component."""

    def setUp(self) -> None:
        self.code = render_radial_gauge_component()
        self.ir = example_ir("rideshare-favourites")

    def test_radial_gauge_component_is_client_component(self) -> None:
        """The RadialGauge component must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "RadialGauge must have 'use client' as the first statement.",
        )

    def test_radial_gauge_component_exports_types(self) -> None:
        """Verify export of TypeScript interfaces and union types."""
        self.assertIn("export type RadialGaugeVariant", self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"gradient"', self.code)
        self.assertIn('"minimal"', self.code)
        self.assertIn("export type RadialGaugeSize", self.code)
        self.assertIn("export interface RadialGaugeThreshold", self.code)
        self.assertIn("export interface ActivityRingItem", self.code)
        self.assertIn("export interface RadialGaugeProps", self.code)
        self.assertIn("export interface ActivityRingsProps", self.code)
        self.assertIn("export interface RadialGaugeValueProps", self.code)
        self.assertIn("export interface RadialGaugeLabelProps", self.code)

    def test_radial_gauge_component_exports_compound(self) -> None:
        """Verify RadialGauge compound component and default export."""
        self.assertIn("export const RadialGauge =", self.code)
        self.assertIn("RadialGauge.Rings = ActivityRings;", self.code)
        self.assertIn("RadialGauge.Value = RadialGaugeValue;", self.code)
        self.assertIn("RadialGauge.Label = RadialGaugeLabel;", self.code)
        self.assertIn("export default RadialGauge;", self.code)

    def test_radial_gauge_zero_external_dependencies(self) -> None:
        """RadialGauge uses only React; zero external package imports."""
        import_lines = [
            line for line in self.code.splitlines() if line.startswith("import ")
        ]
        self.assertTrue(len(import_lines) >= 1)
        for line in import_lines:
            self.assertIn(
                'from "react"',
                line,
                f"Unexpected external import in RadialGauge component: {line}",
            )

    def test_radial_gauge_diff_invariant(self) -> None:
        """RadialGauge output is 100% diff-invariant across ir.description changes."""
        mutated_ir = dataclasses.replace(
            self.ir,
            description="Completely mutated description with unpredictable tokens",
        )
        adapter = NextjsWebAdapter()
        f1 = adapter.generate(self.ir).get("components/radial-gauge.tsx")
        f2 = adapter.generate(mutated_ir).get("components/radial-gauge.tsx")

        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(self.code, f1.content)
        self.assertEqual(f1.content, f2.content)

    def test_adapter_emits_radial_gauge_file(self) -> None:
        """NextjsWebAdapter emits components/radial-gauge.tsx in generated project."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/radial-gauge.tsx")
        self.assertIsNotNone(f, "components/radial-gauge.tsx must be generated")
        self.assertEqual(f.content, self.code)

    def test_package_codegen_exports_render_radial_gauge_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_radial_gauge_component."""
        self.assertTrue(hasattr(cg, "render_radial_gauge_component"))
        self.assertIn("render_radial_gauge_component", cg.__all__)
        fn = getattr(cg, "render_radial_gauge_component")
        self.assertEqual(fn(), self.code)

    def test_radial_gauge_pure_svg_arc_trigonometry(self) -> None:
        """Verify trigonometric polar-to-cartesian and arc description math."""
        self.assertIn("export function polarToCartesian", self.code)
        self.assertIn("Math.cos(angleInRadians)", self.code)
        self.assertIn("Math.sin(angleInRadians)", self.code)
        self.assertIn("export function describeArc", self.code)
        self.assertIn("largeArcFlag", self.code)

    def test_radial_gauge_supports_variants(self) -> None:
        """Verify visual variant styling logic for neon, glass, gradient, and minimal."""
        self.assertIn('omnistack-gauge-${variant}', self.code)
        self.assertIn("gauge-neon-glow", self.code)
        self.assertIn("gauge-grad-accent", self.code)
        self.assertIn('variant === "glass"', self.code)
        self.assertIn("backdropFilter", self.code)

    def test_radial_gauge_supports_angle_sweeps(self) -> None:
        """Verify support for configurable angle sweeps."""
        self.assertIn("startAngle", self.code)
        self.assertIn("sweepAngle", self.code)
        self.assertIn("trackEndAngle", self.code)
        self.assertIn("valueEndAngle", self.code)

    def test_radial_gauge_supports_thresholds(self) -> None:
        """Verify threshold color evaluation logic."""
        self.assertIn("export function resolveThresholdColor", self.code)
        self.assertIn("thresholds", self.code)
        self.assertIn("activeColor", self.code)

    def test_radial_gauge_supports_target_marker(self) -> None:
        """Verify target goal tick marker rendering."""
        self.assertIn("targetValue", self.code)
        self.assertIn("targetCoord", self.code)
        self.assertIn("#fbbf24", self.code)  # Amber target line

    def test_radial_gauge_supports_endpoint_dot(self) -> None:
        """Verify glowing endpoint dot on active arc tip."""
        self.assertIn("showEndpointDot", self.code)
        self.assertIn("endpointCoord", self.code)
        self.assertIn("drop-shadow(0 0 4px currentColor)", self.code)

    def test_radial_gauge_supports_activity_rings(self) -> None:
        """Verify concentric multi-ring activity mode."""
        self.assertIn("export const ActivityRings", self.code)
        self.assertIn("rings", self.code)
        self.assertIn("ringGap", self.code)
        self.assertIn("maxRadius", self.code)
        self.assertIn("showLegend", self.code)
        self.assertIn("onRingHover", self.code)

    def test_radial_gauge_wai_aria_semantics(self) -> None:
        """Verify WAI-ARIA accessibility semantics for meter role."""
        self.assertIn('role="meter"', self.code)
        self.assertIn("aria-valuenow", self.code)
        self.assertIn("aria-valuemin", self.code)
        self.assertIn("aria-valuemax", self.code)
        self.assertIn("aria-valuetext", self.code)
        self.assertIn("aria-label", self.code)


if __name__ == "__main__":
    unittest.main()
