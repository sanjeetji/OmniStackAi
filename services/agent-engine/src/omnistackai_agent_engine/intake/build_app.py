"""Prompt -> generated app repo (R-417).

Brick 2 of the "chat -> create an app" front door: chain the R-416 intake agent into
the existing assembler + git service so a single plain-English description becomes a
real, customer-owned Git repository.

    prompt --generate_ir--> ApplicationIR --assemble_project--> GeneratedProject
           --create_repository--> owned Git repo on disk

``build_app_from_ir`` is pure disk work (no model); ``build_app_from_prompt`` adds the
single model step and depends only on the vendor-neutral ``ModelProvider`` protocol, so
`task verify` exercises it against an in-memory stub (0 model calls, 0 network).
"""

from __future__ import annotations

import os
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path

from ..application_ir import ApplicationIR
from ..codegen import assemble_project
from ..git_service import create_repository
from ..model_gateway import ModelProvider
from .build_verify import verify_and_repair_build
from .ecosystem_intent import detect_ecosystem_intent
from .nl_to_ir import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_TEMPLATE_EXAMPLE,
    DEFAULT_TIMEOUT_SECONDS,
    IntakeResult,
    generate_ir,
    generate_ir_stream,
)


@dataclass(frozen=True)
class AppBuildResult:
    """Outcome of compiling a description into a materialized, owned Git repository."""

    prompt: str
    ir: ApplicationIR
    target_dir: str
    file_count: int
    commit_sha: str
    context_truncated: bool = False
    active_skills: tuple[str, ...] = ()
    truncated_skills: tuple[str, ...] = ()
    #: R-555: set when the prompt named a second kind of user and the whole ecosystem was built.
    #: `ecosystem_reason` is shown to the user, because "you got four apps" needs a because.
    ecosystem_apps: tuple[str, ...] = ()
    ecosystem_reason: str = ""
    #: R-559: set when the requested stack had no adapter and the nearest supported one was built
    #: instead. Carried to the console because "you asked for Flutter and this is React Native"
    #: has to reach the person who asked, not only the generated README.
    substitutions: tuple[dict, ...] = ()
    #: R-560: what happened when the generated web app was type-checked — clean, repaired, reverted
    #: or skipped with a reason. Always present, because "we did not check this, and here is why" is
    #: a different message from saying nothing.
    verification: dict = field(default_factory=dict)
    #: PC-004: endpoints and screens with no real data behind them, by name. Shown to the user so
    #: "is this real?" never has to be answered by clicking.
    not_connected: tuple[dict, ...] = ()
    #: PC-084: seconds spent in each stage of this build (plan, assemble, repository, verify), so
    #: speed is measured on every build rather than guessed at.
    timings: dict = field(default_factory=dict)
    #: PC-127: what was built - the scope the person confirmed, or the one proposed for the prompt.
    scope: dict = field(default_factory=dict)


