"""Unit tests for Knowledge & Skills context assembly and truncation (F-04 / R-502).

100% offline, standard library unittest.
"""

from __future__ import annotations

import os
import unittest

from omnistackai_agent_engine.intake.context import (
    DEFAULT_CONTEXT_MAX_CHARS,
    assemble_context,
    get_context_max_chars,
)


class TestSkillsContextAssembly(unittest.TestCase):
    def test_empty_or_none_context(self) -> None:
        text, truncated, active, cut = assemble_context(None)
        self.assertEqual(text, "")
        self.assertFalse(truncated)
        self.assertEqual(active, [])
        self.assertEqual(cut, [])

        text, truncated, active, cut = assemble_context({})
        self.assertEqual(text, "")
        self.assertFalse(truncated)
        self.assertEqual(active, [])
        self.assertEqual(cut, [])

    def test_knowledge_only(self) -> None:
        ctx = {"knowledge": "Target audience is Indian SME retailers."}
        text, truncated, active, cut = assemble_context(ctx)
        expected = "## Project knowledge\nTarget audience is Indian SME retailers."
        self.assertEqual(text, expected)
        self.assertFalse(truncated)
        self.assertEqual(active, [])
        self.assertEqual(cut, [])

    def test_skills_only(self) -> None:
        ctx = {
            "skills": [
                {"name": "design-system", "body": "Use Tailwind and shadcn."},
                {"name": "backend-rules", "body": "Use Go and Postgres."},
            ]
        }
        text, truncated, active, cut = assemble_context(ctx)
        expected = (
            "## Active skills\n\n"
            "### design-system\n"
            "Use Tailwind and shadcn.\n\n"
            "### backend-rules\n"
            "Use Go and Postgres."
        )
        self.assertEqual(text, expected)
        self.assertFalse(truncated)
        self.assertEqual(active, ["design-system", "backend-rules"])
        self.assertEqual(cut, [])

    def test_knowledge_and_skills_combined(self) -> None:
        ctx = {
            "knowledge": "Always add dark mode.",
            "skills": [
                {"name": "design-system", "body": "Use OKLCH palette."},
            ],
        }
        text, truncated, active, cut = assemble_context(ctx)
        expected = (
            "## Project knowledge\n"
            "Always add dark mode.\n\n"
            "## Active skills\n\n"
            "### design-system\n"
            "Use OKLCH palette."
        )
        self.assertEqual(text, expected)
        self.assertFalse(truncated)
        self.assertEqual(active, ["design-system"])
        self.assertEqual(cut, [])

    def test_truncation_when_exceeding_max_chars(self) -> None:
        # Budget = 120 chars
        ctx = {
            "knowledge": "Project Brief: Healthcare app.",
            "skills": [
                {"name": "hipaa-rules", "body": "Strict data privacy and encryption at rest."},
                {"name": "extra-skill", "body": "This skill should be truncated or cut."},
            ],
        }
        limit = 110
        text, truncated, active, cut = assemble_context(ctx, max_chars=limit)
        self.assertTrue(truncated)
        self.assertLessEqual(len(text), limit)
        self.assertIn("## Project knowledge", text)
        self.assertIn("Project Brief: Healthcare app.", text)
        self.assertIn("hipaa-rules", text)
        self.assertIn("extra-skill", cut)

    def test_truncation_drops_oversized_skills(self) -> None:
        ctx = {
            "knowledge": "Short knowledge.",
            "skills": [
                {"name": "skill-1", "body": "A" * 50},
                {"name": "skill-2", "body": "B" * 50},
                {"name": "skill-3", "body": "C" * 50},
            ],
        }
        # Force a small limit that fits skill-1 but cuts skill-2 and skill-3
        limit = 120
        text, truncated, active, cut = assemble_context(ctx, max_chars=limit)
        self.assertTrue(truncated)
        self.assertLessEqual(len(text), limit)
        self.assertIn("skill-1", active)
        self.assertIn("skill-3", cut)

    def test_default_context_max_chars_env_override(self) -> None:
        old_val = os.environ.get("OMNISTACKAI_CONTEXT_MAX_CHARS")
        try:
            os.environ["OMNISTACKAI_CONTEXT_MAX_CHARS"] = "15000"
            self.assertEqual(get_context_max_chars(), 15000)
            os.environ.pop("OMNISTACKAI_CONTEXT_MAX_CHARS", None)
            self.assertEqual(get_context_max_chars(), DEFAULT_CONTEXT_MAX_CHARS)
        finally:
            if old_val is not None:
                os.environ["OMNISTACKAI_CONTEXT_MAX_CHARS"] = old_val

    def test_build_intake_messages_injects_context(self) -> None:
        from omnistackai_agent_engine.intake.nl_to_ir import build_intake_messages

        ctx = {
            "knowledge": "Users are Indian SME merchants.",
            "skills": [{"name": "design-system", "body": "Use warm saffron highlights."}],
        }
        text, truncated, active, cut = assemble_context(ctx)
        messages = build_intake_messages("Build an inventory app", context_text=text)
        self.assertEqual(len(messages), 2)
        system_msg, user_msg = messages[0], messages[1]
        self.assertIn("## Project knowledge\nUsers are Indian SME merchants.", system_msg.content)
        self.assertIn("### design-system\nUse warm saffron highlights.", system_msg.content)
        self.assertIn("Application description:\nBuild an inventory app", user_msg.content)

    def test_build_app_delta_messages_injects_context(self) -> None:
        from omnistackai_agent_engine.application_ir.examples import example_ir
        from omnistackai_agent_engine.intake.app_delta import build_app_delta_messages

        base_ir = example_ir("minimal-blog")
        ctx = {
            "knowledge": "Never remove dark mode.",
            "skills": [{"name": "coding-standards", "body": "Use strict typing."}],
        }
        text, truncated, active, cut = assemble_context(ctx)
        system_msg, user_msg = build_app_delta_messages(base_ir, "Add comments to posts", context_text=text)
        self.assertIn("## Project knowledge\nNever remove dark mode.", system_msg.content)
        self.assertIn("### coding-standards\nUse strict typing.", system_msg.content)
        self.assertIn("Requested change:\nAdd comments to posts", user_msg.content)


if __name__ == "__main__":
    unittest.main()
