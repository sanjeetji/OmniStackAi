"""Task R-299: Generated Form Screen Keyboard Shortcuts.

Verifies keyboard navigation and shortcuts in generated Next.js form screens:
- Cmd+Enter / Ctrl+Enter triggers form submission (requestSubmit).
- Cmd+S / Ctrl+S triggers form submission and prevents browser Save Page As dialog.
- Escape blurs active input/textarea/select when focused.
- Escape outside inputs triggers Cancel navigation to cancel_href with unsaved changes prompt if dirty.
- Proper window keydown event listener cleanup on unmount.
- Preserves 100% diff-invariance across ir.description changes.
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
from omnistackai_agent_engine.codegen import NextjsWebAdapter, render_screen_page


_STRATEGY = ProjectStrategy(
    MobileProfile.NONE,
    WebStrategy.NEXTJS,
    AdminStrategy.NONE,
    BackendStrategy.PYTHON,
    DatabaseStrategy.POSTGRES,
    RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)


def _ir(can_update: bool = True, can_create: bool = True, description: str = "Test App") -> ApplicationIR:
    fields = [
        Field("id", FieldType.UUID),
        Field("title", FieldType.STRING, required=True),
        Field("content", FieldType.TEXT),
    ]
    apis = []
    if can_create:
        apis.append(ApiEndpoint(HttpMethod.POST, "/posts", request_schema="Post", response_schema="Post"))
    if can_update:
        apis.append(ApiEndpoint(HttpMethod.PUT, "/posts/{id}", request_schema="Post", response_schema="Post"))
        apis.append(ApiEndpoint(HttpMethod.GET, "/posts/{id}", response_schema="Post"))

    entities = (Entity("Post", tuple(fields)),)
    screens = [
        Screen("post_form", "admin", components=("form",)),
        Screen("post_list", "admin", components=("collection",)),
    ]

    return ApplicationIR(
        name="Post Platform",
        description=description,
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=_STRATEGY,
        roles=(Role("admin"),),
        entities=entities,
        apis=tuple(apis),
        screens=tuple(screens),
    )


def _render(can_update: bool = True, can_create: bool = True, description: str = "Test App") -> str:
    app_ir = _ir(can_update=can_update, can_create=can_create, description=description)
    return render_screen_page(app_ir.screens[0], app_ir)


class FormKeyboardShortcutsTests(TestCase):
    def test_form_screen_wires_save_shortcuts(self) -> None:
        page = _render(can_update=True, can_create=True)
        self.assertIn('e.metaKey || e.ctrlKey', page)
        self.assertIn('e.key === "Enter" || e.key === "s" || e.key === "S"', page)
        self.assertIn('requestSubmit', page)

    def test_form_screen_wires_escape_shortcut(self) -> None:
        page = _render(can_update=True, can_create=True)
        self.assertIn('e.key === "Escape"', page)
        self.assertIn('active.blur()', page)
        self.assertIn('window.location.href =', page)
        self.assertIn('You have unsaved changes. Discard them and leave?', page)

    def test_submitting_guard_present(self) -> None:
        page = _render(can_update=True, can_create=True)
        self.assertIn('!(submitting || updating)', page)

    def test_listener_cleanup_registered(self) -> None:
        page = _render(can_update=True, can_create=True)
        self.assertIn('window.addEventListener("keydown", handleKeyDown);', page)
        self.assertIn('window.removeEventListener("keydown", handleKeyDown);', page)

    def test_create_only_form_uses_submitting_guard(self) -> None:
        page = _render(can_update=False, can_create=True)
        self.assertIn('!submitting', page)
        self.assertIn('e.key === "Enter" || e.key === "s" || e.key === "S"', page)

    def test_diff_invariance_across_ir_description(self) -> None:
        page1 = _render(description="First description")
        page2 = _render(description="Second completely distinct description")
        self.assertEqual(page1, page2)

    def test_example_projects_still_generate(self) -> None:
        for name in ("minimal-blog", "rideshare-favourites"):
            proj = NextjsWebAdapter().generate(example_ir(name))
            self.assertTrue(any(p.endswith("page.tsx") for p in proj.paths()))


if __name__ == "__main__":
    import unittest
    unittest.main()
