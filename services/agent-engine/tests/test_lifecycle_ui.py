"""R-590: a lifecycle is operable from the screens, and only through its transitions.

Proven live on 2026-09-26 against PostgreSQL on Python, Go, Node/Express and Node/Hono (32/32):
a new record starts in the initial state even when the request names another, an ordinary edit
changes other fields but never the state, a role that may not move it gets 403, an illegal move
gets 409, and the two legal moves land in the database.

Found on the way and guarded here:
* create/update wrote the lifecycle field, so the transition rules could be skipped entirely;
* Node transitions called `update`, which had to stop writing the field — they now use a setter;
* the default Python backend could not create anything through its API: the model required a
  client-invented `id`, and the repository called a helper that exists only in the generator;
* the mobile app called `/api/<entity>s`, a path no backend serves;
* Hono's generated routes did not type-check (`c.req.param` and `c.get('user')` typing).
"""

import json
import sys
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen.backend_go import GoBackendAdapter
from omnistackai_agent_engine.codegen.backend_node import NodeBackendAdapter
from omnistackai_agent_engine.codegen.backend_python import PythonBackendAdapter
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter
from omnistackai_agent_engine.codegen.react_native import ReactNativeAdapter
from omnistackai_agent_engine.intake.nl_to_ir import parse_ir_response


def _workflow_ir():
    d = example_ir("minimal-blog").to_dict()
    post = next(e for e in d["entities"] if e["name"] == "Post")
    post["fields"].append({"name": "status", "type": "string", "validation": ["enum:draft|review|live"]})
    d["apis"].append({"method": "PUT", "path": "/posts/{postId}", "auth": True, "request_schema": "Post",
                      "response_schema": "Post"})
    d["apis"].append({"method": "GET", "path": "/posts/{postId}", "auth": False, "response_schema": "Post"})
    d["capabilities"] = [{"kind": "workflow", "name": "post_lifecycle", "config": {
        "entity": "Post", "field": "status", "states": ["draft", "review", "live"], "initial": "draft",
        "transitions": [
            {"name": "submit", "to": "review", "from": ["draft"], "roles": ["author"]},
            {"name": "publish", "to": "live", "from": ["review"], "roles": ["author"]},
        ]}}]
    return parse_ir_response(json.dumps(d))


IR = _workflow_ir()
PLAIN = example_ir("minimal-blog")


def _get(project, path):
    return project.get(path).content


class TheWebShowsTheLifecycle(TestCase):
    PROJECT = NextjsWebAdapter().generate(IR)

    def test_a_panel_per_workflow(self) -> None:
        panel = _get(self.PROJECT, "components/lifecycle/post-lifecycle.tsx")
        self.assertIn("export function PostLifecycle", panel)
        self.assertIn('const STATES = ["draft", "review", "live"]', panel)
        self.assertIn("call: submitPost", panel)
        self.assertIn("call: publishPost", panel)

    def test_only_moves_legal_from_the_current_state_are_offered(self) -> None:
        panel = _get(self.PROJECT, "components/lifecycle/post-lifecycle.tsx")
        self.assertIn("m.from.length === 0 || m.from.includes(current)", panel)

    def test_moves_a_signed_in_role_cannot_make_are_hidden(self) -> None:
        panel = _get(self.PROJECT, "components/lifecycle/post-lifecycle.tsx")
        self.assertIn("m.roles.length === 0 || role === null || m.roles.includes(role)", panel)
        self.assertIn('import { useAuth } from "@/components/auth-provider";', panel)

    def test_the_list_page_offers_the_moves_per_row(self) -> None:
        # This plan has a list page and a form, no detail page — common, and why the list has it.
        pages = [f.content for f in self.PROJECT.files() if f.path.startswith("app/") and "PostLifecycle" in f.content]
        self.assertTrue(pages, "a page must render the panel")
        self.assertIn("<PostLifecycle record={item as Post} compact onChanged={() => refetch()} />", pages[0])

    def test_a_detail_page_renders_the_full_panel(self) -> None:
        import dataclasses

        from omnistackai_agent_engine.application_ir.ir import Screen

        ir = dataclasses.replace(IR, screens=IR.screens + (Screen(id="post_detail", role="author",
                                 components=("detail",), actions=("view",), navigation=()),))
        pages = [f.content for f in NextjsWebAdapter().generate(ir).files()
                 if f.path == "app/post_detail/page.tsx"]
        self.assertTrue(pages)
        self.assertIn("<PostLifecycle record={item} onChanged={() => refetch()} />", pages[0])

    def test_forms_do_not_offer_the_lifecycle_field(self) -> None:
        for f in self.PROJECT.files():
            if f.path.startswith("app/") and "handleSubmit" in f.content and "Post" in f.content:
                self.assertNotIn('name="status"', f.content, f.path)

    def test_no_panel_without_a_workflow(self) -> None:
        paths = NextjsWebAdapter().generate(PLAIN).paths()
        self.assertFalse([p for p in paths if p.startswith("components/lifecycle/")])


