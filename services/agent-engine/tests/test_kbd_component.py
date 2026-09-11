"""Tests for Task R-354: Generated Accessible Futuristic Reusable Keyboard Keycap Component.

Verifies that NextjsWebAdapter emits an accessible, desktop-grade, zero-dependency, and futuristic
Keyboard Keycap & Shortcut Badge component (apps/web/components/kbd.tsx) supporting:
- Semantic <kbd> element with WAI-ARIA compliance (role="group", aria-label, aria-keyshortcuts)
- Automatic modifier key symbol translation ("meta"/"command" -> "⌘", "shift" -> "⇧", "ctrl" -> "⌃", "alt" -> "⌥")
- 4 size scales ("xs", "sm", "md", "lg") with responsive padding, font-size, and border-radius
- 5 futuristic visual styling variants ("default", "outline", "subtle", "ghost", "neon")
- Key combination arrays with configurable separators
- Composite KbdGroup container for multi-key shortcuts
- String shortcut parser KbdShortcut (e.g. "⌘+K", "Ctrl+Shift+P")
- React ref forwarding (forwardRef) for all components
- 100% diff-invariance across ir.description changes
- Zero external runtime dependencies (pure React)
"""

from __future__ import annotations

import dataclasses
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_kbd_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class KbdComponentTests(unittest.TestCase):
    """Verify TypeScript code generation for the Keyboard Keycap (Kbd) component."""

    def setUp(self) -> None:
        self.code = render_kbd_component()
        self.ir = example_ir("rideshare-favourites")

    def test_kbd_is_client_component(self) -> None:
        """Kbd must declare 'use client' at the very top."""
        self.assertTrue(
            self.code.startswith('"use client";'),
            "Kbd must have 'use client' as the first statement.",
        )

    def test_kbd_exports_types(self) -> None:
        """Verify export of TypeScript interfaces and union types."""
        self.assertIn("export type KbdVariant", self.code)
        self.assertIn('"default"', self.code)
        self.assertIn('"outline"', self.code)
        self.assertIn('"subtle"', self.code)
        self.assertIn('"ghost"', self.code)
        self.assertIn('"neon"', self.code)
        self.assertIn("export type KbdSize", self.code)
        self.assertIn('"xs"', self.code)
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)
        self.assertIn("export interface KbdProps", self.code)
        self.assertIn("export interface KbdGroupProps", self.code)
        self.assertIn("export interface KbdShortcutProps", self.code)

    def test_kbd_exports_components(self) -> None:
        """Verify Kbd, KbdGroup, and KbdShortcut component exports."""
        self.assertIn("export const Kbd", self.code)
        self.assertIn('Kbd.displayName = "Kbd";', self.code)
        self.assertIn("export const KbdGroup", self.code)
        self.assertIn('KbdGroup.displayName = "KbdGroup";', self.code)
        self.assertIn("export const KbdShortcut", self.code)
        self.assertIn('KbdShortcut.displayName = "KbdShortcut";', self.code)
        self.assertIn("export default Kbd;", self.code)

    def test_kbd_zero_external_dependencies(self) -> None:
        """Kbd uses only React; zero external package imports."""
        import_lines = [
            line.strip()
            for line in self.code.splitlines()
            if line.strip().startswith("import ")
        ]
        self.assertTrue(len(import_lines) >= 1)
        for line in import_lines:
            self.assertIn(
                'from "react"',
                line,
                f"Unexpected external import found in Kbd: {line}",
            )

    def test_kbd_semantic_element(self) -> None:
        """Verify Kbd renders semantic <kbd> HTML elements."""
        self.assertIn("<kbd", self.code)
        self.assertIn("</kbd>", self.code)

    def test_kbd_key_symbols_mapping(self) -> None:
        """Verify automatic modifier key mapping dictionary and function."""
        self.assertIn("formatKeySymbol", self.code)
        self.assertIn('meta: "⌘"', self.code)
        self.assertIn('shift: "⇧"', self.code)
        self.assertIn('ctrl: "⌃"', self.code)
        self.assertIn('alt: "⌥"', self.code)
        self.assertIn('enter: "↵"', self.code)
        self.assertIn('backspace: "⌫"', self.code)

    def test_kbd_size_presets(self) -> None:
        """Verify 4 size scales in SIZE_STYLES."""
        self.assertIn("SIZE_STYLES: Record<KbdSize", self.code)
        self.assertIn('minWidth: "16px"', self.code)
        self.assertIn('minWidth: "20px"', self.code)
        self.assertIn('minWidth: "24px"', self.code)
        self.assertIn('minWidth: "28px"', self.code)

    def test_kbd_visual_variants(self) -> None:
        """Verify 5 visual variants including neon cyberpunk glow and 3D keycap border."""
        self.assertIn("VARIANT_STYLES: Record<KbdVariant", self.code)
        self.assertIn("borderBottomWidth:", self.code)
        self.assertIn("0 0 8px rgba(56, 189, 248, 0.25)", self.code)
        self.assertIn("transparent", self.code)

    def test_kbd_keys_array_support(self) -> None:
        """Verify composite key combination rendering via keys prop."""
        self.assertIn("keys && keys.length > 0", self.code)
        self.assertIn("renderedKeys.map((keyItem, index)", self.code)

    def test_kbd_separator_support(self) -> None:
        """Verify separator rendering between keys."""
        self.assertIn("separator && index < renderedKeys.length - 1", self.code)
        self.assertIn("var(--kbd-separator-color", self.code)

    def test_kbd_group_component(self) -> None:
        """Verify KbdGroup composite container with role='group'."""
        self.assertIn('role="group"', self.code)
        self.assertIn("React.Children.toArray(children)", self.code)
        self.assertIn("React.cloneElement", self.code)

    def test_kbd_shortcut_convenience_component(self) -> None:
        """Verify KbdShortcut parses shortcut string into keys."""
        self.assertIn("shortcut.split(delimiter)", self.code)
        self.assertIn("autoFormatSymbols={autoFormatSymbols}", self.code)

    def test_kbd_forward_ref(self) -> None:
        """Verify React forwardRef implementation across Kbd, KbdGroup, and KbdShortcut."""
        self.assertIn("forwardRef<HTMLElement, KbdProps>", self.code)
        self.assertIn("forwardRef<HTMLDivElement, KbdGroupProps>", self.code)
        self.assertIn("forwardRef<HTMLElement, KbdShortcutProps>", self.code)

    def test_kbd_accessibility_attributes(self) -> None:
        """Verify data attributes and aria attributes."""
        self.assertIn("data-variant={variant}", self.code)
        self.assertIn("data-size={size}", self.code)
        self.assertIn("aria-label={computedAriaLabel}", self.code)

    def test_kbd_diff_invariance(self) -> None:
        """Ensure code is 100% diff-invariant across IR description changes."""
        adapter = NextjsWebAdapter()
        project1 = adapter.generate(self.ir)
        ir2 = dataclasses.replace(
            self.ir, description="Completely changed description for diff test."
        )
        project2 = adapter.generate(ir2)
        c1 = project1.get("components/kbd.tsx").content
        c2 = project2.get("components/kbd.tsx").content
        self.assertEqual(
            c1,
            c2,
            "components/kbd.tsx must be 100% diff-invariant across ir.description",
        )
        self.assertEqual(c1, self.code)

    def test_kbd_emitted_by_adapter_and_exported(self) -> None:
        """NextjsWebAdapter must emit components/kbd.tsx and export in cg.__all__."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/kbd.tsx")
        self.assertIsNotNone(f, "components/kbd.tsx must be generated")
        self.assertEqual(f.content, self.code)
        self.assertIn("render_kbd_component", cg.__all__)
        self.assertTrue(callable(cg.render_kbd_component))
        self.assertEqual(cg.render_kbd_component(), self.code)


if __name__ == "__main__":
    unittest.main()
