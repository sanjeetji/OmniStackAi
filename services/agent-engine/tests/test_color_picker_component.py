"""Tests for Task R-345: Generated Accessible Futuristic Reusable Color Picker & Palette Swatch Component.

Verifies that NextjsWebAdapter emits an accessible, futuristic, reusable Color Picker & Palette Swatch
component suite (apps/web/components/color-picker.tsx) supporting:
- Compound suite (ColorPicker, ColorPicker.Area, ColorPicker.HueSlider, ColorPicker.AlphaSlider,
  ColorPicker.Swatches, ColorPicker.Inputs, ColorPicker.EyeDropper)
- 4 futuristic visual variants ("neon", "glass", "bordered", "minimal")
- 3 size presets ("sm", "md", "lg")
- Pure mathematical color models (Hex, RGB, HSL, HSV) without external packages
- Interactive 2D saturation/value area and 1D hue & alpha sliders
- Full keyboard navigation for area, sliders, and swatches
- Full WAI-ARIA accessibility semantics (role="slider", role="listbox", role="option", aria-label, etc.)
- Format switcher between HEX, RGB, and HSL
- Preset swatches with keyboard selection
- Native EyeDropper API integration with fallback
- 100% diff-invariance across ir.description changes
- Zero external runtime dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_color_picker_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class ColorPickerComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the ColorPicker component."""

    def setUp(self) -> None:
        self.code = render_color_picker_component()
        self.ir = example_ir("rideshare-favourites")

    def test_color_picker_component_is_client_component(self) -> None:
        """The ColorPicker component must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "ColorPicker must have 'use client' as the first statement.",
        )

    def test_color_picker_component_exports_types(self) -> None:
        """Verify export of TypeScript interfaces and union types."""
        self.assertIn("export type ColorPickerFormat", self.code)
        self.assertIn('"hex"', self.code)
        self.assertIn('"rgb"', self.code)
        self.assertIn('"hsl"', self.code)
        self.assertIn("export type ColorPickerVariant", self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"bordered"', self.code)
        self.assertIn('"minimal"', self.code)
        self.assertIn("export type ColorPickerSize", self.code)
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)
        self.assertIn("export interface ColorSwatch", self.code)
        self.assertIn("export interface ColorPickerProps", self.code)
        self.assertIn("export interface ColorPickerContextValue", self.code)

    def test_color_picker_component_exports_compound(self) -> None:
        """Verify ColorPicker compound component and subcomponents."""
        self.assertIn("export const ColorPicker =", self.code)
        self.assertIn("ColorPicker.Area = ColorArea", self.code)
        self.assertIn("ColorPicker.HueSlider = HueSlider", self.code)
        self.assertIn("ColorPicker.AlphaSlider = AlphaSlider", self.code)
        self.assertIn("ColorPicker.Swatches = ColorSwatches", self.code)
        self.assertIn("ColorPicker.Inputs = ColorInputs", self.code)
        self.assertIn("ColorPicker.EyeDropper = ColorEyeDropper", self.code)
        self.assertIn("export default ColorPicker;", self.code)

    def test_color_picker_pure_math_conversions(self) -> None:
        """Verify presence of pure math color conversion algorithms."""
        self.assertIn("export function hsvToRgb", self.code)
        self.assertIn("export function rgbToHsv", self.code)
        self.assertIn("export function rgbToHsl", self.code)
        self.assertIn("export function parseHexColor", self.code)
        self.assertIn("export function toHex", self.code)

    def test_color_picker_zero_external_dependencies(self) -> None:
        """ColorPicker uses only React; zero external package imports."""
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
                f"Unexpected external import found in ColorPicker: {line}",
            )

    def test_color_picker_wai_aria_slider_semantics(self) -> None:
        """Verify WAI-ARIA slider roles and attributes for spectrum and sliders."""
        self.assertIn('role="slider"', self.code)
        self.assertIn('aria-label="Color saturation and brightness"', self.code)
        self.assertIn('aria-label="Hue"', self.code)
        self.assertIn('aria-label="Alpha opacity"', self.code)
        self.assertIn("aria-valuemin=", self.code)
        self.assertIn("aria-valuemax=", self.code)
        self.assertIn("aria-valuenow=", self.code)
        self.assertIn("aria-valuetext=", self.code)

    def test_color_picker_wai_aria_swatches_listbox(self) -> None:
        """Verify WAI-ARIA listbox and option semantics for preset swatches."""
        self.assertIn('role="listbox"', self.code)
        self.assertIn('aria-label="Preset color swatches"', self.code)
        self.assertIn('role="option"', self.code)
        self.assertIn("aria-selected=", self.code)

    def test_color_picker_keyboard_navigation(self) -> None:
        """Verify keyboard adjustment on spectrum area and 1D sliders."""
        self.assertIn('e.key === "ArrowRight"', self.code)
        self.assertIn('e.key === "ArrowLeft"', self.code)
        self.assertIn('e.key === "ArrowUp"', self.code)
        self.assertIn('e.key === "ArrowDown"', self.code)
        self.assertIn('e.key === "Home"', self.code)
        self.assertIn('e.key === "End"', self.code)
        self.assertIn("e.shiftKey", self.code)

    def test_color_picker_pointer_and_touch_dragging(self) -> None:
        """Verify pointer capture and touch-action handling."""
        self.assertIn("setPointerCapture", self.code)
        self.assertIn("releasePointerCapture", self.code)
        self.assertIn('touchAction: "none"', self.code)
        self.assertIn("onPointerDown=", self.code)
        self.assertIn("onPointerMove=", self.code)
        self.assertIn("onPointerUp=", self.code)

    def test_color_picker_eyedropper_integration(self) -> None:
        """Verify native EyeDropper API check and graceful fallback."""
        self.assertIn('"EyeDropper" in window', self.code)
        self.assertIn("new window.EyeDropper()", self.code)
        self.assertIn("eyeDropper.open()", self.code)
        self.assertIn("export function EyeDropperIcon", self.code)

    def test_color_picker_format_inputs_switcher(self) -> None:
        """Verify inputs subcomponent with hex, rgb, and hsl format switching."""
        self.assertIn("ColorInputs", self.code)
        self.assertIn("toggleFormat", self.code)
        self.assertIn('format === "hex"', self.code)
        self.assertIn('format === "rgb"', self.code)
        self.assertIn('aria-label="Hex color value"', self.code)

    def test_color_picker_variants_and_sizes(self) -> None:
        """Verify futuristic visual variants and size dimensions."""
        self.assertIn("omnistack-color-picker-${variant}", self.code)
        self.assertIn("widthMap", self.code)

    def test_color_picker_package_codegen_exports_render(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_color_picker_component."""
        self.assertTrue(hasattr(cg, "render_color_picker_component"))
        self.assertIn("render_color_picker_component", cg.__all__)
        fn = getattr(cg, "render_color_picker_component")
        self.assertTrue(callable(fn))
        code = fn()
        self.assertTrue(isinstance(code, str) and len(code) > 200)

    def test_adapter_emits_color_picker_file(self) -> None:
        """NextjsWebAdapter emits components/color-picker.tsx in generated project."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/color-picker.tsx")
        self.assertIsNotNone(f, "components/color-picker.tsx must be generated")
        self.assertEqual(f.content, self.code)


    def test_color_picker_diff_invariant(self) -> None:
        """ColorPicker output is 100% diff-invariant across ir.description changes."""
        adapter = NextjsWebAdapter()
        project1 = adapter.generate(self.ir)
        ir2 = dataclasses.replace(
            self.ir, description="Completely changed description for diff test."
        )
        project2 = adapter.generate(ir2)
        cp1 = project1.get("components/color-picker.tsx").content
        cp2 = project2.get("components/color-picker.tsx").content
        self.assertEqual(
            cp1,
            cp2,
            "components/color-picker.tsx must be 100% diff-invariant across ir.description",
        )


if __name__ == "__main__":
    unittest.main()
