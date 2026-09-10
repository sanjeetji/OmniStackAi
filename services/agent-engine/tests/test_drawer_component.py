"""Tests for Task R-318: Generated Accessible Reusable Drawer / Sheet Component.

Verifies that NextjsWebAdapter emits an accessible, reusable compound Drawer component
(apps/web/components/drawer.tsx) with Drawer, DrawerHeader, DrawerTitle, DrawerDescription,
DrawerContent, and DrawerFooter subcomponents, supporting WAI-ARIA modal dialog semantics.
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import (
    render_drawer_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
)


class DrawerComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.code = render_drawer_component()

    def test_drawer_component_is_client_component(self) -> None:
        """Drawer component specifies 'use client' directive."""
        self.assertTrue(self.code.startswith('"use client";'))

    def test_drawer_component_exports_types_and_subcomponents(self) -> None:
        """Drawer component exports types, interfaces, and compound subcomponents."""
        self.assertIn('export type DrawerPosition = "left" | "right" | "top" | "bottom";', self.code)
        self.assertIn('export type DrawerSize = "sm" | "md" | "lg" | "xl" | "full";', self.code)
        self.assertIn("export interface DrawerProps", self.code)
        self.assertIn("export interface DrawerHeaderProps", self.code)
        self.assertIn("export interface DrawerTitleProps", self.code)
        self.assertIn("export interface DrawerDescriptionProps", self.code)
        self.assertIn("export interface DrawerContentProps", self.code)
        self.assertIn("export interface DrawerFooterProps", self.code)
        self.assertIn("export function Drawer(", self.code)
        self.assertIn("export function DrawerHeader(", self.code)
        self.assertIn("export function DrawerTitle(", self.code)
        self.assertIn("export function DrawerDescription(", self.code)
        self.assertIn("export function DrawerContent(", self.code)
        self.assertIn("export function DrawerFooter(", self.code)
        self.assertIn("export default Drawer;", self.code)

    def test_drawer_component_uses_wai_aria_dialog_semantics(self) -> None:
        """Drawer applies role='dialog' and aria-modal='true'."""
        self.assertIn('role="dialog"', self.code)
        self.assertIn('aria-modal="true"', self.code)
        self.assertIn("aria-labelledby=", self.code)

    def test_drawer_component_supports_positions(self) -> None:
        """Drawer supports left, right, top, bottom positions."""
        self.assertIn('position = "right"', self.code)
        self.assertIn("left:", self.code)
        self.assertIn("right:", self.code)
        self.assertIn("top:", self.code)
        self.assertIn("bottom:", self.code)

    def test_drawer_component_supports_sizes(self) -> None:
        """Drawer supports sm, md, lg, xl, full size presets."""
        self.assertIn("sizeMap", self.code)
        self.assertIn("sm:", self.code)
        self.assertIn("md:", self.code)
        self.assertIn("lg:", self.code)
        self.assertIn("xl:", self.code)
        self.assertIn("full:", self.code)

    def test_drawer_component_handles_escape_key(self) -> None:
        """Drawer listens for Escape key to close when open."""
        self.assertIn('e.key === "Escape"', self.code)
        self.assertIn("closeOnEscape", self.code)

    def test_drawer_component_handles_backdrop_click(self) -> None:
        """Drawer supports backdrop overlay click to close."""
        self.assertIn("closeOnBackdropClick", self.code)
        self.assertIn("handleBackdropClick", self.code)

    def test_drawer_component_accessible_close_button(self) -> None:
        """Drawer provides an accessible close button with aria-label."""
        self.assertIn('aria-label="Close drawer"', self.code)

    def test_codegen_module_exports_render_drawer_component(self) -> None:
        """render_drawer_component is exported from omnistackai_agent_engine.codegen."""
        self.assertTrue(hasattr(cg, "render_drawer_component"))
        self.assertEqual(cg.render_drawer_component(), self.code)

    def test_adapter_generate_registers_drawer_component(self) -> None:
        """NextjsWebAdapter.generate outputs components/drawer.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/drawer.tsx")
        self.assertIsNotNone(f)
        self.assertEqual(f.content, self.code)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        """render_drawer_component is 100% diff-invariant across changes to ir.description."""
        ir1 = example_ir("minimal-blog")
        ir2 = dataclasses.replace(ir1, description="Completely changed IR description for R-318")

        adapter = NextjsWebAdapter()
        p1 = adapter.generate(ir1).get("components/drawer.tsx")
        p2 = adapter.generate(ir2).get("components/drawer.tsx")

        self.assertIsNotNone(p1)
        self.assertIsNotNone(p2)
        self.assertEqual(p1.content, p2.content)


if __name__ == "__main__":
    unittest.main()
