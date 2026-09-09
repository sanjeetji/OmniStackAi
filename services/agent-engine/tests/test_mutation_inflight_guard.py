"""Task R-288: Deduplicated In-Flight Generated Mutation Requests.

The generated useCreate/useUpdate/useDelete hooks must dedupe concurrent invocations: while a mutation
is in flight, a second call returns the pending promise instead of firing a duplicate POST/PUT/DELETE.
Return shape and the underlying api call are preserved. Deterministic / description-only stable.
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
from omnistackai_agent_engine.codegen import render_hooks


def _make_ir(description: str = "Test App") -> ApplicationIR:
    entities = (
        Entity(
            name="Article",
            fields=(
                Field("id", FieldType.STRING, required=True),
                Field("title", FieldType.STRING, required=True),
            ),
        ),
    )
    apis = (
        ApiEndpoint(HttpMethod.GET, "/articles", response_schema="Article"),
        ApiEndpoint(HttpMethod.POST, "/articles", request_schema="Article", response_schema="Article"),
        ApiEndpoint(HttpMethod.PUT, "/articles/{id}", request_schema="Article", response_schema="Article"),
        ApiEndpoint(HttpMethod.DELETE, "/articles/{id}", response_schema="Article"),
    )
    screens = (
        Screen("article_form", "admin", components=("form",), actions=("create", "update")),
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


def _hook(hooks: str, name: str) -> str:
    start = hooks.index(f"export function {name}(")
    nxt = hooks.find("\nexport ", start + 1)
    return hooks[start:nxt] if nxt != -1 else hooks[start:]


class MutationInFlightGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hooks = render_hooks(_make_ir())

    def _assert_dedupe(self, hook: str, api_call: str, pending_type: str, mutate_alias: str) -> None:
        self.assertIn(f"const pendingRef = useRef<Promise<{pending_type}> | null>(null);", hook)
        # dedupe guard is the first statement of the callback
        guard = hook.index("if (pendingRef.current) return pendingRef.current;")
        set_loading = hook.index("setLoading(true);")
        self.assertLess(guard, set_loading, "dedupe guard must precede setLoading(true)")
        # the body runs in an IIFE captured in the ref and returned
        self.assertIn("const request = (async () => {", hook)
        self.assertIn("pendingRef.current = request;", hook)
        self.assertIn("return request;", hook)
        # underlying api call preserved
        self.assertIn(api_call, hook)
        # finally clears both loading and the pending ref
        self.assertIn("setLoading(false);", hook)
        self.assertIn("pendingRef.current = null;", hook)
        # public return shape preserved
        self.assertIn(f"return {{ {mutate_alias}, mutate: {mutate_alias}, loading, error, reset }};", hook)

    def test_create_hook_dedupes(self) -> None:
        self._assert_dedupe(
            _hook(self.hooks, "useCreateArticle"),
            "return await api.createArticle(data, options);",
            "Article", "create",
        )

    def test_update_hook_dedupes(self) -> None:
        self._assert_dedupe(
            _hook(self.hooks, "useUpdateArticle"),
            "return await api.updateArticle(id, data, options);",
            "Article", "update",
        )

    def test_delete_hook_dedupes(self) -> None:
        hook = _hook(self.hooks, "useDeleteArticle")
        self.assertIn("const pendingRef = useRef<Promise<void> | null>(null);", hook)
        self.assertIn("if (pendingRef.current) return pendingRef.current;", hook)
        self.assertIn("const request = (async () => {", hook)
        self.assertIn("pendingRef.current = request;", hook)
        self.assertIn("await api.deleteArticle(id, options);", hook)
        self.assertIn("pendingRef.current = null;", hook)
        self.assertIn("return { remove, mutate: remove, loading, error, reset };", hook)

    def test_errors_still_reject_and_set_error(self) -> None:
        hook = _hook(self.hooks, "useCreateArticle")
        self.assertIn("setError(e);", hook)
        self.assertIn("throw e;", hook)

    def test_fetch_hooks_unchanged_by_this_task(self) -> None:
        # The list hook keeps its R-280 abort wiring; no pendingRef leaks into fetch hooks.
        list_hook = _hook(self.hooks, "useListArticles")
        self.assertIn("const abortRef = useRef<AbortController | null>(null);", list_hook)
        self.assertNotIn("pendingRef", list_hook)


class DiffInvarianceTests(unittest.TestCase):
    def test_description_only_change_is_byte_identical(self) -> None:
        self.assertEqual(
            render_hooks(_make_ir(description="First description")),
            render_hooks(_make_ir(description="A completely different description")),
        )


if __name__ == "__main__":
    unittest.main()
