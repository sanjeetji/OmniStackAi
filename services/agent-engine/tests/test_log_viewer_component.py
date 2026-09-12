"""Tests for the Accessible Futuristic Live Log Viewer & Event Stream Inspector Suite (components/log-viewer.tsx)."""

from __future__ import annotations

import re
import unittest
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_log_viewer_component,
)


class TestLogViewerComponent(unittest.TestCase):
    """Unit tests for Accessible Futuristic Live Log Viewer & Event Stream Inspector Suite (R-396)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_log_viewer_component()

    def test_file_generated(self) -> None:
        """components/log-viewer.tsx must be emitted by NextjsWebAdapter."""
        adapter = NextjsWebAdapter()
        ir = example_ir("minimal-blog")
        project = adapter.generate(ir)
        f = project.get("components/log-viewer.tsx")
        self.assertIsNotNone(f)

    def test_diff_invariance_and_codegen_export(self) -> None:
        """render_log_viewer_component must be exported and output diff-invariant."""
        src1 = render_log_viewer_component()
        adapter = NextjsWebAdapter()
        proj1 = adapter.generate(example_ir("minimal-blog"))
        proj2 = adapter.generate(example_ir("rideshare-favourites"))

        f1 = proj1.get("components/log-viewer.tsx")
        f2 = proj2.get("components/log-viewer.tsx")

        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, src1)

    def test_use_client_directive(self) -> None:
        """Must have 'use client' as first statement for Next.js App Router."""
        self.assertTrue(self.source.startswith("'use client';"))

    def test_zero_runtime_dependencies(self) -> None:
        """Only imports from 'react' are allowed — 0 external npm dependencies."""
        imports = re.findall(r'from\s+[\'"]([^\'"]+)[\'"]', self.source)
        for pkg in imports:
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected non-react import found: {pkg}",
            )

    def test_forward_ref_and_imperative_handle(self) -> None:
        """Must wrap component in forwardRef and expose useImperativeHandle with LogViewerHandle."""
        self.assertIn("forwardRef<LogViewerHandle, LogViewerProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        self.assertIn("scrollToBottom,", self.source)
        self.assertIn("scrollToTop,", self.source)
        self.assertIn("clear:", self.source)
        self.assertIn("exportLogs:", self.source)
        self.assertIn("getLogs:", self.source)
        self.assertIn("addLog:", self.source)

    def test_typescript_types_present(self) -> None:
        """All required TypeScript type exports must be present."""
        expected_types = [
            "export type LogViewerVariant",
            "export type LogViewerSize",
            "export type LogLevel",
            "export interface LogEntry",
            "export interface LogViewerHandle",
            "export interface LogToolbarProps",
            "export interface LogEntryRowProps",
            "export interface LogViewerProps",
        ]
        for t in expected_types:
            self.assertIn(t, self.source, f"Missing TypeScript type export: {t}")

    def test_compound_and_alias_exports(self) -> None:
        """Must export LogViewer, LogStream, EventViewer, ConsoleLogs, LogToolbar, LogEntryRow, and default export."""
        self.assertIn("export const LogViewer =", self.source)
        self.assertIn("export const LogStream =", self.source)
        self.assertIn("export const EventViewer =", self.source)
        self.assertIn("export const ConsoleLogs =", self.source)
        self.assertIn("export const LogToolbar =", self.source)
        self.assertIn("export const LogEntryRow =", self.source)
        self.assertIn("export default LogViewerComponent", self.source)

    def test_display_names_defined(self) -> None:
        """Must define explicit displayName on all compound and alias exports."""
        self.assertIn("LogToolbar.displayName = 'LogToolbar'", self.source)
        self.assertIn("LogEntryRow.displayName = 'LogEntryRow'", self.source)
        self.assertIn("LogViewerComponent.displayName = 'LogViewer'", self.source)

    def test_variants_present(self) -> None:
        """Must define all 4 required visual styling variants: default, card, glass, neon."""
        self.assertIn("'default' | 'card' | 'glass' | 'neon'", self.source)
        self.assertIn("isNeon", self.source)
        self.assertIn("isGlass", self.source)
        self.assertIn("isCard", self.source)

    def test_sizes_present(self) -> None:
        """Must define sm, md, lg size scales."""
        self.assertIn("'sm' | 'md' | 'lg'", self.source)

    def test_wai_aria_accessibility(self) -> None:
        """Must include appropriate WAI-ARIA roles, labels, and live regions."""
        self.assertIn('role="log"', self.source)
        self.assertIn('aria-live="polite"', self.source)
        self.assertIn('role="region"', self.source)
        self.assertIn('role="toolbar"', self.source)
        self.assertIn('role="row"', self.source)
        self.assertIn('aria-label="Log stream entries"', self.source)

    def test_log_levels_and_level_colors(self) -> None:
        """Must define all 6 log levels: trace, debug, info, warn, error, fatal."""
        levels = ["trace", "debug", "info", "warn", "error", "fatal"]
        for lvl in levels:
            self.assertIn(f"'{lvl}'", self.source)
        self.assertIn("LEVEL_COLORS", self.source)

    def test_search_and_highlighting(self) -> None:
        """Must implement live search filtering and text substring highlighting."""
        self.assertIn("searchQuery", self.source)
        self.assertIn("<mark", self.source)
        self.assertIn("Search logs (regex/text)...", self.source)

    def test_autoscroll_and_paused_badge(self) -> None:
        """Must implement auto-scroll lock and floating unread resume badge when paused."""
        self.assertIn("autoScroll", self.source)
        self.assertIn("isPaused", self.source)
        self.assertIn("unreadCount", self.source)
        self.assertIn("New logs below", self.source)

    def test_metadata_drawer_and_copy(self) -> None:
        """Must support expandable structured JSON metadata drawer and copy to clipboard."""
        self.assertIn("isExpanded", self.source)
        self.assertIn("Structured Metadata", self.source)
        self.assertIn("navigator.clipboard.writeText", self.source)

    def test_export_and_clear_actions(self) -> None:
        """Must support export to TXT and JSON files, alongside clear logs."""
        self.assertIn("exportLogs", self.source)
        self.assertIn("handleExport", self.source)
        self.assertIn("handleClear", self.source)
        self.assertIn("application/json", self.source)
        self.assertIn("text/plain", self.source)

    def test_package_codegen_exports_render_log_viewer_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_log_viewer_component."""
        import omnistackai_agent_engine.codegen as cg

        self.assertTrue(hasattr(cg, "render_log_viewer_component"))
        self.assertTrue(callable(cg.render_log_viewer_component))
        self.assertIn("render_log_viewer_component", cg.__all__)
