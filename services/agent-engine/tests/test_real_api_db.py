"""PC-004: a generated app never pretends. Real data, or an honest "not connected yet".

Proven live on 2026-09-26 against PostgreSQL: a malformed id is a client error (422) on Python,
Go, Express and Hono; with the database unreachable, Node answers create and list with 500 — not a
fake 201 or an empty list — leaks no internals, and stays up reporting the database unavailable.

What was fake before this task, each guarded below:
* Node fell back to an in-memory Map on any database error and reported success;
* Node answered endpoints it could not wire with 200 and a placeholder body;
* "cart" and "review" screens shipped invented products and reviews;
* fallback pages carried buttons with no handler;
* Go sent raw database errors (SQL state and all) to the client, and so did Node's error handler;
* Express 4 did not catch async errors, so once the fake fallback went a database error would have
  crashed the whole server — hence Express 5.
"""

import dataclasses
import json
from unittest import TestCase

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.application_ir.ir import ApiEndpoint, Screen
from omnistackai_agent_engine.codegen.assembler import assemble_project
from omnistackai_agent_engine.codegen.backend_go import GoBackendAdapter
from omnistackai_agent_engine.codegen.backend_node import NodeBackendAdapter
from omnistackai_agent_engine.codegen.backend_python import PythonBackendAdapter
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter, render_screen_page
from omnistackai_agent_engine.codegen.wiring_report import readme_section, wiring_gaps

IR = example_ir("minimal-blog")
UNWIRED = dataclasses.replace(IR, apis=IR.apis + (ApiEndpoint(method="POST", path="/posts/{postId}/boost"),))


class NodeNeverPretendsToSave(TestCase):
    def test_no_in_memory_fallback(self) -> None:
        for framework in ("express", "hono"):
            project = NodeBackendAdapter(framework).generate(IR)
            for f in project.files():
                if f.path.startswith("src/db/"):
                    with self.subTest(framework=framework, path=f.path):
                        self.assertNotIn("memoryStore", f.content)
                        self.assertNotIn("catch {", f.content)

    def test_health_says_unavailable_not_in_memory(self) -> None:
        app = NodeBackendAdapter("express").generate(IR).get("src/app.ts").content
        self.assertIn("'unavailable'", app)
        self.assertNotIn("in-memory", app)

    def test_express_5_so_async_errors_reach_the_handler(self) -> None:
        deps = json.loads(NodeBackendAdapter("express").generate(IR).get("package.json").content)
        self.assertTrue(deps["dependencies"]["express"].startswith("^5"))


class UnwiredEndpointsAreHonest(TestCase):
    def test_node_answers_501_not_a_fake_200(self) -> None:
        for framework in ("express", "hono"):
            routes = NodeBackendAdapter(framework).generate(UNWIRED).get("src/routes/posts.ts").content
            with self.subTest(framework=framework):
                self.assertIn("not_implemented", routes)
                self.assertNotIn("message: '/posts/{postId}/boost'", routes)

    def test_python_and_go_already_answer_501(self) -> None:
        py = PythonBackendAdapter().generate(UNWIRED).get("app/routers/posts.py").content
        self.assertIn('status_code=501, detail="not_implemented"', py)


class NoInternalsReachTheClient(TestCase):
    def test_go_never_echoes_a_database_error(self) -> None:
        project = GoBackendAdapter().generate(IR)
        for f in project.files():
            if f.path.startswith("internal/handlers/"):
                with self.subTest(path=f.path):
                    self.assertNotIn("http.Error(w, err.Error()", f.content)
        shared = project.get("internal/handlers/handlers.go").content
        self.assertIn('strings.HasPrefix(pgErr.Code, "22")', shared)
        self.assertIn('"detail": "internal_error"', shared)

    def test_node_error_handlers_log_rather_than_send(self) -> None:
        express = NodeBackendAdapter("express").generate(IR).get("src/app.ts").content
        self.assertNotIn("err.message || 'An unexpected error occurred'", express)
        self.assertIn("detail: status >= 500 ? 'internal_error'", express)
        hono = NodeBackendAdapter("hono").generate(IR).get("src/app.ts").content
        self.assertIn("app.onError((err, c) => {", hono)

    def test_malformed_values_are_client_errors(self) -> None:
        main = PythonBackendAdapter().generate(IR).get("app/main.py").content
        self.assertIn("@app.exception_handler(_pg_errors.DataError)", main)
        self.assertIn("status_code=422", main)
        express = NodeBackendAdapter("express").generate(IR).get("src/app.ts").content
        self.assertIn("err.code.startsWith('22')", express)


class PagesDoNotFake(TestCase):
    def test_no_invented_cart_or_reviews(self) -> None:
        ir = dataclasses.replace(IR, entities=(), apis=(), screens=(
            Screen(id="cart", role="reader", components=("list",), actions=("checkout",), navigation=()),
            Screen(id="reviews", role="reader", components=("list",), actions=("rate",), navigation=()),
        ))
        for screen in ir.screens:
            page = render_screen_page(screen, ir)
            with self.subTest(screen=screen.id):
                self.assertNotIn("INITIAL_ITEMS", page)
                self.assertNotIn("INITIAL_REVIEWS", page)
                self.assertIn("Not connected to data yet.", page)

    def test_no_buttons_without_handlers(self) -> None:
        screen = Screen(id="dispatch_board", role="reader", components=("board",), actions=("assign", "reroute"),
                        navigation=())
        page = render_screen_page(screen, dataclasses.replace(IR, entities=(), apis=(), screens=(screen,)))
        self.assertNotIn("<button", page)
        self.assertIn("Planned actions", page)


class TheUserIsToldWhatIsNotReal(TestCase):
    def test_gaps_are_named(self) -> None:
        gaps = wiring_gaps(UNWIRED)
        self.assertEqual([(g["kind"], g["name"]) for g in gaps], [("endpoint", "POST /posts/{postId}/boost")])

    def test_a_fully_wired_app_says_so(self) -> None:
        self.assertEqual(wiring_gaps(IR), ())
        self.assertIn("Every endpoint and screen in this app is backed by the real API and database.",
                      readme_section(IR))

    def test_the_readme_carries_it(self) -> None:
        readme = assemble_project(UNWIRED).get("README.md").content
        self.assertIn("## Not connected to data yet", readme)
        self.assertIn("POST /posts/{postId}/boost", readme)

    def test_the_build_result_carries_it(self) -> None:
        from omnistackai_agent_engine.intake.build_app import _not_connected

        self.assertEqual(len(_not_connected(UNWIRED)), 1)
