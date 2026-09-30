"""PC-101: defects seen while building PC-050 to PC-104, each fixed where it starts.

- The preview's server-side proxy routes answered 503: they read NEXT_PUBLIC_API_URL (in a preview,
  a path the browser uses, which a server cannot fetch), never the API_URL the preview sets.
- A preview's live-reload WebSocket reached no one through the console (a route cannot upgrade).
- A model-written page in an app without accounts offered "Sign in" to a page that does not exist.
- The Expo app failed tsc on `process` under pnpm (no Node types hoisted).
- A plan with a list and no detail screen had no page to read one record in full.
"""

import json
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen.assembler import assemble_project
from omnistackai_agent_engine.codegen.llm_ui import build_ui_synthesis_prompt, clean_and_validate_jsx
from omnistackai_agent_engine.codegen.reachable_references import with_detail_screens

_REPO = Path(__file__).resolve().parents[3]


def _files(ir) -> dict[str, str]:
    return {f.path: f.content for f in assemble_project(ir).files()}


class TheProxyRouteReachesTheApi(TestCase):
    def test_it_reads_the_server_address_first_and_strips_the_base_path(self) -> None:
        routes = [c for p, c in _files(example_ir("minimal-blog")).items() if p.endswith("/route.ts") and "apps/web/app/" in p]
        self.assertTrue(routes)
        route = routes[0]
        self.assertLess(route.index("process.env.API_URL"), route.index("process.env.BACKEND_INTERNAL_URL"))
        self.assertIn('PUBLIC_API.startsWith("https://") ? PUBLIC_API : ""', route, "a relative public path is never fetched")
        self.assertIn("url.pathname.slice(BASE_PATH.length)", route)

    def test_the_preview_and_the_published_stack_set_it(self) -> None:
        plan = (_REPO / "services/agent-engine/src/omnistackai_agent_engine/localrun/plan.py").read_text()
        self.assertIn('("API_URL", api_url),', plan)
        bundle = (_REPO / "services/agent-engine/src/omnistackai_agent_engine/publish/bundle.py").read_text()
        self.assertIn('f"      API_URL: http://api:{API_PORT}"', bundle)


class TheConsoleCarriesThePreviewReloadSocket(TestCase):
    def test_only_the_reload_path_after_the_same_checks_as_the_http_proxy(self) -> None:
        server = (_REPO / "apps/console-web/server.mjs").read_text()
        self.assertIn('pathname.endsWith("/_next/webpack-hmr")', server)
        self.assertIn("/projects/${projectId}/preview", server, "the session must resolve the project")
        self.assertIn("if (!LOOPBACK.has(origin.hostname)) return null;", server)
        self.assertIn("delete headers.cookie;", server, "the console session never reaches the app")
        self.assertIn("node server.mjs start", (_REPO / "scripts/console.sh").read_text())


class NoSignInWithoutAccounts(TestCase):
    PAGE = 'export default function P() { return <header><a href="/login">Sign in</a></header>; }'

    def test_a_page_offering_sign_in_is_refused_only_when_there_are_no_accounts(self) -> None:
        valid, _, reason = clean_and_validate_jsx(self.PAGE, has_auth=False)
        self.assertFalse(valid)
        self.assertIn("no accounts", reason)
        self.assertTrue(clean_and_validate_jsx(self.PAGE, has_auth=True)[0])
        plain = 'export default function P() { return <p>Signing in is not needed to browse.</p>; }'
        self.assertTrue(clean_and_validate_jsx(plain, has_auth=False)[0])

    def test_the_model_is_told(self) -> None:
        from dataclasses import replace

        from omnistackai_agent_engine.codegen.auth_guard import needs_auth

        blog = example_ir("minimal-blog")
        public = replace(blog, apis=tuple(replace(a, auth=False, required_roles=()) for a in blog.apis))
        self.assertFalse(needs_auth(public))
        self.assertIn("no Sign in / Log in / Sign up buttons", build_ui_synthesis_prompt(public, "a blog"))
        self.assertNotIn("no Sign in / Log in / Sign up buttons", build_ui_synthesis_prompt(blog, "a blog"))


