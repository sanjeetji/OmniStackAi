"""R-580: a two-sided domain builds every side's app even when the prompt names only the customer."""

from unittest import TestCase

from omnistackai_agent_engine.application_ir import ApplicationIR
from omnistackai_agent_engine.intake.ecosystem import plan_ecosystem_from_prompt
from omnistackai_agent_engine.intake.ecosystem_intent import detect_ecosystem_intent
from omnistackai_agent_engine.intake.scope_compiler import classify_domain


def _apps(prompt: str) -> list[str]:
    intent = detect_ecosystem_intent(prompt)
    if not intent.build_ecosystem:
        return []
    return [app.ir.name for app in plan_ecosystem_from_prompt(prompt, intent.option_id).apps]


class TheDomainImpliesTheOtherSide(TestCase):
    def test_two_sided_domains(self) -> None:
        cases = {
            "A logistics app where customers book parcel shipments and track them.": {"Shipper Portal", "Driver App", "Dispatch Console"},
            "A ride-hailing app for my city.": {"Rider App", "Driver App", "Operations Dashboard"},
            "Customers book plumbers and electricians for jobs at home.": {"Customer App", "Technician App", "Operations Dashboard"},
            "A marketplace for handmade jewellery.": {"Buyer Storefront", "Seller Portal", "Marketplace Admin"},
            "A food delivery app.": {"Customer Ordering App", "Merchant Portal", "Courier Dispatch App", "Super-Admin Dashboard"},
        }
        for prompt, wanted in cases.items():
            with self.subTest(prompt=prompt):
                self.assertLessEqual(wanted, set(_apps(prompt)))

    def test_one_sided_stays_one_app(self) -> None:
        for prompt in ("An online store to sell my products.", "Plan a trip with friends and share the itinerary.",
                       "A simple blog.", "Track my daily habits."):
            with self.subTest(prompt=prompt):
                self.assertEqual(_apps(prompt), [])

    def test_the_reason_says_why(self) -> None:
        self.assertIn("a logistics business has drivers as well as the customers",
                      detect_ecosystem_intent("A logistics app for my company.").reason)


class TheNewDomains(TestCase):
    def test_classified(self) -> None:
        self.assertEqual(classify_domain("We ship freight and parcels with a fleet of vans").domain, "logistics")
        self.assertEqual(classify_domain("Book an electrician or a plumber").domain, "home-services")

    def test_each_app_is_a_valid_plan(self) -> None:
        for prompt in ("A logistics app.", "A home services app for plumbers."):
            plan = plan_ecosystem_from_prompt(prompt, "complete")
            for app in plan.apps:
                with self.subTest(app=app.ir.name):
                    ApplicationIR.from_dict(app.ir.to_dict())
                    self.assertTrue(app.ir.entities)
        driver = next(a for a in plan_ecosystem_from_prompt("A logistics app.", "complete").apps if a.ir.name == "Driver App")
        self.assertIn("ProofOfDelivery", [e.name for e in driver.ir.entities])


class TheDomainImpliesPrivacy(TestCase):
    """Found in R-580's live proof: a logistics prompt with no rule let any customer list every shipment."""

    def _rules(self, prompt: str) -> dict:
        from omnistackai_agent_engine.intake.build_app import _with_prompt_rules_for_plan

        plan = _with_prompt_rules_for_plan(plan_ecosystem_from_prompt(prompt, "complete"), prompt)
        return {c.config["entity"]: c.config for c in plan.apps[0].ir.capabilities if c.kind == "ownership"}

    def test_creator_and_assignee(self) -> None:
        self.assertEqual(self._rules("A logistics app where customers book parcel shipments.")["Shipment"]["assignee"], "driver_id")
        self.assertEqual(self._rules("A ride-hailing app for my city.")["Trip"]["assignee"], "driver_id")
        self.assertEqual(self._rules("Customers book plumbers for jobs at home.")["Job"]["assignee"], "technician_id")

    def test_merchants_are_not_locked_out(self) -> None:
        self.assertNotIn("Order", self._rules("A food delivery app."), "a merchant must see its restaurant's orders (PC-120)")

    def test_the_prompt_wins(self) -> None:
        rules = self._rules("A logistics app. Shipments are visible to everyone: read all, write own.")
        self.assertIn("Shipment", rules)
