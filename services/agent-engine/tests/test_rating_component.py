"""Tests for Task R-333: Generated Accessible Reusable Rating & Review Component.

Verifies that NextjsWebAdapter emits an accessible, reusable Rating component
(apps/web/components/rating.tsx) supporting interactive hover preview, half-star selection
(allowHalf), keyboard navigation (Arrows, Home, End), WAI-ARIA slider pattern semantics,
built-in inline vector icons (star, heart, thumb), read-only and disabled modes, score formatting,
and 100% diff invariance.
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import (
    render_rating_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
)


class RatingComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.code = render_rating_component()

    def test_rating_component_is_client_component(self) -> None:
        """Rating component specifies 'use client' directive."""
        self.assertTrue(self.code.startswith('"use client";'))

    def test_rating_component_exports_types_and_component(self) -> None:
        """Rating component exports RatingSize, RatingIcon, RatingProps, and Rating function."""
        self.assertIn('export type RatingSize = "sm" | "md" | "lg";', self.code)
        self.assertIn('export type RatingIcon = "star" | "heart" | "thumb";', self.code)
        self.assertIn("export interface RatingProps", self.code)
        self.assertIn("export function Rating(", self.code)
        self.assertIn("export default Rating;", self.code)

    def test_rating_wai_aria_slider_semantics(self) -> None:
        """Rating implements WAI-ARIA slider pattern attributes."""
        self.assertIn('role="slider"', self.code)
        self.assertIn("aria-valuenow={displayValue}", self.code)
        self.assertIn("aria-valuemin={0}", self.code)
        self.assertIn("aria-valuemax={max}", self.code)
        self.assertIn("aria-valuetext={`${displayValue} of ${max} ${icon}s`}", self.code)
        self.assertIn("aria-readonly={readOnly}", self.code)
        self.assertIn("aria-disabled={disabled}", self.code)
        self.assertIn("tabIndex={disabled || readOnly ? -1 : 0}", self.code)

    def test_rating_supports_hover_preview_and_click_selection(self) -> None:
        """Rating updates score preview on mouse move and fires change on click."""
        self.assertIn("handleItemMouseMove", self.code)
        self.assertIn("handleItemClick", self.code)
        self.assertIn("handleMouseLeave", self.code)
        self.assertIn("onHover?.(calculated)", self.code)
        self.assertIn("onChange?.(calculated)", self.code)
        self.assertIn("setHoverValue(null)", self.code)

    def test_rating_supports_half_increments(self) -> None:
        """Rating supports half-star selection detecting left half of item rect."""
        self.assertIn("allowHalf = false", self.code)
        self.assertIn("const isLeft = e.clientX - rect.left < rect.width / 2;", self.code)
        self.assertIn("const calculated = allowHalf && isLeft ? index - 0.5 : index;", self.code)
        self.assertIn("const fillRatio = Math.max(0, Math.min(1, displayValue - (index - 1)));", self.code)

    def test_rating_keyboard_navigation_arrows_home_end(self) -> None:
        """Rating handles Arrow keys, Home, and End for keyboard navigation."""
        self.assertIn('case "ArrowRight":', self.code)
        self.assertIn('case "ArrowUp":', self.code)
        self.assertIn('case "ArrowLeft":', self.code)
        self.assertIn('case "ArrowDown":', self.code)
        self.assertIn('case "Home":', self.code)
        self.assertIn('case "End":', self.code)
        self.assertIn("const step = allowHalf ? 0.5 : 1;", self.code)

    def test_rating_built_in_icons_star_heart_thumb(self) -> None:
        """Rating provides inline vector SVG paths for star, heart, and thumb."""
        self.assertIn("const ICON_PATHS: Record<RatingIcon, string>", self.code)
        self.assertIn("star:", self.code)
        self.assertIn("heart:", self.code)
        self.assertIn("thumb:", self.code)
        self.assertIn("pathData = ICON_PATHS[icon]", self.code)

    def test_rating_read_only_and_disabled_states(self) -> None:
        """Rating supports read-only and disabled interaction guards."""
        self.assertIn("if (readOnly || disabled) return;", self.code)
        self.assertIn('opacity: disabled ? 0.5 : 1', self.code)
        self.assertIn('cursor: disabled ? "not-allowed" : (readOnly ? "default" : "pointer")', self.code)

    def test_rating_score_formatting(self) -> None:
        """Rating renders formatted score badge when showScore is enabled."""
        self.assertIn("showScore = false", self.code)
        self.assertIn("formatScore?: (value: number, max: number) => string;", self.code)
        self.assertIn("`${displayValue} / ${max}`", self.code)
        self.assertIn("{scoreFormatted}", self.code)

    def test_rating_size_presets(self) -> None:
        """Rating provides size presets for sm, md, and lg."""
        self.assertIn("const SIZE_CONFIGS: Record<RatingSize,", self.code)
        self.assertIn("sm: { iconSize: 16, gap: 4, fontSize: 12 }", self.code)
        self.assertIn("md: { iconSize: 24, gap: 6, fontSize: 14 }", self.code)
        self.assertIn("lg: { iconSize: 32, gap: 8, fontSize: 16 }", self.code)

    def test_adapter_generates_components_rating_tsx(self) -> None:
        """NextjsWebAdapter outputs components/rating.tsx in the generated project."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        rating_file = project.get("components/rating.tsx")
        self.assertIsNotNone(rating_file)
        self.assertEqual(rating_file.content, self.code)

    def test_package_codegen_exports_render_rating_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_rating_component."""
        self.assertTrue(callable(cg.render_rating_component))
        self.assertIn("render_rating_component", cg.__all__)
        self.assertEqual(cg.render_rating_component(), self.code)

    def test_diff_invariance_across_ir_description(self) -> None:
        """render_rating_component is 100% diff-invariant across changes to ir.description."""
        modified_ir = dataclasses.replace(
            self.ir,
            description="Completely different description to test diff-invariance",
        )
        adapter = NextjsWebAdapter()
        original_file = adapter.generate(self.ir).get("components/rating.tsx")
        modified_file = adapter.generate(modified_ir).get("components/rating.tsx")

        self.assertIsNotNone(original_file)
        self.assertIsNotNone(modified_file)
        self.assertEqual(original_file.content, modified_file.content)
