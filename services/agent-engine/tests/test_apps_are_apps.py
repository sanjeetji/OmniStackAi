"""R-562: a request for an app is answered with an app.

"A platform for food delivery with a marketing website, admin panel, customer + driver apps"
returned four Next.js websites. `ecosystem.py` built every surface with `MobileProfile.NONE` and
`WebStrategy.NEXTJS` hardcoded, and `assemble_ecosystem` only ever reached for a Next.js adapter, so
the driver "app" was a web page and nothing anywhere said so.

R-559 removed this for stacks: when we cannot build what was asked for, build the nearest thing and
explain. This was the same disappearance with a worse excuse, because here we *could* build the app
and simply did not.

Two rules carry most of the weight, and both were learned the hard way while writing this:

* **A customer's app is built beside their website, not instead of it.** Flipping the customer
  surface to mobile deleted the only public web presence — in a prompt that asked for a marketing
  website in the same sentence. Answering one request by dropping another is the failure this task
  exists to end, so an operator's app replaces their portal and a customer's app is additional.
* **The app carries the website's scope.** The companion was first derived from a renamed surface,
  and entity scoping is keyed by surface kind, so it fell through to a word match and lost
  `MenuItem` — a food-delivery customer app that cannot show a menu.
"""

from unittest import TestCase

from omnistackai_agent_engine.application_ir import MobileProfile
from omnistackai_agent_engine.codegen.ecosystem_assembler import assemble_ecosystem
from omnistackai_agent_engine.intake.ecosystem import plan_ecosystem_from_prompt
from omnistackai_agent_engine.intake.surface_form import form_for_surface

_FOOD = (
    "Create a platform for the food delivery with marketing website, admin-panel, "
    "customer + driver apps"
)


def _plan(prompt: str = _FOOD):
    return plan_ecosystem_from_prompt(prompt, "complete")


def _forms(plan) -> dict[str, str]:
    return {
        app.surface.kind: (
            "mobile"
            if app.ir.project_strategy.mobile_profile is MobileProfile.REACT_NATIVE
            else "web"
        )
        for app in plan.apps
    }


class AnAppRequestProducesAnApp(TestCase):
    def test_the_driver_gets_a_phone_app(self) -> None:
        self.assertEqual(_forms(_plan())["driver_portal"], "mobile")

    def test_the_customer_gets_a_phone_app(self) -> None:
        self.assertEqual(_forms(_plan())["customer_app"], "mobile")

    def test_the_admin_panel_stays_a_web_app(self) -> None:
        # Desk work. Tables, filters and bulk actions are not a phone job.
        self.assertEqual(_forms(_plan())["admin_dashboard"], "web")

    def test_a_role_nobody_asked_about_stays_a_web_app(self) -> None:
        # The prompt never mentions a merchant app, so inventing one would be its own imposition.
        self.assertEqual(_forms(_plan())["merchant_portal"], "web")


class TheWebsiteSurvivesTheApp(TestCase):
    """The regression this task nearly shipped: answering one request by deleting another."""

    def test_the_customer_website_is_still_built(self) -> None:
        self.assertEqual(_forms(_plan())["customer_web"], "web")

    def test_the_app_carries_the_websites_scope(self) -> None:
        plan = _plan()
        by_kind = {app.surface.kind: {e.name for e in app.ir.entities} for app in plan.apps}
        self.assertEqual(
            by_kind["customer_app"],
            by_kind["customer_web"],
            "the app is the same product on a phone; a reduced scope makes it a different one",
        )

    def test_an_operators_app_replaces_their_portal_rather_than_doubling_it(self) -> None:
        # A courier on a bike has no use for a website, and two surfaces for one job is two things
        # to maintain.
        kinds = [app.surface.kind for app in _plan().apps]
        self.assertIn("driver_portal", kinds)
        self.assertNotIn("driver_app", kinds)


