"""Tests for Task R-315: Generated Accessible Reusable Card Component.

Verifies that NextjsWebAdapter emits an accessible, reusable compound Card component
(apps/web/components/card.tsx) with Card, CardHeader, CardTitle, CardDescription,
CardContent, and CardFooter subcomponents.
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import (
    render_card_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
)


class CardComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.code = render_card_component()

    def test_card_component_is_client_component(self) -> None:
        """Card component specifies 'use client' directive."""
        self.assertTrue(self.code.startswith('"use client";'))

    def test_card_component_exports_types_and_subcomponents(self) -> None:
        """Card component exports types and all compound subcomponents."""
        self.assertIn('export type CardVariant = "default" | "bordered" | "flat" | "elevated";', self.code)
        self.assertIn('export type CardPadding = "none" | "sm" | "md" | "lg";', self.code)
        self.assertIn("export interface CardProps", self.code)
        self.assertIn("export interface CardHeaderProps", self.code)
        self.assertIn("export interface CardTitleProps", self.code)
        self.assertIn("export interface CardDescriptionProps", self.code)
        self.assertIn("export interface CardContentProps", self.code)
        self.assertIn("export interface CardFooterProps", self.code)
        self.assertIn("export function Card(", self.code)
        self.assertIn("export function CardHeader(", self.code)
        self.assertIn("export function CardTitle(", self.code)
        self.assertIn("export function CardDescription(", self.code)
        self.assertIn("export function CardContent(", self.code)
        self.assertIn("export function CardFooter(", self.code)
        self.assertIn("export default Card;", self.code)

    def test_card_component_supports_variants(self) -> None:
        """Card component defines variant styles for default, bordered, flat, elevated."""
        self.assertIn("variantStyles: Record<CardVariant, React.CSSProperties>", self.code)
        self.assertIn("default:", self.code)
        self.assertIn("bordered:", self.code)
        self.assertIn("flat:", self.code)
        self.assertIn("elevated:", self.code)

    def test_card_component_supports_padding_presets(self) -> None:
        """Card component defines padding styles for none, sm, md, lg."""
        self.assertIn("paddingStyles: Record<CardPadding, string>", self.code)
        self.assertIn('none: "0"', self.code)
        self.assertIn('sm: "12px 16px"', self.code)
        self.assertIn('md: "20px 24px"', self.code)
        self.assertIn('lg: "28px 32px"', self.code)

    def test_card_component_supports_polymorphic_tags(self) -> None:
        """Card and CardTitle support polymorphic tags via the 'as' prop."""
        self.assertIn('as?: "div" | "article" | "section";', self.code)
        self.assertIn('as?: "h1" | "h2" | "h3" | "h4" | "h5" | "h6" | "div";', self.code)
        self.assertIn("const Component = as;", self.code)

    def test_card_component_supports_interactive_click_and_keyboard(self) -> None:
        """Card component handles onClick with role='button', tabIndex=0, and Enter/Space keyboard trigger."""
        self.assertIn("const isInteractive = Boolean(onClick);", self.code)
        self.assertIn('role={role ?? (isInteractive ? "button" : undefined)}', self.code)
        self.assertIn("tabIndex={tabIndex ?? (isInteractive ? 0 : undefined)}", self.code)
        self.assertIn('e.key === "Enter" || e.key === " "', self.code)

    def test_card_header_supports_action_and_title_props(self) -> None:
        """CardHeader supports action slot, title, and description props."""
        self.assertIn("action?: React.ReactNode;", self.code)
        self.assertIn("title?: React.ReactNode;", self.code)
        self.assertIn("description?: React.ReactNode;", self.code)

    def test_card_footer_supports_alignment(self) -> None:
        """CardFooter defines alignment styles for left, right, between, center."""
        self.assertIn('align?: "left" | "right" | "between" | "center";', self.code)
        self.assertIn("justifyContent", self.code)

    def test_codegen_module_exports_render_card_component(self) -> None:
        """render_card_component is exported from omnistackai_agent_engine.codegen."""
        self.assertTrue(hasattr(cg, "render_card_component"))
        self.assertEqual(cg.render_card_component(), self.code)

    def test_adapter_generate_registers_card_component(self) -> None:
        """NextjsWebAdapter.generate outputs components/card.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/card.tsx")
        self.assertIsNotNone(f)
        self.assertEqual(f.content, self.code)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        """render_card_component is 100% diff-invariant across changes to ir.description."""
        ir1 = example_ir("minimal-blog")
        ir2 = dataclasses.replace(ir1, description="Completely changed IR description for R-315")

        adapter = NextjsWebAdapter()
        p1 = adapter.generate(ir1).get("components/card.tsx")
        p2 = adapter.generate(ir2).get("components/card.tsx")

        self.assertIsNotNone(p1)
        self.assertIsNotNone(p2)
        self.assertEqual(p1.content, p2.content)


if __name__ == "__main__":
    unittest.main()