def build_app_from_ir(
    ir: ApplicationIR,
    target_dir: str | os.PathLike[str],
    *,
    author_name: str,
    author_email: str,
    prompt: str = "",
    overwrite: bool = False,
    provider: ModelProvider | None = None,
    model_id: str | None = None,
    synthesize_screens: bool = False,
    ui_outcomes: list | None = None,
    context_truncated: bool = False,
    active_skills: tuple[str, ...] = (),
    truncated_skills: tuple[str, ...] = (),
    model_written_pages: bool = True,
) -> AppBuildResult:
    """Assemble ``ir`` into a monorepo and materialize it as an owned Git repo at ``target_dir``.

    ``model_written_pages`` (PC-084): with a provider, the overview page is normally model-written.
    The console's streaming path turns that off — measured live, it cost 82 s of a 165 s build and
    its admin page did not compile — while still passing the provider so verification and repair run.

    ``synthesize_screens`` / ``ui_outcomes`` (R-465) opt the web target into model-written screens and
    collect the per-file outcome records; both are no-ops without a ``provider``.
    """
    timings: dict[str, float] = {}
    # PC-099: the design direction is chosen once and saved in the plan the workspace keeps, so a
    # chat edit (which assembles from the plan alone) keeps the project's look.
    if prompt:
        from ..codegen.design_direction import with_design_direction
        from ..codegen.rich_text import with_rich_text

        ir = with_rich_text(with_design_direction(ir, prompt), prompt)
        # R-570 / R-567: whose records are whose and what is paid, from the prompt's own words -
        # here, so every planner (one app, an ecosystem, an edit) gets the same floor.
        from .nl_to_ir import _with_prompt_ownership

        ir, _ = _with_prompt_ownership(ir, prompt)
    # PC-101: every record a form must point at can be listed (and so picked).
    from ..codegen.reachable_references import with_detail_screens, with_reachable_references

    ir = with_detail_screens(with_reachable_references(ir))
    started = time.perf_counter()
    project = assemble_project(
        ir,
        provider=provider if model_written_pages else None,
        prompt=prompt,
        model_id=model_id,
        synthesize_screens=synthesize_screens,
        ui_outcomes=ui_outcomes,
    )
    timings["assemble"] = round(time.perf_counter() - started, 3)
    started = time.perf_counter()
    repo = create_repository(
        project,
        target_dir,
        author_name=author_name,
        author_email=author_email,
        commit_message=f"Initial commit: {ir.name}",
        overwrite=overwrite,
    )
    timings["repository"] = round(time.perf_counter() - started, 3)
    started = time.perf_counter()
    # R-560: the one seam. Both build twins and the ecosystem builder reach this function, so
    # verification cannot be wired into the sibling the console does not call — which is exactly
    # how R-555's ecosystem branch came to be live-broken while its tests passed.
    verification = verify_and_repair_build(
        target_dir=repo.target_dir,
        ir=ir,
        prompt=prompt,
        provider=provider,
        model_id=model_id,
        synthesize_screens=synthesize_screens,
        author_name=author_name,
        author_email=author_email,
        outcomes=ui_outcomes,
    )
    timings["verify"] = round(time.perf_counter() - started, 3)
    return AppBuildResult(
        prompt=prompt,
        ir=ir,
        target_dir=repo.target_dir,
        file_count=repo.file_count,
        commit_sha=repo.commit_sha,
        verification=verification,
        context_truncated=context_truncated,
        active_skills=active_skills,
        truncated_skills=truncated_skills,
        substitutions=_substitutions_for(ir, prompt),
        not_connected=_not_connected(ir),
        timings=timings,
    )


def _not_connected(ir: ApplicationIR) -> tuple[dict, ...]:
    from ..codegen.wiring_report import wiring_gaps

    return wiring_gaps(ir)


def _substitutions_for(ir: ApplicationIR, prompt: str = "") -> tuple[dict, ...]:
    """What the assembler substituted, from the same function the assembler used to decide it.

    Deliberately not recomputed with its own rules: the console reporting one stack while the
    repository on disk holds another is the failure mode this task exists to remove.

    PC-003: plus the stacks the prompt named that no IR field can hold (React.js, Vue, Spring,
    MySQL ...), judged against the *resolved* strategy so the note names what was really built.
    """
    from ..codegen.capabilities import named_stack_substitutions, resolve_stack

    plan = resolve_stack(ir.project_strategy)
    notes = [s.as_dict() for s in plan.substitutions]
    layers_already_explained = {n["layer"] for n in notes}
    for s in named_stack_substitutions(prompt, plan.strategy):
        if s.layer not in layers_already_explained:
            notes.append(s.as_dict())
    return tuple(notes)


