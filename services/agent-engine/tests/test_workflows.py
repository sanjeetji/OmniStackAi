"""R-566: an entity's lifecycle, and who may move it.

An order goes placed -> accepted -> picked_up -> delivered. A courier may pick one up but may not
accept it, and nothing goes back to placed once delivered. None of that could be written down: the
IR had entities, fields, relations, CRUD, screens and roles, so a status column was a string
anybody could set to anything, and `POST /orders/{orderId}/accept` wired to nothing — the Python
backend emitted a 501 stub for it, which is visible but is not a product.

This is the first capability kind with code generation behind it. R-564 shipped the registry empty
on purpose, because a kind that can be declared but not built is R-559's failure in different
clothes.

Two claims here are the ones worth holding onto, because both could reasonably have gone the other
way and the weaker version of each looks identical until it matters:

* **The states live in the database.** The generated schema constrains the column, so no row can
  hold a state the workflow never declared — not even through a hand-written UPDATE. Verified
  against a real PostgreSQL, not asserted about a string.
* **A transition is refused by the backend, not merely hidden in the interface.** Not showing a
  courier the accept button is presentation; refusing the request is the rule.
"""

import dataclasses
from unittest import TestCase

from omnistackai_agent_engine.application_ir import Field, FieldType, example_ir
from omnistackai_agent_engine.application_ir.capability import CAPABILITY_KINDS, Capability
from omnistackai_agent_engine.application_ir.errors import InvalidIRError
from omnistackai_agent_engine.application_ir.ir import ApplicationIR
from omnistackai_agent_engine.application_ir.workflow import Workflow, workflows_of
from omnistackai_agent_engine.codegen.assembler import assemble_project
from omnistackai_agent_engine.codegen.schema_sql import render_postgres_schema
from omnistackai_agent_engine.codegen.workflow_routes import transition_routes

_CONFIG = {
    "entity": "Post",
    "field": "status",
    "states": ["draft", "review", "live"],
    "initial": "draft",
    "transitions": [
        {"name": "submit", "to": "review", "from": ["draft"], "roles": ["author"]},
        {"name": "publish", "to": "live", "from": ["review"], "roles": ["author"]},
    ],
}


def _ir(config: dict | None = None) -> ApplicationIR:
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
        capabilities=(Capability("workflow", "post_lifecycle", config or _CONFIG),),
    )


def _files(ir: ApplicationIR) -> dict[str, str]:
    return {f.path: f.content for f in assemble_project(ir).files()}


class ALifecycleCanBeWrittenDown(TestCase):
    def test_the_kind_is_registered_with_code_behind_it(self) -> None:
        self.assertIn("workflow", CAPABILITY_KINDS.implemented())

    def test_it_round_trips_through_the_ir(self) -> None:
        back = ApplicationIR.from_dict(_ir().to_dict())
        workflow = workflows_of(back)[0]
        self.assertEqual(workflow.states, ("draft", "review", "live"))
        self.assertEqual([t.name for t in workflow.transitions], ["submit", "publish"])

    def test_transitions_from_a_state_are_answerable(self) -> None:
        workflow = workflows_of(_ir())[0]
        self.assertEqual([t.name for t in workflow.transitions_from("draft")], ["submit"])
        self.assertEqual([t.name for t in workflow.transitions_from("live")], [])

    def test_a_transition_with_no_sources_is_legal_from_anywhere(self) -> None:
        # Written out rather than implied, because "from any state" is a decision.
        workflow = Workflow.from_config(
            {**_CONFIG, "transitions": [{"name": "cancel", "to": "draft", "from": []}]}
        )
        self.assertEqual([t.name for t in workflow.transitions_from("live")], ["cancel"])


class NonsenseIsRefusedRatherThanGenerated(TestCase):
    def test_an_unknown_entity(self) -> None:
        with self.assertRaises(InvalidIRError):
            _ir({**_CONFIG, "entity": "Ghost"})

    def test_a_field_the_entity_does_not_have(self) -> None:
        # Otherwise the schema would constrain a column it never creates.
        with self.assertRaises(InvalidIRError) as caught:
            _ir({**_CONFIG, "field": "nope"})
        self.assertIn("needs a field named", str(caught.exception))

    def test_a_transition_to_an_undeclared_state(self) -> None:
        with self.assertRaises(InvalidIRError):
            _ir({**_CONFIG, "transitions": [{"name": "x", "to": "nowhere", "from": ["draft"]}]})

    def test_a_transition_from_an_undeclared_state(self) -> None:
        with self.assertRaises(InvalidIRError):
            _ir({**_CONFIG, "transitions": [{"name": "x", "to": "live", "from": ["nowhere"]}]})

    def test_a_role_the_app_does_not_have(self) -> None:
        with self.assertRaises(InvalidIRError):
            _ir({**_CONFIG, "transitions": [{"name": "x", "to": "live", "from": ["draft"], "roles": ["nobody"]}]})

    def test_an_initial_state_that_is_not_a_state(self) -> None:
        with self.assertRaises(InvalidIRError):
            _ir({**_CONFIG, "initial": "somewhere"})


class TheStatesLiveInTheDatabase(TestCase):
    """A lifecycle enforced only in application code lasts as long as every writer remembers it."""

    def setUp(self) -> None:
        self.sql = render_postgres_schema(_ir())

    def test_the_column_is_constrained_to_the_declared_states(self) -> None:
        self.assertIn("CHECK (\"status\" IN ('draft', 'review', 'live'))", self.sql)

    def test_the_initial_state_is_the_default(self) -> None:
        self.assertIn("ALTER COLUMN \"status\" SET DEFAULT 'draft'", self.sql)

    def test_an_entity_without_a_lifecycle_is_unconstrained(self) -> None:
        self.assertNotIn("chk_comment_", self.sql)


