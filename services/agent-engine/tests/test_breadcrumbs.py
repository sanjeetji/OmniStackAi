"""Task R-306: Generated Accessible Breadcrumb Navigation Component & Screen Hierarchy.

Tests for:
1. Reusable Breadcrumbs component structure and WAI-ARIA compliance
2. NextjsWebAdapter generates components/breadcrumbs.tsx
3. Detail screen renders Breadcrumbs with Overview, Collection, and Record hierarchy
4. Detail screen gracefully handles absence of collection screen in breadcrumbs
5. Form screen renders Breadcrumbs with Overview, Collection, and New/Edit action hierarchy
6. Form screen gracefully handles absence of collection screen in breadcrumbs
7. Strict diff invariance across ir.description modifications
8. Public render_breadcrumbs_component export in codegen
"""

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
from omnistackai_agent_engine.codegen import render_breadcrumbs_component
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
    render_screen_page,
)


_STRATEGY = ProjectStrategy(
    MobileProfile.NONE,
    WebStrategy.NEXTJS,
    AdminStrategy.NONE,
    BackendStrategy.GO,
    DatabaseStrategy.POSTGRES,
    RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)


def _make_test_ir(
    with_collection_screen: bool = True,
    with_detail_screen: bool = True,
    with_form_screen: bool = True,
    with_update: bool = True,
    description: str = "Test Blog Application",
) -> ApplicationIR:
    entities = (
        Entity(
            "Post",
            (
                Field("id", FieldType.STRING, required=True),
                Field("title", FieldType.STRING, required=True),
                Field("content", FieldType.TEXT, required=False),
            ),
        ),
    )

    screens = []
    if with_collection_screen:
        screens.append(Screen("posts", "member", components=("list", "table")))
    if with_detail_screen:
        screens.append(Screen("post_detail", "member", components=("detail", "card")))
    if with_form_screen:
        screens.append(Screen("post_editor", "member", components=("form",), actions=("create", "update" if with_update else "")))

    endpoints = [
        ApiEndpoint(HttpMethod.GET, "/posts", False, response_schema="Post"),
        ApiEndpoint(HttpMethod.POST, "/posts", False, request_schema="Post", response_schema="Post"),
        ApiEndpoint(HttpMethod.GET, "/posts/{id}", False, response_schema="Post"),
    ]
    if with_update:
        endpoints.append(
            ApiEndpoint(HttpMethod.PUT, "/posts/{id}", False, request_schema="Post", response_schema="Post")
        )

    return ApplicationIR(
        name="TestApp",
        description=description,
        platforms=(Platform.WEB,),
        project_strategy=_STRATEGY,
        roles=(Role("member", ("read", "write")),),
        entities=entities,
        screens=tuple(screens),
        apis=tuple(endpoints),
    )


