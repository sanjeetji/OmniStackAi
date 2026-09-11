"""Tests for the Markdown & Rich Content Editor component codegen (R-365).

Verifies:
1. Zero runtime dependencies (pure React).
2. "use client" directive present.
3. React forwardRef and explicit displayName.
4. Exported types (MarkdownEditorVariant, MarkdownEditorSize, MarkdownEditorViewMode,
   MarkdownToolbarAction, MarkdownEditorProps, MarkdownToolbarProps, MarkdownPreviewProps,
   MarkdownStatusBarProps).
5. Compound and alias exports (MarkdownEditor, MarkdownToolbar, MarkdownPreview,
   MarkdownStatusBar, RichTextEditor, ContentEditor).
6. 4 visual variants ("default", "card", "glass", "neon").
7. 3 size presets ("sm", "md", "lg").
8. View mode switching (Write/Edit, Preview, Split view) with WAI-ARIA tab semantics.
9. Toolbar formatting actions (bold, italic, strike, headings, quote, code, lists, link, image, table, hr).
10. Built-in zero-dependency vector icons.
11. Built-in markdown parser & live preview (headings, quotes, code blocks, checklists, tables, links).
12. Status bar metrics (lines, words, characters, reading time).
13. Keyboard shortcuts (Ctrl/Cmd+B, Ctrl/Cmd+I, Ctrl/Cmd+K, Tab).
14. Hidden input form submission integration.
15. NextjsWebAdapter emits components/markdown-editor.tsx.
16. 100% diff-invariance across ir.description changes.
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_markdown_editor_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TestMarkdownEditorComponent(unittest.TestCase):
    """Test suite for components/markdown-editor.tsx codegen."""

    def setUp(self) -> None:
        self.code = render_markdown_editor_component()
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
        """Must use React.forwardRef and set explicit displayName."""
        self.assertIn("forwardRef", self.code)
        self.assertIn('MarkdownEditor.displayName = "MarkdownEditor"', self.code)
        self.assertIn('MarkdownPreview.displayName = "MarkdownPreview"', self.code)

    def test_exported_types(self) -> None:
        """Must export all canonical TypeScript types and interfaces."""
        self.assertIn("export type MarkdownEditorVariant =", self.code)
        self.assertIn("export type MarkdownEditorSize =", self.code)
        self.assertIn("export type MarkdownEditorViewMode =", self.code)
        self.assertIn("export type MarkdownToolbarAction =", self.code)
        self.assertIn("export interface MarkdownEditorProps", self.code)
        self.assertIn("export interface MarkdownToolbarProps", self.code)
        self.assertIn("export interface MarkdownPreviewProps", self.code)
        self.assertIn("export interface MarkdownStatusBarProps", self.code)

    def test_compound_and_alias_exports(self) -> None:
        """Must export MarkdownEditor, subcomponents, and semantic aliases."""
        self.assertIn("export const MarkdownEditor =", self.code)
        self.assertIn("export function MarkdownToolbar", self.code)
        self.assertIn("export const MarkdownPreview =", self.code)
        self.assertIn("export function MarkdownStatusBar", self.code)
        self.assertIn("export const RichTextEditor = MarkdownEditor", self.code)
        self.assertIn('RichTextEditor.displayName = "RichTextEditor"', self.code)
        self.assertIn("export const ContentEditor = MarkdownEditor", self.code)
        self.assertIn('ContentEditor.displayName = "ContentEditor"', self.code)
        self.assertIn("export default MarkdownEditor", self.code)

    def test_four_visual_variants(self) -> None:
        """Must support 'default', 'card', 'glass', 'neon' variants."""
        for variant in ["default", "card", "glass", "neon"]:
            self.assertIn(f'"{variant}"', self.code)
        self.assertIn("backdropFilter", self.code)  # glass
        self.assertIn("boxShadow", self.code)  # card and neon
        self.assertIn("22d3ee", self.code)  # neon cyan accent

    def test_three_size_presets(self) -> None:
        """Must support 'sm', 'md', and 'lg' size scales."""
        for size in ["sm", "md", "lg"]:
            self.assertIn(f'"{size}"', self.code)
        self.assertIn("SIZE_CONFIGS", self.code)

    def test_view_mode_switching_and_wai_aria(self) -> None:
        """Must support Write, Preview, and Split view modes with tablist semantics."""
        self.assertIn('"edit"', self.code)
        self.assertIn('"preview"', self.code)
        self.assertIn('"split"', self.code)
        self.assertIn('role="tablist"', self.code)
        self.assertIn('role="tab"', self.code)
        self.assertIn("aria-selected", self.code)
        self.assertIn('role="toolbar"', self.code)
        self.assertIn('role="status"', self.code)
        self.assertIn('aria-live="polite"', self.code)

    def test_builtin_vector_icons(self) -> None:
        """Must include zero-dependency SVG icons for all toolbar actions."""
        self.assertIn("BoldIcon", self.code)
        self.assertIn("ItalicIcon", self.code)
        self.assertIn("StrikethroughIcon", self.code)
        self.assertIn("Heading1Icon", self.code)
        self.assertIn("Heading2Icon", self.code)
        self.assertIn("Heading3Icon", self.code)
        self.assertIn("QuoteIcon", self.code)
        self.assertIn("CodeIcon", self.code)
        self.assertIn("CodeBlockIcon", self.code)
        self.assertIn("ListIcon", self.code)
        self.assertIn("ListOrderedIcon", self.code)
        self.assertIn("CheckSquareIcon", self.code)
        self.assertIn("LinkIcon", self.code)
        self.assertIn("ImageIcon", self.code)
        self.assertIn("TableIcon", self.code)
        self.assertIn("MinusIcon", self.code)
        self.assertIn("EditIcon", self.code)
        self.assertIn("EyeIcon", self.code)
        self.assertIn("SplitIcon", self.code)

    def test_markdown_parser_and_preview_features(self) -> None:
        """Must parse headings, quotes, code blocks, lists, checklists, tables, links, images."""
        self.assertIn("renderMarkdownToNodes", self.code)
        self.assertIn("parseInlineMarkdown", self.code)
        self.assertIn("code-block", self.code)
        self.assertIn("blockquote", self.code)
        self.assertIn("table", self.code)
        self.assertIn("checkbox", self.code)

    def test_status_bar_metrics(self) -> None:
        """Must calculate character count, word count, line count, and reading time."""
        self.assertIn("charCount", self.code)
        self.assertIn("wordCount", self.code)
        self.assertIn("lineCount", self.code)
        self.assertIn("readTimeMin", self.code)
        self.assertIn("fontVariantNumeric", self.code)

    def test_keyboard_shortcuts(self) -> None:
        """Must handle Ctrl/Cmd+B, Ctrl/Cmd+I, Ctrl/Cmd+K, and Tab indentation."""
        self.assertIn("isCmdOrCtrl", self.code)
        self.assertIn('"b"', self.code)
        self.assertIn('"i"', self.code)
        self.assertIn('"k"', self.code)
        self.assertIn('"Tab"', self.code)

    def test_form_integration_hidden_inputs(self) -> None:
        """Must render hidden input when name prop is supplied."""
        self.assertIn('type="hidden"', self.code)
        self.assertIn("name={name}", self.code)

    def test_adapter_emits_markdown_editor_file(self) -> None:
        """NextjsWebAdapter must generate components/markdown-editor.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/markdown-editor.tsx")
        self.assertIsNotNone(f, "components/markdown-editor.tsx must be emitted")
        self.assertEqual(f.content, self.code)

    def test_package_codegen_exports_render_markdown_editor_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_markdown_editor_component."""
        self.assertTrue(
            hasattr(cg, "render_markdown_editor_component"),
            "render_markdown_editor_component must be exported from codegen package",
        )
        self.assertIn("render_markdown_editor_component", cg.__all__)
        self.assertTrue(callable(cg.render_markdown_editor_component))
        self.assertEqual(cg.render_markdown_editor_component(), self.code)

    def test_diff_invariance_across_description(self) -> None:
        """Component code must be 100% diff-invariant across ir.description changes."""
        modified_ir = dataclasses.replace(
            self.ir,
            description="Completely different prompt description for markdown editor diff invariance test",
        )
        adapter = NextjsWebAdapter()
        f_a = adapter.generate(self.ir).get("components/markdown-editor.tsx")
        f_b = adapter.generate(modified_ir).get("components/markdown-editor.tsx")
        self.assertIsNotNone(f_a)
        self.assertIsNotNone(f_b)
        self.assertEqual(f_a.content, f_b.content)


if __name__ == "__main__":
    unittest.main()
