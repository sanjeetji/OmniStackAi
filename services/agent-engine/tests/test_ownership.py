"""R-570: whose records are whose, in every backend the platform generates.

Seen live in PC-008: a published notes app saved every note with `created_by` empty and listed
everybody's notes to everybody. Every generated app with sign-in now records who created a row, and
an `ownership` rule narrows an entity to its creator - enforced by the API, refused as "not found".
These check the plan, the prompt reading and the code each backend emits; the live proof runs a
generated app with two users.
"""

import ast
import json
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import ApplicationIR, InvalidIRError
from omnistackai_agent_engine.application_ir.ownership import OwnershipRule, ownership_for_entity
from omnistackai_agent_engine.codegen.backend_go import GoBackendAdapter
from omnistackai_agent_engine.codegen.backend_node import ExpressBackendAdapter, HonoBackendAdapter
from omnistackai_agent_engine.codegen.backend_python import PythonBackendAdapter
from omnistackai_agent_engine.intake.ir_repair import repair_ir_dict, resolve_entity_reference
from omnistackai_agent_engine.intake.ownership_intent import ownership_from_prompt

FIXTURE = Path(__file__).parent / "fixtures" / "ir" / "hiring_portal.json"


def _plan(*rules: dict, public_list: bool = True, workflow: bool = True) -> dict:
    data = json.loads(FIXTURE.read_text())
    data["roles"].append({"id": "manager", "permissions": []})
    caps = []
    if workflow:
        caps.append({"kind": "workflow", "name": "order_flow", "config": {
            "entity": "Order", "field": "status", "states": ["placed", "cancelled"], "initial": "placed",
            "transitions": [{"name": "cancel", "to": "cancelled", "from": ["placed"], "roles": []}]}})
    caps += [{"kind": "ownership", "name": f"{r['entity'].lower()}_ownership", "config": r} for r in rules]
    data["capabilities"] = caps
    if public_list:
        for api in data["apis"]:
            if api["method"] == "GET" and api["path"] == "/orders":
                api["auth"] = False
    return data


def _ir(*rules: dict, **kw) -> ApplicationIR:
    return ApplicationIR.from_dict(_plan(*rules, **kw))


ORDER_OWN = {"entity": "Order", "read": "own", "write": "own", "see_all": ["manager"]}


def _files(adapter, ir) -> dict[str, str]:
    return {f.path: f.content for f in adapter.generate(ir).files()}


class TheRuleIsPartOfThePlan(TestCase):
    def test_round_trip_and_defaults(self) -> None:
        ir = _ir(ORDER_OWN, {"entity": "Product"})
        again = ApplicationIR.from_dict(ir.to_dict())
        self.assertEqual(ownership_for_entity(again, "Order"), OwnershipRule("Order", "own", "own", ("manager",)))
        product = ownership_for_entity(again, "Product")
        self.assertEqual((product.read, product.write), ("all", "own"))
        self.assertEqual(product.bypass_roles, ("admin",))

    def test_what_you_cannot_see_you_cannot_change(self) -> None:
        self.assertTrue(OwnershipRule("Note", read="own", write="all").writes_own)

    def test_bad_rules_are_refused(self) -> None:
        for rule in ({"entity": "Ghost"}, {"entity": "Order", "read": "mine"},
                     {"entity": "Order", "see_all": ["nobody_declared"]}, {"entity": "Order", "colour": "red"}):
            with self.subTest(rule=rule), self.assertRaises(InvalidIRError):
                _ir(rule)
        with self.assertRaises(InvalidIRError):
            _ir(ORDER_OWN, {"entity": "Order"})  # two rules for one entity


class ThePromptIsRead(TestCase):
    def _rules(self, prompt: str, entities: list[str]) -> list[str]:
        data = {"entities": [{"name": e} for e in entities], "capabilities": []}
        ownership_from_prompt(prompt, data)
        return [c["config"]["entity"] for c in data["capabilities"]]

    def test_private_records_become_owner_scoped(self) -> None:
        self.assertEqual(self._rules("A private notes app", ["Note", "Tag"]), ["Note"])
        self.assertEqual(self._rules("Personal journal entries with moods", ["JournalEntry", "Mood"]), ["JournalEntry"])
        self.assertEqual(self._rules("Track my own expenses", ["Expense"]), ["Expense"])

    def test_words_that_do_not_mean_each_users_records_are_left_alone(self) -> None:
        self.assertEqual(self._rules("Booking for a private clinic", ["Clinic", "Appointment"]), [])
        # A driver's orders were created by customers: a creator rule would hide them all.
        self.assertEqual(self._rules("A driver sees only their own orders", ["Order", "Driver"]), [])

    def test_a_rule_the_plan_already_has_is_kept(self) -> None:
        data = {"entities": [{"name": "Note"}], "capabilities": [
            {"kind": "ownership", "name": "n", "config": {"entity": "Note", "read": "all", "write": "own"}}]}
        self.assertEqual(ownership_from_prompt("private notes", data), [])
        self.assertEqual(data["capabilities"][0]["config"]["read"], "all")

    def test_se_plurals_resolve(self) -> None:
        self.assertEqual(resolve_entity_reference("expenses", ["Expense"]), "Expense")
        self.assertEqual(resolve_entity_reference("addresses", ["Address"]), "Address")


