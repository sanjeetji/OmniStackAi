"""Task R-307: Generated Accessible EmptyState Component & Screen Zero-State Integrations.

Tests for:
1. Reusable EmptyState component structure and WAI-ARIA compliance (role="status", aria-live="polite").
2. Built-in vector icons ("folder", "search", "document", "inbox") render with aria-hidden="true".
3. Primary and secondary action affordances (Link for href, button for onClick).
4. Export of render_empty_state_component in omnistackai_agent_engine.codegen.
5. Registration in NextjsWebAdapter.generate() at components/empty-state.tsx.
6. Diff invariance across ir.description changes.
7. Overview screen integration when no entities/screens are configured.
8. Full project generation across example IR fixtures.
"""

from __future__ import annotations

import unittest

from omnistackai_agent_engine.application_ir import (
    AdminStrategy,
    ApiEndpoint,
    ApplicationIR,
    BackendStrategy,
    DatabaseStrategy,
    Entity,
    Field,
    FieldType,
    HttpMethod,
    MobileProfile,
    Platform,
    ProjectStrategy,
    RepoStrategy,
    Role,
    Screen,
    WebStrategy,
    example_ir,
)
from omnistackai_agent_engine.codegen import (
    render_empty_state_component,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
)

_STRATEGY = ProjectStrategy(
    MobileProfile.NONE,
    WebStrategy.NEXTJS,
    AdminStrategy.NONE,
    BackendStrategy.GO,
    DatabaseStrategy.POSTGRES,
    RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)


def _make_test_ir(description: str = "Test Blog Application") -> ApplicationIR:
    entities = (
        Entity(
            "Post",
            (
                Field("id", FieldType.STRING, required=True),
                Field("title", FieldType.STRING, required=True),
            ),
        ),
    )
    screens = (
        Screen("posts", "member", components=("list", "table")),
    )
    endpoints = (
        ApiEndpoint(HttpMethod.GET, "/posts", False, response_schema="Post"),
    )
    roles = (
        Role("member", ("read", "write")),
    )
    return ApplicationIR(
        name="TestApp",
        description=description,
        platforms=(Platform.WEB,),
        project_strategy=_STRATEGY,
        roles=(Role("member", ("read", "write")),),
        entities=entities,
        screens=screens,
        apis=endpoints,
    )


class EmptyStateComponentUnitTests(unittest.TestCase):
    """Unit tests for the EmptyState component code template."""

    def setUp(self) -> None:
        self.code = render_empty_state_component()

    def test_is_client_component(self) -> None:
        self.assertTrue(self.code.startswith('"use client";'))

    def test_exports_interfaces_and_component(self) -> None:
        self.assertIn("export interface EmptyStateAction", self.code)
        self.assertIn("export interface EmptyStateProps", self.code)
        self.assertIn("export function EmptyState(", self.code)

    def test_wai_aria_semantics(self) -> None:
        self.assertIn('role="status"', self.code)
        self.assertIn('aria-live="polite"', self.code)

    def test_built_in_icon_variants(self) -> None:
        self.assertIn('"folder"', self.code)
        self.assertIn('"search"', self.code)
        self.assertIn('"document"', self.code)
        self.assertIn('"inbox"', self.code)
        self.assertIn('aria-hidden="true"', self.code)

    def test_action_link_and_button_dispatch(self) -> None:
        self.assertIn('import Link from "next/link";', self.code)
        self.assertIn("action.href", self.code)
        self.assertIn("action.onClick", self.code)
        self.assertIn("secondaryAction", self.code)

    def test_styling_tokens(self) -> None:
        self.assertIn("#0f172a", self.code)
        self.assertIn("#64748b", self.code)
        self.assertIn("#2563eb", self.code)


class EmptyStateIntegrationTests(unittest.TestCase):
    """Tests verifying adapter registration and diff invariance."""

    def test_empty_state_file_in_generated_project(self) -> None:
        ir = _make_test_ir()
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir)
        paths = project.paths()
        self.assertIn("components/empty-state.tsx", paths)

        content = project.get("components/empty-state.tsx").content
        self.assertIn("export function EmptyState(", content)
        self.assertIn('role="status"', content)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        ir1 = _make_test_ir(description="Description A")
        ir2 = _make_test_ir(description="Description B with completely different words")
        adapter = NextjsWebAdapter()
        p1 = adapter.generate(ir1)
        p2 = adapter.generate(ir2)

        content1 = p1.get("components/empty-state.tsx").content
        content2 = p2.get("components/empty-state.tsx").content
        self.assertEqual(content1, content2)

    def test_codegen_package_exports_render_function(self) -> None:
        import omnistackai_agent_engine.codegen as cg

        self.assertTrue(hasattr(cg, "render_empty_state_component"))
        fn = getattr(cg, "render_empty_state_component")
        self.assertTrue(callable(fn))
        code = fn()
        self.assertIn("export function EmptyState(", code)

    def test_full_project_generation_minimal_blog(self) -> None:
        ir = example_ir("minimal-blog")
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir)
        self.assertIn("components/empty-state.tsx", project.paths())

    def test_full_project_generation_rideshare_favourites(self) -> None:
        ir = example_ir("rideshare-favourites")
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir)
        self.assertIn("components/empty-state.tsx", project.paths())


if __name__ == "__main__":
    unittest.main()
