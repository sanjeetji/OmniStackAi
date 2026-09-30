"""PC-101: a record a form must point at can be listed, and a nested-only create gets a plain one.

Both seen live in PC-102: a job posting's required recruiter_id pointed at a Recruiter with no API
(no form could fill it, so no posting could be created), and applications could only be created
under /job_postings/{id}/applications, which no backend wires and the admin console cannot offer.
"""

import json
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import ApplicationIR, example_ir
from omnistackai_agent_engine.codegen.nextjs import entity_api_functions
from omnistackai_agent_engine.codegen.reachable_references import with_reachable_references
from omnistackai_agent_engine.codegen.route_wiring import Op

_PORTAL = Path(__file__).parent / "fixtures" / "ir" / "hiring_portal.json"


def _plan_with_gaps() -> ApplicationIR:
    data = json.loads(_PORTAL.read_text(encoding="utf-8"))
    field = lambda name, kind, required=True: {"name": name, "type": kind, "required": required, "unique": False, "validation": []}  # noqa: E731
    data["entities"].append({"name": "Recruiter", "fields": [field("id", "uuid"), field("name", "string")], "relations": []})
    product = next(e for e in data["entities"] if e["name"] == "Product")
    product["fields"].append(field("recruiter_id", "uuid"))
    data["apis"] = [a for a in data["apis"] if "OrderItem" not in (a["request_schema"], a["response_schema"])]
    data["apis"].append({"method": "POST", "path": "/orders/{id}/items", "auth": True, "request_schema": "OrderItem",
                         "response_schema": "OrderItem", "error_schema": None, "required_roles": ["analyst"]})
    return ApplicationIR.from_dict(data)


class EveryReferenceCanBePicked(TestCase):
    def setUp(self) -> None:
        self.before = _plan_with_gaps()
        self.after = with_reachable_references(self.before)
        self.added = {(a.method.value, a.path): a for a in self.after.apis[len(self.before.apis):]}

    def test_a_referenced_entity_without_an_api_can_be_listed_read_and_added(self) -> None:
        self.assertIn(("GET", "/recruiters"), self.added)
        self.assertIn(("GET", "/recruiters/{id}"), self.added)
        create = self.added[("POST", "/recruiters")]
        self.assertEqual(create.required_roles, ("admin",), "adding one is for the admin")
        self.assertTrue(self.added[("GET", "/recruiters")].auth, "reading follows the app's sign-in")

    def test_a_nested_only_create_gets_a_plain_one_under_the_same_roles(self) -> None:
        create = self.added[("POST", "/order_items")]
        self.assertEqual(create.required_roles, ("analyst",))
        self.assertIn(("GET", "/order_items"), self.added)

    def test_the_admin_console_can_now_offer_new_for_both(self) -> None:
        functions = entity_api_functions(self.after)
        for entity in ("Recruiter", "OrderItem"):
            self.assertIn(Op.LIST, functions[entity], entity)
            self.assertIn(Op.CREATE, functions[entity], entity)

    def test_complete_plans_are_unchanged_and_it_is_idempotent(self) -> None:
        self.assertEqual(with_reachable_references(self.after), self.after)
        blog = example_ir("minimal-blog")
        self.assertEqual(with_reachable_references(blog), blog)

    def test_the_fixture_plan_had_the_gap_too(self) -> None:
        # Its order items could be created, edited and deleted only under /orders/{orderId}/items.
        portal = ApplicationIR.from_dict(json.loads(_PORTAL.read_text(encoding="utf-8")))
        added = {(a.method.value, a.path) for a in with_reachable_references(portal).apis[len(portal.apis):]}
        self.assertEqual(added, {("GET", "/order_items"), ("GET", "/order_items/{id}"), ("POST", "/order_items"),
                                 ("PUT", "/order_items/{id}"), ("DELETE", "/order_items/{id}")})
        functions = entity_api_functions(with_reachable_references(portal))["OrderItem"]
        self.assertEqual(set(functions), {Op.LIST, Op.GET, Op.CREATE, Op.UPDATE, Op.DELETE})


class TheAddedPathsUseThePlansParameterNames(TestCase):
    def test_an_existing_param_name_under_the_same_path_is_reused(self) -> None:
        # PC-101, seen live: /projects/{id} beside /projects/{projectId}/tasks broke `next dev`
        # ("different slug names for the same dynamic path").
        portal = ApplicationIR.from_dict(json.loads(_PORTAL.read_text(encoding="utf-8")))
        from dataclasses import replace as _replace

        from omnistackai_agent_engine.application_ir import ApiEndpoint, HttpMethod

        plan = _replace(portal, apis=portal.apis + (ApiEndpoint(HttpMethod.GET, "/order_items/{orderItemId}/notes", auth=True),))
        added = {(a.method.value, a.path) for a in with_reachable_references(plan).apis[len(plan.apis):]}
        self.assertIn(("GET", "/order_items/{orderItemId}"), added)
        self.assertNotIn(("GET", "/order_items/{id}"), added)
