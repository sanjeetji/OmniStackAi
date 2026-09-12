"""Tests for the Accessible Futuristic Before/After Image Comparison Slider Suite (components/image-comparison.tsx)."""

from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine import codegen as cg
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_image_comparison_component,
)


class TestImageComparisonComponent(unittest.TestCase):
    """Unit tests for the Accessible Futuristic Before/After Image Comparison Slider Suite (R-400)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_image_comparison_component()

    def test_file_generated(self) -> None:
        project = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        self.assertIsNotNone(project.get("components/image-comparison.tsx"))

    def test_diff_invariance_and_codegen_export(self) -> None:
        proj1 = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        proj2 = NextjsWebAdapter().generate(example_ir("rideshare-favourites"))
        f1 = proj1.get("components/image-comparison.tsx")
        f2 = proj2.get("components/image-comparison.tsx")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, render_image_comparison_component())

    def test_use_client_directive(self) -> None:
        self.assertTrue(self.source.startswith("'use client';"))

    def test_zero_runtime_dependencies(self) -> None:
        for pkg in re.findall(r"from\s+['\"]([^'\"]+)['\"]", self.source):
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected import: {pkg}",
            )

    def test_forward_ref_and_imperative_handle(self) -> None:
        self.assertIn("forwardRef<ImageComparisonHandle, ImageComparisonProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        for method in ("setPosition:", "getPosition:", "reset:"):
            self.assertIn(method, self.source)

    def test_typescript_types_present(self) -> None:
        for decl in (
            "export type ImageComparisonVariant",
            "export type ImageComparisonSize",
            "export type ImageComparisonOrientation",
            "export interface ImageComparisonHandle",
            "export interface ImageComparisonProps",
        ):
            self.assertIn(decl, self.source)

    def test_compound_and_alias_exports(self) -> None:
        for decl in (
            "export const ImageComparison =",
            "export const BeforeAfterSlider =",
            "export const CompareSlider =",
            "export const ImageReveal =",
            "export default ImageComparisonComponent",
        ):
            self.assertIn(decl, self.source)

    def test_display_names_defined(self) -> None:
        for line in (
            "ImageComparisonComponent.displayName = 'ImageComparison'",
            "BeforeAfterSlider.displayName = 'BeforeAfterSlider'",
            "CompareSlider.displayName = 'CompareSlider'",
            "ImageReveal.displayName = 'ImageReveal'",
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

    def test_slider_aria_semantics(self) -> None:
        for token in (
            'role="slider"',
            "aria-valuenow",
            "aria-valuemin",
            "aria-valuemax",
            "aria-valuetext",
            "aria-orientation",
        ):
            self.assertIn(token, self.source)

    def test_group_role(self) -> None:
        self.assertIn('role="group"', self.source)

    def test_pointer_drag(self) -> None:
        for token in ("onPointerDown", "onPointerMove", "onPointerUp", "setPointerCapture"):
            self.assertIn(token, self.source)

    def test_keyboard_control(self) -> None:
        for token in ("onKeyDown", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End", "PageUp", "PageDown"):
            self.assertIn(token, self.source)

    def test_clip_path_reveal(self) -> None:
        self.assertIn("clipPath", self.source)
        self.assertIn("Math.max(0, Math.min(100", self.source)

    def test_orientation_support(self) -> None:
        self.assertIn("orientation", self.source)
        self.assertIn("'vertical'", self.source)
        self.assertIn("'horizontal'", self.source)

    def test_labels_and_images(self) -> None:
        for token in ("beforeLabel", "afterLabel", "beforeSrc", "afterSrc"):
            self.assertIn(token, self.source)

    def test_package_codegen_export(self) -> None:
        self.assertTrue(hasattr(cg, "render_image_comparison_component"))
        self.assertTrue(callable(cg.render_image_comparison_component))
        self.assertIn("render_image_comparison_component", cg.__all__)


if __name__ == "__main__":
    unittest.main()