class TheExpoAppTypeChecksUnderPnpm(TestCase):
    def test_node_types_are_declared(self) -> None:
        from dataclasses import replace

        blog = example_ir("minimal-blog")
        mobile = replace(blog, project_strategy=replace(blog.project_strategy, mobile_profile="react_native"))
        manifest = next(json.loads(c) for p, c in _files(mobile).items() if p.startswith("apps/mobile") and p.endswith("package.json"))
        self.assertIn("@types/node", manifest["devDependencies"])


class EveryListHasAPageToReadOne(TestCase):
    def test_a_plan_without_a_detail_screen_gets_one_and_the_list_links_to_it(self) -> None:
        blog = with_detail_screens(example_ir("minimal-blog"))
        self.assertIn("post_detail", [s.id for s in blog.screens])
        files = _files(blog)
        self.assertIn("apps/web/app/post_detail/page.tsx", files)
        self.assertIn("href={`/post_detail?id=${(item as any).id}`}", files["apps/web/app/post_list/page.tsx"])
        self.assertEqual(with_detail_screens(blog), blog, "idempotent")

    def test_a_list_only_entity_detail_page_finds_the_record_in_the_list(self) -> None:
        # Seen in the task-tracker benchmark: the page used `item` and never defined it (tsc failed);
        # checked with tsc against the shared type-check cache, web and admin compile.
        page = _files(with_detail_screens(example_ir("minimal-blog")))["apps/web/app/post_detail/page.tsx"]
        self.assertIn("const item = currentIndex >= 0 && listItems ? listItems[currentIndex] : null;", page)
        self.assertIn("{item && (", page, "the record is shown")


class EveryPreviewAppHasItsOwnBasePath(TestCase):
    """A lone web app was served at /preview/<id>/ with no base path: its scripts and links left the
    preview, the proxy rewrote its HTML (a hydration mismatch on every page), and the browser was
    sent to the API's loopback address."""

    def test_a_single_web_app_runs_under_its_own_path(self) -> None:
        plan = (_REPO / "services/agent-engine/src/omnistackai_agent_engine/localrun/plan.py").read_text()
        self.assertIn("multi_app = (bool(web_apps) or has_mobile) and bool(public_base)", plan)

    def test_the_console_routes_reload_sockets_before_next_can_close_them(self) -> None:
        server = (_REPO / "apps/console-web/server.mjs").read_text()
        self.assertIn("server.emit = (event, ...args) => {", server)
        self.assertIn("if (isPreviewUpgrade(req)) {", server)


class TheAppLooksFinishedToTheEye(TestCase):
    def test_it_has_an_icon_under_its_base_path(self) -> None:
        files = _files(example_ir("minimal-blog"))
        for app in ("web", "admin"):
            self.assertIn('<svg xmlns="http://www.w3.org/2000/svg"', files[f"apps/{app}/app/icon.svg"])

    def test_subtle_text_meets_contrast_in_both_themes(self) -> None:
        def ratio(a: str, b: str) -> float:
            def lum(h: str) -> float:
                c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
                c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
                return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
            hi, lo = sorted((lum(a), lum(b)), reverse=True)
            return (hi + 0.05) / (lo + 0.05)

        css = _files(example_ir("minimal-blog"))["apps/web/styles/tokens.css"]
        import re

        subtle = re.findall(r"--color-text-subtle: (#[0-9a-f]{6})", css)
        self.assertEqual(subtle[0], "#64748b")
        self.assertGreaterEqual(ratio(subtle[0], "#ffffff"), 4.5)
        for dark in subtle[1:]:
            self.assertGreaterEqual(ratio(dark, "#0f172a"), 4.5)


class EveryPreviewPageIsCompiledBeforeAnyoneOpensIt(TestCase):
    def test_static_routes_are_found_and_requested_under_the_base_path(self) -> None:
        import tempfile
        from unittest import mock

        from omnistackai_agent_engine.localrun import run as run_module
        from omnistackai_agent_engine.localrun.plan import RunPlan

        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / "apps" / "web" / "app"
            for route in ("", "orders", "orders/[id]", "(shop)/cart", "_private"):
                (app / route).mkdir(parents=True, exist_ok=True)
                (app / route / "page.tsx").write_text("export default function P() { return null; }")
            self.assertEqual(run_module.page_routes(app.parent), ["/", "/cart", "/orders"])
            plan = RunPlan(repo_dir=tmp, app_slug="s", db_name="d", backend_kind="none", has_web=True,
                           api_url="", web_url="http://127.0.0.1:3000", db_password="x", multi_app=True,
                           public_base="/preview/p1", web_surfaces=(("web", "http://127.0.0.1:3000"),))
            seen: list[str] = []
            with mock.patch.object(run_module.urllib.request, "urlopen", side_effect=lambda url, timeout: seen.append(url) or (_ for _ in ()).throw(OSError())):
                run_module.warm_pages(plan).join(5)
            self.assertEqual(seen, ["http://127.0.0.1:3000/preview/p1/web", "http://127.0.0.1:3000/preview/p1/web/cart",
                                    "http://127.0.0.1:3000/preview/p1/web/orders"])