def app_build_result_to_dict(
    result: AppBuildResult,
    *,
    max_files: int = 500,
    ui_outcomes: list | None = None,
    usage: dict | None = None,
) -> dict:
    """A JSON-safe view of an AppBuildResult for the studio/API (no secrets)."""
    from ..codegen.design_direction import describe as describe_direction

    root = Path(result.target_dir)
    files: list[str] = []
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root)
            if ".git" in rel.parts:
                continue
            files.append(str(rel))
            if len(files) >= max_files:
                break
    payload = {
        "prompt": result.prompt,
        "name": result.ir.name,
        "description": result.ir.description,
        "entities": [entity.name for entity in result.ir.entities],
        # PC-099: what the app will look like, in one line (empty for a plan with no direction).
        "design_direction": describe_direction(result.ir.brand),
        "file_count": result.file_count,
        "target_dir": result.target_dir,
        "commit_sha": result.commit_sha,
        "files": files,
        "context_truncated": result.context_truncated,
        "active_skills": list(result.active_skills),
        "truncated_skills": list(result.truncated_skills),
        # R-557: carried so the console can say why a project has four apps in it. Absent for a
        # single-app build, which is how the console knows to render nothing extra — an empty
        # panel reading "1 app" would be noise on every ordinary build.
        **(
            {
                "ecosystem_apps": list(result.ecosystem_apps),
                "ecosystem_reason": result.ecosystem_reason,
            }
            if result.ecosystem_apps
            else {}
        ),
        # R-559: absent when nothing was substituted, so an ordinary build renders nothing extra.
        **({"substitutions": [dict(s) for s in result.substitutions]} if result.substitutions else {}),
        **({"not_connected": [dict(g) for g in result.not_connected]} if result.not_connected else {}),
        **({"timings": dict(result.timings)} if result.timings else {}),
        **({"scope": dict(result.scope)} if result.scope else {}),
        # R-560: always present, unlike the two above. A build that was not type-checked has to say
        # so; silence would read as "checked and fine", which is the impression that let a
        # non-compiling app ship for nine tasks.
        **({"verification": dict(result.verification)} if result.verification else {}),
    }
    if ui_outcomes:
        payload["ui_outcomes"] = [outcome.to_dict() for outcome in ui_outcomes]
    if usage is not None:
        payload["usage"] = usage
    return payload


def _with_prompt_rules_for_plan(plan, prompt: str):
    """R-570 / R-567 for an ecosystem: what the prompt says about privacy and money, applied to the
    whole product once (over the union of its apps), then given to every app that has the entities.

    Found live: "a marketplace where customers pay ... 10% commission" planned as a buyer storefront,
    a seller app and an admin, and the money the prompt asked for was nowhere - the prompt passes
    ran only on the single-app planner's path.
    """
    from dataclasses import replace as _replace

    from ..application_ir import ApplicationIR
    from ..codegen.ecosystem_assembler import union_ir
    from .nl_to_ir import _with_prompt_ownership

    shared = union_ir(plan)
    ruled, notes = _with_prompt_ownership(shared, prompt)
    # R-580: the privacy the domain implies, where the prompt set none.
    from .domain_rules import domain_defaults

    data = ruled.to_dict()
    implied = domain_defaults(getattr(plan, "domain", ""), data)
    if implied:
        ruled, notes = ApplicationIR.from_dict(data), (*notes, *implied)
    if not notes:
        return plan
    known = {c.name for c in shared.capabilities}
    added = [c for c in ruled.capabilities if c.name not in known]
    fields_by_entity = {e.name: e.fields for e in ruled.entities}

    def referenced(capability) -> set[str]:
        config = capability.config
        if capability.kind == "money":
            return {c.get("entity") for c in config.get("charges") or ()}
        if capability.kind == "jobs":  # R-568
            return {s.get("entity") for s in config.get("schedules") or ()}
        if capability.kind == "notifications":  # PC-053
            return {r.get("entity") for r in config.get("rules") or ()}
        return {config.get("entity")}

    apps = []
    for app in plan.apps:
        data = app.ir.to_dict()
        names = {e["name"] for e in data["entities"]}
        for entity in data["entities"]:
            have = {f["name"] for f in entity["fields"]}
            for field in fields_by_entity.get(entity["name"], ()):
                if field.name not in have:
                    entity["fields"].append(field.to_dict())
        data["capabilities"] = data.get("capabilities", []) + [
            c.to_dict() for c in added if c.kind != "realtime" and referenced(c) <= names]
        for c in added:  # R-569: each app takes the live entities it has
            if c.kind == "realtime":
                mine = [e for e in c.config.get("entities") or () if e in names]
                if mine:
                    data["capabilities"].append({"kind": "realtime", "name": c.name, "config": {"entities": mine}})
        apps.append(_replace(app, ir=ApplicationIR.from_dict(data)))
    return _replace(plan, apps=tuple(apps))


