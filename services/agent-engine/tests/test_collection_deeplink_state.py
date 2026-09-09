"""Tests for Task R-280: Deep-Linked Collection List State + Debounced, Race-Safe Search.

The generated useList<Entities> hook must sync sort/order/q/page/pageSize to the URL and hydrate them
from the URL on mount, and its refetch must abort the previous in-flight request. The collection screen
search input must debounce its committed query. Rule-free of ir.description (diff invariant).
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
from omnistackai_agent_engine.codegen import NextjsWebAdapter, render_hooks, render_screen_page


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
        ApiEndpoint(HttpMethod.POST, "/articles", request_schema="Article", response_schema="Article"),
        ApiEndpoint(HttpMethod.GET, "/articles/{id}", response_schema="Article"),
        ApiEndpoint(HttpMethod.DELETE, "/articles/{id}", response_schema="Article"),
    )
    screens = (
        Screen("article_list", "admin", components=("list",), actions=("view", "delete"), navigation=("article_form",)),
        Screen("article_form", "admin", components=("form",), actions=("create",), navigation=("article_list",)),
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


class UseListDeepLinkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hooks = render_hooks(_make_ir())

    def test_useRef_imported(self) -> None:
        self.assertIn(
            'import { useCallback, useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";',
            self.hooks,
        )

    def test_hydrate_effect_reads_all_list_params_from_url(self) -> None:
        self.assertIn("const sp = new URLSearchParams(window.location.search);", self.hooks)
        for key in ('sp.get("q")', 'sp.get("sort")', 'sp.get("order")', 'sp.get("pageSize")', 'sp.get("page")'):
            self.assertIn(key, self.hooks)
        self.assertIn("setParams((prev) => ({ ...prev, ...next }));", self.hooks)
        # hydration is client-only (no SSR hydration mismatch)
        self.assertIn('if (typeof window === "undefined") return;', self.hooks)

    def test_sync_effect_writes_params_to_url_via_replaceState(self) -> None:
        self.assertIn("const url = new URL(window.location.href);", self.hooks)
        self.assertIn('window.history.replaceState({}, "", url.toString());', self.hooks)
        for key in ('setOrDelete("q"', 'setOrDelete("sort"', 'setOrDelete("order"', 'setOrDelete("page"', 'setOrDelete("pageSize"'):
            self.assertIn(key, self.hooks)
        # only non-default values are written to keep URLs clean
        self.assertIn('params.sort !== "id"', self.hooks)
        self.assertIn('params.order !== "asc"', self.hooks)
        self.assertIn("pageV > 1", self.hooks)
        self.assertIn("limitV !== 100", self.hooks)

    def test_refetch_is_race_safe_with_abortcontroller(self) -> None:
        self.assertIn("const abortRef = useRef<AbortController | null>(null);", self.hooks)
        self.assertIn("abortRef.current?.abort();", self.hooks)
        self.assertIn("const controller = new AbortController();", self.hooks)
        self.assertIn("api.listArticlesWithCount({ params, signal: controller.signal, ...options });", self.hooks)
        self.assertIn("if (controller.signal.aborted) return;", self.hooks)
        self.assertIn('err instanceof DOMException && err.name === "AbortError"', self.hooks)
        self.assertIn("if (!controller.signal.aborted) setLoading(false);", self.hooks)
        # aborts any in-flight request on unmount
        self.assertIn("return () => abortRef.current?.abort();", self.hooks)

    def test_subcollection_hook_unchanged_signature(self) -> None:
        # useList<Child>By<Parent> is intentionally out of R-280 scope: no abort/URL wiring there.
        ir = example_ir("minimal-blog")
        hooks = render_hooks(ir)
        self.assertIn("const res = await api.listCommentsByPostWithCount(postId, { params, ...options });", hooks)


class CollectionSearchDebounceTests(unittest.TestCase):
    def setUp(self) -> None:
        ir = _make_ir()
        self.page = render_screen_page(ir.screens[0], ir)

    def test_collection_imports_useEffect(self) -> None:
        self.assertIn('from "react";', self.page)
        self.assertIn("useEffect", self.page.split('from "react";')[0])

    def test_search_is_debounced(self) -> None:
        self.assertIn("const timer = setTimeout(() => {", self.page)
        self.assertIn("}, 300);", self.page)
        self.assertIn("return () => clearTimeout(timer);", self.page)
        # guard prevents clobbering a hydrated page offset when the value is unchanged
        self.assertIn('if (searchInput !== (params.q ?? "")) setSearch(searchInput);', self.page)

    def test_onchange_does_not_fetch_per_keystroke(self) -> None:
        self.assertIn("setSearchInput(e.target.value);", self.page)
        self.assertNotIn("setSearch(e.target.value)", self.page)

    def test_input_reflects_hydrated_query(self) -> None:
        self.assertIn('setSearchInput(params.q ?? "");', self.page)
        self.assertIn("}, [params.q]);", self.page)

    def test_form_submit_still_searches_immediately(self) -> None:
        self.assertIn("setSearch(searchInput);", self.page)


class DiffInvarianceTests(unittest.TestCase):
    def test_hooks_and_page_invariant_across_ir_description(self) -> None:
        ir_a = _make_ir(description="First description")
        ir_b = _make_ir(description="A completely different description text")
        self.assertEqual(render_hooks(ir_a), render_hooks(ir_b))
        self.assertEqual(
            render_screen_page(ir_a.screens[0], ir_a),
            render_screen_page(ir_b.screens[0], ir_b),
        )


class DemoProjectsTests(unittest.TestCase):
    def test_demo_projects_generate_with_deeplink_and_debounce(self) -> None:
        for name in ("minimal-blog", "rideshare-favourites"):
            proj = NextjsWebAdapter().generate(example_ir(name))
            hooks = proj.get("lib/hooks.ts").content
            self.assertIn("window.history.replaceState", hooks)
            self.assertIn("new AbortController()", hooks)
            # at least one collection page carries the debounce timer
            pages = [p for p in proj.paths() if p.endswith("page.tsx")]
            self.assertTrue(
                any("const timer = setTimeout(() => {" in proj.get(p).content for p in pages),
                f"{name}: expected a debounced collection page",
            )


if __name__ == "__main__":
    unittest.main()
