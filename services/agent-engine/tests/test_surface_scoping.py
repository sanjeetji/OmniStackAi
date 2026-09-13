"""R-433: deterministic per-surface entity and capability scoping."""

from __future__ import annotations

import unittest

from omnistackai_agent_engine.application_ir import (
    Entity,
    Field,
    FieldType,
    HttpMethod,
    Relation,
    RelationKind,
    validate_ir,
)
from omnistackai_agent_engine.application_ir.validate import has_errors
from omnistackai_agent_engine.codegen.route_wiring import wire_endpoint
from omnistackai_agent_engine.intake import (
    Actor,
    AppSurface,
    DOMAIN_ENTITIES,
    DOMAIN_LIBRARY,
    ScopeProposal,
    plan_ecosystem,
    plan_ecosystem_from_prompt,
)
from omnistackai_agent_engine.intake.ecosystem import (
    CURATED_SURFACE_ENTITIES,
    CURATED_SURFACE_WRITABLE_ENTITIES,
)


def _app(plan, kind: str):
    return next(app for app in plan.apps if app.surface.kind == kind)


def _custom_proposal(*surfaces: AppSurface) -> ScopeProposal:
    actors = tuple(Actor(surface.actor, f"{surface.actor} user") for surface in surfaces)
    return ScopeProposal(
        prompt="Manage apiaries, hive inspections, and treatments",
        domain="apiary-management",
        domain_confidence=1.0,
        business_model="Apiary operations",
        actors=actors,
        surfaces=surfaces,
        options=(),
        questions=(),
        matched_keywords=(),
    )


class CuratedSurfaceScopingTests(unittest.TestCase):
    def test_curated_policies_cover_every_surface_and_writes_are_visible(self) -> None:
        for entry in DOMAIN_LIBRARY:
            expected_kinds = {surface.kind for surface in entry.surfaces}
            domain_entities = {entity.name for entity in DOMAIN_ENTITIES[entry.domain]}
            self.assertEqual(set(CURATED_SURFACE_ENTITIES[entry.domain]), expected_kinds)
            self.assertEqual(set(CURATED_SURFACE_WRITABLE_ENTITIES[entry.domain]), expected_kinds)
            for kind in expected_kinds:
                self.assertTrue(set(CURATED_SURFACE_ENTITIES[entry.domain][kind]) <= domain_entities)
                self.assertTrue(
                    set(CURATED_SURFACE_WRITABLE_ENTITIES[entry.domain][kind])
                    <= set(CURATED_SURFACE_ENTITIES[entry.domain][kind])
                )

    def test_food_delivery_courier_has_order_scope_and_read_only_dependency(self) -> None:
        plan = plan_ecosystem_from_prompt(
            "Create a food delivery app where customers order from restaurants and couriers deliver",
            "complete",
        )
        courier_app = _app(plan, "driver_portal")
        courier = courier_app.ir

        self.assertEqual({entity.name for entity in courier.entities}, {"Order", "Restaurant"})
        self.assertEqual({screen.id for screen in courier.screens}, {"order_list", "order_editor"})
        self.assertEqual(len(courier.roles), 1)
        self.assertEqual(courier.roles[0].id, "driver")
        self.assertEqual(
            set(courier.roles[0].permissions),
            {"order:read", "order:write", "restaurant:read"},
        )

        restaurant_mutations = [
            api
            for api in courier.apis
            if api.path.startswith("/restaurants") and api.method is not HttpMethod.GET
        ]
        self.assertEqual(restaurant_mutations, [])
        order_mutations = [
            api
            for api in courier.apis
            if api.path.startswith("/orders") and api.method is not HttpMethod.GET
        ]
        self.assertTrue(order_mutations)
        self.assertTrue(all(api.required_roles == ("driver",) for api in order_mutations))
        self.assertEqual(courier_app.to_dict()["writable_entities"], ["Order"])
        self.assertEqual(courier_app.to_dict()["roles"], [courier.roles[0].to_dict()])

    def test_food_delivery_admin_excludes_menu_items(self) -> None:
        plan = plan_ecosystem_from_prompt("food delivery with restaurant operations", "complete")
        admin = _app(plan, "admin_dashboard").ir
        self.assertEqual({entity.name for entity in admin.entities}, {"Order", "Restaurant"})
        self.assertNotIn("menu_item_list", {screen.id for screen in admin.screens})

    def test_each_surface_declares_only_its_actor_and_role_gates_mutations(self) -> None:
        for entry in DOMAIN_LIBRARY:
            plan = plan_ecosystem_from_prompt(entry.example_prompt, "complete")
            for app in plan.apps:
                expected_role = app.surface.actor.lower().replace("-", "_").replace(" ", "_")
                self.assertEqual([role.id for role in app.ir.roles], [expected_role])
                self.assertFalse(has_errors(validate_ir(app.ir)))
                mutations = [api for api in app.ir.apis if api.method is not HttpMethod.GET]
                has_write_permission = any(
                    permission.endswith(":write")
                    for permission in app.ir.roles[0].permissions
                )
                self.assertEqual(bool(mutations), has_write_permission)
                self.assertTrue(
                    all(api.auth and api.required_roles == (expected_role,) for api in mutations),
                    f"{entry.domain}/{app.ir.name} has an unscoped mutation",
                )
                self.assertTrue(all(not api.auth for api in app.ir.apis if api.method is HttpMethod.GET))

    def test_customer_catalog_is_read_only_and_public_site_has_no_mutations(self) -> None:
        food = plan_ecosystem_from_prompt("food delivery with restaurant menus", "complete")
        customer = _app(food, "customer_web").ir
        self.assertEqual(
            {
                api.request_schema or api.response_schema
                for api in customer.apis
                if api.method is not HttpMethod.GET
            },
            {"Order"},
        )
        self.assertIn("restaurant_list", {screen.id for screen in customer.screens})
        self.assertNotIn("restaurant_editor", {screen.id for screen in customer.screens})
        self.assertNotIn("menu_item_editor", {screen.id for screen in customer.screens})

        blog = plan_ecosystem_from_prompt("blog CMS for authors and readers", "complete")
        public = _app(blog, "public_web").ir
        self.assertTrue(all(api.method is HttpMethod.GET for api in public.apis))
        self.assertEqual(public.roles[0].permissions, ("article:read",))