class AModelsMistakesAreRepaired(TestCase):
    def test_entity_names_resolve_and_unknown_roles_drop(self) -> None:
        data = _plan({"entity": "orders", "read": "own", "see_all": ["manager", "wizard"]}, workflow=False)
        data, notes = repair_ir_dict(data)
        config = data["capabilities"][0]["config"]
        self.assertEqual((config["entity"], config["see_all"]), ("Order", ["manager"]))
        self.assertTrue(any("wizard" in n for n in notes))
        ApplicationIR.from_dict(data)

    def test_a_client_supplied_owner_reference_goes(self) -> None:
        """Seen live: Note had a required user_id and a relation to User; every create got a 422."""
        data = _plan({"entity": "Order", "read": "own"}, workflow=False)
        order = next(e for e in data["entities"] if e["name"] == "Order")
        order["fields"].append({"name": "user_id", "type": "uuid", "required": True})
        order.setdefault("relations", []).append({"name": "user", "target_entity": "Customer", "kind": "many_to_one"})
        data, notes = repair_ir_dict(data)
        order = next(e for e in data["entities"] if e["name"] == "Order")
        self.assertNotIn("user_id", [f["name"] for f in order["fields"]])
        self.assertNotIn("user", [r["name"] for r in order.get("relations", [])])
        self.assertIn("customer", [r["name"] for r in order.get("relations", [])], "a real relation stays")
        ApplicationIR.from_dict(data)

    def test_a_rule_for_nothing_is_removed_not_fatal(self) -> None:
        data, notes = repair_ir_dict(_plan({"entity": "Spaceship"}, workflow=False))
        self.assertEqual(data["capabilities"], [])
        self.assertTrue(any("Spaceship" in n for n in notes))


class PythonEnforcesIt(TestCase):
    def setUp(self) -> None:
        self.files = _files(PythonBackendAdapter(), _ir(ORDER_OWN, {"entity": "OrderItem", "read": "own"},
                                                        {"entity": "Product"}))
        for path, content in self.files.items():
            if path.endswith(".py"):
                ast.parse(content, path)
        self.orders = self.files["app/routers/orders.py"]

    def test_every_create_records_its_creator_from_the_token(self) -> None:
        for router in ("orders", "products", "customers"):
            with self.subTest(router=router):
                self.assertIn("created_by=owner_of(claims)", self.files[f"app/routers/{router}.py"])
        self.assertNotIn("created_by", self.files["app/models.py"], "a client cannot set it")

    def test_lists_are_narrowed_in_sql_and_the_public_list_needs_sign_in(self) -> None:
        self.assertIn("claims: dict = Depends(require_auth)", self.orders.split('@router.get("/orders")')[1].split("\n")[1])
        self.assertIn("owner = owner_scope(claims, ('manager', 'admin'))", self.orders)
        self.assertIn("owner=owner", self.orders)
        repo = self.files["app/repositories/order.py"]
        self.assertIn('WHERE "created_by" = %s) AS scoped', repo)
        self.assertIn("(*src_params,", repo)

    def test_someone_elses_record_is_not_found(self) -> None:
        for fn in ("get_orders_orderid", "put_orders_orderid", "cancel_order"):
            with self.subTest(fn=fn):
                body = self.orders.split(f"async def {fn}(")[1].split("\n@router")[0]
                self.assertIn("not can_touch(", body)
                self.assertIn('status_code=404', body)

    def test_a_read_all_entity_is_not_narrowed(self) -> None:
        products = self.files["app/routers/products.py"]
        self.assertNotIn("owner_scope", products)
        self.assertIn("can_touch", products.split("async def put_products_productid(")[1])

    def test_the_dev_session_and_strangers_see_nothing_by_default(self) -> None:
        auth = self.files["app/auth.py"]
        self.assertIn("return owner_of(claims) or NOBODY", auth)
        self.assertIn('return isinstance(held, list) and bool(set(held) & (set(roles) | {"admin"}))', auth)

    def test_the_repository_shapes_all_compile_with_the_owner_filter(self) -> None:
        # Customer (search), Order (filters), OrderItem (by-relation lists) - three query shapes.
        for table in ("order", "order_item"):
            with self.subTest(table=table):
                repo = self.files[f"app/repositories/{table}.py"]
                ast.parse(repo)
                listing = [part for part in repo.split("\nasync def ")[1:] if part.startswith(("list_", "count_"))]
                self.assertGreaterEqual(len(listing), 2)
                for fn in listing:
                    self.assertNotIn("FROM {TABLE}", fn, fn.split("(")[0])
                    self.assertIn("src, src_params = _scoped(owner)", fn)


