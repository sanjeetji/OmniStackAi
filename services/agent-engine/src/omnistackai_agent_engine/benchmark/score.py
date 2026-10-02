"""PC-122: how one benchmark build is scored. Pure functions - no model, no network, no files.

A case gets a 0-100 score from what was measured, each part 0..1:

* **build** - the platform produced the project and its code type-checks (clean or repaired 1.0;
  checked but still failing 0.25; not checked 0.5 - unknown is not the same as good);
* **runs** - the preview started: the API answers and every web app serves its home page;
* **api** - every list endpoint answers 2xx against the real database;
* **pages** - the share of page views (every page at phone and desktop width) with no problem:
  overflow, console errors, failed requests, broken images, low contrast;
* **complete** - what the prompt needs and the build has: the case's expected things, building
  blocks and number of apps;
* **designed** - the share of pages the model designed rather than left as the template (only
  when the run designs pages).

A part that was not measured (no preview, no design step, no browser) is left out of the average and
the report says so, rather than counted as zero or as full marks.
"""

from __future__ import annotations

from typing import Any, Iterable

from .cases import Case

WEIGHTS = {"build": 0.20, "runs": 0.20, "api": 0.15, "pages": 0.15, "complete": 0.20, "designed": 0.10}
#: A case whose score falls by more than this against the baseline is a regression.
REGRESSION_POINTS = 10.0


def build_part(built: bool, verification: dict | None) -> float:
    """1.0 when every surface type-checked clean (or was repaired); less for what was not checked.

    Found in the first run: a Python API that only *parses* and web apps that were skipped (no
    type-check cache) scored as fully checked - and two of those apps referenced components they
    never imported.
    """
    if not built:
        return 0.0
    statuses = _statuses(verification or {})
    if any(s == "failing" for s in statuses):
        return 0.25
    checked = [s for s in statuses if s in ("clean", "repaired")]
    unchecked = [s for s in statuses if s not in ("clean", "repaired")]
    if not checked:
        return 0.5
    return 1.0 if not unchecked else 0.75


def _statuses(verification: dict) -> list[str]:
    """The leaf statuses: each surface's own, or the record's when it has none."""
    surfaces = verification.get("surfaces")
    if isinstance(surfaces, dict) and surfaces:
        return [str(v.get("status")) for v in surfaces.values() if isinstance(v, dict)]
    return [verification["status"]] if isinstance(verification.get("status"), str) else []


def runs_part(api_up: bool | None, web_ready: dict[str, bool] | None) -> float | None:
    if api_up is None and not web_ready:
        return None
    checks = ([bool(api_up)] if api_up is not None else []) + [bool(v) for v in (web_ready or {}).values()]
    return sum(checks) / len(checks) if checks else None


def ratio(ok: int, total: int) -> float | None:
    return ok / total if total else None


def complete_part(case: Case, entity_names: Iterable[str], capability_kinds: Iterable[str], apps: int) -> tuple[float, list[str]]:
    """The share of the case's floor the build meets, and what it lacks (in words)."""
    from ..intake.ir_repair import resolve_entity_reference

    names = list(entity_names)
    kinds = set(capability_kinds)
    missing: list[str] = []
    checks = 0
    for wanted in case.entities:
        checks += 1
        if not (resolve_entity_reference(wanted, names) or any(wanted.lower() in n.lower() for n in names)):
            missing.append(f"no {wanted}")
    for kind in case.capabilities:
        checks += 1
        if kind not in kinds:
            missing.append(f"no {kind} building block")
    checks += 1
    low, high = case.app_range
    if not low <= apps <= high:
        expected = str(low) if low == high else f"{low} to {high}"
        missing.append(f"{apps} app{'s' if apps != 1 else ''}, expected {expected}")
    return (checks - len(missing)) / checks, missing


def total(parts: dict[str, float | None]) -> float:
    measured = {k: v for k, v in parts.items() if v is not None and k in WEIGHTS}
    weight = sum(WEIGHTS[k] for k in measured)
    return round(100 * sum(WEIGHTS[k] * v for k, v in measured.items()) / weight, 1) if weight else 0.0


def compare(current: list[dict[str, Any]], baseline: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Each case against the same case in the baseline run; a fall beyond REGRESSION_POINTS regresses."""
    if not baseline:
        return {"baseline": False, "regressions": [], "changes": {}}
    before = {c["id"]: c for c in baseline}
    changes: dict[str, float] = {}
    regressions: list[str] = []
    for case in current:
        old = before.get(case["id"])
        if old is None:
            continue
        delta = round(case["score"] - old["score"], 1)
        changes[case["id"]] = delta
        if delta < -REGRESSION_POINTS:
            regressions.append(f"{case['id']}: {old['score']} -> {case['score']}")
    shared = [c for c in current if c["id"] in before]
    mean_now = _mean(c["score"] for c in shared)
    mean_before = _mean(before[c["id"]]["score"] for c in shared)
    return {"baseline": True, "regressions": regressions, "changes": changes,
            "mean_before": mean_before, "mean_now": mean_now}


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return round(sum(values) / len(values), 1) if values else 0.0