class TheMonorepoCarriesSeveralApps(TestCase):
    def setUp(self) -> None:
        self.paths = {f.path for f in assemble_ecosystem(_plan()).files()}

    def _dirs_with(self, marker: str) -> set[str]:
        return {
            path.split("/")[1]
            for path in self.paths
            if path.startswith("apps/") and path.endswith(marker)
        }

    def test_two_separate_react_native_apps_are_generated(self) -> None:
        # There was exactly one `apps/mobile` before this; an ecosystem needs one per role.
        native = self._dirs_with("app.config.js")
        self.assertEqual(native, {"customer-app", "driver"})

    def test_the_web_apps_are_still_next_js(self) -> None:
        self.assertEqual(self._dirs_with("next.config.mjs"), {"web", "admin", "merchant"})

    def test_there_is_still_exactly_one_backend(self) -> None:
        backends = {p.split("/")[1] for p in self.paths if p.startswith("services/")}
        self.assertEqual(backends, {"api"}, "the apps share one API and one database")

    def test_each_native_app_is_runnable(self) -> None:
        for app in ("customer-app", "driver"):
            with self.subTest(app=app):
                self.assertIn(f"apps/{app}/package.json", self.paths)
                self.assertIn(f"apps/{app}/index.js", self.paths)

    def test_the_readme_says_which_is_which(self) -> None:
        # A user who asked for apps should see that they got them without opening five directories.
        readme = next(
            f.content for f in assemble_ecosystem(_plan()).files() if f.path == "README.md"
        )
        self.assertIn("| `apps/driver` | Courier Dispatch App | React Native app |", readme)
        self.assertIn("| `apps/web` | Customer Ordering App | web app |", readme)


class TheDecisionIsDeterministicAndExplained(TestCase):
    def test_the_same_prompt_gives_the_same_surfaces_twice(self) -> None:
        self.assertEqual(_forms(_plan()), _forms(_plan()))

    def test_every_decision_carries_a_reason(self) -> None:
        for kind, actor in (("driver_portal", "courier"), ("admin_dashboard", "admin")):
            with self.subTest(kind=kind):
                form = form_for_surface(kind=kind, actor=actor, prompt=_FOOD)
                self.assertTrue(form.reason.strip(), "a surface decided in silence cannot be argued with")

    def test_a_product_noun_does_not_conjure_a_phone_app(self) -> None:
        """"a delivery app" is what people call a web product. Reading it as a form-factor request
        would turn "a blog app" into React Native, and being handed a phone project nobody asked
        for is worse than a web page that opens anywhere."""
        form = form_for_surface(kind="customer_web", actor="customer", prompt="a delivery app")
        self.assertEqual(form.form, "web")

    def test_an_app_elsewhere_in_the_sentence_does_not_move_the_admin_panel(self) -> None:
        form = form_for_surface(
            kind="admin_dashboard", actor="admin", prompt="a delivery app with an admin panel"
        )
        self.assertEqual(form.form, "web")


class ThePreviewOffersOneQrPerApp(TestCase):
    """A single `expo_url` cannot stand for a courier app and a customer app at once."""

    def setUp(self) -> None:
        import base64
        import tempfile
        from pathlib import Path

        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        for f in assemble_ecosystem(_plan()).files():
            out = root / f.path
            out.parent.mkdir(parents=True, exist_ok=True)
            if f.base64_encoded:
                out.write_bytes(base64.b64decode(f.content))
            else:
                out.write_text(f.content, encoding="utf-8")
        from omnistackai_agent_engine.localrun.plan import build_run_plan

        self.plan = build_run_plan(str(root), db_password="x", extra_app_ports=(3200, 3300))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_each_native_app_is_offered_separately(self) -> None:
        mobile = [a for a in self.plan.preview_apps() if a["kind"] == "mobile"]
        self.assertEqual({a["id"] for a in mobile}, {"customer-app", "driver"})

    def test_each_one_has_its_own_port_and_its_own_qr(self) -> None:
        mobile = [a for a in self.plan.preview_apps() if a["kind"] == "mobile"]
        self.assertEqual(len({a["port"] for a in mobile}), 2, "two apps cannot share a port")
        self.assertEqual(len({a["scan"] for a in mobile}), 2, "two apps cannot share a QR")
        for app in mobile:
            self.assertTrue(app["scan"].startswith("exp://"), "Expo Go opens exp:// URLs")

    def test_each_one_is_started(self) -> None:
        started = [s.label for s in self.plan.steps if "expo" in s.label]
        self.assertEqual(len(started), 2, f"both apps must be started: {started}")

    def test_the_native_apps_are_not_proxied_as_web_apps(self) -> None:
        # A native app cannot be rendered in an iframe, and listing one as a web surface would put
        # a blank frame in the console.
        web = {a["id"] for a in self.plan.preview_apps() if a["kind"] in ("web", "admin")}
        self.assertEqual(web, {"web", "admin", "merchant"})
