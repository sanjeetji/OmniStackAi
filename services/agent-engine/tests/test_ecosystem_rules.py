"""PC-114, found creating the payments test project: what the prompt says about privacy and money
reaches every app of an ecosystem, and a customer who signs up can buy.

"Bazaar Lite: ... customers place orders and pay online in rupees, 10% commission" was planned as a
buyer storefront, a seller portal and an admin; the money was nowhere (the prompt passes ran only on
the single-app planner), the shared backend took the first app's rules alone, a purchase had no page
to pay from, and every new account was `user` while buying required `buyer`.
"""

from dataclasses import replace
from unittest import TestCase

from omnistackai_agent_engine.application_ir import ApplicationIR, Role
from omnistackai_agent_engine.codegen.auth_templates import signup_role
from omnistackai_agent_engine.codegen.ecosystem_assembler import assemble_ecosystem, union_ir
from omnistackai_agent_engine.codegen.reachable_references import with_detail_screens, with_reachable_references
from omnistackai_agent_engine.intake.build_app import _with_prompt_rules_for_plan
from omnistackai_agent_engine.intake.ecosystem import plan_ecosystem_from_prompt
from omnistackai_agent_engine.intake.ecosystem_intent import detect_ecosystem_intent

PROMPT = ("Bazaar Lite: a small marketplace where vendors list products and customers place orders and pay "
          "online in rupees. The platform takes a 10% commission on every order, vendors see their earnings "
          "and request payouts.")


def _plan():
    return _with_prompt_rules_for_plan(plan_ecosystem_from_prompt(PROMPT, detect_ecosystem_intent(PROMPT).option_id), PROMPT)


class ThePromptsRulesReachEveryApp(TestCase):
    def test_money_in_every_app_and_the_shared_backend(self) -> None:
        plan = _plan()
        self.assertGreater(len(plan.apps), 1)
        for app in plan.apps:
            with self.subTest(app=app.ir.name):
                self.assertIn("money", [c.kind for c in app.ir.capabilities])
        money = next(c for c in union_ir(plan).capabilities if c.kind == "money").config
        self.assertEqual((money["currency"], money["commission_bps"]), ("INR", 1000))
        self.assertEqual(money["charges"][0]["entity"], "Purchase")

    def test_the_shared_backend_takes_every_apps_rules(self) -> None:
        plan = plan_ecosystem_from_prompt(PROMPT, detect_ecosystem_intent(PROMPT).option_id)
        second = plan.apps[1].ir
        workflow_free = second.to_dict()
        workflow_free["capabilities"] = [{"kind": "ownership", "name": "only_here", "config": {
            "entity": second.entities[0].name, "read": "own", "write": "own"}}]
        plan = replace(plan, apps=(plan.apps[0], replace(plan.apps[1], ir=ApplicationIR.from_dict(workflow_free)), *plan.apps[2:]))
        self.assertIn("only_here", [c.name for c in union_ir(plan).capabilities])

    def test_a_purchase_has_a_page_to_pay_from(self) -> None:
        plan = _plan()
        plan = replace(plan, apps=tuple(replace(a, ir=with_detail_screens(with_reachable_references(a.ir))) for a in plan.apps))
        files = {f.path: f.content for f in assemble_ecosystem(plan, prompt=PROMPT).files()}
        self.assertIn("PayPanel", files["apps/web/app/purchase_detail/page.tsx"])
        self.assertIn("services/api/app/money.py", files)


class ACustomerCanSignUpAndBuy(TestCase):
    def _ir(self, *roles: str):
        from types import SimpleNamespace

        return SimpleNamespace(roles=tuple(Role(r) for r in roles))

    def test_the_plans_customer_role(self) -> None:
        self.assertEqual(signup_role(self._ir("admin", "buyer", "seller")), "buyer")
        self.assertEqual(signup_role(self._ir("admin", "patient", "doctor")), "patient")

    def test_staff_roles_are_never_self_chosen(self) -> None:
        self.assertEqual(signup_role(self._ir("admin", "seller", "manager")), "user")
