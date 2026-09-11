"""Tests for the Kanban Board & Task Flow Matrix Suite codegen (R-367).

Verifies:
1. Zero runtime dependencies (pure React).
2. "use client" directive present.
3. React forwardRef and explicit displayName.
4. Exported types (KanbanVariant, KanbanSize, KanbanPriority, KanbanColumn,
   KanbanAssignee, KanbanItem, KanbanProps).
5. Semantic aliases (KanbanBoard, TaskBoard, default export).
6. 4 visual styling variants ("default", "card", "glass", "neon").
7. 3 size presets ("sm", "md", "lg").
8. WAI-ARIA 1.2 region & listbox semantics (role="region", role="group", role="listbox", role="option").
9. Built-in zero-dependency vector icons (PlusIcon, GripVerticalIcon, ChevronDownIcon,
   ChevronRightIcon, ClockIcon, TagIcon, AlertCircleIcon, UserIcon, SearchIcon).
10. HTML5 drag & drop card movement handlers (draggable, onDragStart, onDragOver, onDragLeave, onDrop, onDragEnd).
11. Column collapsing, WIP limit warning badge, and add task action triggers.
12. Priority badges (urgent, high, medium, low) and search filtering.
13. Hidden input form submission integration when name prop is present.
14. NextjsWebAdapter emits components/kanban.tsx.
15. Codegen package export render_kanban_component in __all__.
16. 100% diff-invariance across ir.description changes.
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_kanban_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TestKanbanComponent(unittest.TestCase):
    """Test suite for components/kanban.tsx codegen."""

    def setUp(self) -> None:
        self.code = render_kanban_component()
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
        self.assertIn('Kanban.displayName = "Kanban"', self.code)
        self.assertIn('KanbanBoard.displayName = "KanbanBoard"', self.code)
        self.assertIn('TaskBoard.displayName = "TaskBoard"', self.code)

    def test_exported_types(self) -> None:
        """Must export canonical TypeScript types and interfaces."""
        self.assertIn("export type KanbanVariant =", self.code)
        self.assertIn("export type KanbanSize =", self.code)
        self.assertIn("export type KanbanPriority =", self.code)
        self.assertIn("export interface KanbanColumn", self.code)
        self.assertIn("export interface KanbanAssignee", self.code)
        self.assertIn("export interface KanbanItem", self.code)
        self.assertIn("export interface KanbanProps", self.code)

    def test_semantic_aliases_and_default_export(self) -> None:
        """Must export Kanban, KanbanBoard, TaskBoard, and default export."""
        self.assertIn("export const Kanban =", self.code)
        self.assertIn("export const KanbanBoard = Kanban", self.code)
        self.assertIn("export const TaskBoard = Kanban", self.code)
        self.assertIn("export default Kanban", self.code)

    def test_four_visual_variants(self) -> None:
        """Must support 'default', 'card', 'glass', 'neon' visual variants."""
        for variant in ["default", "card", "glass", "neon"]:
            self.assertIn(f'"{variant}"', self.code)
        self.assertIn("backdropFilter", self.code)  # glass
        self.assertIn("boxShadow", self.code)  # card / neon glow
        self.assertTrue(
            "22d3ee" in self.code or "rgba(6, 182, 212" in self.code,
            "Must feature neon cyan accent styling",
        )

    def test_three_size_presets(self) -> None:
        """Must support 'sm', 'md', and 'lg' size scales."""
        for size in ["sm", "md", "lg"]:
            self.assertIn(f'"{size}"', self.code)
        self.assertIn("SIZE_CONFIGS", self.code)

    def test_wai_aria_semantics(self) -> None:
        """Must implement WAI-ARIA 1.2 region & listbox pattern semantics."""
        self.assertIn('role="region"', self.code)
        self.assertIn('role="group"', self.code)
        self.assertIn('role="listbox"', self.code)
        self.assertIn('role="option"', self.code)
        self.assertIn("aria-label", self.code)

    def test_builtin_vector_icons(self) -> None:
        """Must provide zero-dependency SVG navigation and indicator icons."""
        self.assertIn("PlusIcon", self.code)
        self.assertIn("GripVerticalIcon", self.code)
        self.assertIn("ChevronDownIcon", self.code)
        self.assertIn("ChevronRightIcon", self.code)
        self.assertIn("ClockIcon", self.code)
        self.assertIn("TagIcon", self.code)
        self.assertIn("AlertCircleIcon", self.code)
        self.assertIn("UserIcon", self.code)
        self.assertIn("SearchIcon", self.code)

    def test_html5_drag_and_drop_handlers(self) -> None:
        """Must implement HTML5 drag and drop card movement handlers."""
        self.assertIn("draggable={allowDragDrop}", self.code)
        self.assertIn("handleDragStart", self.code)
        self.assertIn("handleDragOver", self.code)
        self.assertIn("handleDragLeave", self.code)
        self.assertIn("handleDrop", self.code)
        self.assertIn("handleDragEnd", self.code)

    def test_column_collapsing_and_wip_limits(self) -> None:
        """Must support column collapse toggling and WIP limit warning indicator."""
        self.assertIn("toggleColumnCollapse", self.code)
        self.assertIn("isCollapsed", self.code)
        self.assertIn("isOverLimit", self.code)
        self.assertIn("columnCollapsedWidth", self.code)

    def test_priority_styles_and_search_filter(self) -> None:
        """Must define priority styles and support search filtering."""
        self.assertIn("PRIORITY_STYLES", self.code)
        self.assertIn("urgent", self.code)
        self.assertIn("filteredItems", self.code)

    def test_form_integration_hidden_input(self) -> None:
        """Must render hidden input when name prop is supplied."""
        self.assertIn('type="hidden"', self.code)
        self.assertIn("name={name}", self.code)
        self.assertIn("JSON.stringify(items)", self.code)

    def test_adapter_emits_kanban_file(self) -> None:
        """NextjsWebAdapter must generate components/kanban.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/kanban.tsx")
        self.assertIsNotNone(f, "components/kanban.tsx must be emitted")
        self.assertEqual(f.content, self.code)

    def test_package_codegen_exports_render_kanban_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_kanban_component."""
        self.assertTrue(
            hasattr(cg, "render_kanban_component"),
            "render_kanban_component must be exported from codegen package",
        )
        self.assertIn("render_kanban_component", cg.__all__)
        self.assertTrue(callable(cg.render_kanban_component))
        self.assertEqual(cg.render_kanban_component(), self.code)

    def test_diff_invariance_across_description(self) -> None:
        """Component code must be 100% diff-invariant across ir.description changes."""
        modified_ir = dataclasses.replace(
            self.ir,
            description="Completely different prompt description for kanban diff invariance test",
        )
        adapter = NextjsWebAdapter()
        f_a = adapter.generate(self.ir).get("components/kanban.tsx")
        f_b = adapter.generate(modified_ir).get("components/kanban.tsx")
        self.assertIsNotNone(f_a)
        self.assertIsNotNone(f_b)
        self.assertEqual(f_a.content, f_b.content)


if __name__ == "__main__":
    unittest.main()
