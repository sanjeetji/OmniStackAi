"""Tests for Task R-319: Generated Accessible Reusable Avatar Component.

Verifies that NextjsWebAdapter emits an accessible, reusable compound Avatar component
(apps/web/components/avatar.tsx) with Avatar and AvatarGroup subcomponents, supporting
WAI-ARIA img and status semantics.
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import (
    render_avatar_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
)


class AvatarComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.code = render_avatar_component()

    def test_avatar_component_is_client_component(self) -> None:
        """Avatar component specifies 'use client' directive."""
        self.assertTrue(self.code.startswith('"use client";'))

    def test_avatar_component_exports_types_and_subcomponents(self) -> None:
        """Avatar component exports types, interfaces, and compound subcomponents."""
        self.assertIn('export type AvatarShape = "circle" | "rounded" | "square";', self.code)
        self.assertIn('export type AvatarSize = "xs" | "sm" | "md" | "lg" | "xl";', self.code)
        self.assertIn('export type AvatarStatus = "online" | "offline" | "busy" | "away";', self.code)
        self.assertIn("export interface AvatarProps", self.code)
        self.assertIn("export interface AvatarGroupProps", self.code)
        self.assertIn("export function Avatar(", self.code)
        self.assertIn("export function AvatarGroup(", self.code)
        self.assertIn("export default Avatar;", self.code)

    def test_avatar_component_uses_wai_aria_semantics(self) -> None:
        """Avatar applies role='img', aria-label, and decorative aria-hidden attributes."""
        self.assertIn('role="img"', self.code)
        self.assertIn("aria-label=", self.code)
        self.assertIn('aria-hidden="true"', self.code)

    def test_avatar_component_supports_shapes(self) -> None:
        """Avatar supports circle, rounded, square shapes."""
        self.assertIn('shape = "circle"', self.code)
        self.assertIn("circle:", self.code)
        self.assertIn("rounded:", self.code)
        self.assertIn("square:", self.code)

    def test_avatar_component_supports_sizes(self) -> None:
        """Avatar supports xs, sm, md, lg, xl size presets."""
        self.assertIn("sizeMap: Record<AvatarSize,", self.code)
        self.assertIn("xs:", self.code)
        self.assertIn("sm:", self.code)
        self.assertIn("md:", self.code)
        self.assertIn("lg:", self.code)
        self.assertIn("xl:", self.code)

    def test_avatar_component_supports_status_indicators(self) -> None:
        """Avatar supports presence status indicators (online, offline, busy, away)."""
        self.assertIn("status?: AvatarStatus;", self.code)
        self.assertIn("online:", self.code)
        self.assertIn("offline:", self.code)
        self.assertIn("busy:", self.code)
        self.assertIn("away:", self.code)

    def test_avatar_component_supports_initials_and_color_hashing(self) -> None:
        """Avatar extracts initials and maps deterministically to palette."""
        self.assertIn("getInitials", self.code)
        self.assertIn("getColorFromName", self.code)

    def test_avatar_component_supports_image_fallback(self) -> None:
        """Avatar provides image rendering with onError fallback."""
        self.assertIn("<img", self.code)
        self.assertIn("onError={() => setImageError(true)}", self.code)

    def test_avatar_group_supports_max_and_overflow(self) -> None:
        """AvatarGroup renders overlapping items with max limit and excess counter."""
        self.assertIn("max?: number;", self.code)
        self.assertIn("+{excessCount}", self.code)

    def test_codegen_module_exports_render_avatar_component(self) -> None:
        """render_avatar_component is exported from omnistackai_agent_engine.codegen."""
        self.assertTrue(hasattr(cg, "render_avatar_component"))
        self.assertEqual(cg.render_avatar_component(), self.code)

    def test_adapter_generate_registers_avatar_component_and_diff_invariance(self) -> None:
        """NextjsWebAdapter.generate outputs components/avatar.tsx and maintains diff-invariance."""
        ir1 = example_ir("minimal-blog")
        ir2 = dataclasses.replace(ir1, description="Completely changed IR description for R-319")

        adapter = NextjsWebAdapter()
        p1 = adapter.generate(ir1).get("components/avatar.tsx")
        p2 = adapter.generate(ir2).get("components/avatar.tsx")

        self.assertIsNotNone(p1)
        self.assertIsNotNone(p2)
        self.assertEqual(p1.content, self.code)
        self.assertEqual(p1.content, p2.content)


if __name__ == "__main__":
    unittest.main()
