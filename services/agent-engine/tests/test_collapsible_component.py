"""Tests for Task R-351: Generated Accessible Futuristic Reusable Collapsible Component.

Verifies that NextjsWebAdapter emits an accessible, desktop-grade, zero-dependency, and futuristic
Collapsible / Disclosure compound component suite (apps/web/components/collapsible.tsx) supporting:
- Compound suite (Collapsible, Collapsible.Trigger, Collapsible.Content, useCollapsible)
- Smooth animated expansion using CSS grid template rows (1fr / 0fr) with overflow: hidden
- Built-in rotating indicator chevron (180deg) with custom indicator slot and hideIndicator option
- Full WAI-ARIA 1.2 disclosure pattern compliance (aria-expanded, aria-controls, role="region", aria-labelledby)
- Full keyboard navigation (Enter and Space trigger activation)
- Controlled and uncontrolled open state management (open, defaultOpen, onOpenChange)
- Disabled state management (disabled, aria-disabled)
- 4 futuristic visual variants ("neon", "glass", "bordered", "minimal")
- 3 size presets ("sm", "md", "lg")
- 100% diff-invariance across ir.description changes
- Zero external runtime dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_collapsible_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class CollapsibleComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the Collapsible component suite."""

    def setUp(self) -> None:
        self.code = render_collapsible_component()
        self.ir = example_ir("rideshare-favourites")

    def test_collapsible_is_client_component(self) -> None:
        """Collapsible must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "Collapsible must have 'use client' as the first statement.",
        )

    def test_collapsible_exports_types(self) -> None:
        """Verify export of TypeScript interfaces and union types."""
        self.assertIn("export type CollapsibleVariant", self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"bordered"', self.code)
        self.assertIn('"minimal"', self.code)
        self.assertIn("export type CollapsibleSize", self.code)
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)
        self.assertIn("export interface CollapsibleProps", self.code)
        self.assertIn("export interface CollapsibleTriggerProps", self.code)
        self.assertIn("export interface CollapsibleContentProps", self.code)
        self.assertIn("export interface CollapsibleContextValue", self.code)

    def test_collapsible_exports_compound_components(self) -> None:
        """Verify Collapsible compound component and all subcomponents."""
        self.assertIn("export const CollapsibleRoot", self.code)
        self.assertIn("export const CollapsibleTrigger", self.code)
        self.assertIn("export const CollapsibleContent", self.code)
        self.assertIn("export function useCollapsible()", self.code)
        self.assertIn("Collapsible.Trigger = CollapsibleTrigger;", self.code)
        self.assertIn("Collapsible.Content = CollapsibleContent;", self.code)
        self.assertIn("export default Collapsible;", self.code)

    def test_collapsible_zero_external_dependencies(self) -> None:
        """Collapsible uses only React; zero external package imports."""
        import_lines = [
            line.strip()
            for line in self.code.splitlines()
            if line.strip().startswith("import ")
        ]
        self.assertTrue(len(import_lines) >= 1)
        for line in import_lines:
            self.assertIn(
                'from "react"',
                line,
                f"Unexpected external import found in Collapsible: {line}",
            )

    def test_collapsible_wai_aria_disclosure_semantics(self) -> None:
        """Verify WAI-ARIA 1.2 disclosure roles and accessibility attributes."""
        self.assertIn("aria-expanded={open}", self.code)
        self.assertIn("aria-controls={contentId}", self.code)
        self.assertIn('role="region"', self.code)
        self.assertIn("aria-labelledby={triggerId}", self.code)
        self.assertIn('type="button"', self.code)
        self.assertIn('data-state={open ? "open" : "closed"}', self.code)

    def test_collapsible_keyboard_accessibility(self) -> None:
        """Verify keyboard activation on trigger button (Enter / Space)."""
        self.assertIn('e.key === "Enter"', self.code)
        self.assertIn('e.key === " "', self.code)
        self.assertIn("e.preventDefault()", self.code)

    def test_collapsible_controlled_and_uncontrolled(self) -> None:
        """Verify controlled and uncontrolled open state management."""
        self.assertIn("controlledOpen !== undefined", self.code)
        self.assertIn("setUncontrolledOpen", self.code)
        self.assertIn("onOpenChange?.(next)", self.code)
        self.assertIn("defaultOpen = false", self.code)

    def test_collapsible_disabled_state(self) -> None:
        """Verify disabled prop disables button and prevents toggling."""
        self.assertIn("aria-disabled={disabled}", self.code)
        self.assertIn("disabled={disabled}", self.code)
        self.assertIn("if (disabled) return;", self.code)

    def test_collapsible_css_grid_transition(self) -> None:
        """Verify smooth CSS grid template rows transition with overflow: hidden."""
        self.assertIn('display: "grid"', self.code)
        self.assertIn('gridTemplateRows: open ? "1fr" : "0fr"', self.code)
        self.assertIn('overflow: "hidden"', self.code)
        self.assertIn("cubic-bezier", self.code)

    def test_collapsible_indicator_and_custom_slot(self) -> None:
        """Verify rotating indicator chevron and customizable indicator slot."""
        self.assertIn('transform: open ? "rotate(180deg)" : "rotate(0deg)"', self.code)
        self.assertIn("hideIndicator", self.code)
        self.assertIn("indicator", self.code)
        self.assertIn("<polyline points=", self.code)

    def test_collapsible_supports_variants(self) -> None:
        """Verify 4 futuristic visual variants."""
        self.assertIn('"neon"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"bordered"', self.code)
        self.assertIn('"minimal"', self.code)
        self.assertIn("backdropFilter", self.code)

    def test_collapsible_supports_sizes(self) -> None:
        """Verify 3 size presets for padding and font sizing."""
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)

    def test_collapsible_force_mount_support(self) -> None:
        """Verify forceMount support on CollapsibleContent."""
        self.assertIn("forceMount", self.code)
        self.assertIn("hidden={!open && !forceMount}", self.code)

    def test_collapsible_diff_invariant(self) -> None:
        """Collapsible output is 100% diff-invariant across ir.description changes."""
        adapter = NextjsWebAdapter()
        project1 = adapter.generate(self.ir)
        ir2 = dataclasses.replace(
            self.ir, description="Completely changed description for diff test."
        )
        project2 = adapter.generate(ir2)
        c1 = project1.get("components/collapsible.tsx").content
        c2 = project2.get("components/collapsible.tsx").content
        self.assertEqual(
            c1,
            c2,
            "components/collapsible.tsx must be 100% diff-invariant across ir.description",
        )
        self.assertEqual(c1, self.code)

    def test_adapter_emits_collapsible_file(self) -> None:
        """NextjsWebAdapter emits components/collapsible.tsx in generated project."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/collapsible.tsx")
        self.assertIsNotNone(f, "components/collapsible.tsx must be generated")
        self.assertEqual(f.content, self.code)

    def test_package_codegen_exports_render_collapsible_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_collapsible_component."""
        self.assertTrue(callable(cg.render_collapsible_component))
        self.assertEqual(cg.render_collapsible_component(), self.code)


if __name__ == "__main__":
    unittest.main()
