"""Tests for Task R-325: Generated Theme Switcher / Mode Toggle Component.

Verifies that NextjsWebAdapter emits an accessible, reusable Theme Switcher component
(apps/web/components/theme-toggle.tsx) supporting Light/Dark/System modes, ThemeProvider,
useTheme hook, ThemeToggle button, ThemeSelect segmented control, FOUC-prevention ThemeScript,
WAI-ARIA semantics, and 100% diff invariance.
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_theme_toggle_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    _THEME_TOGGLE_COMPONENT,
)


class ThemeToggleComponentTests(unittest.TestCase):
    """Assertions ensuring the emitted Theme Switcher component conforms to platform standards."""

    def setUp(self) -> None:
        self.code = _THEME_TOGGLE_COMPONENT
        self.ir = example_ir("minimal-blog")
        self.adapter = NextjsWebAdapter()
        self.project = self.adapter.generate(self.ir)

    def test_theme_toggle_is_client_component(self) -> None:
        """Component must specify 'use client' directive."""
        self.assertTrue(
            self.code.strip().startswith('"use client";')
            or self.code.strip().startswith("'use client';")
        )

    def test_theme_toggle_exports_types_and_components(self) -> None:
        """Module must export ThemeMode, ThemeProvider, useTheme, ThemeToggle, ThemeSelect, and ThemeScript."""
        self.assertIn("export type ThemeMode", self.code)
        self.assertIn("export type ResolvedTheme", self.code)
        self.assertIn("export interface ThemeContextValue", self.code)
        self.assertIn("export function ThemeProvider(", self.code)
        self.assertIn("export function useTheme():", self.code)
        self.assertIn("export function ThemeToggle(", self.code)
        self.assertIn("export function ThemeSelect(", self.code)
        self.assertIn("export function ThemeScript(", self.code)

    def test_theme_provider_manages_modes(self) -> None:
        """ThemeProvider must handle light, dark, and system modes."""
        self.assertIn('"light"', self.code)
        self.assertIn('"dark"', self.code)
        self.assertIn('"system"', self.code)
        self.assertIn("data-theme", self.code)

    def test_theme_provider_handles_local_storage(self) -> None:
        """Theme state must synchronize with browser localStorage."""
        self.assertIn("localStorage.getItem(", self.code)
        self.assertIn("localStorage.setItem(", self.code)

    def test_theme_provider_handles_system_media_query(self) -> None:
        """System mode must listen to window.matchMedia for system color scheme shifts."""
        self.assertIn('prefers-color-scheme: dark', self.code)
        self.assertIn("matchMedia", self.code)
        self.assertIn("addEventListener", self.code)

    def test_theme_toggle_uses_wai_aria_attributes(self) -> None:
        """Toggle buttons must emit accessible ARIA labels and hidden vector SVGs."""
        self.assertIn('aria-label=', self.code)
        self.assertIn('aria-hidden="true"', self.code)

    def test_theme_select_uses_radiogroup_semantics(self) -> None:
        """Segmented theme selector must emit radiogroup and radio attributes."""
        self.assertIn('role="radiogroup"', self.code)
        self.assertIn('role="radio"', self.code)
        self.assertIn("aria-checked=", self.code)

    def test_theme_script_fouc_prevention(self) -> None:
        """ThemeScript must emit inline script setting data-theme before body hydration."""
        self.assertIn("dangerouslySetInnerHTML", self.code)
        self.assertIn("document.documentElement.setAttribute", self.code)

    def test_theme_toggle_contains_svg_icons(self) -> None:
        """Icons for Sun, Moon, and System Monitor must be present as inline SVGs."""
        self.assertIn("<svg", self.code)
        self.assertIn("viewBox", self.code)
        self.assertIn("SunIcon", self.code)
        self.assertIn("MoonIcon", self.code)
        self.assertIn("SystemIcon", self.code)

    def test_adapter_generates_theme_toggle_file(self) -> None:
        """NextjsWebAdapter must emit components/theme-toggle.tsx in generated files."""
        paths = set(self.project.paths())
        self.assertIn("components/theme-toggle.tsx", paths)
        generated_content = self.project.get("components/theme-toggle.tsx").content
        self.assertEqual(generated_content, self.code)

    def test_exports_in_codegen_package(self) -> None:
        """render_theme_toggle_component must be exported from codegen package."""
        self.assertTrue(callable(cg.render_theme_toggle_component))
        self.assertEqual(cg.render_theme_toggle_component(), self.code)
        self.assertEqual(render_theme_toggle_component(), self.code)

    def test_theme_toggle_diff_invariance(self) -> None:
        """Theme switcher template must be 100% diff-invariant across ir.description changes."""
        ir1 = self.ir
        ir2 = dataclasses.replace(ir1, description="Completely changed description for test")
        proj1 = self.adapter.generate(ir1)
        proj2 = self.adapter.generate(ir2)

        file1 = proj1.get("components/theme-toggle.tsx").content
        file2 = proj2.get("components/theme-toggle.tsx").content
        self.assertEqual(file1, file2)


if __name__ == "__main__":
    unittest.main()
