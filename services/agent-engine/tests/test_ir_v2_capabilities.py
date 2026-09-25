"""R-564: the IR can describe what a product *does*, and older projects still open.

The IR modelled entities, fields, relations, CRUD, screens and roles — a database with pages over
it. `route_wiring.wire_endpoint` matches six CRUD shapes and returns `None` for anything else, so
`POST /orders/{id}/assign-driver` was dropped on the floor. An order lifecycle, a payout ledger, a
nightly settlement and "a driver sees only their own orders" had nowhere to be written down, which
is why no model produced them. That is the ceiling, and it was in the data model.

This file guards the frame rather than any capability: the record, the registry, and — the part
that would hurt most if it broke — the migration. Every project built since R-563 has an `ir.json`
on disk. `from_dict` used to reject any version that was not exactly 1, so bumping the number
without migrating would have made every existing project unopenable and uneditable, which is a
worse outcome than the ceiling this task exists to lift.

The registry keeps **declared** apart from **implemented** on purpose. `GenerationTarget` declared
FLUTTER and NATIVE_* with nothing behind them, and a request for either produced a website in
silence until R-559. A capability that is accepted and then ignored is that failure again, so
nothing may be declared in an IR until a kind is registered, and intake says nothing about
capabilities while none is implemented.
"""

import dataclasses
import json
import tempfile
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.application_ir.capability import (
    CAPABILITY_KINDS,
    Capability,
    CapabilityKind,
    CapabilityRegistry,
)
from omnistackai_agent_engine.application_ir.errors import (
    InvalidIRError,
    UnsupportedIRVersionError,
)
from omnistackai_agent_engine.application_ir.ir import (
    IR_SCHEMA_VERSION,
    READABLE_IR_SCHEMA_VERSIONS,
    ApplicationIR,
)


def _as_v1(ir: ApplicationIR) -> dict:
    """An IR document as it was written before this task existed."""
    document = ir.to_dict()
    document["schema_version"] = 1
    document.pop("capabilities", None)
    return document


class AProjectSavedBeforeThisStillOpens(TestCase):
    """The migration. Everything else here is worth less than this passing."""

    def test_a_version_1_document_loads(self) -> None:
        ir = example_ir("minimal-blog")
        loaded = ApplicationIR.from_dict(_as_v1(ir))
        self.assertEqual(loaded.name, ir.name)
        self.assertEqual([e.name for e in loaded.entities], [e.name for e in ir.entities])

    def test_it_is_upgraded_rather_than_left_behind(self) -> None:
        loaded = ApplicationIR.from_dict(_as_v1(example_ir("minimal-blog")))
        self.assertEqual(loaded.schema_version, IR_SCHEMA_VERSION)
        self.assertEqual(loaded.capabilities, (), "a version 1 project has none by definition")

    def test_a_workspace_written_before_this_is_still_editable(self) -> None:
        """The real shape of the risk: an `ir.json` on disk from an earlier build."""
        from omnistackai_agent_engine.studio.workspace import StudioWorkspaceStore

        with tempfile.TemporaryDirectory() as tmp:
            store = StudioWorkspaceStore(tmp)
            store.ensure_workspace("old-project")
            # Written by hand exactly as the older build would have written it.
            path = store.workspace_path("old-project") / "ir.json"
            path.write_text(json.dumps(_as_v1(example_ir("minimal-blog"))), encoding="utf-8")

            loaded = store.load_ir("old-project")
            self.assertIsNotNone(loaded, "an existing project must not become unopenable")
            self.assertEqual(loaded.schema_version, IR_SCHEMA_VERSION)

    def test_a_future_version_is_refused_with_a_reason(self) -> None:
        # Guessing at a document a later engine wrote is worse than saying we cannot read it.
        document = example_ir("minimal-blog").to_dict()
        document["schema_version"] = IR_SCHEMA_VERSION + 1
        with self.assertRaises(UnsupportedIRVersionError) as caught:
            ApplicationIR.from_dict(document)
        self.assertIn(str(IR_SCHEMA_VERSION), str(caught.exception))

    def test_both_readable_versions_are_declared(self) -> None:
        self.assertEqual(READABLE_IR_SCHEMA_VERSIONS, (1, 2))