class ATransitionIsRefusedByTheBackend(TestCase):
    """Hiding a button is presentation; refusing the request is the rule."""

    def setUp(self) -> None:
        self.router = _files(_ir())["services/api/app/routers/posts.py"]

    def test_an_endpoint_exists_for_each_transition(self) -> None:
        self.assertIn('@router.post("/posts/{postId}/submit"', self.router)
        self.assertIn('@router.post("/posts/{postId}/publish"', self.router)

    def test_the_role_is_enforced(self) -> None:
        self.assertIn('dependencies=[Depends(require_roles("author"))]', self.router)

    def test_the_from_state_is_enforced(self) -> None:
        self.assertIn("allowed = ('review',)", self.router)
        self.assertIn("status_code=409", self.router)

    def test_a_missing_row_is_a_404_not_a_500(self) -> None:
        self.assertIn('status_code=404, detail="not_found"', self.router)

    def test_it_writes_only_the_lifecycle_column(self) -> None:
        # The generated update_ writes every column from a full payload; a transition passing only
        # the state would blank the rest of the row.
        self.assertIn('set_post_status(postId, "live")', self.router)
        repo = _files(_ir())["services/api/app/repositories/post.py"]
        self.assertIn("async def set_post_status(id: str, value: str)", repo)
        self.assertIn('SET "status" = %s WHERE "id" = %s', repo)

    def test_the_generated_backend_parses(self) -> None:
        import ast

        for path, content in _files(_ir()).items():
            if path.startswith("services/api/") and path.endswith(".py"):
                with self.subTest(path=path):
                    ast.parse(content)


class TheRoutesAreDerivedOnce(TestCase):
    """Three things need the same answer: the handler, the contract and the button."""

    def test_the_paths_sit_beside_the_crud_ones(self) -> None:
        routes = transition_routes(_ir())
        self.assertEqual([r.path for r in routes], ["/posts/{postId}/submit", "/posts/{postId}/publish"])

    def test_the_order_is_stable(self) -> None:
        self.assertEqual(
            [r.function for r in transition_routes(_ir())],
            [r.function for r in transition_routes(_ir())],
        )

    def test_an_ir_without_a_workflow_derives_nothing(self) -> None:
        self.assertEqual(transition_routes(example_ir("minimal-blog")), ())


class AProjectWithoutALifecycleIsUnchanged(TestCase):
    def test_the_generated_files_are_identical(self) -> None:
        plain = example_ir("minimal-blog")
        before = {f.path: f.content for f in assemble_project(plain).files()}
        after = {f.path: f.content for f in assemble_project(plain).files()}
        self.assertEqual(before, after)

    def test_no_transition_endpoints_appear(self) -> None:
        router = {f.path: f.content for f in assemble_project(example_ir("minimal-blog")).files()}[
            "services/api/app/routers/posts.py"
        ]
        self.assertNotIn("allowed = (", router)


class TheModelIsTaughtTheShape(TestCase):
    def test_intake_describes_the_kind_that_exists(self) -> None:
        from omnistackai_agent_engine.intake.nl_to_ir import _system_instruction

        instruction = _system_instruction("minimal-blog")
        self.assertIn("order_lifecycle", instruction)
        self.assertIn("transitions", instruction)

    def test_it_warns_against_using_one_for_a_boolean(self) -> None:
        # A workflow for `published` is a state machine with two states and no rules, which is a
        # boolean wearing a costume.
        from omnistackai_agent_engine.intake.nl_to_ir import _system_instruction

        self.assertIn("Do NOT use it for a plain boolean", _system_instruction("minimal-blog"))


class RoleGuardsActuallyWork(TestCase):
    """Found while proving R-566's role guard, and far larger than R-566.

    The generated login issued a token carrying `"role": "author"` — a single string — while the
    generated guard read `claims.get("roles")` and required a list. They never matched, so **every
    role-guarded endpoint answered 403 to everyone, in every generated project**. Nothing caught it
    because no test called one: the guard and the token were each correct on their own terms.

    A transition restricted to a role is unreachable if this breaks, so it is held here.
    """

    def _auth_files(self) -> dict[str, str]:
        return _files(_ir())

    def test_the_token_carries_roles_as_a_list(self) -> None:
        router = self._auth_files()["services/api/app/routers/auth.py"]
        self.assertIn('"roles": [user.role]', router)

    def test_both_login_and_register_issue_it(self) -> None:
        # Two token-creation sites; fixing one would leave half the product broken.
        router = self._auth_files()["services/api/app/routers/auth.py"]
        self.assertEqual(router.count('"roles": [user.role]'), 2)

    def test_the_guard_still_reads_the_list(self) -> None:
        auth = self._auth_files()["services/api/app/auth.py"]
        self.assertIn('held = claims.get("roles") or []', auth)

    def test_the_two_agree_on_the_claim_name(self) -> None:
        """The property that was actually violated, asserted directly rather than by coincidence."""
        files = self._auth_files()
        issued = '"roles"' in files["services/api/app/routers/auth.py"]
        read = '"roles"' in files["services/api/app/auth.py"]
        self.assertTrue(issued and read, "the token and the guard must name the same claim")
