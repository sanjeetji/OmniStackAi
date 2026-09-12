"""Tests for the Accessible Futuristic Countdown Timer, Stopwatch & Live Clock Suite (components/countdown.tsx)."""

from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine import codegen as cg
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_countdown_component,
)


class TestCountdownComponent(unittest.TestCase):
    """Unit tests for the Accessible Futuristic Countdown Timer, Stopwatch & Live Clock Suite (R-401)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_countdown_component()

    def test_file_generated(self) -> None:
        project = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        self.assertIsNotNone(project.get("components/countdown.tsx"))

    def test_diff_invariance_and_codegen_export(self) -> None:
        proj1 = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        proj2 = NextjsWebAdapter().generate(example_ir("rideshare-favourites"))
        f1 = proj1.get("components/countdown.tsx")
        f2 = proj2.get("components/countdown.tsx")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, render_countdown_component())

    def test_use_client_directive(self) -> None:
        self.assertTrue(self.source.startswith("'use client';"))

    def test_zero_runtime_dependencies(self) -> None:
        for pkg in re.findall(r"from\s+['\"]([^'\"]+)['\"]", self.source):
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected import: {pkg}",
            )

    def test_forward_ref_and_imperative_handle(self) -> None:
        self.assertIn("forwardRef<CountdownHandle, CountdownProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        for method in ("start:", "pause:", "reset:", "restart:", "getTime:", "isRunning:"):
            self.assertIn(method, self.source)

    def test_typescript_types_present(self) -> None:
        for decl in (
            "export type CountdownVariant",
            "export type CountdownSize",
            "export type CountdownMode",
            "export interface CountdownHandle",
            "export interface CountdownProps",
        ):
            self.assertIn(decl, self.source)

    def test_compound_and_alias_exports(self) -> None:
        for decl in (
            "export const Countdown =",
            "export const CountdownTimer =",
            "export const Stopwatch =",
            "export const LiveClock =",
            "export default CountdownComponent",
        ):
            self.assertIn(decl, self.source)

    def test_display_names_defined(self) -> None:
        for line in (
            "CountdownComponent.displayName = 'Countdown'",
            "CountdownTimer.displayName = 'CountdownTimer'",
            "Stopwatch.displayName = 'Stopwatch'",
            "LiveClock.displayName = 'LiveClock'",
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

    def test_modes_present(self) -> None:
        self.assertIn("'countdown' | 'stopwatch' | 'clock'", self.source)

    def test_interval_ticking(self) -> None:
        self.assertIn("setInterval(", self.source)
        self.assertIn("clearInterval(", self.source)

    def test_ssr_safe_mounting(self) -> None:
        self.assertIn("mounted", self.source)
        self.assertIn("Date.now()", self.source)

    def test_timer_aria_semantics(self) -> None:
        self.assertIn('role="timer"', self.source)
        self.assertIn("aria-atomic", self.source)
        self.assertIn("aria-live", self.source)

    def test_prefers_reduced_motion(self) -> None:
        self.assertIn("matchMedia('(prefers-reduced-motion: reduce)')", self.source)

    def test_callbacks(self) -> None:
        self.assertIn("onComplete", self.source)
        self.assertIn("onTick", self.source)

    def test_time_formatting(self) -> None:
        self.assertIn("padStart", self.source)
        for token in ("targetDate", "duration", "days", "hours", "minutes", "seconds"):
            self.assertIn(token, self.source)

    def test_package_codegen_export(self) -> None:
        self.assertTrue(hasattr(cg, "render_countdown_component"))
        self.assertTrue(callable(cg.render_countdown_component))
        self.assertIn("render_countdown_component", cg.__all__)


if __name__ == "__main__":
    unittest.main()