class BreadcrumbsTests(unittest.TestCase):
    """Unit tests for R-306 Breadcrumbs component and screen integration."""

    def test_render_breadcrumbs_component_structure(self) -> None:
        """Verify the breadcrumbs template has correct exports, types, and ARIA markup."""
        code = render_breadcrumbs_component()
        self.assertIn('"use client";', code)
        self.assertIn("export interface BreadcrumbItem", code)
        self.assertIn("label: string;", code)
        self.assertIn("href?: string;", code)
        self.assertIn("export interface BreadcrumbsProps", code)
        self.assertIn("items: BreadcrumbItem[];", code)
        self.assertIn("export function Breadcrumbs(", code)
        self.assertIn('<nav aria-label="Breadcrumb"', code)
        self.assertIn("<ol", code)
        self.assertIn("<li", code)
        self.assertIn('aria-hidden="true"', code)
        self.assertIn('aria-current={isLast ? "page" : undefined}', code)
        self.assertIn("<Link", code)

    def test_breadcrumbs_in_generated_files(self) -> None:
        """Verify NextjsWebAdapter generates components/breadcrumbs.tsx."""
        ir = _make_test_ir()
        adapter = NextjsWebAdapter()
        proj = adapter.generate(ir)
        paths = set(proj.paths())
        self.assertIn("components/breadcrumbs.tsx", paths)

    def test_detail_screen_renders_breadcrumbs_with_collection(self) -> None:
        """Verify detail screen renders Breadcrumbs with Overview and Collection links."""
        ir = _make_test_ir(with_collection_screen=True)
        screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(screen, ir)

        self.assertIn('import { Breadcrumbs } from "../components/breadcrumbs";', content)
        self.assertIn("<Breadcrumbs items={breadcrumbs} />", content)
        self.assertIn('{ label: "Overview", href: "/" }', content)
        self.assertIn('{ label: "Posts", href: "/posts" }', content)
        self.assertIn('{ label: selectedId ? `Post #${selectedId}` : "Post Details" }', content)

    def test_detail_screen_renders_breadcrumbs_without_collection(self) -> None:
        """Verify detail screen breadcrumbs gracefully omit collection link when absent."""
        ir = _make_test_ir(with_collection_screen=False)
        screen = next(s for s in ir.screens if s.id == "post_detail")
        content = render_screen_page(screen, ir)

        self.assertIn('import { Breadcrumbs } from "../components/breadcrumbs";', content)
        self.assertIn("<Breadcrumbs items={breadcrumbs} />", content)
        self.assertIn('{ label: "Overview", href: "/" }', content)
        self.assertNotIn('{ label: "Posts", href: "/posts" }', content)
        self.assertIn('{ label: selectedId ? `Post #${selectedId}` : "Post Details" }', content)

    def test_form_screen_renders_breadcrumbs_create_mode(self) -> None:
        """Verify form screen renders Breadcrumbs with New/Edit item label."""
        ir = _make_test_ir(with_collection_screen=True, with_update=True)
        screen = next(s for s in ir.screens if s.id == "post_editor")
        content = render_screen_page(screen, ir)

        self.assertIn('import { Breadcrumbs } from "../components/breadcrumbs";', content)
        self.assertIn("<Breadcrumbs items={breadcrumbs} />", content)
        self.assertIn('{ label: "Overview", href: "/" }', content)
        self.assertIn('{ label: "Posts", href: "/posts" }', content)
        self.assertIn('isEdit ? "Edit Post" : "New Post"', content)

    def test_form_screen_renders_breadcrumbs_without_collection(self) -> None:
        """Verify form screen breadcrumbs gracefully omit collection link when absent."""
        ir = _make_test_ir(with_collection_screen=False)
        screen = next(s for s in ir.screens if s.id == "post_editor")
        content = render_screen_page(screen, ir)

        self.assertIn('import { Breadcrumbs } from "../components/breadcrumbs";', content)
        self.assertIn("<Breadcrumbs items={breadcrumbs} />", content)
        self.assertIn('{ label: "Overview", href: "/" }', content)
        self.assertNotIn('{ label: "Posts", href: "/posts" }', content)
        self.assertIn("New Post", content)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        """Verify breadcrumbs component and screen pages are diff-invariant across IR description."""
        ir1 = _make_test_ir(description="Description A")
        ir2 = _make_test_ir(description="Description B")

        adapter = NextjsWebAdapter()
        proj1 = adapter.generate(ir1)
        proj2 = adapter.generate(ir2)

        self.assertEqual(
            proj1.get("components/breadcrumbs.tsx").content,
            proj2.get("components/breadcrumbs.tsx").content,
        )
        self.assertEqual(
            proj1.get("app/post_detail/page.tsx").content,
            proj2.get("app/post_detail/page.tsx").content,
        )
        self.assertEqual(
            proj1.get("app/post_editor/page.tsx").content,
            proj2.get("app/post_editor/page.tsx").content,
        )


class FullProjectBreadcrumbsTests(unittest.TestCase):
    """Integration tests verifying components/breadcrumbs.tsx in full projects."""

    def test_full_project_includes_breadcrumbs_in_minimal_blog(self) -> None:
        """minimal-blog generated project includes components/breadcrumbs.tsx and screen breadcrumbs."""
        ir = example_ir("minimal-blog")
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir)
        self.assertIn("components/breadcrumbs.tsx", set(project.paths()))
        content = project.get("components/breadcrumbs.tsx").content
        self.assertIn("export function Breadcrumbs", content)
        self.assertIn('<nav aria-label="Breadcrumb"', content)

        # Check post_editor imports and mounts Breadcrumbs
        post_editor = project.get("app/post_editor/page.tsx").content
        self.assertIn('import { Breadcrumbs } from "../components/breadcrumbs";', post_editor)
        self.assertIn("<Breadcrumbs items={breadcrumbs} />", post_editor)

    def test_full_project_includes_breadcrumbs_in_rideshare(self) -> None:
        """rideshare-favourites generated project includes components/breadcrumbs.tsx."""
        ir = example_ir("rideshare-favourites")
        adapter = NextjsWebAdapter()
        project = adapter.generate(ir)
        self.assertIn("components/breadcrumbs.tsx", set(project.paths()))
        content = project.get("components/breadcrumbs.tsx").content
        self.assertIn("export function Breadcrumbs", content)


if __name__ == "__main__":
    unittest.main()
