"""Task R-287: Race-Safe Generated Detail Refetches.

The generated use<Entity> detail hook must cancel a superseded GET so a stale response cannot overwrite
the currently selected record. Mirrors the R-280 (LIST) / R-286 (LIST_BY) AbortController design, with
the internally owned signal passed AFTER caller options.
"""

import unittest

from omnistackai_agent_engine.application_ir.ir import (
    ApiEndpoint,
    ApplicationIR,
    Entity,
    Field,
    FieldType,
    HttpMethod,
    MobileProfile,
    Platform,
    ProjectStrategy,
    Role,
    Screen,
    WebStrategy,
    AdminStrategy,
    BackendStrategy,
    DatabaseStrategy,
    RepoStrategy,
)
from omnistackai_agent_engine.application_ir.examples import example_ir
from omnistackai_agent_engine.codegen import NextjsWebAdapter, render_hooks


def _make_ir(description: str = "Test App") -> ApplicationIR:
    entities = (
        Entity(
            name="Article",
            fields=(
                Field("id", FieldType.STRING, required=True),
                Field("title", FieldType.STRING, required=True),
                Field("body", FieldType.TEXT, required=False),
            ),
        ),
    )
    apis = (
        ApiEndpoint(HttpMethod.GET, "/articles", response_schema="Article"),
        ApiEndpoint(HttpMethod.GET, "/articles/{id}", response_schema="Article"),
    )
    screens = (
        Screen("article_detail", "admin", components=("detail",), actions=("view",)),
    )
    return ApplicationIR(
        name="Article Platform",
        description=description,
        platforms=(Platform.WEB,),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE,
            WebStrategy.NEXTJS,
            AdminStrategy.NONE,
            BackendStrategy.PYTHON,
            DatabaseStrategy.POSTGRES,
            RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        roles=(Role("admin"),),
        entities=entities,
        apis=apis,
        screens=screens,
    )


def _detail_hook(hooks: str, name: str = "Article") -> str:
    """Slice out the use<Entity> detail hook body for focused, unambiguous assertions."""
    start = hooks.index(f"export function use{name}(")
    # up to the next exported symbol (or end of file), keeping the leading "export"
    nxt = hooks.find("\nexport ", start + 1)
    return hooks[start:nxt] if nxt != -1 else hooks[start:]


class DetailHookCancellationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hook = _detail_hook(render_hooks(_make_ir()))

    def test_owns_abortcontroller_ref(self) -> None:
        self.assertIn("const abortRef = useRef<AbortController | null>(null);", self.hook)

    def test_aborts_previous_before_missing_id_reset(self) -> None:
        abort_at = self.hook.index("abortRef.current?.abort();")
        missing_at = self.hook.index("if (!id) {")
        self.assertLess(abort_at, missing_at, "must abort the previous request before the !id reset")

    def test_missing_id_branch_resets_record_error_and_loading(self) -> None:
        missing = self.hook[self.hook.index("if (!id) {"):self.hook.index("if (!id) {") + 200]
        self.assertIn("setData(null);", missing)
        self.assertIn("setError(null);", missing)
        self.assertIn("setLoading(false);", missing)

    def test_valid_id_creates_and_registers_controller(self) -> None:
        self.assertIn("const controller = new AbortController();", self.hook)
        self.assertIn("abortRef.current = controller;", self.hook)

    def test_signal_passed_after_caller_options(self) -> None:
        self.assertIn("const item = await api.getArticle(id, { ...options, signal: controller.signal });", self.hook)
        self.assertNotIn("api.getArticle(id, options)", self.hook)

    def test_stale_success_cannot_update_state(self) -> None:
        success_guard = self.hook.index("if (controller.signal.aborted) return;")
        set_data = self.hook.index("setData(item);")
        self.assertLess(success_guard, set_data, "aborted success must return before setData")

    def test_abort_error_is_ignored(self) -> None:
        self.assertIn('if (controller.signal.aborted || (err instanceof DOMException && err.name === "AbortError")) return;', self.hook)

    def test_only_active_request_clears_loading(self) -> None:
        self.assertIn("if (!controller.signal.aborted) setLoading(false);", self.hook)

    def test_effect_cleanup_aborts(self) -> None:
        self.assertIn("return () => abortRef.current?.abort();", self.hook)

    def test_public_shape_preserved(self) -> None:
        self.assertIn("export function useArticle(", self.hook)
        self.assertIn("id: string | null | undefined,", self.hook)
        self.assertIn("return { data, loading, error, refetch };", self.hook)


class DiffInvarianceTests(unittest.TestCase):
    def test_description_only_change_is_byte_identical(self) -> None:
        self.assertEqual(
            render_hooks(_make_ir(description="First description")),
            render_hooks(_make_ir(description="A completely different description")),
        )


class DemoProjectsTests(unittest.TestCase):
    def test_generated_project_detail_hook_is_race_safe(self) -> None:
        # End-to-end: the assembled lib/hooks.ts carries the race-safe detail hook when a GET-by-id exists.
        project = NextjsWebAdapter().generate(_make_ir())
        hooks = project.get("lib/hooks.ts").content
        hook = _detail_hook(hooks, "Article")
        self.assertIn("const abortRef = useRef<AbortController | null>(null);", hook)
        self.assertIn("const item = await api.getArticle(id, { ...options, signal: controller.signal });", hook)
        self.assertIn("return () => abortRef.current?.abort();", hook)

    def test_example_projects_still_generate(self) -> None:
        # The bundled examples have no GET-by-id detail hook; generation must remain unaffected (no crash,
        # no stray detail-hook cancellation wiring introduced).
        for name in ("minimal-blog", "rideshare-favourites"):
            hooks = render_hooks(example_ir(name))
            self.assertNotIn("): UseDetailState<", hooks)


if __name__ == "__main__":
    unittest.main()
