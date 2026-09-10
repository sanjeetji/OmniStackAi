"""Tests for Task R-340: Generated Accessible Futuristic Reusable Code Block & Syntax Presentation Component.

Verifies that NextjsWebAdapter emits an accessible, futuristic, reusable CodeBlock compound component
suite (apps/web/components/code-block.tsx) supporting:
- Built-in zero-dependency lexical tokenizer for major languages (TS/JS, Python, JSON, SQL, Bash, Go, Diff)
- Multi-tab snippet switcher with keyboard navigation and active tab indicators
- Line numbering with customizable starting index
- Line highlighting supporting discrete lines and ranges (e.g. [2, 4, "7-10"])
- Git diff mode with emerald green additions (+) and rose red deletions (-)
- One-click copy-to-clipboard with smooth animated checkmark feedback
- Line wrap toggle and expandable/collapsible max-height view
- 4 futuristic visual variants ("terminal", "glass", "neon", "minimal")
- Full WAI-ARIA accessibility semantics (role="region", role="tablist", keyboard scrollable <pre>)
- 100% diff-invariance across ir.description changes
- Zero external runtime dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_code_block_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class CodeBlockComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the CodeBlock component."""

    def setUp(self) -> None:
        self.code = render_code_block_component()
        self.ir = example_ir("rideshare-favourites")

    def test_code_block_component_is_client_component(self) -> None:
        """The CodeBlock component must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "CodeBlock must have 'use client' as the first statement.",
        )

    def test_code_block_component_exports_types(self) -> None:
        """Verify export of TypeScript interfaces and union types."""
        self.assertIn("export type CodeBlockVariant", self.code)
        self.assertIn('"terminal"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn('"minimal"', self.code)
        self.assertIn("export type CodeBlockSize", self.code)
        self.assertIn("export interface CodeSnippet", self.code)
        self.assertIn("export type TokenType", self.code)
        self.assertIn("export interface CodeToken", self.code)
        self.assertIn("export interface CodeBlockProps", self.code)
        self.assertIn("export interface CodeBlockHeaderProps", self.code)
        self.assertIn("export interface CodeBlockContentProps", self.code)
        self.assertIn("export interface CodeBlockLineProps", self.code)
        self.assertIn("export interface CodeBlockCopyButtonProps", self.code)

    def test_code_block_component_exports_compound(self) -> None:
        """Verify CodeBlock compound component and default export."""
        self.assertIn("export const CodeBlock =", self.code)
        self.assertIn("CodeBlock.Header = CodeBlockHeader;", self.code)
        self.assertIn("CodeBlock.Content = CodeBlockContent;", self.code)
        self.assertIn("CodeBlock.Line = CodeBlockLine;", self.code)
        self.assertIn("CodeBlock.CopyButton = CodeBlockCopyButton;", self.code)
        self.assertIn("export default CodeBlock;", self.code)

    def test_code_block_zero_external_dependencies(self) -> None:
        """CodeBlock uses only React; zero external package imports."""
        import_lines = [
            line for line in self.code.splitlines() if line.startswith("import ")
        ]
        self.assertTrue(len(import_lines) >= 1)
        for line in import_lines:
            self.assertIn(
                'from "react"',
                line,
                f"Unexpected external import in CodeBlock component: {line}",
            )

    def test_code_block_diff_invariant(self) -> None:
        """CodeBlock output is 100% diff-invariant across ir.description changes."""
        mutated_ir = dataclasses.replace(
            self.ir,
            description="Completely mutated description with unpredictable tokens",
        )
        adapter = NextjsWebAdapter()
        f1 = adapter.generate(self.ir).get("components/code-block.tsx")
        f2 = adapter.generate(mutated_ir).get("components/code-block.tsx")

        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(self.code, f1.content)
        self.assertEqual(f1.content, f2.content)

    def test_adapter_emits_code_block_file(self) -> None:
        """NextjsWebAdapter emits components/code-block.tsx in generated project."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/code-block.tsx")
        self.assertIsNotNone(f, "components/code-block.tsx must be generated")
        self.assertEqual(f.content, self.code)

    def test_package_codegen_exports_render_code_block_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_code_block_component."""
        self.assertTrue(hasattr(cg, "render_code_block_component"))
        self.assertIn("render_code_block_component", cg.__all__)
        fn = getattr(cg, "render_code_block_component")
        self.assertEqual(fn(), self.code)

    def test_code_block_supports_variants(self) -> None:
        """Verify visual variant styling logic for terminal, glass, neon, and minimal."""
        self.assertIn('case "glass":', self.code)
        self.assertIn("backdropFilter", self.code)
        self.assertIn('case "neon":', self.code)
        self.assertIn("rgba(56, 189, 248", self.code)
        self.assertIn('case "minimal":', self.code)
        self.assertIn('case "terminal":', self.code)
        self.assertIn("TerminalDots", self.code)

    def test_code_block_tokenizer_logic(self) -> None:
        """Verify built-in zero-dependency lexical tokenizer logic."""
        self.assertIn("export function tokenizeCodeLine", self.code)
        self.assertIn("KEYWORDS_BY_LANG", self.code)
        self.assertIn("COMMON_TYPES", self.code)
        self.assertIn("normalizeLang", self.code)
        # Check token type classifications
        self.assertIn('"keyword"', self.code)
        self.assertIn('"string"', self.code)
        self.assertIn('"comment"', self.code)
        self.assertIn('"number"', self.code)
        self.assertIn('"operator"', self.code)
        self.assertIn('"punctuation"', self.code)

    def test_code_block_line_numbers_and_highlighting(self) -> None:
        """Verify line numbering and line highlighting logic."""
        self.assertIn("showLineNumbers", self.code)
        self.assertIn("startLineNumber", self.code)
        self.assertIn("highlightLines", self.code)
        self.assertIn("export function parseHighlightLines", self.code)
        self.assertIn("omnistack-code-linenumber", self.code)
        self.assertIn("highlighted", self.code)

    def test_code_block_diff_mode(self) -> None:
        """Verify git diff mode handling additions and deletions."""
        self.assertIn("diffMode", self.code)
        self.assertIn("diffType", self.code)
        self.assertIn("diff-add", self.code)
        self.assertIn("diff-delete", self.code)
        self.assertIn("#10b981", self.code)  # emerald
        self.assertIn("#f43f5e", self.code)  # rose

    def test_code_block_multi_tab_snippets(self) -> None:
        """Verify multi-tab snippet switcher support."""
        self.assertIn("snippets", self.code)
        self.assertIn("activeSnippetId", self.code)
        self.assertIn("onSnippetChange", self.code)
        self.assertIn('role="tablist"', self.code)
        self.assertIn('role="tab"', self.code)
        self.assertIn("aria-selected", self.code)

    def test_code_block_copy_clipboard(self) -> None:
        """Verify clipboard copy interaction with animated feedback."""
        self.assertIn("navigator.clipboard.writeText", self.code)
        self.assertIn("Copied!", self.code)
        self.assertIn("CopyIcon", self.code)
        self.assertIn("CheckIcon", self.code)
        self.assertIn("showCopyButton", self.code)

    def test_code_block_wrap_and_expand_controls(self) -> None:
        """Verify word wrap toggle and expandable max-height container."""
        self.assertIn("wrapLines", self.code)
        self.assertIn("showWrapToggle", self.code)
        self.assertIn("WrapIcon", self.code)
        self.assertIn("maxHeight", self.code)
        self.assertIn("isExpanded", self.code)
        self.assertIn("ExpandIcon", self.code)
        self.assertIn("Expand code", self.code)
        self.assertIn("Collapse code", self.code)

    def test_code_block_wai_aria_semantics(self) -> None:
        """Verify WAI-ARIA accessibility semantics."""
        self.assertIn('role="region"', self.code)
        self.assertIn("aria-label", self.code)
        self.assertIn("tabIndex={0}", self.code)
        self.assertIn("aria-hidden", self.code)


if __name__ == "__main__":
    unittest.main()
