"""R-554: a planned ecosystem assembles into one monorepo over one API and one database.

`plan_ecosystem_from_prompt` has long planned four role-scoped surfaces for a food-delivery
prompt, and `intake.build_ecosystem` materialises each one as its own separate Git repo with its
own backend and its own database. That is four disconnected apps, not an ecosystem: the courier's
app cannot see the customer's order, which is the entire point.

The invariant this file exists to hold: **every route a surface calls must exist on the shared
server, and every role allowed to call it in a surface must be allowed there too.** Each app is
generated from its own scoped IR — the courier app ships no menu editor — so only the server knows
everything, and if the union is wrong a surface calls a route that 404s or a role that 403s.
"""

import re
import hashlib
from unittest import TestCase

from omnistackai_agent_engine.codegen.ecosystem_assembler import (
    SURFACE_DIRECTORIES,
    assemble_ecosystem,
    surface_directory,
    union_ir,
)
from omnistackai_agent_engine.intake.ecosystem import plan_ecosystem_from_prompt

DELIVERY = "a food delivery app with customers, drivers and restaurants"


def _plan(prompt: str = DELIVERY):
    return plan_ecosystem_from_prompt(prompt, "complete")


def _paths(project) -> list[str]:
    return [f.path for f in project.files()]


class ItIsOneProjectNotFour(TestCase):
    def setUp(self) -> None:
        self.plan = _plan()
        self.project = assemble_ecosystem(self.plan)
        self.paths = _paths(self.project)

    def test_every_planned_surface_becomes_an_app(self) -> None:
        directories = sorted({p.split("/")[1] for p in self.paths if p.startswith("apps/")})
        self.assertEqual(directories, ["admin", "driver", "merchant", "web"])
        self.assertEqual(len(directories), len(self.plan.apps))

    def test_there_is_exactly_one_backend(self) -> None:
        """Four backends is four databases, and the courier could not see the customer's order."""
        backends = {p.split("/")[1] for p in self.paths if p.startswith("services/")}
        self.assertEqual(backends, {"api"})

    def test_there_is_one_brand_and_one_contract(self) -> None:
        self.assertIn("brand.json", self.paths)
        self.assertIn("contracts/openapi.json", self.paths)
        self.assertEqual(sum(1 for p in self.paths if p == "brand.json"), 1)

    def test_the_customer_app_and_admin_land_where_the_runner_expects_them(self) -> None:
        """R-553's runner gives `web` and `admin` established ids, ports and base paths, and the
        console renders them specially."""
        self.assertIn("apps/web/package.json", self.paths)
        self.assertIn("apps/admin/package.json", self.paths)

    def test_the_readme_explains_the_shared_api(self) -> None:
        readme = self.project.get("README.md").content
        self.assertIn("same API and the same database", readme)
        for directory in ("apps/web", "apps/merchant", "apps/driver", "apps/admin"):
            self.assertIn(directory, readme)


class TheSharedServerKnowsWhatEveryAppNeeds(TestCase):
    """The invariant. A surface calling a route the server does not serve is a 404 in production."""

    def setUp(self) -> None:
        self.plan = _plan()
        self.union = union_ir(self.plan)

    def test_every_route_any_surface_calls_exists_on_the_server(self) -> None:
        served = {(api.method.value, api.path) for api in self.union.apis}
        for app in self.plan.apps:
            with self.subTest(surface=app.surface.kind):
                called = {(api.method.value, api.path) for api in app.ir.apis}
                self.assertEqual(called - served, set(), "routes the server does not serve")

    def test_a_role_allowed_in_a_surface_is_allowed_on_the_server(self) -> None:
        """Union, not first-wins: `DELETE /orders/{id}` is reached by four different roles, and
        taking whichever surface merged first would 403 the other three."""
        expected: dict[tuple[str, str], set[str]] = {}
        for app in self.plan.apps:
            for api in app.ir.apis:
                expected.setdefault((api.method.value, api.path), set()).update(api.required_roles)
        served = {(a.method.value, a.path): set(a.required_roles) for a in self.union.apis}
        for key, roles in expected.items():
            with self.subTest(route=key):
                self.assertEqual(served.get(key), roles)

    def test_every_entity_any_surface_uses_exists_on_the_server(self) -> None:
        served = {entity.name for entity in self.union.entities}
        for app in self.plan.apps:
            with self.subTest(surface=app.surface.kind):
                self.assertEqual({e.name for e in app.ir.entities} - served, set())

    def test_a_shared_entity_keeps_every_surfaces_fields(self) -> None:
        """Superset, not first-wins: a backend missing a column silently breaks whichever surface
        needed it."""
        expected: dict[str, set[str]] = {}
        for app in self.plan.apps:
            for entity in app.ir.entities:
                expected.setdefault(entity.name, set()).update(f.name for f in entity.fields)
        served = {e.name: {f.name for f in e.fields} for e in self.union.entities}
        for name, fields in expected.items():
            with self.subTest(entity=name):
                self.assertTrue(fields <= served[name], f"{name} lost {fields - served[name]}")

    def test_every_role_in_the_ecosystem_is_known_to_the_server(self) -> None:
        served = {role.id for role in self.union.roles}
        self.assertEqual(served, {"admin", "customer", "driver", "merchant"})

    def test_the_server_carries_no_screens(self) -> None:
        """Screens belong to the app that renders them; keeping them would generate pages twice."""
        self.assertEqual(self.union.screens, ())


