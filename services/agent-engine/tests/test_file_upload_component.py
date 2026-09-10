"""Tests for Task R-335: Generated Accessible Reusable File Upload / Dropzone Component.

Verifies that NextjsWebAdapter emits an accessible, reusable FileUpload component
(apps/web/components/file-upload.tsx) supporting:
- FileUploadStatus, FileUploadVariant, FileEntry, FileUploadProps types
- Drag-and-drop zone with dragover/dragleave/drop handlers
- Click-to-browse via hidden <input type="file">
- accept, multiple, maxSize, maxFiles constraints with inline validation
- File list preview with formatBytes size, remove buttons, upload progressbar
- Avatar circular variant with CameraIcon overlay
- Compact variant
- WAI-ARIA: role="button", aria-label, aria-describedby, aria-live="polite", aria-disabled
- Keyboard: Enter / Space opens picker
- 100% diff-invariance across ir.description changes
- Zero external dependencies
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_file_upload_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class FileUploadComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.code = render_file_upload_component()

    def test_file_upload_is_client_component(self) -> None:
        """FileUpload component specifies 'use client' directive."""
        self.assertTrue(self.code.startswith('"use client";'))

    def test_file_upload_exports_types(self) -> None:
        """FileUpload exports all required types."""
        self.assertIn(
            'export type FileUploadStatus = "idle" | "dragging" | "uploading" | "success" | "error";',
            self.code,
        )
        self.assertIn(
            'export type FileUploadVariant = "default" | "compact" | "avatar";',
            self.code,
        )
        self.assertIn("export interface FileEntry", self.code)
        self.assertIn("export interface FileUploadProps", self.code)

    def test_file_upload_exports_main_function(self) -> None:
        """FileUpload exports FileUpload function and default."""
        self.assertIn("export function FileUpload(", self.code)
        self.assertIn("export default FileUpload;", self.code)

    def test_file_upload_drag_handlers(self) -> None:
        """FileUpload implements dragover, dragleave, and drop handlers."""
        self.assertIn("handleDragOver", self.code)
        self.assertIn("handleDragLeave", self.code)
        self.assertIn("handleDrop", self.code)
        self.assertIn("onDragOver={handleDragOver}", self.code)
        self.assertIn("onDragLeave={handleDragLeave}", self.code)
        self.assertIn("onDrop={handleDrop}", self.code)

    def test_file_upload_hidden_input(self) -> None:
        """FileUpload renders a hidden <input type='file'> with accept and multiple."""
        self.assertIn('type="file"', self.code)
        self.assertIn("accept={accept}", self.code)
        self.assertIn("multiple={multiple}", self.code)
        self.assertIn('style={{ display: "none" }}', self.code)

    def test_file_upload_wai_aria_dropzone(self) -> None:
        """Dropzone implements role='button', aria-label, aria-describedby, aria-disabled."""
        self.assertIn('role="button"', self.code)
        self.assertIn("aria-label={label}", self.code)
        self.assertIn("aria-disabled={disabled}", self.code)

    def test_file_upload_aria_live(self) -> None:
        """FileUpload announces file selection results via aria-live='polite'."""
        self.assertIn('aria-live="polite"', self.code)
        self.assertIn('role="status"', self.code)
        self.assertIn("aria-atomic=\"true\"", self.code)

    def test_file_upload_keyboard_enter_space(self) -> None:
        """FileUpload opens picker on Enter and Space keys."""
        self.assertIn('e.key === "Enter"', self.code)
        self.assertIn('e.key === " "', self.code)
        self.assertIn("openPicker()", self.code)

    def test_file_upload_maxsize_validation(self) -> None:
        """FileUpload validates file size against maxSize."""
        self.assertIn("maxSize > 0 && file.size > maxSize", self.code)
        self.assertIn("formatBytes(maxSize)", self.code)

    def test_file_upload_accept_validation(self) -> None:
        """FileUpload validates MIME type / extension against accept prop."""
        self.assertIn('token.endsWith("/*")', self.code)
        self.assertIn('token.startsWith(".")', self.code)
        self.assertIn("is not accepted", self.code)

    def test_file_upload_maxfiles_constraint(self) -> None:
        """FileUpload enforces maxFiles by slicing the combined array."""
        self.assertIn("maxFiles !== undefined ? combined.slice(0, maxFiles) : combined", self.code)

    def test_file_upload_format_bytes_helper(self) -> None:
        """formatBytes helper renders B, KB, and MB units."""
        self.assertIn("function formatBytes(bytes: number): string", self.code)
        self.assertIn("} B`", self.code)
        self.assertIn("} KB`", self.code)
        self.assertIn("} MB`", self.code)

    def test_file_upload_avatar_variant(self) -> None:
        """Avatar variant renders circular crop with CameraIcon overlay."""
        self.assertIn('variant === "avatar"', self.code)
        self.assertIn("omnistackai-file-upload--avatar", self.code)
        self.assertIn("omnistackai-file-upload__avatar-overlay", self.code)
        self.assertIn("CameraIcon", self.code)

    def test_file_upload_file_row_remove_button(self) -> None:
        """File list rows include an accessible remove button."""
        self.assertIn("aria-label={`Remove ${entry.file.name}`}", self.code)
        self.assertIn("onRemove", self.code)

    def test_file_upload_progressbar_per_file(self) -> None:
        """File rows render a progressbar when status is uploading."""
        self.assertIn('entry.status === "uploading"', self.code)
        self.assertIn('role="progressbar"', self.code)
        self.assertIn("aria-valuenow={entry.progress}", self.code)

    def test_file_upload_emitted_in_generated_app(self) -> None:
        """NextjsWebAdapter includes components/file-upload.tsx in generated files."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/file-upload.tsx")
        self.assertIsNotNone(f)

    def test_file_upload_content_matches_template(self) -> None:
        """Generated file-upload.tsx content matches render_file_upload_component()."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/file-upload.tsx")
        self.assertIsNotNone(f)
        self.assertEqual(f.content, render_file_upload_component())

    def test_file_upload_diff_invariant(self) -> None:
        """FileUpload output is identical regardless of ir.description."""
        ir_b = dataclasses.replace(self.ir, description="Completely different description")
        adapter = NextjsWebAdapter()
        f_a = adapter.generate(self.ir).get("components/file-upload.tsx")
        f_b = adapter.generate(ir_b).get("components/file-upload.tsx")
        self.assertIsNotNone(f_a)
        self.assertIsNotNone(f_b)
        self.assertEqual(f_a.content, f_b.content)

    def test_file_upload_zero_external_dependencies(self) -> None:
        """FileUpload uses only React built-ins; no external package imports."""
        # Collect all from-import module paths (the quoted string after 'from')
        import re
        modules = re.findall(r'from\s+"([^"]+)"', self.code)
        for mod in modules:
            self.assertEqual(mod, "react", f"Unexpected external import: {mod}")

    def test_package_codegen_exports_render_file_upload_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_file_upload_component."""
        self.assertTrue(callable(cg.render_file_upload_component))
        self.assertIn("render_file_upload_component", cg.__all__)
        self.assertEqual(cg.render_file_upload_component(), self.code)


if __name__ == "__main__":
    unittest.main()
