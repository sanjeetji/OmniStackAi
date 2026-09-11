"""Tests for the Accessible Futuristic Reusable Terminal & Command Console Suite codegen (R-381).

Verifies:
1. Zero runtime dependencies (pure React).
2. "use client" directive present.
3. React forwardRef and explicit displayName across compound exports.
4. Exported canonical TypeScript types & interfaces.
5. Compound and semantic alias exports (Terminal, TerminalHeader, TerminalTabs, TerminalOutput, TerminalPrompt, ConsoleViewer, CommandLine, default).
6. Command prompt and input submission handling.
7. Command history navigation with ArrowUp/ArrowDown.
8. ANSI color code parser and style rendering.
9. Line types (stdout, stderr, command, system, info).
10. 4 visual styling variants (terminal, neon, glass, minimal).
11. 3 size presets (sm, md, lg).
12. Multi-tab sessions support (TerminalTabs, tabs).
13. Search filtering in terminal output buffer.
14. WAI-ARIA log semantics (role="log", aria-live="polite").
15. Imperative handle methods (write, writeln, clear, focus, scrollToBottom, getHistory, getOutput, execute).
16. NextjsWebAdapter emits components/terminal.tsx and codegen package exports render_terminal_component.
17. 100% diff-invariance across ir.description changes.
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_terminal_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TestTerminalComponent(unittest.TestCase):
    """Test suite for components/terminal.tsx codegen."""

    def setUp(self) -> None:
        self.code = render_terminal_component()
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
        self.assertIn('Terminal.displayName = "Terminal"', self.code)
        self.assertIn('TerminalHeader.displayName = "TerminalHeader"', self.code)
        self.assertIn('TerminalTabs.displayName = "TerminalTabs"', self.code)
        self.assertIn('TerminalOutput.displayName = "TerminalOutput"', self.code)
        self.assertIn('TerminalPrompt.displayName = "TerminalPrompt"', self.code)
        self.assertIn('ConsoleViewer.displayName = "ConsoleViewer"', self.code)
        self.assertIn('CommandLine.displayName = "CommandLine"', self.code)

    def test_exported_canonical_types(self) -> None:
        """Canonical TypeScript types and interfaces must be exported."""
        self.assertIn("export type TerminalVariant =", self.code)
        self.assertIn("export type TerminalSize =", self.code)
        self.assertIn("export type TerminalLineType =", self.code)
        self.assertIn("export interface TerminalLine", self.code)
        self.assertIn("export interface TerminalTab", self.code)
        self.assertIn("export interface TerminalHandle", self.code)
        self.assertIn("export interface TerminalProps", self.code)
        self.assertIn("export interface TerminalHeaderProps", self.code)
        self.assertIn("export interface TerminalOutputProps", self.code)
        self.assertIn("export interface TerminalPromptProps", self.code)

    def test_compound_and_alias_exports(self) -> None:
        """Must export Terminal, TerminalHeader, TerminalTabs, TerminalOutput, TerminalPrompt, ConsoleViewer, CommandLine, and default."""
        self.assertIn("export const Terminal =", self.code)
        self.assertIn("export const TerminalHeader", self.code)
        self.assertIn("export const TerminalTabs", self.code)
        self.assertIn("export const TerminalOutput", self.code)
        self.assertIn("export const TerminalPrompt", self.code)
        self.assertIn("export const ConsoleViewer = Terminal;", self.code)
        self.assertIn("export const CommandLine = Terminal;", self.code)
        self.assertIn("export default Terminal;", self.code)

    def test_command_prompt_and_submission(self) -> None:
        """Must support customizable command prompt and execution handler."""
        self.assertIn("prompt =", self.code)
        self.assertIn("onCommand", self.code)
        self.assertIn("executeCommand", self.code)
        self.assertIn("TerminalPrompt", self.code)

    def test_command_history_navigation(self) -> None:
        """Must navigate command history with ArrowUp and ArrowDown."""
        self.assertIn("ArrowUp", self.code)
        self.assertIn("ArrowDown", self.code)
        self.assertIn("commandHistory", self.code)
        self.assertIn("historyIndex", self.code)

    def test_ansi_color_code_parser(self) -> None:
        """Must parse ANSI escape codes and apply color/style formatting."""
        self.assertIn("parseAnsi", self.code)
        self.assertIn("ansiRegex", self.code)
        self.assertIn("#ef4444", self.code)  # red
        self.assertIn("#10b981", self.code)  # green
        self.assertIn("#3b82f6", self.code)  # blue

    def test_line_types(self) -> None:
        """Must style distinct line types (stdout, stderr, command, system, info)."""
        for line_type in ["stdout", "stderr", "command", "system", "info"]:
            self.assertIn(f'"{line_type}"', self.code)
        self.assertIn("data-line-type", self.code)

    def test_four_visual_variants(self) -> None:
        """Must support 4 visual styling variants."""
        for variant in ["terminal", "neon", "glass", "minimal"]:
            self.assertIn(f'"{variant}"', self.code)
        self.assertIn("backdropFilter", self.code)
        self.assertIn("rgba(6, 182, 212", self.code)

    def test_three_size_presets(self) -> None:
        """Must define sm, md, lg size presets."""
        self.assertIn('size === "sm"', self.code)
        self.assertIn('size === "lg"', self.code)

    def test_multi_tab_sessions(self) -> None:
        """Must support multi-tab terminal sessions."""
        self.assertIn("TerminalTabs", self.code)
        self.assertIn("role=\"tablist\"", self.code)
        self.assertIn("role=\"tab\"", self.code)
        self.assertIn("onTabAdd", self.code)
        self.assertIn("onTabClose", self.code)

    def test_search_filtering_in_output(self) -> None:
        """Must support live search filtering across output buffer."""
        self.assertIn("searchQuery", self.code)
        self.assertIn("filteredLines", self.code)
        self.assertIn("Search logs...", self.code)

    def test_wai_aria_log_semantics(self) -> None:
        """Must implement WAI-ARIA 1.2 log semantics."""
        self.assertIn('role="region"', self.code)
        self.assertIn('role="log"', self.code)
        self.assertIn('aria-live="polite"', self.code)
        self.assertIn('aria-label="Terminal Console"', self.code)

    def test_imperative_handle_methods(self) -> None:
        """Must expose imperative handle methods via useImperativeHandle."""
        self.assertIn("useImperativeHandle", self.code)
        self.assertIn("write:", self.code)
        self.assertIn("writeln:", self.code)
        self.assertIn("clear:", self.code)
        self.assertIn("focus:", self.code)
        self.assertIn("scrollToBottom:", self.code)
        self.assertIn("getHistory:", self.code)
        self.assertIn("getOutput:", self.code)
        self.assertIn("execute:", self.code)

    def test_nextjs_adapter_and_codegen_exports(self) -> None:
        """NextjsWebAdapter emits components/terminal.tsx and codegen exposes render function."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        term_file = project.get("components/terminal.tsx")
        self.assertIsNotNone(term_file, "components/terminal.tsx must be generated")
        self.assertEqual(term_file.content, self.code)

        self.assertIn("render_terminal_component", cg.__all__)
        self.assertTrue(callable(cg.render_terminal_component))
        self.assertEqual(cg.render_terminal_component(), self.code)

    def test_diff_invariance(self) -> None:
        """Component code must be 100% diff-invariant across varying IR descriptions."""
        adapter = NextjsWebAdapter()
        ir1 = self.ir
        ir2 = dataclasses.replace(self.ir, description="Modified IR for terminal invariance")

        file1 = adapter.generate(ir1).get("components/terminal.tsx")
        file2 = adapter.generate(ir2).get("components/terminal.tsx")

        self.assertIsNotNone(file1)
        self.assertIsNotNone(file2)
        self.assertEqual(file1.content, file2.content)


if __name__ == "__main__":
    unittest.main()
