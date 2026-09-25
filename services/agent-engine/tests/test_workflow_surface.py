"""R-588: a transition is describable and callable, not only implemented.

R-566 generated working transition handlers and stopped there. The contract described an API
without them, and the typed client had no function to call one — so a lifecycle existed in the
backend and nothing outside it could reach it. An endpoint nobody can call is not far from an
endpoint that does not exist.

All three now come from `transition_routes`, the same derivation the handlers use. Three separate
derivations would be three chances for the handler, the contract and the client to describe
different endpoints, which is the shape of most of the defects this repository has found.
"""

import dataclasses
import json
from unittest import TestCase

from omnistackai_agent_engine.application_ir import Field, FieldType, example_ir
from omnistackai_agent_engine.application_ir.capability import Capability
from omnistackai_agent_engine.codegen.assembler import assemble_project
from omnistackai_agent_engine.codegen.openapi import render_openapi_json
from omnistackai_agent_engine.codegen.workflow_routes import transition_routes

_CONFIG = {
    "entity": "Post",
    "field": "status",
    "states": ["draft", "review", "live"],
    "initial": "draft",
    "transitions": [{"name": "publish", "to": "live", "from": ["review"], "roles": ["author"]}],
}


def _ir():
    base = example_ir("minimal-blog")
    entities = tuple(
        dataclasses.replace(e, fields=e.fields + (Field(name="status", type=FieldType.STRING, required=True),))
        if e.name == "Post"
        else e
        for e in base.entities
    )
    return dataclasses.replace(
        base, entities=entities, capabilities=(Capability("workflow", "post_lifecycle", _CONFIG),)
    )


def _files():
    return {f.path: f.content for f in assemble_project(_ir()).files()}


class TheContractDescribesTheTransition(TestCase):
    def setUp(self) -> None:
        self.doc = json.loads(render_openapi_json(_ir()))

    def test_the_path_is_documented(self) -> None:
        self.assertIn("/posts/{postId}/publish", self.doc["paths"])

    def test_it_says_which_states_it_is_allowed_from(self) -> None:
        # A contract that only names the endpoint leaves a caller to discover the rule by 409.
        description = self.doc["paths"]["/posts/{postId}/publish"]["post"]["description"]
        self.assertIn("Allowed from: review", description)

    def test_it_says_which_role_it_needs(self) -> None:
        description = self.doc["paths"]["/posts/{postId}/publish"]["post"]["description"]
        self.assertIn("Requires role: author", description)

    def test_the_conflict_response_is_declared(self) -> None:
        # 409 rather than 400: the payload is fine, the row is simply not where it needs to be.
        self.assertIn("409", self.doc["paths"]["/posts/{postId}/publish"]["post"]["responses"])

    def test_it_returns_the_entity(self) -> None:
        responses = self.doc["paths"]["/posts/{postId}/publish"]["post"]["responses"]
        ref = responses["200"]["content"]["application/json"]["schema"]["$ref"]
        self.assertEqual(ref, "#/components/schemas/Post")

    def test_a_project_without_a_workflow_documents_nothing_extra(self) -> None:
        plain = json.loads(render_openapi_json(example_ir("minimal-blog")))
        self.assertFalse([p for p in plain["paths"] if "publish" in p])


class TheClientCanCallIt(TestCase):
    def setUp(self) -> None:
        self.api = _files()["apps/web/lib/api.ts"]

    def test_a_function_is_generated(self) -> None:
        self.assertIn("export async function publishPost(", self.api)

    def test_it_posts_to_the_right_path(self) -> None:
        self.assertIn("/posts/${encodeURIComponent(id)}/publish", self.api)
        self.assertIn('method: "POST"', self.api)

    def test_it_is_exported_on_the_api_object(self) -> None:
        # Everything else is reached through `api.*`; a function nobody can find is not callable.
        self.assertIn("  publishPost,", self.api)

    def test_the_rule_is_written_where_a_developer_reads_it(self) -> None:
        self.assertIn("Allowed from: review", self.api)
        self.assertIn("Requires role: author", self.api)

    def test_it_returns_the_entity_type(self) -> None:
        self.assertIn("Promise<Post>", self.api)

    def test_a_project_without_a_workflow_gains_nothing(self) -> None:
        plain = {f.path: f.content for f in assemble_project(example_ir("minimal-blog")).files()}
        self.assertNotIn("publishPost", plain["apps/web/lib/api.ts"])


class TheThreeAgreeBecauseTheyShareOneDerivation(TestCase):
    def test_the_handler_the_contract_and_the_client_name_one_path(self) -> None:
        route = transition_routes(_ir())[0]
        files = _files()
        doc = json.loads(render_openapi_json(_ir()))
        self.assertIn(route.path, doc["paths"])
        self.assertIn(f'@router.post("{route.path}"', files["services/api/app/routers/posts.py"])
        self.assertIn("/posts/${encodeURIComponent(id)}/publish", files["apps/web/lib/api.ts"])
