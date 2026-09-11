"""Tests for the Accessible Futuristic Reusable Diff Viewer & Code/Text Comparison Suite codegen (R-373).

Verifies:
1. Zero runtime dependencies (pure React + mathematical LCS).
2. "use client" directive present.
3. React forwardRef and explicit displayName across compound exports.
4. Exported canonical TypeScript types & interfaces.
5. Compound and semantic alias exports (DiffViewer, CodeDiff, TextDiff, default).
6. 4 visual styling variants ("default", "card", "glass", "neon").
7. 3 size presets ("sm", "md", "lg").
8. WAI-ARIA accessibility semantics (role="region", role="table", role="row", role="cell", aria-label).
9. Mathematical LCS (Longest Common Subsequence) diff calculation.
10. Word-level/intraline character diff highlighting.
11. Split (side-by-side) comparison view mode.
12. Unified (inline) comparison view mode.
13. Unchanged lines folding and expandable banner threshold.
14. Clipboard copy actions and imperative handle methods.
15. Statistical additions (+N) and deletions (-N) counter pills.
16. NextjsWebAdapter emits components/diff-viewer.tsx and codegen package exports render_diff_viewer_component.
17. 100% diff-invariance across ir.description changes.
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_diff_viewer_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TestDiffViewerComponent(unittest.TestCase):
    """Test suite for components/diff-viewer.tsx codegen."""

    def setUp(self) -> None:
        self.code = render_diff_viewer_component()
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
        self.assertIn('DiffViewer.displayName = "DiffViewer"', self.code)
        self.assertIn('CodeDiff.displayName = "CodeDiff"', self.code)
        self.assertIn('TextDiff.displayName = "TextDiff"', self.code)

    def test_exported_canonical_types(self) -> None:
        """Canonical TypeScript types must be exported."""
        self.assertIn("export type DiffViewMode =", self.code)
        self.assertIn("export type DiffLineType =", self.code)
        self.assertIn("export type DiffViewerVariant =", self.code)
        self.assertIn("export type DiffViewerSize =", self.code)
        self.assertIn("export interface DiffWordPart", self.code)
        self.assertIn("export interface DiffLine", self.code)
        self.assertIn("export interface SplitDiffRow", self.code)
        self.assertIn("export interface DiffViewerHandle", self.code)
        self.assertIn("export interface DiffViewerProps", self.code)

    def test_compound_and_semantic_exports(self) -> None:
        """Must export DiffViewer, CodeDiff, TextDiff, and default export."""
        self.assertIn("export const DiffViewer =", self.code)
        self.assertIn("export const CodeDiff =", self.code)
        self.assertIn("export const TextDiff =", self.code)
        self.assertIn("export default DiffViewer;", self.code)

    def test_visual_variants(self) -> None:
        """Must support 4 visual styling variants."""
        for variant in ["default", "card", "glass", "neon"]:
            self.assertIn(f'"{variant}"', self.code)
        self.assertIn("backdrop-blur-md", self.code)
        self.assertIn("border-cyan-500", self.code)

    def test_size_presets(self) -> None:
        """Must define sm, md, lg size presets."""
        self.assertIn("sm:", self.code)
        self.assertIn("md:", self.code)
        self.assertIn("lg:", self.code)

    def test_wai_aria_semantics(self) -> None:
        """Must contain WAI-ARIA region and table semantics for accessibility."""
        self.assertIn('role="region"', self.code)
        self.assertIn('aria-label="Code diff viewer"', self.code)
        self.assertIn('aria-roledescription="diff view"', self.code)
        self.assertIn('role="table"', self.code)
        self.assertIn('role="row"', self.code)
        self.assertIn('role="cell"', self.code)

    def test_lcs_algorithm_implementation(self) -> None:
        """Must implement mathematical Longest Common Subsequence line diff."""
        self.assertIn("computeLineDiff", self.code)
        self.assertIn("oldLines", self.code)
        self.assertIn("newLines", self.code)
        self.assertIn("matrix", self.code)

    def test_word_level_intraline_diffing(self) -> None:
        """Must implement within-line word/character difference highlighting."""
        self.assertIn("computeWordDiff", self.code)
        self.assertIn("oldParts", self.code)
        self.assertIn("newParts", self.code)
        self.assertIn("highlightWords", self.code)

    def test_split_view_side_by_side(self) -> None:
        """Must support split mode side-by-side rendering."""
        self.assertIn('mode === "split"', self.code)
        self.assertIn("splitRows", self.code)
        self.assertIn("oldTitle", self.code)
        self.assertIn("newTitle", self.code)

    def test_unified_view_inline(self) -> None:
        """Must support unified mode inline rendering."""
        self.assertIn("unified", self.code)
        self.assertIn("diffLines.map", self.code)
        self.assertIn("rawUnifiedDiff", self.code)

    def test_unchanged_lines_folding(self) -> None:
        """Must support folding unchanged lines with threshold."""
        self.assertIn("collapseUnchanged", self.code)
        self.assertIn("foldThreshold", self.code)
        self.assertIn("contextLines", self.code)
        self.assertIn("unchanged lines", self.code)

    def test_copy_actions_and_imperative_handle(self) -> None:
        """Must provide copy actions and expose imperative handle methods."""
        self.assertIn("copyToClipboard", self.code)
        self.assertIn("getRawDiff", self.code)
        self.assertIn("copyAll", self.code)
        self.assertIn("copyOriginal", self.code)
        self.assertIn("copyModified", self.code)

    def test_additions_and_deletions_counters(self) -> None:
        """Must compute and render additions and deletions statistics."""
        self.assertIn("additions", self.code)
        self.assertIn("deletions", self.code)
        self.assertIn("+{stats.additions}", self.code)
        self.assertIn("-{stats.deletions}", self.code)

    def test_nextjs_adapter_and_codegen_exports(self) -> None:
        """NextjsWebAdapter emits components/diff-viewer.tsx and codegen exposes render function."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        diff_file = project.get("components/diff-viewer.tsx")
        self.assertIsNotNone(diff_file, "components/diff-viewer.tsx must be generated")
        self.assertEqual(diff_file.content, self.code)

        self.assertIn("render_diff_viewer_component", cg.__all__)
        self.assertTrue(callable(cg.render_diff_viewer_component))
        self.assertEqual(cg.render_diff_viewer_component(), self.code)

    def test_diff_invariance(self) -> None:
        """Component code must be 100% diff-invariant across varying IR descriptions."""
        adapter = NextjsWebAdapter()
        ir1 = self.ir
        ir2 = dataclasses.replace(self.ir, description="Modified IR for diff viewer invariance")

        proj1 = adapter.generate(ir1)
        proj2 = adapter.generate(ir2)

        file1 = proj1.get("components/diff-viewer.tsx")
        file2 = proj2.get("components/diff-viewer.tsx")

        self.assertIsNotNone(file1)
        self.assertIsNotNone(file2)
        self.assertEqual(file1.content, file2.content)


if __name__ == "__main__":
    unittest.main()