def build_ecosystem_from_plan(
    plan,
    target_dir: str | os.PathLike[str],
    *,
    author_name: str,
    author_email: str,
    prompt: str = "",
    overwrite: bool = False,
    provider: ModelProvider | None = None,
    reason: str = "",
    context_truncated: bool = False,
    active_skills: tuple[str, ...] = (),
    truncated_skills: tuple[str, ...] = (),
    finish=None,
) -> AppBuildResult:
    """Materialize a planned ecosystem as one owned Git repo (R-555).

    One repo rather than one per surface: the apps share a database, so splitting them would mean
    the courier could not see the customer's order. `ir` on the result is the union the shared
    backend was generated from — the thing that describes the whole product rather than one app.
    """
    from ..codegen.ecosystem_assembler import assemble_ecosystem, surface_directory, union_ir

    if prompt:
        # PC-104: formatting asked for in the prompt reaches every app's plan (one shared backend).
        from dataclasses import replace as _replace

        from ..codegen.rich_text import with_rich_text

        plan = _replace(plan, apps=tuple(_replace(app, ir=with_rich_text(app.ir, prompt)) for app in plan.apps))
        plan = _with_prompt_rules_for_plan(plan, prompt)
    if finish is not None:
        # PC-128: what the owner's brief switched off stays off after the prompt's rules.
        from dataclasses import replace as _finish_replace

        plan = _finish_replace(plan, apps=tuple(_finish_replace(app, ir=finish(app.ir)) for app in plan.apps))
    # PC-101 for ecosystems too: every record a surface lists has a page of its own (found with
    # PC-113: a buyer's purchase had no page, so there was nowhere to pay for it).
    from dataclasses import replace as _replace_app

    from ..codegen.reachable_references import with_detail_screens, with_reachable_references

    plan = _replace_app(plan, apps=tuple(
        _replace_app(app, ir=with_detail_screens(with_reachable_references(app.ir))) for app in plan.apps))
    project = assemble_ecosystem(plan, provider=provider, prompt=prompt)
    # PC-099: the plan the workspace keeps carries the ecosystem's design direction (the same one
    # the assembler applied), so the console can say what it looks like.
    from ..codegen.design_direction import with_design_direction

    shared = with_design_direction(union_ir(plan), prompt) if prompt else union_ir(plan)
    repo = create_repository(
        project,
        target_dir,
        author_name=author_name,
        author_email=author_email,
        commit_message=f"Initial commit: {shared.name}",
        overwrite=overwrite,
    )
    taken: set[str] = set()
    directories = []
    for app in plan.apps:
        directory = surface_directory(app.surface.kind, taken)
        taken.add(directory)
        directories.append(directory)
    # R-560: an ecosystem build does not pass through `build_app_from_ir`, so wiring verification
    # only there would have left every multi-app project unchecked — the same shape as R-555, where
    # the branch was wired into the twin the console does not call. The gate in
    # test_build_verification.py found this within a minute of being written.
    # PC-097: each role app is repaired with its own IR - the union has no screens and would
    # revert a surface's page to a template for a different app.
    next_apps = ecosystem_next_apps(plan, brand=shared.brand)
    verification = verify_and_repair_build(
        target_dir=repo.target_dir,
        ir=shared,
        prompt=prompt,
        provider=provider,
        author_name=author_name,
        author_email=author_email,
        next_apps=next_apps,
    )
    return AppBuildResult(
        prompt=prompt,
        ir=shared,
        target_dir=repo.target_dir,
        file_count=repo.file_count,
        commit_sha=repo.commit_sha,
        verification=verification,
        context_truncated=context_truncated,
        active_skills=active_skills,
        truncated_skills=truncated_skills,
        ecosystem_apps=tuple(directories),
        ecosystem_reason=reason,
        substitutions=_substitutions_for(shared, prompt),
        not_connected=_not_connected(shared),
    )


def ecosystem_next_apps(plan, *, brand=None) -> list[tuple[str, ApplicationIR, str]]:
    """Every Next.js app of an ecosystem: (directory, its own IR, "web" | "admin").

    Laid out exactly as the ecosystem assembler lays it out, so a check or a page design reaches
    the app that was generated. ``brand`` (PC-099) gives each app the ecosystem's direction.
    """
    from dataclasses import replace as _replace

    from ..application_ir import MobileProfile
    from ..codegen.ecosystem_assembler import surface_directory

    taken: set[str] = set()
    apps: list[tuple[str, ApplicationIR, str]] = []
    for app in plan.apps:
        directory = surface_directory(app.surface.kind, taken)
        taken.add(directory)
        if app.ir.project_strategy.mobile_profile is MobileProfile.REACT_NATIVE:
            continue
        app_ir = _replace(app.ir, brand=brand) if brand is not None else app.ir
        apps.append((f"apps/{directory}", app_ir, "admin" if directory == "admin" else "web"))
    return apps