class RefinedSurfaceScopingTests(unittest.TestCase):
    def setUp(self) -> None:
        identifier = Field("id", FieldType.UUID)
        self.entities = (
            Entity("Hive", (identifier, Field("name", FieldType.STRING))),
            Entity(
                "Inspection",
                (identifier, Field("notes", FieldType.TEXT)),
                relations=(Relation("hive", "Hive", RelationKind.MANY_TO_ONE),),
            ),
            Entity(
                "Treatment",
                (identifier, Field("name", FieldType.STRING)),
                relations=(Relation("hive", "Hive", RelationKind.MANY_TO_ONE),),
            ),
        )

    def test_name_matching_selects_primary_entities_and_relation_closure(self) -> None:
        surface = AppSurface(
            "beekeeper_portal",
            "Hive Inspection Console",
            "operator",
            "Beekeeper",
            "Record inspections for managed hives.",
        )
        app = plan_ecosystem(_custom_proposal(surface), entities=self.entities).apps[0]

        self.assertEqual({entity.name for entity in app.ir.entities}, {"Hive", "Inspection"})
        self.assertEqual(
            {screen.id for screen in app.ir.screens},
            {"hive_list", "hive_editor", "inspection_list", "inspection_editor"},
        )
        self.assertFalse(has_errors(validate_ir(app.ir)))
        declared = frozenset(entity.name for entity in app.ir.entities)
        fk_by_entity = {
            entity.name: tuple(relation.name for relation in entity.relations)
            for entity in app.ir.entities
        }
        self.assertTrue(all(wire_endpoint(api, declared, fk_by_entity) for api in app.ir.apis))

    def test_ambiguous_surface_safely_keeps_complete_model(self) -> None:
        surface = AppSurface(
            "admin_dashboard",
            "Operations Dashboard",
            "operator",
            "Admin",
            "Oversee daily operations and reporting.",
        )
        first = plan_ecosystem(_custom_proposal(surface), entities=self.entities)
        second = plan_ecosystem(_custom_proposal(surface), entities=self.entities)

        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(
            {entity.name for entity in first.apps[0].ir.entities},
            {"Hive", "Inspection", "Treatment"},
        )


if __name__ == "__main__":
    unittest.main()
