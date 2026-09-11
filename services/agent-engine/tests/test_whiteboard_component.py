"""
R-391: Accessible Futuristic Reusable Whiteboard & Collaborative Canvas Suite
Unit tests for render_whiteboard_component and the generated components/whiteboard.tsx.
"""
from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_whiteboard_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter, _WHITEBOARD_COMPONENT


class TestWhiteboardComponent(unittest.TestCase):
    """Test suite for components/whiteboard.tsx codegen (R-391)."""

    def setUp(self) -> None:
        self.code = render_whiteboard_component()
        self.ir = example_ir("rideshare-favourites")
        project = NextjsWebAdapter().generate(self.ir)
        self.file = project.get("components/whiteboard.tsx")

    # ------------------------------------------------------------------
    # 1. File is generated at the correct path
    # ------------------------------------------------------------------
    def test_file_generated(self):
        """components/whiteboard.tsx must be emitted by NextjsWebAdapter."""
        ir = example_ir("minimal-blog")
        project = NextjsWebAdapter().generate(ir)
        paths = project.paths()
        self.assertIn("components/whiteboard.tsx", paths)

    # ------------------------------------------------------------------
    # 2. Zero external npm dependencies (only 'react' imports allowed)
    # ------------------------------------------------------------------
    def test_zero_runtime_dependencies(self):
        """Only imports from 'react' are allowed — 0 external npm dependencies."""
        imports = re.findall(r'from\s+[\'"]([^\'"]+)[\'"]', self.code)
        for pkg in imports:
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Forbidden external import detected: {pkg}",
            )

    # ------------------------------------------------------------------
    # 3. TypeScript type interfaces present
    # ------------------------------------------------------------------
    def test_typescript_types_present(self):
        """All required TypeScript type exports must be present."""
        required_types = [
            "WhiteboardVariant",
            "WhiteboardSize",
            "WhiteboardTool",
            "WhiteboardPoint",
            "WhiteboardElement",
            "WhiteboardHandle",
            "WhiteboardToolbarProps",
            "WhiteboardProps",
        ]
        for t in required_types:
            self.assertIn(t, self.code, f"Missing TypeScript type: {t}")

    # ------------------------------------------------------------------
    # 4. Visual variants supported
    # ------------------------------------------------------------------
    def test_variants_present(self):
        """Must define all 4 required visual styling variants: default, card, glass, neon."""
        for variant in ["default", "card", "glass", "neon"]:
            self.assertIn(f"'{variant}'", self.code, f"Missing variant: {variant}")

    # ------------------------------------------------------------------
    # 5. Size scales supported
    # ------------------------------------------------------------------
    def test_sizes_present(self):
        """Must define sm, md, lg size scales."""
        for size in ["sm", "md", "lg"]:
            self.assertIn(f"'{size}'", self.code, f"Missing size scale: {size}")

    # ------------------------------------------------------------------
    # 6. Tools supported
    # ------------------------------------------------------------------
    def test_tools_present(self):
        """Must support select, pencil, line, arrow, rectangle, circle, text, eraser."""
        tools = ["select", "pencil", "line", "arrow", "rectangle", "circle", "text", "eraser"]
        for t in tools:
            self.assertIn(f"'{t}'", self.code, f"Missing tool: {t}")

    # ------------------------------------------------------------------
    # 7. Preset colors palette
    # ------------------------------------------------------------------
    def test_preset_colors_present(self):
        """Must define PRESET_COLORS palette."""
        self.assertIn("PRESET_COLORS", self.code)
        self.assertIn("#f8fafc", self.code)
        self.assertIn("#06b6d4", self.code)

    # ------------------------------------------------------------------
    # 8. Stroke widths selector
    # ------------------------------------------------------------------
    def test_stroke_widths_present(self):
        """Must define STROKE_WIDTHS selector."""
        self.assertIn("STROKE_WIDTHS", self.code)
        self.assertIn("onSelectStrokeWidth", self.code)

    # ------------------------------------------------------------------
    # 9. Canvas rendering logic and shape handling
    # ------------------------------------------------------------------
    def test_canvas_rendering_logic(self):
        """Must implement HTML5 canvas rendering and shape paths."""
        self.assertIn("canvasRef", self.code)
        self.assertIn("redrawCanvas", self.code)
        self.assertIn("gridBackground", self.code)
        self.assertIn("screenToCanvas", self.code)

    # ------------------------------------------------------------------
    # 10. Undo and redo history stack
    # ------------------------------------------------------------------
    def test_undo_redo_history(self):
        """Must implement multi-level undo/redo history tracking."""
        self.assertIn("pushHistory", self.code)
        self.assertIn("historyIndex", self.code)
        self.assertIn("canUndo", self.code)
        self.assertIn("canRedo", self.code)

    # ------------------------------------------------------------------
    # 11. Pan and zoom transform
    # ------------------------------------------------------------------
    def test_zoom_and_pan(self):
        """Must implement canvas pan & zoom controls."""
        self.assertIn("zoom", self.code)
        self.assertIn("pan", self.code)
        self.assertIn("onZoomIn", self.code)
        self.assertIn("onZoomOut", self.code)
        self.assertIn("resetZoom", self.code)

    # ------------------------------------------------------------------
    # 12. Export PNG, SVG, and JSON capabilities
    # ------------------------------------------------------------------
    def test_export_functions(self):
        """Must implement PNG, SVG, and JSON export methods."""
        self.assertIn("exportPng", self.code)
        self.assertIn("exportSvg", self.code)
        self.assertIn("exportJson", self.code)
        self.assertIn("loadJson", self.code)

    # ------------------------------------------------------------------
    # 13. forwardRef and WhiteboardHandle exposed
    # ------------------------------------------------------------------
    def test_forward_ref_and_imperative_handle(self):
        """Must wrap component in forwardRef and expose useImperativeHandle with WhiteboardHandle."""
        self.assertIn("forwardRef", self.code)
        self.assertIn("useImperativeHandle", self.code)
        self.assertIn("getElements", self.code)
        self.assertIn("setColor", self.code)
        self.assertIn("setTool", self.code)

    # ------------------------------------------------------------------
    # 14. Explicit displayName defined on compound exports
    # ------------------------------------------------------------------
    def test_display_names_defined(self):
        """Must define explicit displayName on all compound and alias exports."""
        self.assertIn("WhiteboardComponent.displayName = 'Whiteboard'", self.code)
        self.assertIn("WhiteboardToolbar.displayName = 'WhiteboardToolbar'", self.code)
        self.assertIn("Whiteboard.displayName = 'Whiteboard'", self.code)
        self.assertIn("DrawingCanvas.displayName = 'DrawingCanvas'", self.code)
        self.assertIn("SketchBoard.displayName = 'SketchBoard'", self.code)
        self.assertIn("CollaborativeCanvas.displayName = 'CollaborativeCanvas'", self.code)

    # ------------------------------------------------------------------
    # 15. Compound and semantic alias exports
    # ------------------------------------------------------------------
    def test_compound_and_alias_exports(self):
        """Must export Whiteboard, DrawingCanvas, SketchBoard, CollaborativeCanvas, and default export."""
        self.assertIn("export const Whiteboard =", self.code)
        self.assertIn("export const DrawingCanvas =", self.code)
        self.assertIn("export const SketchBoard =", self.code)
        self.assertIn("export const CollaborativeCanvas =", self.code)
        self.assertIn("export const WhiteboardToolbar", self.code)
        self.assertIn("export default WhiteboardComponent", self.code)

    # ------------------------------------------------------------------
    # 16. WAI-ARIA accessibility semantics
    # ------------------------------------------------------------------
    def test_wai_aria_accessibility(self):
        """Must include appropriate WAI-ARIA application and toolbar roles."""
        self.assertIn('role="application"', self.code)
        self.assertIn('aria-label="Whiteboard Canvas"', self.code)
        self.assertIn('role="toolbar"', self.code)

    # ------------------------------------------------------------------
    # 17. Snapshot diff invariance and codegen export
    # ------------------------------------------------------------------
    def test_diff_invariance_and_codegen_export(self):
        """render_whiteboard_component must be exported and output diff-invariant."""
        self.assertTrue(hasattr(cg, "render_whiteboard_component"))
        code = cg.render_whiteboard_component()
        self.assertIsInstance(code, str)
        self.assertIn("'use client'", code)

        ir1 = example_ir("rideshare-favourites")
        ir2 = example_ir("minimal-blog")
        p1 = NextjsWebAdapter().generate(ir1)
        p2 = NextjsWebAdapter().generate(ir2)
        f1 = p1.get("components/whiteboard.tsx")
        f2 = p2.get("components/whiteboard.tsx")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)


if __name__ == "__main__":
    unittest.main()
