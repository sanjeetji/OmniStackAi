"""Read-only, metadata-only snapshot for the dependency-free Stage 0 console.

Composes accepted platform contracts into a visible builder proof. The project plan and edit patch are
built from bundled Application IR examples; nothing is installed, run, verified, deployed, written to
a customer repository, or connected to a database. Provider configuration remains metadata-only.
"""

from __future__ import annotations

from dataclasses import replace

from .application_ir import example_ir
from .codegen import assemble_project
from .edit import diff_report, unified_patch
from .model_gateway.accounting import PriceBook, UsageLedger
from .model_gateway.overview import platform_overview
from .projectplan import build_project_plan

_PLAN_EXAMPLE = "rideshare-favourites"
_EDIT_EXAMPLE = "minimal-blog"
_EDIT_REQUEST = "Add an offline-first promise to the generated project description."
_EDIT_DESCRIPTION_SUFFIX = " It is designed to stay useful during an internet outage."


def _builder_showcase() -> dict[str, object]:
    plan_ir = example_ir(_PLAN_EXAMPLE)
    base_ir = example_ir(_EDIT_EXAMPLE)
    edited_ir = replace(base_ir, description=base_ir.description + _EDIT_DESCRIPTION_SUFFIX)
    before = assemble_project(base_ir)
    after = assemble_project(edited_ir)
    changes = diff_report(before, after)

    return {
        "note": (
            "Deterministic read-only proof assembled from bundled IR examples. Commands shown are "
            "plans only; no generated app was installed, run, verified, or deployed."
        ),
        "planExample": _PLAN_EXAMPLE,
        "projectPlan": build_project_plan(plan_ir).to_dict(),
        "editPreview": {
            "baseExample": _EDIT_EXAMPLE,
            "requestedChange": _EDIT_REQUEST,
            "changes": [
                {"kind": change.kind.value, "path": change.path, "oldPath": change.old_path}
                for change in changes
            ],
            "unifiedPatch": unified_patch(before, after),
        },
    }


def platform_console_snapshot(
    ledger: UsageLedger | None = None, price_book: PriceBook | None = None
) -> dict[str, object]:
    """Return the complete JSON-serializable console snapshot without secret values."""

    snapshot = platform_overview(ledger=ledger, price_book=price_book)
    snapshot["snapshotVersion"] = 2
    snapshot["builderShowcase"] = _builder_showcase()
    snapshot["note"] = (
        "Static metadata-only snapshot: model-fabric status plus a deterministic builder proof. "
        "Contains no API keys or secret values."
    )
    return snapshot


__all__ = ["platform_console_snapshot"]
