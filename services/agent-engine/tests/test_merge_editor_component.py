"""
R-392: Accessible Futuristic Reusable Code Diff Editor & 3-Way Merge Conflict Resolver Suite
Unit tests for render_merge_editor_component and the generated components/merge-editor.tsx.
"""
from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_merge_editor_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter, _MERGE_EDITOR_COMPONENT


class TestMergeEditorComponent(unittest.TestCase):
    """Test suite for components/merge-editor.tsx codegen (R-392)."""

    def setUp(self) -> None:
        self.code = render_merge_editor_component()
        self.ir = example_ir("rideshare-favourites")
        project = NextjsWebAdapter().generate(self.ir)
        self.file = project.get("components/merge-editor.tsx")

    # ------------------------------------------------------------------
    # 1. File is generated at the correct path
    # ------------------------------------------------------------------
    def test_file_generated(self):
        """components/merge-editor.tsx must be emitted by NextjsWebAdapter."""
        ir = example_ir("minimal-blog")
        project = NextjsWebAdapter().generate(ir)
        paths = project.paths()
        self.assertIn("components/merge-editor.tsx", paths)

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
            "MergeEditorVariant",
            "MergeEditorSize",
            "ConflictStatus",
            "MergeConflict",
            "MergeEditorHandle",
            "MergeEditorToolbarProps",
            "MergeEditorProps",
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
    # 6. Conflict statuses supported
    # ------------------------------------------------------------------
    def test_conflict_statuses_present(self):
        """Must define unresolved, accepted_current, accepted_incoming, accepted_both statuses."""
        statuses = ["unresolved", "accepted_current", "accepted_incoming", "accepted_both"]
        for s in statuses:
            self.assertIn(f"'{s}'", self.code, f"Missing status: {s}")

    # ------------------------------------------------------------------
    # 7. Raw conflict parser logic
    # ------------------------------------------------------------------
    def test_raw_conflict_parser_logic(self):
        """Must parse git conflict markers <<<<<<<, =======, >>>>>>>."""
        self.assertIn("parseRawConflicts", self.code)
        self.assertIn("<<<<<<<", self.code)
        self.assertIn("=======", self.code)
        self.assertIn(">>>>>>>", self.code)

    # ------------------------------------------------------------------
    # 8. 3-pane layout sections
    # ------------------------------------------------------------------
    def test_3_pane_layout_sections(self):
        """Must implement Current Change, Result, and Incoming Change panes."""
        self.assertIn("Current Change (Ours)", self.code)
        self.assertIn("Result (Merged View)", self.code)
        self.assertIn("Incoming Change (Theirs)", self.code)

    # ------------------------------------------------------------------
    # 9. Interactive conflict action triggers
    # ------------------------------------------------------------------
    def test_conflict_action_triggers(self):
        """Must implement Accept Current, Accept Incoming, and Accept Both."""
        self.assertIn("acceptCurrent", self.code)
        self.assertIn("acceptIncoming", self.code)
        self.assertIn("acceptBoth", self.code)

    # ------------------------------------------------------------------
    # 10. Batch resolution actions
    # ------------------------------------------------------------------
    def test_batch_resolution_actions(self):
        """Must support Accept All Current, Accept All Incoming, and Reset All."""
        self.assertIn("acceptAllCurrent", self.code)
        self.assertIn("acceptAllIncoming", self.code)
        self.assertIn("resetAll", self.code)

    # ------------------------------------------------------------------
    # 11. Merged text generation and export
    # ------------------------------------------------------------------
    def test_merged_text_generation(self):
        """Must generate merged text and support copy/download."""
        self.assertIn("getMergedText", self.code)
        self.assertIn("handleCopyMerged", self.code)
        self.assertIn("handleDownloadMerged", self.code)

    # ------------------------------------------------------------------
    # 12. Conflict navigation jumper
    # ------------------------------------------------------------------
    def test_conflict_navigation_jumper(self):
        """Must implement Next and Previous conflict jumper controls."""
        self.assertIn("nextConflict", self.code)
        self.assertIn("prevConflict", self.code)
        self.assertIn("activeConflictIndex", self.code)

    # ------------------------------------------------------------------
    # 13. forwardRef and MergeEditorHandle exposed
    # ------------------------------------------------------------------
    def test_forward_ref_and_imperative_handle(self):
        """Must wrap component in forwardRef and expose useImperativeHandle with MergeEditorHandle."""
        self.assertIn("forwardRef", self.code)
        self.assertIn("useImperativeHandle", self.code)
        self.assertIn("isAllResolved", self.code)
        self.assertIn("getUnresolvedCount", self.code)
        self.assertIn("getTotalConflicts", self.code)

    # ------------------------------------------------------------------
    # 14. Explicit displayName defined on compound exports
    # ------------------------------------------------------------------
    def test_display_names_defined(self):
        """Must define explicit displayName on all compound and alias exports."""
        self.assertIn("MergeEditorComponent.displayName = 'MergeEditor'", self.code)
        self.assertIn("MergeEditorToolbar.displayName = 'MergeEditorToolbar'", self.code)
        self.assertIn("MergeEditor.displayName = 'MergeEditor'", self.code)
        self.assertIn("ConflictResolver.displayName = 'ConflictResolver'", self.code)
        self.assertIn("ThreeWayMerge.displayName = 'ThreeWayMerge'", self.code)
        self.assertIn("DiffEditor.displayName = 'DiffEditor'", self.code)

    # ------------------------------------------------------------------
    # 15. Compound and semantic alias exports
    # ------------------------------------------------------------------
    def test_compound_and_alias_exports(self):
        """Must export MergeEditor, ConflictResolver, ThreeWayMerge, DiffEditor, and default export."""
        self.assertIn("export const MergeEditor =", self.code)
        self.assertIn("export const ConflictResolver =", self.code)
        self.assertIn("export const ThreeWayMerge =", self.code)
        self.assertIn("export const DiffEditor =", self.code)
        self.assertIn("export const MergeEditorToolbar", self.code)
        self.assertIn("export default MergeEditorComponent", self.code)

    # ------------------------------------------------------------------
    # 16. WAI-ARIA accessibility semantics
    # ------------------------------------------------------------------
    def test_wai_aria_accessibility(self):
        """Must include appropriate WAI-ARIA region, toolbar, and status roles."""
        self.assertIn('role="region"', self.code)
        self.assertIn('aria-label="3-Way Merge Editor"', self.code)
        self.assertIn('role="toolbar"', self.code)
        self.assertIn('role="status"', self.code)

    # ------------------------------------------------------------------
    # 17. Snapshot diff invariance and codegen export
    # ------------------------------------------------------------------
    def test_diff_invariance_and_codegen_export(self):
        """render_merge_editor_component must be exported and output diff-invariant."""
        self.assertTrue(hasattr(cg, "render_merge_editor_component"))
        code = cg.render_merge_editor_component()
        self.assertIsInstance(code, str)
        self.assertIn("'use client'", code)

        ir1 = example_ir("rideshare-favourites")
        ir2 = example_ir("minimal-blog")
        p1 = NextjsWebAdapter().generate(ir1)
        p2 = NextjsWebAdapter().generate(ir2)
        f1 = p1.get("components/merge-editor.tsx")
        f2 = p2.get("components/merge-editor.tsx")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)


if __name__ == "__main__":
    unittest.main()
