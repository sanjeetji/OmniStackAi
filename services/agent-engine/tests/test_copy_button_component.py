"""Tests for the Accessible Futuristic Copy-to-Clipboard Button Suite (components/copy-button.tsx)."""

from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine import codegen as cg
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_copy_button_component,
)


class TestCopyButtonComponent(unittest.TestCase):
    """Unit tests for the Accessible Futuristic Copy-to-Clipboard Button Suite (R-413)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_copy_button_component()

    def test_file_generated(self) -> None:
        project = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        self.assertIsNotNone(project.get("components/copy-button.tsx"))

    def test_diff_invariance_and_codegen_export(self) -> None:
        proj1 = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        proj2 = NextjsWebAdapter().generate(example_ir("rideshare-favourites"))
        f1 = proj1.get("components/copy-button.tsx")
        f2 = proj2.get("components/copy-button.tsx")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, render_copy_button_component())

    def test_use_client_directive(self) -> None:
        self.assertTrue(self.source.startswith("'use client';"))

    def test_zero_runtime_dependencies(self) -> None:
        for pkg in re.findall(r"from\s+['\"]([^'\"]+)['\"]", self.source):
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected import: {pkg}",
            )

    def test_ascii_only_source(self) -> None:
        non_ascii = [c for c in self.source if ord(c) > 126]
        self.assertEqual(non_ascii, [], f"non-ASCII chars present: {non_ascii[:8]}")

    def test_forward_ref_and_imperative_handle(self) -> None:
        self.assertIn("forwardRef<CopyButtonHandle, CopyButtonProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        for method in ("copy:", "isCopied:", "reset:", "focus:"):
            self.assertIn(method, self.source)

    def test_typescript_types_present(self) -> None:
        for decl in (
            "export type CopyButtonVariant",
            "export type CopyButtonSize",
            "export interface CopyButtonHandle",
            "export interface CopyButtonProps",
        ):
            self.assertIn(decl, self.source)

    def test_compound_and_alias_exports(self) -> None:
        for decl in (
            "export const CopyButton =",
            "export const CopyToClipboard =",
            "export const ClipboardButton =",
            "export const CopyIconButton =",
            "export default CopyButtonComponent",
        ):
            self.assertIn(decl, self.source)

    def test_display_names_defined(self) -> None:
        for line in (
            "CopyButtonComponent.displayName = 'CopyButton'",
            "CopyToClipboard.displayName = 'CopyToClipboard'",
            "ClipboardButton.displayName = 'ClipboardButton'",
            "CopyIconButton.displayName = 'CopyIconButton'",
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

    def test_clipboard_write(self) -> None:
        for token in ("navigator.clipboard", "writeText", "execCommand"):
            self.assertIn(token, self.source)

    def test_feedback(self) -> None:
        for token in ("copied", "copiedLabel", "timeout"):
            self.assertIn(token, self.source)

    def test_aria(self) -> None:
        self.assertIn("aria-label", self.source)
        self.assertIn("aria-live", self.source)

    def test_icon(self) -> None:
        self.assertIn("<svg", self.source)
        self.assertIn("showIcon", self.source)

    def test_callbacks(self) -> None:
        self.assertIn("onCopy", self.source)
        self.assertIn("onError", self.source)

    def test_value_and_disabled(self) -> None:
        self.assertIn("value", self.source)
        self.assertIn("disabled", self.source)

    def test_package_codegen_export(self) -> None:
        self.assertTrue(hasattr(cg, "render_copy_button_component"))
        self.assertTrue(callable(cg.render_copy_button_component))
        self.assertIn("render_copy_button_component", cg.__all__)


if __name__ == "__main__":
    unittest.main()
