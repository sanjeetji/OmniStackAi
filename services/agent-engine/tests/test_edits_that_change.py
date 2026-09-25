"""R-584: an edit can change a project, not only add to it.

`apply_app_delta` merged net-new entities, endpoints and screens by tuple concatenation, and the
parser raised on anything that already existed. "rename Post to Article", "remove the published
field" and "add a notes field to each check-in" had no way through, and both ways of failing were
bad: restating the entity gave `AppDeltaError: proposed entity 'Post' already exists`, while
proposing nothing parsed cleanly and reported that no files needed changing — an edit that silently
did nothing. The platform's own smoke test uses "Add a notes field to each check-in" as its edit
prompt, so this was a request the product asked itself to handle and could not.

The tests that matter most here are about **everything pointing at the thing being changed**.
Renaming an entity and leaving its endpoints behind produces an IR that either fails validation or,
worse, validates while its endpoints point at something gone — a rename that quietly became a
deletion. The same for removals: an entity's endpoints, screens, fixtures and the relations others
declared towards it all have to go with it, deliberately rather than by accident.
"""

import json
from unittest import TestCase

from omnistackai_agent_engine.application_ir import Field, FieldType, example_ir, validate_ir
from omnistackai_agent_engine.application_ir.validate import has_errors
from omnistackai_agent_engine.intake import ir_changes
from omnistackai_agent_engine.intake.app_delta import (
    AppDeltaError,
    AppDeltaProposal,
    IrChange,
    apply_app_delta,
    build_app_delta_messages,
    parse_app_delta_proposal,
)


def _base():
    return example_ir("minimal-blog")


def _apply(*changes: IrChange):
    return apply_app_delta(_base(), AppDeltaProposal(changes=changes))


def _fields(ir, entity: str) -> list[str]:
    return [f.name for e in ir.entities if e.name == entity for f in e.fields]


class TheThreeRequestsThatCouldNotBeMade(TestCase):
    def test_a_field_can_be_added_to_an_existing_entity(self) -> None:
        # The platform's own smoke test asks for exactly this.
        self.assertIn("notes", _fields(_apply(IrChange("add_field", entity="Post", name="notes", field_type="text")), "Post"))

    def test_an_entity_can_be_renamed(self) -> None:
        out = _apply(IrChange("rename_entity", name="Post", new_name="Article"))
        self.assertEqual([e.name for e in out.entities], ["Article", "Comment"])

    def test_a_field_can_be_removed(self) -> None:
        self.assertNotIn("published", _fields(_apply(IrChange("remove_field", entity="Post", name="published")), "Post"))


class EverythingPointingAtItMovesToo(TestCase):
    """A rename that leaves references behind is a deletion nobody asked for."""

    def setUp(self) -> None:
        self.renamed = _apply(IrChange("rename_entity", name="Post", new_name="Article"))

    def test_the_result_is_a_valid_ir(self) -> None:
        self.assertFalse(has_errors(validate_ir(self.renamed)))

    def test_relations_follow_the_rename(self) -> None:
        targets = [r.target_entity for e in self.renamed.entities for r in e.relations]
        self.assertEqual(targets, ["Article"])

    def test_endpoint_paths_and_schemas_follow(self) -> None:
        paths = [a.path for a in self.renamed.apis]
        self.assertIn("/articles", paths)
        self.assertIn("/articles/{articleId}/comments", paths)
        self.assertNotIn("Post", {a.response_schema for a in self.renamed.apis})

    def test_screens_follow(self) -> None:
        ids = {s.id for s in self.renamed.screens}
        self.assertIn("article_list", ids)
        self.assertNotIn("post_list", ids)

    def test_fixtures_follow(self) -> None:
        self.assertIn("Article", {f.entity for f in self.renamed.fixtures})
        self.assertNotIn("Post", {f.entity for f in self.renamed.fixtures})


class RemovingCascadesDeliberately(TestCase):
    def setUp(self) -> None:
        self.without = _apply(IrChange("remove_entity", name="Comment"))

    def test_the_result_is_a_valid_ir(self) -> None:
        self.assertFalse(has_errors(validate_ir(self.without)))

    def test_its_endpoints_go_with_it(self) -> None:
        self.assertNotIn("/posts/{postId}/comments", [a.path for a in self.without.apis])

    def test_its_fixtures_go_with_it(self) -> None:
        self.assertNotIn("Comment", {f.entity for f in self.without.fixtures})

    def test_relations_towards_it_go_with_it(self) -> None:
        self.assertEqual([r.target_entity for e in self.without.entities for r in e.relations], [])

    def test_removing_a_field_drops_its_fixture_values(self) -> None:
        out = _apply(IrChange("remove_field", entity="Post", name="published"))
        for fixture in out.fixtures:
            if fixture.entity == "Post":
                for row in fixture.rows:
                    self.assertNotIn("published", row)