class CapabilitiesSurviveASaveAndLoad(TestCase):
    def setUp(self) -> None:
        # A kind registered for this test only, then removed: the real registry stays empty until
        # a task ships code generation for a kind.
        self._kind = CapabilityKind(name="test_only", summary="a kind that exists for this test")
        CAPABILITY_KINDS.register(self._kind)
        self.addCleanup(CAPABILITY_KINDS._kinds.pop, "test_only", None)

    def test_a_capability_round_trips(self) -> None:
        ir = dataclasses.replace(
            example_ir("minimal-blog"),
            capabilities=(Capability("test_only", "order_lifecycle", {"states": ["new", "done"]}),),
        )
        back = ApplicationIR.from_dict(ir.to_dict())
        self.assertEqual(len(back.capabilities), 1)
        self.assertEqual(back.capabilities[0].name, "order_lifecycle")
        self.assertEqual(back.capabilities[0].config["states"], ["new", "done"])

    def test_two_capabilities_cannot_share_a_name(self) -> None:
        with self.assertRaises(InvalidIRError):
            dataclasses.replace(
                example_ir("minimal-blog"),
                capabilities=(
                    Capability("test_only", "same"),
                    Capability("test_only", "same"),
                ),
            )


class AKindMustExistBeforeAnIrMayUseIt(TestCase):
    def test_an_unregistered_kind_is_refused(self) -> None:
        # Accepting it and ignoring it later is the failure R-559 removed for stacks.
        with self.assertRaises(InvalidIRError) as caught:
            Capability("ledger", "payouts")
        self.assertIn("registered", str(caught.exception))

    def test_only_kinds_with_code_behind_them_are_implemented(self) -> None:
        """R-564 shipped the frame and no kind; R-566 registered the first one that generates code.

        The assertion changed from "nothing is registered" to "everything registered is real",
        which is the property that actually matters — the empty registry was only how R-564 could
        guarantee it before anything existed.
        """
        for kind in CAPABILITY_KINDS.implemented():
            with self.subTest(kind=kind):
                self.assertIsNotNone(CAPABILITY_KINDS.get(kind))
        self.assertIn("workflow", CAPABILITY_KINDS.implemented())

    def test_declared_and_implemented_are_kept_apart(self) -> None:
        registry = CapabilityRegistry()
        registry.register(CapabilityKind(name="planned", summary="declared, not built"))
        registry.register(CapabilityKind(name="real", summary="built", implemented=True))
        self.assertEqual(registry.known(), ("planned", "real"))
        self.assertEqual(registry.implemented(), ("real",))

    def test_a_kind_cannot_be_registered_twice(self) -> None:
        registry = CapabilityRegistry()
        registry.register(CapabilityKind(name="once", summary="x"))
        with self.assertRaises(InvalidIRError):
            registry.register(CapabilityKind(name="once", summary="x"))

    def test_a_kinds_validator_owns_its_config(self) -> None:
        def reject_empty(name: str, config: dict) -> None:
            if not config:
                raise InvalidIRError(f"{name} needs a config")

        registry = CapabilityRegistry()
        registry.register(CapabilityKind(name="strict", summary="x", validator=reject_empty))
        CAPABILITY_KINDS.register(CapabilityKind(name="strict", summary="x", validator=reject_empty))
        self.addCleanup(CAPABILITY_KINDS._kinds.pop, "strict", None)
        with self.assertRaises(InvalidIRError):
            Capability("strict", "thing", {})
        self.assertTrue(Capability("strict", "thing", {"ok": True}))


class IntakeOffersExactlyWhatCanBeBuilt(TestCase):
    def test_the_capabilities_field_returned_by_itself(self) -> None:
        """R-564 hid the key while nothing could build a capability, and said it would come back
        on its own once a kind was registered. R-566 registered one, and it did — no string
        anywhere had to be remembered."""
        from omnistackai_agent_engine.intake.nl_to_ir import _system_instruction

        self.assertIn('"capabilities"', _system_instruction("minimal-blog"))

    def test_the_model_is_told_how_to_write_the_kind_that_exists(self) -> None:
        # An empty list with no schema beside it is an invitation to invent one.
        from omnistackai_agent_engine.intake.nl_to_ir import _system_instruction

        instruction = _system_instruction("minimal-blog")
        self.assertIn("workflow", instruction)
        self.assertIn("transitions", instruction)

    def test_the_template_still_states_the_current_version(self) -> None:
        from omnistackai_agent_engine.intake.nl_to_ir import _system_instruction

        self.assertIn(f'"schema_version": {IR_SCHEMA_VERSION}', _system_instruction("minimal-blog"))