class EachAppKeepsItsOwnScope(TestCase):
    def setUp(self) -> None:
        self.paths = _paths(assemble_ecosystem(_plan()))

    def _screens(self, directory: str) -> set[str]:
        """The screen ids an app ships, whichever kind of app it is.

        R-562: a surface asked for as an app is now built in React Native, which lays its screens
        out as `src/features/<entity>/ui/<Entity>ListScreen.tsx` rather than as Next.js route
        folders. The scoping rules below are about *what* an app can reach, not how its files are
        arranged, so this reads both shapes and the assertions are unchanged.
        """
        prefix = f"apps/{directory}/app/"
        routes = {
            p[len(prefix):].split("/")[0]
            for p in self.paths
            if p.startswith(prefix) and "/" in p[len(prefix):]
        }
        if routes:
            return routes
        native = re.compile(rf"^apps/{re.escape(directory)}/src/features/[^/]+/ui/(\w+?)(List|Detail|Editor)Screen\.tsx$")
        screens = set()
        for path in self.paths:
            found = native.match(path)
            if found:
                entity = re.sub(r"(?<!^)(?=[A-Z])", "_", found.group(1)).lower()
                screens.add(f"{entity}_{found.group(2).lower()}")
        return screens

    def test_a_courier_app_does_not_ship_a_menu_editor(self) -> None:
        """The whole point of scoping: a courier never edits a menu."""
        self.assertNotIn("menu_item_editor", self._screens("driver"))
        self.assertNotIn("menu_item_list", self._screens("driver"))

    def test_the_merchant_portal_does(self) -> None:
        self.assertIn("menu_item_editor", self._screens("merchant"))

    def test_the_customer_app_browses_but_does_not_edit_menus(self) -> None:
        screens = self._screens("web")
        self.assertIn("menu_item_list", screens)
        self.assertNotIn("menu_item_editor", screens)

    def test_every_app_can_reach_orders(self) -> None:
        for directory in ("web", "merchant", "driver", "admin"):
            with self.subTest(app=directory):
                self.assertIn("order_list", self._screens(directory))


class SurfacesMapToStableDirectories(TestCase):
    def test_known_surface_kinds_have_readable_names(self) -> None:
        self.assertEqual(SURFACE_DIRECTORIES["customer_web"], "web")
        self.assertEqual(SURFACE_DIRECTORIES["admin_dashboard"], "admin")
        self.assertEqual(SURFACE_DIRECTORIES["driver_portal"], "driver")

    def test_an_unknown_kind_still_gets_a_directory(self) -> None:
        self.assertEqual(surface_directory("warehouse_console", set()), "warehouse-console")

    def test_two_surfaces_cannot_collide(self) -> None:
        taken = {"web"}
        self.assertEqual(surface_directory("customer_web", taken), "web-2")


class OtherDomainsAssembleToo(TestCase):
    def test_a_booking_prompt_produces_its_own_surfaces(self) -> None:
        project = assemble_ecosystem(_plan("a salon booking system for customers and staff"))
        directories = sorted({p.split("/")[1] for p in _paths(project) if p.startswith("apps/")})
        self.assertEqual(directories, ["admin", "provider", "web"])
        self.assertTrue(any(p.startswith("services/api/") for p in _paths(project)))


class TheOutputIsReproducible(TestCase):
    def test_the_same_plan_assembles_byte_identically_twice(self) -> None:
        def digest() -> str:
            hasher = hashlib.sha256()
            for generated in sorted(assemble_ecosystem(_plan()).files(), key=lambda f: f.path):
                hasher.update(generated.path.encode())
                hasher.update(generated.content.encode())
            return hasher.hexdigest()

        self.assertEqual(digest(), digest())

    def test_assembling_a_single_ir_is_untouched(self) -> None:
        """This adds an assembler beside the existing one; it does not change it."""
        from omnistackai_agent_engine.application_ir import example_ir
        from omnistackai_agent_engine.codegen.assembler import assemble_project

        first = {f.path: f.content for f in assemble_project(example_ir("minimal-blog")).files()}
        second = {f.path: f.content for f in assemble_project(example_ir("minimal-blog")).files()}
        self.assertEqual(first, second)
        self.assertIn("apps/web/package.json", first)
