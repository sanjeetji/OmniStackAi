"""Tests for Task R-317: Generated Accessible Reusable Skeleton Loader Component.

Verifies that NextjsWebAdapter emits an accessible, reusable compound Skeleton component
(apps/web/components/skeleton.tsx) with Skeleton, SkeletonText, SkeletonCard, and SkeletonTable
subcomponents, supporting WAI-ARIA status and busy semantics.
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import (
    render_skeleton_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
)


class SkeletonComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.code = render_skeleton_component()

    def test_skeleton_component_is_client_component(self) -> None:
        """Skeleton component specifies 'use client' directive."""
        self.assertTrue(self.code.startswith('"use client";'))

    def test_skeleton_component_exports_types_and_subcomponents(self) -> None:
        """Skeleton component exports types, interfaces, and compound subcomponents."""
        self.assertIn('export type SkeletonVariant = "text" | "circular" | "rectangular" | "rounded";', self.code)
        self.assertIn('export type SkeletonAnimation = "pulse" | "wave" | "none";', self.code)
        self.assertIn("export interface SkeletonProps", self.code)
        self.assertIn("export interface SkeletonTextProps", self.code)
        self.assertIn("export interface SkeletonCardProps", self.code)
        self.assertIn("export interface SkeletonTableProps", self.code)
        self.assertIn("export function Skeleton(", self.code)
        self.assertIn("export function SkeletonText(", self.code)
        self.assertIn("export function SkeletonCard(", self.code)
        self.assertIn("export function SkeletonTable(", self.code)
        self.assertIn("export default Skeleton;", self.code)

    def test_skeleton_component_uses_wai_aria_semantics(self) -> None:
        """Skeleton component applies role='status', aria-busy='true', and aria-live='polite'."""
        self.assertIn('role="status"', self.code)
        self.assertIn('aria-busy="true"', self.code)
        self.assertIn('aria-live="polite"', self.code)

    def test_skeleton_component_screen_reader_announcement(self) -> None:
        """Skeleton provides accessible screen-reader announcement label."""
        self.assertIn('ariaLabel = "Loading..."', self.code)
        self.assertIn('clip: "rect(0, 0, 0, 0)"', self.code)

    def test_skeleton_component_variants_and_shapes(self) -> None:
        """Skeleton supports text, circular, rectangular, and rounded variants."""
        self.assertIn("variantBorderRadius", self.code)
        self.assertIn('text: "4px"', self.code)
        self.assertIn('circular: "50%"', self.code)
        self.assertIn('rectangular: "0px"', self.code)
        self.assertIn('rounded: "8px"', self.code)

    def test_skeleton_component_custom_dimensions_and_styles(self) -> None:
        """Skeleton supports width, height, className, and style props."""
        self.assertIn("width?: string | number;", self.code)
        self.assertIn("height?: string | number;", self.code)
        self.assertIn("className?: string;", self.code)
        self.assertIn("style?: React.CSSProperties;", self.code)

    def test_skeleton_component_animation_and_reduced_motion(self) -> None:
        """Skeleton defines pulse animation keyframes and reduced-motion support."""
        self.assertIn("animation?: SkeletonAnimation;", self.code)
        self.assertIn("@keyframes omnistack-skeleton-pulse", self.code)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.code)

    def test_codegen_module_exports_render_skeleton_component(self) -> None:
        """render_skeleton_component is exported from omnistackai_agent_engine.codegen."""
        self.assertTrue(hasattr(cg, "render_skeleton_component"))
        self.assertEqual(cg.render_skeleton_component(), self.code)

    def test_adapter_generate_registers_skeleton_component(self) -> None:
        """NextjsWebAdapter.generate outputs components/skeleton.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/skeleton.tsx")
        self.assertIsNotNone(f)
        self.assertEqual(f.content, self.code)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        """render_skeleton_component is 100% diff-invariant across changes to ir.description."""
        ir1 = example_ir("minimal-blog")
        ir2 = dataclasses.replace(ir1, description="Completely changed IR description for R-317")

        adapter = NextjsWebAdapter()
        p1 = adapter.generate(ir1).get("components/skeleton.tsx")
        p2 = adapter.generate(ir2).get("components/skeleton.tsx")

        self.assertIsNotNone(p1)
        self.assertIsNotNone(p2)
        self.assertEqual(p1.content, p2.content)


if __name__ == "__main__":
    unittest.main()