async def build_app_from_prompt(
    prompt: str,
    provider: ModelProvider,
    target_dir: str | os.PathLike[str],
    *,
    model_id: str,
    author_name: str,
    author_email: str,
    example_name: str = DEFAULT_TEMPLATE_EXAMPLE,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    overwrite: bool = False,
    synthesize_screens: bool = False,
    ui_outcomes: list | None = None,
    context: dict | str | None = None,
    scope: dict | None = None,
    brief: dict | None = None,
) -> AppBuildResult:
    """Compile ``prompt`` into an IR via ``provider`` and materialize an owned Git repo.

    Raises IntakeResponseError (from the intake step) if the model output cannot be turned
    into a valid Application IR. ``synthesize_screens`` (R-465) additionally lets the same provider write
    every screen page (the overview page is always model-written when a provider is given).
    """
    # R-555: does this prompt want one app or a whole ecosystem? Decided from the prompt alone,
    # deterministically and offline — whether a build produces one app or four must not vary
    # between runs of the same sentence, and it is not a judgement for a small local model.
    owner_brief, prompt, scope = _with_brief(prompt, brief, scope)
    intent = detect_ecosystem_intent(prompt)
    chosen = _chosen_scope(prompt, scope)
    plan = _scoped_ecosystem_plan(prompt, intent, chosen, owner_brief)
    if plan is not None:
        built = build_ecosystem_from_plan(
            plan,
            target_dir,
            author_name=author_name,
            author_email=author_email,
            prompt=prompt,
            overwrite=overwrite,
            provider=provider,
            reason=intent.reason,
            finish=_brief_finish(owner_brief),
        )
        built = _replace_result(built, scope=chosen.to_dict())
        return built

    plan_started = time.perf_counter()
    result = await generate_ir(
        prompt,
        provider,
        model_id=model_id,
        example_name=example_name,
        max_output_tokens=max_output_tokens,
        timeout_seconds=timeout_seconds,
        context=context,
    )
    plan_seconds = round(time.perf_counter() - plan_started, 3)
    built = build_app_from_ir(
        _briefed_ir(_scoped_ir(result.ir, chosen, confirmed=scope is not None), owner_brief),
        target_dir,
        author_name=author_name,
        author_email=author_email,
        prompt=prompt,
        overwrite=overwrite,
        provider=provider,
        model_id=model_id,
        synthesize_screens=synthesize_screens,
        ui_outcomes=ui_outcomes,
        context_truncated=result.context_truncated,
        active_skills=result.active_skills,
        truncated_skills=result.truncated_skills,
    )
    built.timings["plan"] = plan_seconds
    built = _replace_result(built, scope=chosen.to_dict())
    return built


def _replace_result(result: AppBuildResult, **changes) -> AppBuildResult:
    from dataclasses import replace as _replace

    return _replace(result, **changes)


def _chosen_scope(prompt: str, scope: dict | None):
    """PC-127: the scope the person confirmed, or the one the prompt implies."""
    from .scope import ProjectScope, propose_scope

    if scope:
        try:
            chosen = ProjectScope.from_dict(scope)
            if chosen.apps:
                return chosen
        except (TypeError, ValueError):
            pass
    return propose_scope(prompt)


def _scoped_ecosystem_plan(prompt: str, intent, chosen, owner_brief=None):
    """The ecosystem to build, with only the apps the scope includes; None for one product."""
    from .scope import apply_to_plan

    if not (intent.build_ecosystem and chosen.plan == "ecosystem"):
        return None
    from .ecosystem import plan_ecosystem_from_prompt  # local: `ecosystem` imports this module

    plan = apply_to_plan(plan_ecosystem_from_prompt(prompt, intent.option_id), chosen)
    if owner_brief is not None:
        plan = _replace_result(plan, apps=tuple(_replace_result(app, ir=_briefed_ir(app.ir, owner_brief, rename=False))
                                                for app in plan.apps))
    return plan if len(plan.apps) > 1 else None


def _with_brief(prompt: str, brief: dict | None, scope: dict | None):
    """PC-128: the brief the owner confirmed - its answers become the plan's facts, its apps the scope."""
    if not brief:
        return None, prompt, scope
    from .brief import Brief, plan_prompt

    try:
        owner_brief = Brief.from_dict({**brief, "prompt": brief.get("prompt") or prompt})
    except (TypeError, ValueError, KeyError):
        return None, prompt, scope
    return owner_brief, plan_prompt(owner_brief), scope or owner_brief.scope.to_dict()


