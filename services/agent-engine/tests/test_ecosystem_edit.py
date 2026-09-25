"""R-563: a multi-app project can be changed after it is built.

An edit to a five-app platform used to reach the backend and **not one of the apps**. The workspace
does hold the union IR, so nothing errored — `_workspace_edit` called `plan_edit`, which assembles
both sides with `assemble_project`, and the union deliberately carries no screens ("screens belong
to the app that renders them"). Measured: adding an entity produced five changes, every one of them
under `services/api` or `contracts/`. The database and the API gained the feature, all five apps
stayed exactly as they were, and the edit reported success.

The rule this file holds, decided before the code was written:

    A new entity reaches every surface that already holds something it points at. If it points at
    nothing any surface holds, it stands alone and reaches every surface.

The fallback is not invented for this task — it is what `ecosystem.py` already does when scoping is
ambiguous ("Ambiguous intent is not permission to fabricate a partition"). It is also the
recoverable direction: an entity on one app too many is a visible mistake a user can report, while
one hidden everywhere is indistinguishable from an edit that did nothing.

Scoping still governs everything it already knew, which is why the courier test below matters more
than the rest: if an edit could smuggle a menu editor into the courier's app, the ecosystem's whole
premise would be gone.
"""

import dataclasses
from unittest import TestCase

from omnistackai_agent_engine.application_ir import (
    Entity,
    Field,
    FieldType,
    Relation,
    RelationKind,
)
from omnistackai_agent_engine.codegen.ecosystem_assembler import assemble_ecosystem, union_ir
from omnistackai_agent_engine.edit.diff import plan_ecosystem_edit, plan_edit
from omnistackai_agent_engine.intake.ecosystem import plan_ecosystem_from_prompt, reach_of_new_entities
from omnistackai_agent_engine.studio.live_serve import _apps_touched

PROMPT = (
    "Create a platform for the food delivery with marketing website, admin-panel, "
    "customer + driver apps"
)


def _entity(name: str, *, points_at: str | None = None) -> Entity:
    relations = (
        (Relation(name=points_at.lower(), kind=RelationKind.MANY_TO_ONE, target_entity=points_at),)
        if points_at
        else ()
    )
    return Entity(
        name=name,
        fields=(Field(name="id", type=FieldType.UUID, required=True),),
        relations=relations,
    )


def _before():
    return union_ir(plan_ecosystem_from_prompt(PROMPT, "complete"))


def _after(*entities: Entity):
    old = _before()
    return dataclasses.replace(old, entities=old.entities + entities)


def _apps_in(diff) -> set[str]:
    return set(_apps_touched(diff))


class TheOldPathChangedNoApps(TestCase):
    """The defect, kept as a test so it cannot come back quietly."""

    def test_plan_edit_touches_only_the_backend(self) -> None:
        diff = plan_edit(_before(), _after(_entity("LoyaltyPoint", points_at="Order")))
        self.assertEqual(
            _apps_in(diff),
            set(),
            "this is the bug: the single-app diff reaches no app in a multi-app project",
        )


class AnEditReachesTheApps(TestCase):
    def test_a_related_entity_reaches_the_apps_that_hold_what_it_points_at(self) -> None:
        diff = plan_ecosystem_edit(
            _before(), _after(_entity("LoyaltyPoint", points_at="Order")), prompt=PROMPT
        )
        # Every surface carries Order, so every surface carries this.
        self.assertEqual(_apps_in(diff), {"web", "customer-app", "merchant", "driver", "admin"})

    def test_the_backend_is_still_updated(self) -> None:
        diff = plan_ecosystem_edit(
            _before(), _after(_entity("LoyaltyPoint", points_at="Order")), prompt=PROMPT
        )
        self.assertTrue(
            any(p.startswith("services/") for p in list(diff.added()) + list(diff.modified()))
        )

    def test_nothing_is_deleted(self) -> None:
        # Diffing an ecosystem against a single-app layout is the failure mode this replaces.
        diff = plan_ecosystem_edit(
            _before(), _after(_entity("LoyaltyPoint", points_at="Order")), prompt=PROMPT
        )
        self.assertEqual(diff.deleted(), ())

    def test_an_unchanged_project_produces_an_empty_diff(self) -> None:
        before = _before()
        self.assertTrue(plan_ecosystem_edit(before, before, prompt=PROMPT).is_empty())


