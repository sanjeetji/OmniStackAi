"""R-589: a lifecycle runs on every backend, not only the default one.

R-566 implemented transitions for Python. Go and Node emitted the 501 scaffold for them, so a user
who chose Go got a lifecycle that did not run — visible rather than silent, but not the feature.
Each backend now enforces the same two rules the Python one does: the role, and the state the row
is in. Verified by running each generated server against PostgreSQL: a reader is refused 403, an
author publishing from draft gets 409 with the states it is allowed from, and from review the row
really becomes live.

The same scaffold the Go setter was written against held a bug of its own, older than R-566.
`Update<Entity>` declared `var out`, scanned the RETURNING row into `m`, and returned `&out` — a
struct never written. Every PATCH/PUT in every generated Go backend answered with a blank record
while the database held the right one. The setter hit the same mismatch in the opposite direction
and failed to compile, which is how the older one was found.
"""

import dataclasses
from unittest import TestCase

from omnistackai_agent_engine.application_ir import BackendStrategy, Field, FieldType, example_ir
from omnistackai_agent_engine.application_ir.capability import Capability
from omnistackai_agent_engine.codegen.assembler import assemble_project
from omnistackai_agent_engine.codegen.backend_node import NodeBackendAdapter

_CONFIG = {
    "entity": "Post",
    "field": "status",
    "states": ["draft", "review", "live"],
    "initial": "draft",
    "transitions": [{"name": "publish", "to": "live", "from": ["review"], "roles": ["author"]}],
}


def _ir(backend: BackendStrategy, with_workflow: bool = True):
    base = example_ir("minimal-blog")
    entities = tuple(
        dataclasses.replace(e, fields=e.fields + (Field(name="status", type=FieldType.STRING, required=True),))
        if e.name == "Post"
        else e
        for e in base.entities
    )
    return dataclasses.replace(
        base,
        entities=entities,
        capabilities=(Capability("workflow", "post_lifecycle", _CONFIG),) if with_workflow else (),
        project_strategy=dataclasses.replace(base.project_strategy, backend_strategy=backend),
    )


def _files(ir) -> dict[str, str]:
    return {f.path: f.content for f in assemble_project(ir).files()}


class GoRunsTheLifecycle(TestCase):
    def setUp(self) -> None:
        self.files = _files(_ir(BackendStrategy.GO))

    def test_no_transition_is_left_as_a_501(self) -> None:
        handlers = self.files["services/api/internal/handlers/posts.go"]
        self.assertIn("func (h *Handlers) PublishPost(", handlers)

    def test_the_route_is_registered_behind_the_role_guard(self) -> None:
        main = self.files["services/api/main.go"]
        self.assertIn('mux.HandleFunc("POST /posts/{postId}/publish", handlers.RequireRoles(h.PublishPost, "author"))', main)

    def test_the_from_state_is_enforced(self) -> None:
        handlers = self.files["services/api/internal/handlers/posts.go"]
        self.assertIn('allowed := map[string]bool{"review": true}', handlers)
        self.assertIn("http.StatusConflict", handlers)

    def test_it_writes_only_the_lifecycle_column(self) -> None:
        store = self.files["services/api/internal/store/post.go"]
        self.assertIn("func SetPostStatus(ctx context.Context, db *sql.DB, id string, value string)", store)
        self.assertIn('SET "status" = $1 WHERE "id" = $2', store)


class GoReturnsWhatItWrote(TestCase):
    """The older bug: a PATCH that answered with a blank record."""

    def setUp(self) -> None:
        self.store = _files(_ir(BackendStrategy.GO, with_workflow=False))["services/api/internal/store/post.go"]

    def test_update_returns_the_scanned_row(self) -> None:
        body = self.store[self.store.index("func UpdatePost("):]
        body = body[: body.index("\n}\n")]
        self.assertIn("return &m, nil", body)
        self.assertNotIn("var out", body, "a struct declared and never written is what it used to return")

    def test_every_store_function_returns_the_variable_it_scanned(self) -> None:
        # The general form of the bug: scan targets name `m`, so whatever is returned must be `m`.
        for function in ("func UpdatePost(", "func SetPostStatus("):
            with self.subTest(function=function):
                store = _files(_ir(BackendStrategy.GO))["services/api/internal/store/post.go"]
                body = store[store.index(function):]
                body = body[: body.index("\n}\n")]
                if "Scan(&m." in body:
                    self.assertIn("return &m, nil", body)


class NodeRunsTheLifecycle(TestCase):
    def _router(self, framework: str) -> str:
        project = NodeBackendAdapter(framework).generate(_ir(BackendStrategy.NODE))
        return {f.path: f.content for f in project.files()}["src/routes/posts.ts"]

    def test_both_flavours_emit_the_transition(self) -> None:
        for framework in ("express", "hono"):
            with self.subTest(framework=framework):
                self.assertIn("router.post('/:postId/publish', requireAuth,", self._router(framework))

    def test_the_role_is_checked_because_node_has_no_role_middleware(self) -> None:
        for framework in ("express", "hono"):
            with self.subTest(framework=framework):
                router = self._router(framework)
                self.assertIn("['author'].some((r) => held.includes(r))", router)
                self.assertIn("403", router)

    def test_the_from_state_is_enforced(self) -> None:
        for framework in ("express", "hono"):
            with self.subTest(framework=framework):
                router = self._router(framework)
                self.assertIn("const allowed = ['review'];", router)
                self.assertIn("409", router)


class APlainProjectIsUnchanged(TestCase):
    def test_no_transition_code_without_a_workflow(self) -> None:
        for backend in (BackendStrategy.GO, BackendStrategy.NODE):
            with self.subTest(backend=backend.value):
                joined = "\n".join(_files(_ir(backend, with_workflow=False)).values())
                self.assertNotIn("PublishPost", joined)
                self.assertNotIn("/:postId/publish", joined)
