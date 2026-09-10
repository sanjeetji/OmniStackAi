"""Tests for Task R-330: Generated Accessible Command Palette / Search Menu Component.

Verifies that NextjsWebAdapter emits an accessible, reusable Command Palette component
(apps/web/components/command-palette.tsx) supporting global Cmd+K / Ctrl+K keyboard shortcut,
instant fuzzy/substring filtering across labels/descriptions/keywords, keyboard navigation
(ArrowDown/ArrowUp/Enter/Escape/Home/End), WAI-ARIA combobox/listbox pattern, group headers,
item shortcut badges, empty search states, and diff invariance.
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import (
    render_command_palette_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
)


class CommandPaletteComponentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.code = render_command_palette_component()

    def test_command_palette_component_is_client_component(self) -> None:
        """Command palette component specifies 'use client' directive."""
        self.assertTrue(self.code.startswith('"use client";'))

    def test_command_palette_component_exports_types_and_component(self) -> None:
        """Command palette component exports types, interfaces, and CommandPalette function."""
        self.assertIn("export interface CommandItem", self.code)
        self.assertIn("export interface CommandGroup", self.code)
        self.assertIn("export interface CommandPaletteProps", self.code)
        self.assertIn("export function CommandPalette", self.code)
        self.assertIn("export default CommandPalette;", self.code)

    def test_command_palette_global_shortcut_listener(self) -> None:
        """Command palette binds Cmd+K / Ctrl+K global keyboard shortcut listener."""
        self.assertIn("triggerShortcut", self.code)
        self.assertIn('e.key.toLowerCase() === "k"', self.code)
        self.assertIn("e.metaKey || e.ctrlKey", self.code)
        self.assertIn('window.addEventListener("keydown"', self.code)
        self.assertIn('window.removeEventListener("keydown"', self.code)

    def test_command_palette_query_filtering(self) -> None:
        """Command palette filters items by query across labels, descriptions, and keywords."""
        self.assertIn("filteredItems", self.code)
        self.assertIn("item.label.toLowerCase().includes", self.code)
        self.assertIn("item.description", self.code)
        self.assertIn("item.keywords", self.code)

    def test_command_palette_keyboard_traversal(self) -> None:
        """Command palette supports keyboard navigation including arrows, Enter, Escape, Home, End."""
        self.assertIn('case "ArrowDown":', self.code)
        self.assertIn('case "ArrowUp":', self.code)
        self.assertIn('case "Home":', self.code)
        self.assertIn('case "End":', self.code)
        self.assertIn('case "Enter":', self.code)
        self.assertIn('case "Escape":', self.code)
        self.assertIn("scrollIntoView", self.code)

    def test_command_palette_active_descendant_and_combobox_semantics(self) -> None:
        """Command palette implements WAI-ARIA combobox pattern with active descendant tracking."""
        self.assertIn('role="combobox"', self.code)
        self.assertIn('role="listbox"', self.code)
        self.assertIn('role="option"', self.code)
        self.assertIn('aria-expanded="true"', self.code)
        self.assertIn('aria-haspopup="listbox"', self.code)
        self.assertIn('aria-autocomplete="list"', self.code)
        self.assertIn("aria-controls={listboxId}", self.code)
        self.assertIn("aria-activedescendant={activeOptionId}", self.code)
        self.assertIn("aria-selected={isActive}", self.code)
        self.assertIn("aria-disabled={item.disabled}", self.code)

    def test_command_palette_group_headers_and_sublists(self) -> None:
        """Command palette groups filtered items under role='group' with group headings."""
        self.assertIn('groupedFilteredItems', self.code)
        self.assertIn('role="group"', self.code)
        self.assertIn("aria-labelledby", self.code)

    def test_command_palette_kbd_badges(self) -> None:
        """Command palette renders shortcut badges and footer navigation hint kbd elements."""
        self.assertIn("<kbd", self.code)
        self.assertIn("navigate", self.code)
        self.assertIn("select", self.code)
        self.assertIn("close", self.code)

    def test_command_palette_empty_search_state(self) -> None:
        """Command palette displays configurable emptyMessage when no items match search query."""
        self.assertIn("emptyMessage", self.code)
        self.assertIn("No matching commands found.", self.code)

    def test_command_palette_dialog_backdrop_and_body_scroll_lock(self) -> None:
        """Command palette renders in modal dialog overlay with body scroll lock management."""
        self.assertIn('role="dialog"', self.code)
        self.assertIn('aria-modal="true"', self.code)
        self.assertIn('document.body.style.overflow = "hidden"', self.code)

    def test_command_palette_exported_from_codegen_package(self) -> None:
        """render_command_palette_component is exposed at omnistackai_agent_engine.codegen top level."""
        self.assertTrue(callable(cg.render_command_palette_component))
        self.assertIn("render_command_palette_component", cg.__all__)

    def test_command_palette_registered_in_nextjs_adapter(self) -> None:
        """NextjsWebAdapter registers components/command-palette.tsx in generated file set."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/command-palette.tsx")

        self.assertIsNotNone(f)
        self.assertEqual(f.content, self.code)

    def test_command_palette_is_diff_invariant_across_ir_descriptions(self) -> None:
        """Command palette output remains byte-for-byte identical across differing IR descriptions."""
        ir2 = dataclasses.replace(
            self.ir,
            description="Completely different description to test diff invariance",
        )
        adapter = NextjsWebAdapter()
        p1 = adapter.generate(self.ir).get("components/command-palette.tsx")
        p2 = adapter.generate(ir2).get("components/command-palette.tsx")

        self.assertIsNotNone(p1)
        self.assertIsNotNone(p2)
        self.assertEqual(p1.content, p2.content)


if __name__ == "__main__":
    unittest.main()