class ScopingSurvivesTheEdit(TestCase):
    """If an edit could smuggle a menu editor into the courier's app, the premise would be gone."""

    def _entities_by_surface(self, new_ir, added):
        plan = plan_ecosystem_from_prompt(
            PROMPT, "complete", entities=new_ir.entities, added=frozenset(added)
        )
        return {app.surface.kind: {e.name for e in app.ir.entities} for app in plan.apps}

    def test_the_courier_still_has_no_menu(self) -> None:
        by_surface = self._entities_by_surface(
            _after(_entity("LoyaltyPoint", points_at="Order")), {"LoyaltyPoint"}
        )
        self.assertNotIn("MenuItem", by_surface["driver_portal"])

    def test_the_courier_does_receive_the_new_entity(self) -> None:
        by_surface = self._entities_by_surface(
            _after(_entity("LoyaltyPoint", points_at="Order")), {"LoyaltyPoint"}
        )
        self.assertIn("LoyaltyPoint", by_surface["driver_portal"])

    def test_an_entity_pointing_at_a_menu_stays_off_the_courier(self) -> None:
        # The rule doing its job: MenuItem is not on the courier's app, so neither is this.
        by_surface = self._entities_by_surface(
            _after(_entity("MenuPhoto", points_at="MenuItem")), {"MenuPhoto"}
        )
        self.assertIn("MenuPhoto", by_surface["merchant_portal"])
        self.assertNotIn("MenuPhoto", by_surface["driver_portal"])


class TheRuleItself(TestCase):
    def test_it_follows_what_an_entity_points_at(self) -> None:
        entities = (_entity("Order"), _entity("LoyaltyPoint", points_at="Order"))
        holding_order = reach_of_new_entities(
            new_names=frozenset({"LoyaltyPoint"}),
            entities=entities,
            surface_selected=frozenset({"Order"}),
        )
        self.assertEqual(holding_order, frozenset({"LoyaltyPoint"}))

    def test_a_surface_without_the_target_does_not_get_it(self) -> None:
        entities = (_entity("Order"), _entity("Restaurant"), _entity("LoyaltyPoint", points_at="Order"))
        self.assertEqual(
            reach_of_new_entities(
                new_names=frozenset({"LoyaltyPoint"}),
                entities=entities,
                surface_selected=frozenset({"Restaurant"}),
            ),
            frozenset(),
        )

    def test_a_standalone_entity_reaches_everything(self) -> None:
        # Hiding it everywhere is indistinguishable from an edit that did nothing.
        entities = (_entity("Order"), _entity("Announcement"))
        for selected in (frozenset({"Order"}), frozenset({"Restaurant"}), frozenset()):
            with self.subTest(selected=sorted(selected)):
                self.assertEqual(
                    reach_of_new_entities(
                        new_names=frozenset({"Announcement"}),
                        entities=entities,
                        surface_selected=selected,
                    ),
                    frozenset({"Announcement"}),
                )


class TheUserIsToldWhichAppsChanged(TestCase):
    def test_the_apps_are_named(self) -> None:
        diff = plan_ecosystem_edit(
            _before(), _after(_entity("LoyaltyPoint", points_at="Order")), prompt=PROMPT
        )
        named = _apps_touched(diff)
        self.assertEqual(named, sorted(named), "a stable order, so two runs read the same")
        self.assertIn("driver", named)

    def test_a_backend_only_change_names_no_apps(self) -> None:
        diff = plan_ecosystem_edit(_before(), _before(), prompt=PROMPT)
        self.assertEqual(_apps_touched(diff), [])


class TheRepositoryStaysWhole(TestCase):
    def test_every_app_that_existed_still_exists_after_an_edit(self) -> None:
        before = _before()
        after = _after(_entity("LoyaltyPoint", points_at="Order"))
        built = {f.path for f in assemble_ecosystem(plan_ecosystem_from_prompt(PROMPT, "complete")).files()}
        diff = plan_ecosystem_edit(before, after, prompt=PROMPT)
        surviving = (built - set(diff.deleted())) | set(diff.added())
        for app in ("web", "customer-app", "merchant", "driver", "admin"):
            with self.subTest(app=app):
                self.assertTrue(
                    any(p.startswith(f"apps/{app}/") for p in surviving),
                    f"apps/{app} disappeared during an edit",
                )
