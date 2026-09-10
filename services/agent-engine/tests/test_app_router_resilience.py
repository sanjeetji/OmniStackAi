"""Task R-294: Next.js App Router resilience special files.

The generated web app must ship the four App Router "special files": app/error.tsx,
app/global-error.tsx, app/not-found.tsx, and app/loading.tsx. They are static, inline-styled,
dependency-free, and never reference ir.description or ir.name (so generation is deterministic and
description-only-stable, and they never enter the console-snapshot description-edit diff set).
"""

from unittest import TestCase

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
    NextjsWebAdapter,
    render_error_page,
    render_global_error_page,
    render_loading_page,
    render_not_found_page,
)


_STRATEGY = ProjectStrategy(
    MobileProfile.NONE, WebStrategy.NEXTJS, AdminStrategy.NONE,
    BackendStrategy.PYTHON, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)


def _ir(name: str = "Blog App", description: str = "Blog") -> ApplicationIR:
    return ApplicationIR(
        name=name,
        description=description,
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=_STRATEGY,
        roles=(Role("member"),),
        entities=(Entity("Post", (Field("id", FieldType.UUID), Field("title", FieldType.STRING))),),
        apis=(
            ApiEndpoint(HttpMethod.GET, "/posts", response_schema="Post"),
            ApiEndpoint(HttpMethod.POST, "/posts", request_schema="Post", response_schema="Post"),
        ),
        screens=(Screen("post_list", "member", components=("list",), actions=("view",)),),
    )


class GeneratedFilesPresentTests(TestCase):
    def setUp(self) -> None:
        self.project = NextjsWebAdapter().generate(_ir())
        self.paths = set(self.project.paths())

    def test_all_four_special_files_present(self) -> None:
        for path in ("app/error.tsx", "app/global-error.tsx", "app/not-found.tsx", "app/loading.tsx"):
            self.assertIn(path, self.paths)

    def test_error_page_is_client_with_reset(self) -> None:
        content = self.project.get("app/error.tsx").content
        self.assertTrue(content.startswith('"use client";'))
        self.assertIn("{ error, reset }", content)
        self.assertIn("error: Error & { digest?: string }; reset: () => void", content)
        self.assertIn("reset()", content)
        self.assertIn("console.error(error)", content)
        self.assertIn('href="/"', content)

    def test_global_error_page_renders_own_html_body(self) -> None:
        content = self.project.get("app/global-error.tsx").content
        self.assertTrue(content.startswith('"use client";'))
        self.assertIn("<html lang=\"en\">", content)
        self.assertIn("<body", content)
        self.assertIn("reset()", content)

    def test_not_found_is_server_component_with_link(self) -> None:
        content = self.project.get("app/not-found.tsx").content
        self.assertNotIn('"use client"', content)
        self.assertIn("404", content)
        self.assertIn('href="/"', content)

    def test_loading_is_server_component_with_skeletons(self) -> None:
        content = self.project.get("app/loading.tsx").content
        self.assertNotIn('"use client"', content)
        self.assertIn(".map((i) =>", content)
        self.assertIn('background: "#f1f5f9"', content)
        self.assertIn("opacity: 1 - i *", content)


class DeterminismTests(TestCase):
    def test_render_functions_are_static_and_stable(self) -> None:
        self.assertEqual(render_error_page(), render_error_page())
        self.assertEqual(render_global_error_page(), render_global_error_page())
        self.assertEqual(render_not_found_page(), render_not_found_page())
        self.assertEqual(render_loading_page(), render_loading_page())

    def test_special_files_never_reference_description_or_name(self) -> None:
        # A unique name + description must not leak into any of the four files.
        proj = NextjsWebAdapter().generate(_ir(name="ZZUNIQUENAME", description="ZZUNIQUEDESC"))
        for path in ("app/error.tsx", "app/global-error.tsx", "app/not-found.tsx", "app/loading.tsx"):
            content = proj.get(path).content
            self.assertNotIn("ZZUNIQUENAME", content)
            self.assertNotIn("ZZUNIQUEDESC", content)

    def test_special_files_byte_identical_across_description_changes(self) -> None:
        a = NextjsWebAdapter().generate(_ir(description="First description"))
        b = NextjsWebAdapter().generate(_ir(description="A completely different description"))
        for path in ("app/error.tsx", "app/global-error.tsx", "app/not-found.tsx", "app/loading.tsx"):
            self.assertEqual(a.get(path).content, b.get(path).content, f"{path} differed across description changes!")


class ExampleProjectsTests(TestCase):
    def test_example_projects_include_special_files(self) -> None:
        for name in ("minimal-blog", "rideshare-favourites"):
            proj = NextjsWebAdapter().generate(example_ir(name))
            paths = set(proj.paths())
            for path in ("app/error.tsx", "app/global-error.tsx", "app/not-found.tsx", "app/loading.tsx"):
                self.assertIn(path, paths, f"{name} missing {path}")


if __name__ == "__main__":
    import unittest

    unittest.main()
