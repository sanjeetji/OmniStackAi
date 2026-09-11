"""Tests for the Accessible Futuristic Digital Signature Pad & Drawing Canvas Primitive codegen (R-372).

Verifies:
1. Zero runtime dependencies (pure React and HTML5 Canvas API).
2. "use client" directive present.
3. React forwardRef and explicit displayName across compound exports.
4. Exported canonical TypeScript types & interfaces.
5. Compound and semantic alias exports (SignaturePad, SignatureCanvas, DrawingPad, default).
6. 4 visual styling variants ("default", "card", "glass", "neon").
7. 3 size presets ("sm", "md", "lg").
8. WAI-ARIA accessibility semantics (role="application", aria-roledescription="drawing canvas", aria-label).
9. Native Canvas pointer events (pointerdown, pointermove, pointerup, pointerleave, touch-action: none).
10. High-DPI Retina devicePixelRatio scaling support.
11. Smooth quadratic bezier curve stroke interpolation.
12. Multi-level stroke undo, redo, and clear stack.
13. Vector SVG export generation (toSVG).
14. Signing guide line with customizable text and anchor mark.
15. Native HTML form submission integration via hidden input.
16. NextjsWebAdapter emits components/signature-pad.tsx and codegen package exports render_signature_pad_component.
17. 100% diff-invariance across ir.description changes.
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_signature_pad_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TestSignaturePadComponent(unittest.TestCase):
    """Test suite for components/signature-pad.tsx codegen."""

    def setUp(self) -> None:
        self.code = render_signature_pad_component()
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
        self.assertIn('SignaturePad.displayName = "SignaturePad"', self.code)
        self.assertIn('SignatureCanvas.displayName = "SignatureCanvas"', self.code)
        self.assertIn('DrawingPad.displayName = "DrawingPad"', self.code)

    def test_exported_canonical_types(self) -> None:
        """Canonical TypeScript types must be exported."""
        self.assertIn("export type SignaturePadVariant =", self.code)
        self.assertIn("export type SignaturePadSize =", self.code)
        self.assertIn("export interface SignaturePoint", self.code)
        self.assertIn("export interface SignatureStroke", self.code)
        self.assertIn("export interface SignaturePadHandle", self.code)
        self.assertIn("export interface SignaturePadProps", self.code)

    def test_compound_and_semantic_exports(self) -> None:
        """Must export SignaturePad, SignatureCanvas, DrawingPad, and default export."""
        self.assertIn("export const SignaturePad =", self.code)
        self.assertIn("export const SignatureCanvas =", self.code)
        self.assertIn("export const DrawingPad =", self.code)
        self.assertIn("export default SignaturePad;", self.code)

    def test_visual_variants(self) -> None:
        """Must support 4 visual styling variants."""
        for variant in ["default", "card", "glass", "neon"]:
            self.assertIn(f'"{variant}"', self.code)
        self.assertIn("backdrop-blur-md", self.code)
        self.assertIn("border-cyan-500", self.code)

    def test_size_presets(self) -> None:
        """Must define sm (140), md (200), lg (280) size presets."""
        self.assertIn("sm: 140", self.code)
        self.assertIn("md: 200", self.code)
        self.assertIn("lg: 280", self.code)

    def test_wai_aria_semantics(self) -> None:
        """Must contain WAI-ARIA application semantics for accessibility."""
        self.assertIn('role="application"', self.code)
        self.assertIn('aria-label="Signature Pad"', self.code)
        self.assertIn('aria-roledescription="drawing canvas"', self.code)
        self.assertIn('aria-label="Signature drawing area"', self.code)

    def test_canvas_pointer_events(self) -> None:
        """Must use pointer events with touchAction: 'none' for stylus/touch/mouse drawing."""
        self.assertIn("onPointerDown={handlePointerDown}", self.code)
        self.assertIn("onPointerMove={handlePointerMove}", self.code)
        self.assertIn("onPointerUp={handlePointerUp}", self.code)
        self.assertIn('touchAction: "none"', self.code)

    def test_retina_dpr_scaling(self) -> None:
        """Must handle devicePixelRatio scaling for crisp Retina rendering."""
        self.assertIn("window.devicePixelRatio", self.code)
        self.assertIn("ctx.scale(dpr, dpr)", self.code)

    def test_bezier_interpolation(self) -> None:
        """Must use quadratic bezier curves for stroke smoothing."""
        self.assertIn("quadraticCurveTo", self.code)
        self.assertIn("stroke.points", self.code)

    def test_undo_redo_and_clear_stack(self) -> None:
        """Must implement stroke history stack with undo, redo, and clear capabilities."""
        self.assertIn("redoHistory", self.code)
        self.assertIn("handleUndo", self.code)
        self.assertIn("handleRedo", self.code)
        self.assertIn("handleClear", self.code)

    def test_svg_export_method(self) -> None:
        """Must expose vector SVG generation toSVG() on the component ref."""
        self.assertIn("toSVG", self.code)
        self.assertIn("<svg xmlns=", self.code)
        self.assertIn("<path d=", self.code)

    def test_guide_line_support(self) -> None:
        """Must provide signature guide line with dashed styling and text."""
        self.assertIn("setLineDash([4, 4])", self.code)
        self.assertIn("guideLineText", self.code)
        self.assertIn("Sign on line above", self.code)

    def test_hidden_input_form_integration(self) -> None:
        """Must render hidden input when name prop is supplied."""
        self.assertIn('<input type="hidden" name={name} value={dataUrl}', self.code)

    def test_nextjs_adapter_and_codegen_exports(self) -> None:
        """NextjsWebAdapter emits components/signature-pad.tsx and codegen exposes render function."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        sig_file = project.get("components/signature-pad.tsx")
        self.assertIsNotNone(sig_file, "components/signature-pad.tsx must be generated")
        self.assertEqual(sig_file.content, self.code)

        self.assertIn("render_signature_pad_component", cg.__all__)
        self.assertTrue(callable(cg.render_signature_pad_component))
        self.assertEqual(cg.render_signature_pad_component(), self.code)

    def test_diff_invariance(self) -> None:
        """Component code must be 100% diff-invariant across varying IR descriptions."""
        adapter = NextjsWebAdapter()
        ir1 = self.ir
        ir2 = dataclasses.replace(self.ir, description="Modified IR for signature pad invariance")

        proj1 = adapter.generate(ir1)
        proj2 = adapter.generate(ir2)

        file1 = proj1.get("components/signature-pad.tsx")
        file2 = proj2.get("components/signature-pad.tsx")

        self.assertIsNotNone(file1)
        self.assertIsNotNone(file2)
        self.assertEqual(file1.content, file2.content)


if __name__ == "__main__":
    unittest.main()