def _briefed_ir(ir, owner_brief, *, rename: bool = True):
    if owner_brief is None:
        return ir
    from .brief import apply_brief

    return apply_brief(ir, owner_brief, rename=rename)


def _brief_finish(owner_brief):
    """Applied to each app after the prompt's rules: a building block switched off stays off."""
    if owner_brief is None:
        return None
    return lambda ir: _briefed_ir(ir, owner_brief, rename=False)


def _scoped_ir(ir, chosen, *, confirmed: bool):
    """One product: a confirmed scope decides its apps. Unconfirmed, the planner's choice stands."""
    from .scope import apply_to_ir

    return apply_to_ir(ir, chosen) if confirmed and chosen.plan == "product" else ir


async def build_app_from_prompt_stream(
    prompt: str,
    provider: ModelProvider,
    target_dir: str | os.PathLike[str],
    *,
    model_id: str,
    author_name: str,
    author_email: str,
    example_name: str = DEFAULT_TEMPLATE_EXAMPLE,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    overwrite: bool = False,
    context: dict | str | None = None,
    scope: dict | None = None,
    brief: dict | None = None,
) -> AsyncIterator[str | AppBuildResult]:
    """Streaming twin of `build_app_from_prompt` (R-484): yields text deltas from the IR-generation
    call as they arrive, then does the existing `build_app_from_ir`'s pure-disk work (assemble +
    git commit — fast, not usefully streamable token-by-token) once the IR is complete, and yields
    the final `AppBuildResult`.
    """
    # R-555: the same decision as the non-streaming twin, and the one the console actually takes.
    # Wiring only `build_app_from_prompt` left this path on the single-app branch, which a live run
    # through the console exposed immediately: the offline tests called the function I had wired,
    # not the one the product uses.
    owner_brief, prompt, scope = _with_brief(prompt, brief, scope)
    intent = detect_ecosystem_intent(prompt)
    chosen = _chosen_scope(prompt, scope)
    plan = _scoped_ecosystem_plan(prompt, intent, chosen, owner_brief)
    if plan is not None:
        names = ", ".join(app.ir.name for app in plan.apps)
        # The ecosystem is planned deterministically, so there is no model stream to relay.
        # Say what is happening instead of going silent for the length of a build.
        yield f"Planning {len(plan.apps)} apps over one API and one database: {names}.\n"
        yield f"{intent.reason}.\n"
        built = build_ecosystem_from_plan(
            plan,
            target_dir,
            author_name=author_name,
            author_email=author_email,
            prompt=prompt,
            overwrite=overwrite,
            provider=provider,
            reason=intent.reason,
            finish=_brief_finish(owner_brief),
        )
        built = _replace_result(built, scope=chosen.to_dict())
        yield built
        return

    result: IntakeResult | None = None
    plan_started = time.perf_counter()
    async for item in generate_ir_stream(
        prompt,
        provider,
        model_id=model_id,
        example_name=example_name,
        max_output_tokens=max_output_tokens,
        timeout_seconds=timeout_seconds,
        context=context,
    ):
        if isinstance(item, str):
            yield item
        else:
            result = item
    assert result is not None  # generate_ir_stream always yields exactly one IntakeResult last
    plan_seconds = round(time.perf_counter() - plan_started, 3)
    built = build_app_from_ir(
        _briefed_ir(_scoped_ir(result.ir, chosen, confirmed=scope is not None), owner_brief),
        target_dir,
        author_name=author_name,
        author_email=author_email,
        prompt=prompt,
        overwrite=overwrite,
        # PC-084 (found by timing a live build): the streaming twin — the path the console uses —
        # did not pass the provider, so R-560's type-check-and-repair never ran on it: every
        # console build reported "ran without a model provider, not type-checked".
        provider=provider,
        model_id=model_id,
        model_written_pages=False,
        context_truncated=result.context_truncated,
        active_skills=result.active_skills,
        truncated_skills=result.truncated_skills,
    )
    built.timings["plan"] = plan_seconds
    built = _replace_result(built, scope=chosen.to_dict())
    yield built
