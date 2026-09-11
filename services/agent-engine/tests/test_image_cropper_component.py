"""Tests for the Accessible Futuristic Reusable Image Cropper & Canvas Mask Suite codegen (R-378).

Verifies:
1. Zero runtime dependencies (pure React).
2. "use client" directive present.
3. React forwardRef and explicit displayName across compound exports.
4. Exported canonical TypeScript types & interfaces.
5. Compound and semantic alias exports (ImageCropper, AvatarCropper, CropCanvas, CropToolbar, CropPreview, default).
6. Aspect ratio presets ("free", "1:1", "4:3", "16:9", "circular").
7. 4 visual styling variants ("default", "card", "glass", "neon").
8. 3 size presets ("sm", "md", "lg").
9. 8-point resize handles and pointer event tracking.
10. Zoom and rotation controls (0.5x to 3x, -180° to +180°, 90° step buttons).
11. Horizontal and vertical flip transforms.
12. HTML5 Canvas rendering, clipping, and export capabilities.
13. Keyboard nudging navigation (Arrow keys with shift multiplier).
14. WAI-ARIA accessibility semantics (role="region", aria-label="Image Cropper", aria-roledescription="image cropping canvas").
15. Imperative handle methods (crop, reset, rotate, zoom, flipH, flipV, toDataURL, getCropData).
16. NextjsWebAdapter emits components/image-cropper.tsx and codegen package exports render_image_cropper_component.
17. 100% diff-invariance across ir.description changes.
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_image_cropper_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TestImageCropperComponent(unittest.TestCase):
    """Test suite for components/image-cropper.tsx codegen."""

    def setUp(self) -> None:
        self.code = render_image_cropper_component()
        self.ir = example_ir("rideshare-favourites")

    def test_zero_runtime_dependencies(self) -> None:
        """Only imports from 'react' are allowed — 0 external npm dependencies."""
        imports = re.findall(r'from\s+"([^"]+)"', self.code)
        for imp in imports:
            self.assertEqual(imp, "react", f"Forbidden external import: {imp}")

    def test_use_client_directive(self) -> None:
        """Must have 'use client' as first statement for Next.js App Router."""
        lines = [line.strip() for line in self.code.splitlines() if line.strip()]
        self.assertEqual(lines[0], '"use client";')

    def test_forward_ref_and_display_name(self) -> None:
        """Must use React.forwardRef and set explicit displayName across compound exports."""
        self.assertIn("forwardRef", self.code)
        self.assertIn('ImageCropper.displayName = "ImageCropper"', self.code)
        self.assertIn('AvatarCropper.displayName = "AvatarCropper"', self.code)
        self.assertIn('CropCanvas.displayName = "CropCanvas"', self.code)
        self.assertIn('CropToolbar.displayName = "CropToolbar"', self.code)
        self.assertIn('CropPreview.displayName = "CropPreview"', self.code)

    def test_exported_canonical_types(self) -> None:
        """Canonical TypeScript types and interfaces must be exported."""
        self.assertIn("export type CropAspectRatio =", self.code)
        self.assertIn("export type ImageCropperVariant =", self.code)
        self.assertIn("export type ImageCropperSize =", self.code)
        self.assertIn("export interface CropArea", self.code)
        self.assertIn("export interface CropData", self.code)
        self.assertIn("export interface ImageCropperHandle", self.code)
        self.assertIn("export interface ImageCropperProps", self.code)
        self.assertIn("export interface CropToolbarProps", self.code)
        self.assertIn("export interface CropPreviewProps", self.code)
        self.assertIn("export interface AvatarCropperProps", self.code)

    def test_compound_and_alias_exports(self) -> None:
        """Must export ImageCropper, AvatarCropper, CropCanvas, CropToolbar, CropPreview, and default export."""
        self.assertIn("export const ImageCropper =", self.code)
        self.assertIn("export const AvatarCropper =", self.code)
        self.assertIn("export const CropCanvas =", self.code)
        self.assertIn("export const CropToolbar", self.code)
        self.assertIn("export const CropPreview", self.code)
        self.assertIn("export default ImageCropper;", self.code)

    def test_aspect_ratio_modes(self) -> None:
        """Must support free, 1:1, 4:3, 16:9, and circular aspect ratios."""
        for ar in ["free", "1:1", "4:3", "16:9", "circular"]:
            self.assertIn(f'"{ar}"', self.code)

    def test_visual_variants(self) -> None:
        """Must support 4 visual styling variants."""
        for variant in ["default", "card", "glass", "neon"]:
            self.assertIn(f'"{variant}"', self.code)
        self.assertIn("backdropFilter", self.code)
        self.assertIn("rgba(6, 182, 212", self.code)

    def test_size_presets(self) -> None:
        """Must define sm, md, lg size presets."""
        self.assertIn("sm:", self.code)
        self.assertIn("md:", self.code)
        self.assertIn("lg:", self.code)

    def test_resize_handles(self) -> None:
        """Must support 8 resize handles and pointer event tracking."""
        for handle in ["nw", "n", "ne", "e", "se", "s", "sw", "w"]:
            self.assertIn(f'"{handle}"', self.code)
        self.assertIn("setPointerCapture", self.code)
        self.assertIn("releasePointerCapture", self.code)

    def test_zoom_and_rotation_controls(self) -> None:
        """Must support continuous zoom and rotation sliders with 90 degree buttons."""
        self.assertIn("onZoomChange", self.code)
        self.assertIn("onRotateChange", self.code)
        self.assertIn("onRotateStep", self.code)
        self.assertIn("rotate", self.code)
        self.assertIn("zoom", self.code)

    def test_flip_controls(self) -> None:
        """Must support horizontal and vertical flipping."""
        self.assertIn("flipH", self.code)
        self.assertIn("flipV", self.code)
        self.assertIn("onFlipH", self.code)
        self.assertIn("onFlipV", self.code)

    def test_canvas_rendering_and_export(self) -> None:
        """Must render image to HTML5 canvas and export data URL."""
        self.assertIn('document.createElement("canvas")', self.code)
        self.assertIn('canvas.getContext("2d")', self.code)
        self.assertIn("canvas.toDataURL", self.code)
        self.assertIn("ctx.drawImage", self.code)

    def test_keyboard_nudging_navigation(self) -> None:
        """Must support arrow key nudging with shift acceleration."""
        self.assertIn("ArrowLeft", self.code)
        self.assertIn("ArrowRight", self.code)
        self.assertIn("ArrowUp", self.code)
        self.assertIn("ArrowDown", self.code)
        self.assertIn("shiftKey", self.code)

    def test_wai_aria_semantics(self) -> None:
        """Must contain WAI-ARIA region and roledescription attributes."""
        self.assertIn('role="region"', self.code)
        self.assertIn('aria-label="Image Cropper"', self.code)
        self.assertIn('aria-roledescription="image cropping canvas"', self.code)
        self.assertIn("tabIndex={0}", self.code)

    def test_imperative_handle_methods(self) -> None:
        """Must expose imperative handle methods via useImperativeHandle."""
        self.assertIn("useImperativeHandle", self.code)
        self.assertIn("crop:", self.code)
        self.assertIn("reset,", self.code)
        self.assertIn("rotate:", self.code)
        self.assertIn("zoom:", self.code)
        self.assertIn("flipH:", self.code)
        self.assertIn("flipV:", self.code)
        self.assertIn("toDataURL:", self.code)
        self.assertIn("getCropData", self.code)

    def test_nextjs_adapter_and_codegen_exports(self) -> None:
        """NextjsWebAdapter emits components/image-cropper.tsx and codegen exposes render function."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        cropper_file = project.get("components/image-cropper.tsx")
        self.assertIsNotNone(cropper_file, "components/image-cropper.tsx must be generated")
        self.assertEqual(cropper_file.content, self.code)

        self.assertIn("render_image_cropper_component", cg.__all__)
        self.assertTrue(callable(cg.render_image_cropper_component))
        self.assertEqual(cg.render_image_cropper_component(), self.code)

    def test_diff_invariance(self) -> None:
        """Component code must be 100% diff-invariant across varying IR descriptions."""
        adapter = NextjsWebAdapter()
        ir1 = self.ir
        ir2 = dataclasses.replace(self.ir, description="Modified IR for image cropper invariance")

        file1 = adapter.generate(ir1).get("components/image-cropper.tsx")
        file2 = adapter.generate(ir2).get("components/image-cropper.tsx")

        self.assertIsNotNone(file1)
        self.assertIsNotNone(file2)
        self.assertEqual(file1.content, file2.content)


if __name__ == "__main__":
    unittest.main()