class TheDevAdminIsAnAdmin(TestCase):
    """Seen in the SaaS benchmark: a plan with roles guest/member/owner gave the preview's dev admin
    only those, so the admin console's Users page answered 403 to the developer; and in Go the dev
    admin's roles ([]string) never matched a role check that read []any."""

    def test_every_backend_gives_the_dev_session_the_admin_role(self) -> None:
        from dataclasses import replace

        blog = example_ir("minimal-blog")
        for backend, path, needle in (
            ("python", "services/api/app/auth.py", '"roles": [*ROLES, "admin"]'),
            ("go", "services/api/internal/handlers/auth.go", 'append(append([]string{}, Roles...), "admin")'),
            ("node", "services/api/src/middleware/auth.ts", "roles: [...ROLES, 'admin']"),
        ):
            files = _files(replace(blog, project_strategy=replace(blog.project_strategy, backend_strategy=backend)))
            self.assertIn(needle, files[path], backend)
        go = _files(replace(blog, project_strategy=replace(blog.project_strategy, backend_strategy="go")))
        self.assertIn("case []string:", go["services/api/internal/handlers/auth.go"])


class FilledColoursCarryReadableText(TestCase):
    def test_the_foreground_is_whichever_reads_better(self) -> None:
        from omnistackai_agent_engine.codegen.brand import readable_foreground

        self.assertEqual(readable_foreground("#06b6d4"), "#0f172a", "white on cyan was 2.4:1")
        self.assertEqual(readable_foreground("#4f46e5"), "#ffffff")

    def test_the_library_indigo_becomes_the_primary(self) -> None:
        from omnistackai_agent_engine.codegen.design_direction import theme_component

        self.assertEqual(theme_component('background: "#4f46e5", color: "#fff"'),
                         'background: "var(--color-primary)", color: "#fff"')


class AFormWithAnUploadFieldRendersOnTheServer(TestCase):
    """Seen in the store benchmark: the product editor failed server rendering ("location is not
    defined") because the uploader built Uppy - whose plugins read `location` - while rendering."""

    def test_uppy_is_created_in_an_effect_only(self) -> None:
        from omnistackai_agent_engine.codegen.uploads import FILE_UPLOADER

        self.assertNotIn("useState(() => {\n    const instance = new Uppy", FILE_UPLOADER)
        self.assertIn("if (!uppy) setUppy(createUppy(field, accept, maxSizeMb, maxFiles));", FILE_UPLOADER)
        self.assertIn("{uppy && <Dashboard uppy={uppy}", FILE_UPLOADER)


class TheLifecycleStepperReads(TestCase):
    def test_states_not_reached_yet_meet_contrast(self) -> None:
        source = (_REPO / "services/agent-engine/src/omnistackai_agent_engine/codegen/lifecycle_ui.py").read_text()
        self.assertIn('i < position ? \\"#3730a3\\" : \\"#475569\\"', source, "#64748b on #f1f5f9 was 4.3:1")


class OneSlugNamePerLevel(TestCase):
    def test_proxy_routes_share_the_first_dynamic_name(self) -> None:
        from dataclasses import replace

        from omnistackai_agent_engine.application_ir import ApiEndpoint, HttpMethod

        blog = example_ir("minimal-blog")
        plan = replace(blog, apis=blog.apis + (ApiEndpoint(HttpMethod.GET, "/posts/{id}", auth=True, response_schema="Post"),))
        routes = sorted(p for p in _files(plan) if p.startswith("apps/web/app/posts") and p.endswith("route.ts"))
        self.assertEqual(routes, ["apps/web/app/posts/[postId]/comments/route.ts", "apps/web/app/posts/[postId]/route.ts",
                                  "apps/web/app/posts/route.ts"])
