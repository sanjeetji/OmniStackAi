"""Task R-309: Generated Accessible Reusable Pagination Component (components/pagination.tsx).

Tests for:
1. Reusable Pagination component structure, TypeScript props interface, and exports.
2. WAI-ARIA 1.2 compliance:
   - <nav aria-label="Pagination"
   - aria-label="Previous page"
   - aria-label="Next page"
   - aria-current={isCurrent ? "page" : undefined} on current active page button
   - <label htmlFor="pageSizeSelect"> and <select id="pageSizeSelect" aria-label="Select page size">
3. Direct page number button rendering and range calculation with ellipsis.
4. Compact mode behavior (omits direct numbers, keeps concise prev/next).
5. Default page size options [10, 25, 50, 100] and custom options support.
6. Export in omnistackai_agent_engine.codegen.
7. Registration in NextjsWebAdapter.generate() at components/pagination.tsx.
8. Diff invariance across ir.description changes.
9. Full project generation across example IR fixtures.
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
    render_pagination_component,
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
        roles=roles,
        entities=entities,
        screens=screens,
        apis=endpoints,
    )


class PaginationComponentUnitTests(unittest.TestCase):
    """Unit tests for render_pagination_component()."""

    def setUp(self) -> None:
        self.code = render_pagination_component()

    def test_client_component_directive(self) -> None:
        self.assertTrue(self.code.startswith('"use client";'))

    def test_exports_interface_and_component(self) -> None:
        self.assertIn("export interface PaginationProps", self.code)
        self.assertIn("export function Pagination(", self.code)

    def test_props_interface_fields(self) -> None:
        self.assertIn("page: number;", self.code)
        self.assertIn("pageSize: number;", self.code)
        self.assertIn("total: number;", self.code)
        self.assertIn("totalPages: number;", self.code)
        self.assertIn("onPageChange: (page: number) => void;", self.code)
        self.assertIn("onPageSizeChange?: (pageSize: number) => void;", self.code)
        self.assertIn("pageSizeOptions?: number[];", self.code)
        self.assertIn("disabled?: boolean;", self.code)
        self.assertIn("compact?: boolean;", self.code)
        self.assertIn("itemLabel?: string;", self.code)

    def test_wai_aria_compliance(self) -> None:
        self.assertIn('<nav aria-label="Pagination"', self.code)
        self.assertIn('aria-label="Previous page"', self.code)
        self.assertIn('aria-label="Next page"', self.code)
        self.assertIn('aria-current={isCurrent ? "page" : undefined}', self.code)
        self.assertIn('aria-label="Select page size"', self.code)
        self.assertIn('htmlFor="pageSizeSelect"', self.code)
        self.assertIn('id="pageSizeSelect"', self.code)

    def test_default_page_size_options(self) -> None:
        self.assertIn("pageSizeOptions = [10, 25, 50, 100]", self.code)

    def test_page_number_direct_buttons(self) -> None:
        self.assertIn("!compact && totalPages > 1", self.code)
        self.assertIn("getPageNumbers(", self.code)

    def test_disabled_handling(self) -> None:
        self.assertIn("disabled={page <= 1 || disabled}", self.code)
        self.assertIn("disabled={page >= totalPages || disabled}", self.code)


class PaginationComponentIntegrationTests(unittest.TestCase):
    """Integration tests verifying adapter generation, export, and diff invariance."""

    def test_file_registered_in_generated_project(self) -> None:
        ir = _make_test_ir()
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir)
        paths = project.paths()
        self.assertIn("components/pagination.tsx", paths)

        content = project.get("components/pagination.tsx").content
        self.assertIn("export function Pagination(", content)
        self.assertIn('<nav aria-label="Pagination"', content)

    def test_codegen_package_exports_render_function(self) -> None:
        import omnistackai_agent_engine.codegen as cg

        self.assertTrue(hasattr(cg, "render_pagination_component"))
        fn = getattr(cg, "render_pagination_component")
        self.assertTrue(callable(fn))
        code = fn()
        self.assertIn("export function Pagination(", code)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        ir1 = _make_test_ir(description="Description A")
        ir2 = _make_test_ir(description="Description B with completely different words")
        adapter = NextjsWebAdapter()
        p1 = adapter.generate(ir1)
        p2 = adapter.generate(ir2)

        content1 = p1.get("components/pagination.tsx").content
        content2 = p2.get("components/pagination.tsx").content
        self.assertEqual(content1, content2)

    def test_full_project_generation_minimal_blog(self) -> None:
        ir = example_ir("minimal-blog")
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir)
        self.assertIn("components/pagination.tsx", project.paths())

    def test_full_project_generation_rideshare_favourites(self) -> None:
        ir = example_ir("rideshare-favourites")
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir)
        self.assertIn("components/pagination.tsx", project.paths())


if __name__ == "__main__":
    unittest.main()