class TheMobileAppShowsTheLifecycle(TestCase):
    PROJECT = ReactNativeAdapter().generate(IR)

    def test_the_detail_screen_has_the_panel_and_no_state_input(self) -> None:
        screen = _get(self.PROJECT, "src/features/post/ui/PostDetailScreen.tsx")
        self.assertIn("<PostLifecycle record={record} onChanged={setRecord} />", screen)
        self.assertNotIn('label="Status"', screen)
        panel = _get(self.PROJECT, "src/features/post/ui/PostLifecycle.tsx")
        self.assertIn("path: \"/posts\"", panel)

    def test_it_calls_the_paths_the_backends_serve(self) -> None:
        client = _get(self.PROJECT, "src/features/post/api/client.ts")
        self.assertIn("const ENDPOINT = '/posts';", client)
        self.assertNotIn("ENDPOINT = '/api/", client)


class TheBackendsWriteTheStateOnlyThroughTransitions(TestCase):
    def test_python(self) -> None:
        project = PythonBackendAdapter().generate(IR)
        repo = _get(project, "app/repositories/post.py")
        create_cols = repo.split("columns = [c for c in ", 1)[1].split(" if c in data]", 1)[0]
        self.assertNotIn("'status'", create_cols)
        update = repo.split("async def update_post", 1)[1].split("\nasync def ", 1)[0]
        self.assertNotIn('"status" = %s', update)
        self.assertIn("async def set_post_status", repo)
        models = _get(project, "app/models.py")
        self.assertIn("status: Optional[str] = None", models)

    def test_go(self) -> None:
        project = GoBackendAdapter().generate(IR)
        store = _get(project, "internal/store/post.go")
        insert = store.split("INSERT INTO", 1)[1].split("`", 1)[0]
        self.assertNotIn('"status"', insert)
        update = store.split("func UpdatePost", 1)[1].split("\nfunc ", 1)[0]
        self.assertNotIn('"status" =', update)
        models = _get(project, "internal/models/models.go")
        status_line = next(line for line in models.splitlines() if 'json:"status"' in line)
        self.assertNotIn("validate:", status_line)

    def test_node(self) -> None:
        for framework in ("express", "hono"):
            project = NodeBackendAdapter(framework).generate(IR)
            repo = _get(project, "src/db/post.ts")
            with self.subTest(framework=framework):
                self.assertIn('const WRITABLE: string[] = ["title", "body", "published"];', repo)
                self.assertIn("filter((k) => WRITABLE.includes(k))", repo)
                self.assertIn("static async setLifecycle(id: string, value: string)", repo)
                routes = _get(project, "src/routes/posts.ts")
                self.assertIn("PostRepository.setLifecycle(", routes)
                self.assertNotIn("PostRepository.update(req.params.postId, { status:", routes)


class ThePythonCreateBugsStayFixed(TestCase):
    PROJECT = PythonBackendAdapter().generate(PLAIN)

    def test_the_database_assigns_the_id(self) -> None:
        self.assertIn("id: Optional[str] = None  # assigned by the database", _get(self.PROJECT, "app/models.py"))

    def test_the_generated_repository_does_not_call_a_generator_helper(self) -> None:
        for f in self.PROJECT.files():
            if f.path.startswith("app/repositories/") and f.path.endswith(".py") and f.content:
                with self.subTest(path=f.path):
                    self.assertNotIn("sql_identifier(", f.content)
                    compile(f.content, f.path, "exec")


class HonoTypeChecks(TestCase):
    def test_route_params_and_user_access_are_typed(self) -> None:
        routes = _get(NodeBackendAdapter("hono").generate(IR), "src/routes/posts.ts")
        self.assertNotIn("c.req.param('postId'))", routes)
        self.assertIn("c.req.param('postId') ?? ''", routes)
        self.assertNotIn("(c.get('user') as any)", routes)
