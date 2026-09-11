"""
R-388: Accessible Futuristic Reusable PDF & Document Viewer Suite
Unit tests for render_pdf_viewer_component and the generated components/pdf-viewer.tsx.
"""
from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_pdf_viewer_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter, _PDF_VIEWER_COMPONENT


class TestPdfViewerComponent(unittest.TestCase):
    """Test suite for components/pdf-viewer.tsx codegen (R-388)."""

    def setUp(self) -> None:
        self.code = render_pdf_viewer_component()
        self.ir = example_ir("rideshare-favourites")
        project = NextjsWebAdapter().generate(self.ir)
        self.file = project.get("components/pdf-viewer.tsx")

    # ------------------------------------------------------------------
    # 1. File is generated at the correct path
    # ------------------------------------------------------------------
    def test_file_generated(self):
        """components/pdf-viewer.tsx must be emitted by NextjsWebAdapter."""
        ir = example_ir("minimal-blog")
        project = NextjsWebAdapter().generate(ir)
        paths = project.paths()
        self.assertIn("components/pdf-viewer.tsx", paths)

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
            "PdfViewerVariant",
            "PdfViewerSize",
            "PdfViewMode",
            "PdfPage",
            "PdfViewerHandle",
            "PdfThumbnailProps",
            "PdfToolbarProps",
            "PdfPageCanvasProps",
            "PdfViewerProps",
        ]
        for t in required_types:
            self.assertIn(t, self.code, f"Missing TypeScript type: {t}")

    # ------------------------------------------------------------------
    # 4. All 4 visual variants present
    # ------------------------------------------------------------------
    def test_variants_present(self):
        """All four visual variants must be implemented: default, card, glass, neon."""
        for variant in ("default", "card", "glass", "neon"):
            self.assertIn(f"'{variant}'", self.code, f"Missing variant: {variant}")

    # ------------------------------------------------------------------
    # 5. All 3 size scales present
    # ------------------------------------------------------------------
    def test_sizes_present(self):
        """All three size scales must be configured: sm, md, lg."""
        for size in ("sm", "md", "lg"):
            self.assertIn(f"'{size}'", self.code, f"Missing size: {size}")

    # ------------------------------------------------------------------
    # 6. Compound and semantic alias exports present
    # ------------------------------------------------------------------
    def test_compound_exports(self):
        """All compound and semantic alias exports must be present."""
        exports = [
            "export const PdfViewer",
            "export const DocumentViewer",
            "export const FileViewer",
            "export const PdfThumbnails",
            "export const PdfToolbar",
            "export const PdfPageCanvas",
        ]
        for exp in exports:
            self.assertIn(exp, self.code, f"Missing export: {exp}")

    # ------------------------------------------------------------------
    # 7. Default export present
    # ------------------------------------------------------------------
    def test_default_export(self):
        """A default export must be present."""
        self.assertIn("export default PdfViewerComponent", self.code)

    # ------------------------------------------------------------------
    # 8. WAI-ARIA 1.2 semantics present
    # ------------------------------------------------------------------
    def test_aria_semantics(self):
        """WAI-ARIA 1.2 region & toolbar semantics must be present."""
        for attr in ('role="region"', 'aria-label="Document Viewer"', 'role="toolbar"'):
            self.assertIn(attr, self.code, f"Missing ARIA attribute: {attr}")

    # ------------------------------------------------------------------
    # 9. forwardRef and useImperativeHandle present
    # ------------------------------------------------------------------
    def test_forward_ref_and_imperative_handle(self):
        """forwardRef and useImperativeHandle must be used for the imperative handle API."""
        self.assertIn("forwardRef", self.code)
        self.assertIn("useImperativeHandle", self.code)

    # ------------------------------------------------------------------
    # 10. View modes supported (single and continuous)
    # ------------------------------------------------------------------
    def test_view_modes_present(self):
        """Single and continuous view modes must be supported."""
        for mode in ("'single'", "'continuous'"):
            self.assertIn(mode, self.code, f"Missing view mode: {mode}")

    # ------------------------------------------------------------------
    # 11. Pagination navigation helpers present
    # ------------------------------------------------------------------
    def test_pagination_helpers(self):
        """Pagination methods and indicators must be present."""
        for helper in ("nextPage", "prevPage", "goToPage", "totalPages", "currentPage"):
            self.assertIn(helper, self.code, f"Missing helper: {helper}")

    # ------------------------------------------------------------------
    # 12. Imperative handle methods present
    # ------------------------------------------------------------------
    def test_imperative_handle_methods(self):
        """Imperative handle must expose nextPage, prevPage, goToPage, zoomIn, zoomOut, setZoom, rotate, search."""
        methods = [
            "nextPage",
            "prevPage",
            "goToPage",
            "zoomIn",
            "zoomOut",
            "setZoom",
            "rotate",
            "search",
            "getCurrentPage",
            "getTotalPages",
        ]
        for m in methods:
            self.assertIn(m, self.code, f"Missing imperative handle method: {m}")

    # ------------------------------------------------------------------
    # 13. 'use client' directive present
    # ------------------------------------------------------------------
    def test_use_client_directive(self):
        """'use client' must be the first statement for Next.js App Router."""
        self.assertTrue(
            self.code.strip().startswith("'use client'") or self.code.strip().startswith('"use client"'),
            "Missing 'use client' directive",
        )

    # ------------------------------------------------------------------
    # 14. Explicit displayName on compound exports
    # ------------------------------------------------------------------
    def test_display_names(self):
        """All compound exports must have explicit displayName properties."""
        names = [
            'PdfViewer.displayName = "PdfViewer"',
            'DocumentViewer.displayName = "DocumentViewer"',
            'FileViewer.displayName = "FileViewer"',
            'PdfThumbnails.displayName = "PdfThumbnails"',
            'PdfToolbar.displayName = "PdfToolbar"',
            'PdfPageCanvas.displayName = "PdfPageCanvas"',
        ]
        for name in names:
            single_quote = name.replace('"', "'")
            self.assertTrue(
                name in self.code or single_quote in self.code,
                f"Missing displayName: {name}",
            )

    # ------------------------------------------------------------------
    # 15. Diff invariance across ir.description
    # ------------------------------------------------------------------
    def test_diff_invariance_across_description(self):
        """Generated viewer content must be identical regardless of ir.description."""
        ir1 = example_ir("rideshare-favourites")
        ir2 = example_ir("minimal-blog")
        proj1 = NextjsWebAdapter().generate(ir1)
        proj2 = NextjsWebAdapter().generate(ir2)
        self.assertEqual(
            proj1.get("components/pdf-viewer.tsx").content,
            proj2.get("components/pdf-viewer.tsx").content,
        )

    # ------------------------------------------------------------------
    # 16. Package codegen exports render_pdf_viewer_component
    # ------------------------------------------------------------------
    def test_package_codegen_exports(self):
        """omnistackai_agent_engine.codegen exposes render_pdf_viewer_component."""
        self.assertTrue(hasattr(cg, "render_pdf_viewer_component"))
        self.assertIn("render_pdf_viewer_component", cg.__all__)
        self.assertEqual(cg.render_pdf_viewer_component(), _PDF_VIEWER_COMPONENT)

    # ------------------------------------------------------------------
    # 17. Search highlighting and match navigation
    # ------------------------------------------------------------------
    def test_search_and_highlighting(self):
        """Search query, match count, and text highlight rendering must be present."""
        self.assertIn("searchQuery", self.code)
        self.assertIn("matchCount", self.code)
        self.assertIn("renderHighlighted", self.code)