class SomeChangesAreRefused(TestCase):
    def test_the_id_field_cannot_be_removed(self) -> None:
        with self.assertRaises(AppDeltaError):
            _apply(IrChange("remove_field", entity="Post", name="id"))

    def test_the_last_entity_cannot_be_removed(self) -> None:
        out = _apply(IrChange("remove_entity", name="Comment"))
        with self.assertRaises(AppDeltaError):
            apply_app_delta(out, AppDeltaProposal(changes=(IrChange("remove_entity", name="Post"),)))

    def test_an_unknown_operation_is_refused(self) -> None:
        with self.assertRaises(AppDeltaError):
            IrChange("drop_database", name="Post")

    def test_renaming_onto_an_existing_name_is_refused(self) -> None:
        with self.assertRaises(AppDeltaError):
            _apply(IrChange("rename_entity", name="Post", new_name="Comment"))


class ADestructiveEditSaysSo(TestCase):
    """It is the user's project, so the answer to "remove the published field" is to remove it —
    and to be clear about what that means rather than refusing or staying quiet."""

    def test_removing_data_is_described(self) -> None:
        self.assertIn("removes stored data", ir_changes.describes_data_loss(["remove_field"]))

    def test_an_ordinary_edit_says_nothing_extra(self) -> None:
        self.assertEqual(ir_changes.describes_data_loss(["add_field", "rename_entity"]), "")

    def test_a_change_knows_whether_it_destroys(self) -> None:
        self.assertTrue(IrChange("remove_entity", name="Post").is_destructive)
        self.assertFalse(IrChange("rename_entity", name="Post", new_name="Article").is_destructive)


class AddingStillWorksUnchanged(TestCase):
    def test_a_proposal_with_no_changes_behaves_as_before(self) -> None:
        raw = json.dumps(
            {
                "entities": [
                    {
                        "name": "Tag",
                        "fields": [{"name": "id", "type": "uuid", "required": True}],
                        "relations": [],
                    }
                ],
                "apis": [],
                "screens": [],
                "rationale": "add tags",
            }
        )
        out = apply_app_delta(_base(), parse_app_delta_proposal(raw, base_ir=_base()))
        self.assertIn("Tag", [e.name for e in out.entities])

    def test_changes_and_additions_can_arrive_together(self) -> None:
        # Changes land first: a new endpoint may name the renamed entity.
        out = apply_app_delta(
            _base(),
            AppDeltaProposal(
                changes=(IrChange("rename_entity", name="Post", new_name="Article"),),
                entities=(),
            ),
        )
        self.assertEqual([e.name for e in out.entities], ["Article", "Comment"])


class TheModelIsToldItCanChangeThings(TestCase):
    def test_the_prompt_describes_the_operations(self) -> None:
        system, _ = build_app_delta_messages(_base(), "add a notes field to each post")
        for op in ("add_field", "remove_field", "rename_entity", "remove_entity"):
            with self.subTest(op=op):
                self.assertIn(op, system.content)

    def test_the_prompt_steers_away_from_restating_an_entity(self) -> None:
        # Restating was the failure: it raised, and the user saw an error for a reasonable request.
        system, _ = build_app_delta_messages(_base(), "add a notes field to each post")
        self.assertIn("do NOT put X in `entities`", system.content)


class ChangesRoundTripThroughTheParser(TestCase):
    def test_a_change_survives_json(self) -> None:
        raw = json.dumps(
            {
                "entities": [],
                "apis": [],
                "screens": [],
                "rationale": "rename it",
                "changes": [{"op": "rename_entity", "name": "Post", "new_name": "Article"}],
            }
        )
        proposal = parse_app_delta_proposal(raw, base_ir=_base())
        self.assertEqual(proposal.changes[0].op, "rename_entity")
        self.assertEqual([e.name for e in apply_app_delta(_base(), proposal).entities], ["Article", "Comment"])

    def test_an_unknown_field_type_is_refused(self) -> None:
        raw = json.dumps(
            {
                "entities": [], "apis": [], "screens": [], "rationale": "x",
                "changes": [{"op": "add_field", "entity": "Post", "name": "n", "field_type": "money"}],
            }
        )
        with self.assertRaises(AppDeltaError):
            parse_app_delta_proposal(raw, base_ir=_base())


class TheSameDeltaTwiceGivesTheSameIr(TestCase):
    def test_applying_is_deterministic(self) -> None:
        change = IrChange("add_field", entity="Post", name="notes", field_type="text")
        self.assertEqual(_apply(change).to_dict(), _apply(change).to_dict())

    def test_the_base_ir_is_never_mutated(self) -> None:
        base = _base()
        before = base.to_dict()
        apply_app_delta(base, AppDeltaProposal(changes=(IrChange("remove_entity", name="Comment"),)))
        self.assertEqual(base.to_dict(), before)
