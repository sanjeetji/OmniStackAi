"""
R-384: Accessible Futuristic Reusable Chat & Real-Time Messaging Suite
Unit tests for render_chat_component and the generated components/chat.tsx.
"""
from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_chat_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter, _CHAT_COMPONENT


class TestChatComponent(unittest.TestCase):
    """Test suite for components/chat.tsx codegen (R-384)."""

    def setUp(self) -> None:
        self.code = render_chat_component()
        self.ir = example_ir("rideshare-favourites")
        project = NextjsWebAdapter().generate(self.ir)
        self.file = project.get("components/chat.tsx")

    # ------------------------------------------------------------------
    # 1. File is generated at the correct path
    # ------------------------------------------------------------------
    def test_file_generated(self):
        """components/chat.tsx must be emitted by NextjsWebAdapter."""
        ir = example_ir("minimal-blog")
        project = NextjsWebAdapter().generate(ir)
        paths = project.paths()
        self.assertIn("components/chat.tsx", paths)

    # ------------------------------------------------------------------
    # 2. Zero external npm dependencies (only 'react' imports allowed)
    # ------------------------------------------------------------------
    def test_zero_runtime_dependencies(self):
        """Only imports from 'react' are allowed — 0 external npm dependencies."""
        imports = re.findall(r'from\s+"([^"]+)"', self.code)
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
            "ChatVariant",
            "ChatSize",
            "MessageSender",
            "MessageStatus",
            "ChatAttachment",
            "ChatAction",
            "ChatMessage",
            "ChatConversation",
            "ChatHandle",
            "ChatProps",
            "ChatHeaderProps",
            "ChatMessageProps",
            "ChatInputProps",
            "ChatSidebarProps",
            "ChatMessageListProps",
        ]
        for t in required_types:
            self.assertIn(t, self.code, f"Missing TypeScript type: {t}")

    # ------------------------------------------------------------------
    # 4. All 4 visual variants present
    # ------------------------------------------------------------------
    def test_variants_present(self):
        """All four visual variants must be implemented: default, card, glass, neon."""
        for variant in ("default", "card", "glass", "neon"):
            self.assertIn(f'case "{variant}"', self.code, f"Missing variant: {variant}")

    # ------------------------------------------------------------------
    # 5. All 3 size scales present
    # ------------------------------------------------------------------
    def test_sizes_present(self):
        """All three size scales must be configured: sm, md, lg."""
        for size in ("sm", "md", "lg"):
            self.assertIn(f'case "{size}"', self.code, f"Missing size: {size}")

    # ------------------------------------------------------------------
    # 6. Compound and semantic alias exports present
    # ------------------------------------------------------------------
    def test_compound_exports(self):
        """All compound and semantic alias exports must be present."""
        exports = [
            "export const Chat",
            "export const ChatWindow",
            "export const Messenger",
            "export const ChatWidget",
            "export const ChatHeader",
            "export const ChatSidebar",
            "export const ChatMessageItem",
            "export const ChatInput",
            "export const ChatMessageList",
        ]
        for exp in exports:
            self.assertIn(exp, self.code, f"Missing export: {exp}")

    # ------------------------------------------------------------------
    # 7. Default export present
    # ------------------------------------------------------------------
    def test_default_export(self):
        """A default export must be present."""
        self.assertIn("export default ChatComponent", self.code)

    # ------------------------------------------------------------------
    # 8. WAI-ARIA 1.2 log semantics present
    # ------------------------------------------------------------------
    def test_aria_log_semantics(self):
        """WAI-ARIA 1.2 log & list semantics must be present."""
        for attr in ('role="log"', 'aria-live="polite"', 'role="list"', 'role="listitem"', 'aria-label'):
            self.assertIn(attr, self.code, f"Missing ARIA attribute: {attr}")

    # ------------------------------------------------------------------
    # 9. forwardRef and useImperativeHandle present
    # ------------------------------------------------------------------
    def test_forward_ref_and_imperative_handle(self):
        """forwardRef and useImperativeHandle must be used for the imperative handle API."""
        self.assertIn("forwardRef", self.code)
        self.assertIn("useImperativeHandle", self.code)

    # ------------------------------------------------------------------
    # 10. Message status indicators present
    # ------------------------------------------------------------------
    def test_status_indicators(self):
        """Sent, delivered, read, sending status indicators must be supported."""
        for status in ('"sending"', '"sent"', '"delivered"', '"read"', '"failed"'):
            self.assertIn(status, self.code, f"Missing status indicator: {status}")

    # ------------------------------------------------------------------
    # 11. Typing indicator present
    # ------------------------------------------------------------------
    def test_typing_indicator(self):
        """Typing indicator with animated pulsing dots must be implemented."""
        self.assertIn("is typing...", self.code)
        self.assertIn("animation", self.code)

    # ------------------------------------------------------------------
    # 12. Imperative handle methods present
    # ------------------------------------------------------------------
    def test_imperative_handle_methods(self):
        """Imperative handle must expose scrollToBottom, clearInput, focusInput, appendMessage."""
        for method in ("scrollToBottom", "clearInput", "focusInput", "appendMessage"):
            self.assertIn(method, self.code, f"Missing imperative handle method: {method}")

    # ------------------------------------------------------------------
    # 13. Keyboard interaction support
    # ------------------------------------------------------------------
    def test_keyboard_shortcuts(self):
        """Enter to send and Shift+Enter for newline must be supported."""
        self.assertIn('e.key === "Enter"', self.code)
        self.assertIn("!e.shiftKey", self.code)

    # ------------------------------------------------------------------
    # 14. Multi-thread conversation sidebar present
    # ------------------------------------------------------------------
    def test_conversation_sidebar(self):
        """Sidebar with conversation filter and unread badge count must be supported."""
        self.assertIn("ChatSidebarInner", self.code)
        self.assertIn("unreadCount", self.code)
        self.assertIn("Search threads...", self.code)

    # ------------------------------------------------------------------
    # 15. 'use client' directive present
    # ------------------------------------------------------------------
    def test_use_client_directive(self):
        """'use client' must be the first statement for Next.js App Router."""
        self.assertTrue(
            self.code.startswith('"use client"') or self.code.startswith("'use client'"),
            "Component file must start with 'use client' directive",
        )

    # ------------------------------------------------------------------
    # 16. Display names present on exports
    # ------------------------------------------------------------------
    def test_display_names(self):
        """All compound exports must have explicit displayName properties."""
        for name in ("Chat", "ChatWindow", "Messenger", "ChatWidget", "ChatHeader", "ChatSidebar", "ChatMessageItem", "ChatInput", "ChatMessageList"):
            self.assertIn(f'{name}.displayName = "{name}"', self.code, f"Missing displayName for {name}")

    # ------------------------------------------------------------------
    # 17. 100% diff-invariance across ir.description
    # ------------------------------------------------------------------
    def test_diff_invariance_across_description(self):
        """Generated chat content must be identical regardless of ir.description."""
        ir_a = example_ir("rideshare-favourites")
        ir_b = example_ir("minimal-blog")
        project_a = NextjsWebAdapter().generate(ir_a)
        project_b = NextjsWebAdapter().generate(ir_b)
        content_a = project_a.get("components/chat.tsx")
        content_b = project_b.get("components/chat.tsx")
        self.assertIsNotNone(content_a)
        self.assertIsNotNone(content_b)
        self.assertEqual(
            content_a.content,
            content_b.content,
            "components/chat.tsx must be diff-invariant across ir.description changes",
        )


if __name__ == "__main__":
    unittest.main()
