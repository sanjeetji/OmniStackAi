"""
R-386: Accessible Futuristic Reusable File Explorer & Storage Browser Suite
Unit tests for render_file_explorer_component and the generated components/file-explorer.tsx.
"""
from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_file_explorer_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter, _FILE_EXPLORER_COMPONENT


class TestFileExplorerComponent(unittest.TestCase):
    """Test suite for components/file-explorer.tsx codegen (R-386)."""

    def setUp(self) -> None:
        self.code = render_file_explorer_component()
        self.ir = example_ir("rideshare-favourites")
        project = NextjsWebAdapter().generate(self.ir)
        self.file = project.get("components/file-explorer.tsx")

    # ------------------------------------------------------------------
    # 1. File is generated at the correct path
    # ------------------------------------------------------------------
    def test_file_generated(self):
        """components/file-explorer.tsx must be emitted by NextjsWebAdapter."""
        ir = example_ir("minimal-blog")
        project = NextjsWebAdapter().generate(ir)
        paths = project.paths()
        self.assertIn("components/file-explorer.tsx", paths)

    # ------------------------------------------------------------------
    # 2. Zero external npm dependencies (only 'react' imports allowed)
    # ------------------------------------------------------------------
    def test_zero_runtime_dependencies(self):
        """Only imports from 'react' are allowed — 0 external npm dependencies."""
        imports = re.findall(r'from\s+"([^"]+)"', self.code)
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
            "FileExplorerVariant",
            "FileExplorerSize",
            "FileExplorerViewMode",
            "FileItemType",
            "FileItem",
            "FileExplorerHandle",
            "FileBreadcrumbsProps",
            "FileDetailsProps",
            "FileExplorerProps",
        ]
        for t in required_types:
            self.assertIn(t, self.code, f"Missing TypeScript type: {t}")

    # ------------------------------------------------------------------
    # 4. All 4 visual variants present
    # ------------------------------------------------------------------
    def test_variants_present(self):
        """All four visual variants must be implemented: default, card, glass, neon."""
        for variant in ("default", "card", "glass", "neon"):
            self.assertIn(f'case "{variant}"', self.code, f"Missing variant: {variant}")

    # ------------------------------------------------------------------
    # 5. All 3 size scales present
    # ------------------------------------------------------------------
    def test_sizes_present(self):
        """All three size scales must be configured: sm, md, lg."""
        for size in ("sm", "md", "lg"):
            self.assertIn(f'case "{size}"', self.code, f"Missing size: {size}")

    # ------------------------------------------------------------------
    # 6. Compound and semantic alias exports present
    # ------------------------------------------------------------------
    def test_compound_exports(self):
        """All compound and semantic alias exports must be present."""
        exports = [
            "export const FileExplorer",
            "export const FileManager",
            "export const FileBrowser",
            "export const DocumentManager",
            "export const FileGrid",
            "export const FileList",
            "export const FileDetailsPanel",
            "export const FileBreadcrumbs",
        ]
        for exp in exports:
            self.assertIn(exp, self.code, f"Missing export: {exp}")

    # ------------------------------------------------------------------
    # 7. Default export present
    # ------------------------------------------------------------------
    def test_default_export(self):
        """A default export must be present."""
        self.assertIn("export default FileExplorerComponent", self.code)

    # ------------------------------------------------------------------
    # 8. WAI-ARIA 1.2 semantics present
    # ------------------------------------------------------------------
    def test_aria_semantics(self):
        """WAI-ARIA 1.2 grid, region & selected semantics must be present."""
        for attr in ('role="region"', 'aria-label="File Explorer"', 'role="grid"', 'role="row"', 'aria-selected'):
            self.assertIn(attr, self.code, f"Missing ARIA attribute: {attr}")

    # ------------------------------------------------------------------
    # 9. forwardRef and useImperativeHandle present
    # ------------------------------------------------------------------
    def test_forward_ref_and_imperative_handle(self):
        """forwardRef and useImperativeHandle must be used for the imperative handle API."""
        self.assertIn("forwardRef", self.code)
        self.assertIn("useImperativeHandle", self.code)

    # ------------------------------------------------------------------
    # 10. View modes supported
    # ------------------------------------------------------------------
    def test_view_modes_present(self):
        """Dual view modes grid and list must be supported."""
        for mode in ('"grid"', '"list"'):
            self.assertIn(mode, self.code, f"Missing view mode: {mode}")

    # ------------------------------------------------------------------
    # 11. File item types supported
    # ------------------------------------------------------------------
    def test_file_item_types(self):
        """File types folder, file, image, video, audio, code, archive, pdf must be handled."""
        for ftype in ('"folder"', '"file"', '"image"', '"video"', '"audio"', '"code"', '"archive"', '"pdf"'):
            self.assertIn(ftype, self.code, f"Missing file type: {ftype}")

    # ------------------------------------------------------------------
    # 12. Imperative handle methods present
    # ------------------------------------------------------------------
    def test_imperative_handle_methods(self):
        """Imperative handle must expose selectFile, clearSelection, navigateToFolder, getCurrentFolderId, getSelectedFiles."""
        for method in ("selectFile", "clearSelection", "navigateToFolder", "getCurrentFolderId", "getSelectedFiles"):
            self.assertIn(method, self.code, f"Missing imperative handle method: {method}")

    # ------------------------------------------------------------------
    # 13. Formatting helpers present
    # ------------------------------------------------------------------
    def test_formatting_helpers(self):
        """formatFileSize and formatDate helpers must be present."""
        self.assertIn("formatFileSize", self.code)
        self.assertIn("formatDate", self.code)

    # ------------------------------------------------------------------
    # 14. Exported in codegen __all__
    # ------------------------------------------------------------------
    def test_package_codegen_exports(self):
        """omnistackai_agent_engine.codegen exposes render_file_explorer_component."""
        self.assertTrue(hasattr(cg, "render_file_explorer_component"))
        self.assertIn("render_file_explorer_component", cg.__all__)

    # ------------------------------------------------------------------
    # 15. 'use client' directive present
    # ------------------------------------------------------------------
    def test_use_client_directive(self):
        """'use client' must be the first statement for Next.js App Router."""
        self.assertTrue(
            self.code.startswith('"use client"') or self.code.startswith("'use client'"),
            "Component file must start with 'use client' directive",
        )

    # ------------------------------------------------------------------
    # 16. Display names present on exports
    # ------------------------------------------------------------------
    def test_display_names(self):
        """All compound exports must have explicit displayName properties."""
        for name in ("FileExplorer", "FileManager", "FileBrowser", "DocumentManager", "FileGrid", "FileList", "FileDetailsPanel", "FileBreadcrumbs"):
            self.assertIn(f'{name}.displayName = "{name}"', self.code, f"Missing displayName for {name}")

    # ------------------------------------------------------------------
    # 17. 100% diff-invariance across ir.description
    # ------------------------------------------------------------------
    def test_diff_invariance_across_description(self):
        """Generated file explorer content must be identical regardless of ir.description."""
        ir_a = example_ir("rideshare-favourites")
        ir_b = example_ir("minimal-blog")
        project_a = NextjsWebAdapter().generate(ir_a)
        project_b = NextjsWebAdapter().generate(ir_b)
        content_a = project_a.get("components/file-explorer.tsx")
        content_b = project_b.get("components/file-explorer.tsx")
        self.assertIsNotNone(content_a)
        self.assertIsNotNone(content_b)
        self.assertEqual(
            content_a.content,
            content_b.content,
            "components/file-explorer.tsx must be diff-invariant across ir.description changes",
        )


if __name__ == "__main__":
    unittest.main()