class GoEnforcesIt(TestCase):
    def setUp(self) -> None:
        self.files = _files(GoBackendAdapter(), _ir(ORDER_OWN, {"entity": "Product"}))

    def test_claims_reach_the_handlers(self) -> None:
        auth = self.files["internal/handlers/auth.go"]
        self.assertIn("next(w, withClaims(r, claims))", auth)
        self.assertIn("func OwnerScope(", auth)

    def test_lists_creates_and_reads(self) -> None:
        orders = self.files["internal/handlers/orders.go"]
        self.assertIn('owner := OwnerScope(ClaimsFrom(r), "manager", "admin")', orders)
        self.assertIn("store.CreateOrder(r.Context(), h.DB, m, OwnerOf(ClaimsFrom(r)))", orders)
        self.assertIn('!CanTouch(ClaimsFrom(r), owner, "manager", "admin")', orders)
        store = self.files["internal/store/order.go"]
        self.assertRegex(store, r"NULLIF\(\$\d+, ''\)::uuid\) RETURNING")
        self.assertIn("src := ownedSource(`\"order\"`, owner)", store)
        self.assertIn("func OwnerOrder(", store)
        self.assertIn("ownerID.MatchString(owner)", self.files["internal/store/store.go"])

    def test_the_public_list_and_the_owner_transition_need_sign_in(self) -> None:
        main = self.files["main.go"]
        self.assertIn('mux.HandleFunc("GET /orders", handlers.RequireAuth(h.GetOrders))', main)
        self.assertIn('mux.HandleFunc("POST /orders/{orderId}/cancel", handlers.RequireAuth(h.CancelOrder))', main)


class NodeEnforcesIt(TestCase):
    def test_express_and_hono(self) -> None:
        for adapter, user in ((ExpressBackendAdapter(), "(req as any).user"), (HonoBackendAdapter(), "(c as any).get('user')")):
            with self.subTest(adapter=type(adapter).__name__):
                files = _files(adapter, _ir(ORDER_OWN))
                orders = files["src/routes/orders.ts"]
                self.assertIn(f"ownerScope({user}, ['manager', 'admin'])", orders)
                self.assertIn(f"OrderRepository.create(parsed.data, ownerOf({user}))", orders)
                self.assertIn(f"!canTouch({user}, owner, ['manager', 'admin'])", orders)
                self.assertIn("get('/', requireAuth, ", orders, "the public list now needs sign-in")
                repo = files["src/db/order.ts"]
                self.assertIn("static async ownerOf(id: string)", repo)
                self.assertIn("\"created_by\" = $3 LIMIT $1 OFFSET $2", repo)

    def test_node_crud_now_checks_the_endpoints_roles(self) -> None:
        data = _plan(workflow=False)
        for api in data["apis"]:
            if api["method"] == "POST" and api["path"] == "/products":
                api["required_roles"] = ["manager"]
        files = _files(ExpressBackendAdapter(), ApplicationIR.from_dict(data))
        self.assertIn("router.post('/', requireRoles('manager'), ", files["src/routes/products.ts"])
        self.assertIn("export function requireRoles(", files["src/middleware/auth.ts"])


class WithoutARuleNothingNarrows(TestCase):
    def test_only_the_creator_is_recorded(self) -> None:
        files = _files(PythonBackendAdapter(), _ir(workflow=False, public_list=False))
        orders = files["app/routers/orders.py"]
        self.assertNotIn("owner_scope", orders)
        self.assertNotIn("can_touch", orders)
        self.assertIn("created_by=owner_of(claims)", orders)


class ADeleteWithoutASchemaIsStillWired(TestCase):
    def test_its_collection_names_the_entity(self) -> None:
        """Seen live in the private-notes build: DELETE /notes/{noteId} stayed a 501 stub."""
        from omnistackai_agent_engine.application_ir import ApiEndpoint, HttpMethod
        from omnistackai_agent_engine.codegen.route_wiring import Op, wire_endpoint

        api = ApiEndpoint(HttpMethod.DELETE, "/notes/{noteId}")
        wiring = wire_endpoint(api, frozenset({"Note", "Tag"}))
        self.assertEqual((wiring.op, wiring.entity, wiring.id_param), (Op.DELETE, "Note", "noteId"))
        self.assertIsNone(wire_endpoint(ApiEndpoint(HttpMethod.DELETE, "/sessions/{id}"), frozenset({"Note"})))
