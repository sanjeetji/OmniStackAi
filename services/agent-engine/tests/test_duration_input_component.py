"""Tests for the Accessible Futuristic Duration Input Suite (components/duration-input.tsx)."""

from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine import codegen as cg
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_duration_input_component,
)


class TestDurationInputComponent(unittest.TestCase):
    """Unit tests for the Accessible Futuristic Duration Input Suite (R-414)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_duration_input_component()

    def test_file_generated(self) -> None:
        project = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        self.assertIsNotNone(project.get("components/duration-input.tsx"))

    def test_diff_invariance_and_codegen_export(self) -> None:
        proj1 = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        proj2 = NextjsWebAdapter().generate(example_ir("rideshare-favourites"))
        f1 = proj1.get("components/duration-input.tsx")
        f2 = proj2.get("components/duration-input.tsx")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, render_duration_input_component())

    def test_use_client_directive(self) -> None:
        self.assertTrue(self.source.startswith("'use client';"))

    def test_zero_runtime_dependencies(self) -> None:
        for pkg in re.findall(r"from\s+['\"]([^'\"]+)['\"]", self.source):
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected import: {pkg}",
            )

    def test_ascii_only_source(self) -> None:
        non_ascii = [c for c in self.source if ord(c) > 126]
        self.assertEqual(non_ascii, [], f"non-ASCII chars present: {non_ascii[:8]}")

    def test_forward_ref_and_imperative_handle(self) -> None:
        self.assertIn("forwardRef<DurationInputHandle, DurationInputProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        for method in ("getValue:", "setValue:", "getFormatted:", "clear:", "focus:"):
            self.assertIn(method, self.source)

    def test_typescript_types_present(self) -> None:
        for decl in (
            "export type DurationInputVariant",
            "export type DurationInputSize",
            "export type DurationUnit",
            "export interface DurationInputHandle",
            "export interface DurationInputProps",
        ):
            self.assertIn(decl, self.source)

    def test_compound_and_alias_exports(self) -> None:
        for decl in (
            "export const DurationInput =",
            "export const DurationField =",
            "export const TimeSpanInput =",
            "export const IntervalInput =",
            "export default DurationInputComponent",
        ):
            self.assertIn(decl, self.source)

    def test_display_names_defined(self) -> None:
        for line in (
            "DurationInputComponent.displayName = 'DurationInput'",
            "DurationField.displayName = 'DurationField'",
            "TimeSpanInput.displayName = 'TimeSpanInput'",
            "IntervalInput.displayName = 'IntervalInput'",
        ):
            self.assertIn(line, self.source)

    def test_variants_present(self) -> None:
        self.assertIn("'default' | 'card' | 'glass' | 'neon'", self.source)
        for key in ("default: {", "card: {", "glass: {", "neon: {"):
            self.assertIn(key, self.source)

    def test_sizes_present(self) -> None:
        self.assertIn("'sm' | 'md' | 'lg'", self.source)
        for key in ("sm: {", "md: {", "lg: {"):
            self.assertIn(key, self.source)

    def test_units_present(self) -> None:
        self.assertIn("'days' | 'hours' | 'minutes' | 'seconds'", self.source)
        self.assertIn("UNIT_SECONDS", self.source)

    def test_conversion(self) -> None:
        for token in ("86400", "3600", "toSegments", "fromSegments"):
            self.assertIn(token, self.source)

    def test_formatting(self) -> None:
        self.assertIn("formatDuration", self.source)

    def test_min_max(self) -> None:
        for token in ("min", "max"):
            self.assertIn(token, self.source)

    def test_aria_and_inputmode(self) -> None:
        self.assertIn("aria-label", self.source)
        self.assertIn("inputMode", self.source)

    def test_callbacks_and_controlled(self) -> None:
        for token in ("onChange", "value", "defaultValue"):
            self.assertIn(token, self.source)

    def test_package_codegen_export(self) -> None:
        self.assertTrue(hasattr(cg, "render_duration_input_component"))
        self.assertTrue(callable(cg.render_duration_input_component))
        self.assertIn("render_duration_input_component", cg.__all__)


if __name__ == "__main__":
    unittest.main()
