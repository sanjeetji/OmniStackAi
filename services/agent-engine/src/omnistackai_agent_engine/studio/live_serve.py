"""Opt-in live studio: serve the chat-to-create UI backed by the local Ollama build path.

Also serves a read-only file browser (``GET /api/build/{id}/files`` / ``.../file?path=``, R-467), a
``hybrid_ui`` build option that opts the plain-prompt and Ecosystem Pack paths into R-465's model-written
screens, surfacing R-465's ``ui_outcomes`` in the response and the recorded history, and a follow-up edit
loop (``POST /api/build/{id}/edit`` / ``GET /api/build/{id}/turns``, R-468) that lets a further prompt add
to a plain-prompt or single-surface Ecosystem Pack build as one more commit on the same repo.

Excluded from static verification. Start build-only mode with:

    task agent-engine:studio:serve

or explicitly opt into trusted-local generated-code execution and embedded preview with:

    task agent-engine:studio:preview

then open http://127.0.0.1:4173, type a description, and click Build. Each request compiles
the description into an Application IR and materializes a real owned Git repo on disk. The
output directory comes from OMNISTACKAI_APP_OUT_DIR (a per-build subfolder) or a temp dir.
Requires a running local Ollama; no secrets, no cloud. Preview mode also requires the local
PostgreSQL/toolchain and is not a tenant-isolated sandbox.
"""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import AsyncIterator
from decimal import ROUND_HALF_UP, Decimal

from ..application_ir import ApplicationIR
from ..codegen import assemble_project
from ..edit.apply import commit_edit
from ..edit.diff import plan_edit
from ..intake.app_delta import apply_app_delta, generate_app_delta_proposal
from ..intake.provider_resolution import resolve_generation_provider_from_env
from ..model_gateway.overview import platform_overview
from ..intake.build_app import app_build_result_to_dict, build_app_from_prompt, build_app_from_prompt_stream
from ..model_gateway.accounting import UsageLedger
from .files import BuildNotFoundError, list_build_files, read_build_file
from .history import StudioBuildHistory
from .preview import StudioPreviewManager
from .problems import ProblemsNotCheckedError, StudioProblemsStore, check_build_problems
from .server import create_studio_server
from .session import EditNotSupportedError, StudioSessionStore
from .workspace import StudioWorkspaceStore, WorkspaceLockedError

_MICROS_PER_USD = Decimal(1_000_000)


def _usage_summary_to_dict(ledger: UsageLedger) -> dict:
    """A JSON-safe, secret-free view of ``ledger``'s aggregate cost/usage (R-472, R-504).

    ``cost_micros_usd`` is an int (USD * 1,000,000, rounded) rather than a Decimal or a decimal
    string, so it crosses the eventual Go control-plane boundary with no float/precision risk.
    """
    summary = ledger.summary()
    cost_micros = int((summary.total_cost_usd * _MICROS_PER_USD).to_integral_value(rounding=ROUND_HALF_UP))
    calls_list = []
    for r in ledger.records():
        call_cost_micros = (
            int((r.cost_usd * _MICROS_PER_USD).to_integral_value(rounding=ROUND_HALF_UP))
            if r.cost_usd is not None
            else 0
        )
        calls_list.append({
            "request_id": r.request_id,
            "provider_id": r.provider_id,
            "model_id": r.model_id,
            "tier": r.tier,
            "complexity": r.complexity,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "latency_ms": r.latency_ms,
            "success": r.success,
            "error_code": r.error_code,
            "cost_micros_usd": call_cost_micros,
        })
    return {
        "total_calls": summary.total_calls,
        "successful_calls": summary.successful_calls,
        "failed_calls": summary.failed_calls,
        "input_tokens": summary.input_tokens,
        "output_tokens": summary.output_tokens,
        "unpriced_calls": summary.unpriced_calls,
        "cost_micros_usd": cost_micros,
        "calls": calls_list,
    }

_AUTHOR_NAME = "sanjeetji"
_AUTHOR_EMAIL = "sk698166@gmail.com"


def _target_dir_for(
    prompt: str,
    *,
    custom_dir: str | None = None,
    folder_name: str | None = None,
    custom_name: str | None = None,
) -> str:
    base = custom_dir or os.environ.get("OMNISTACKAI_APP_OUT_DIR")
    slug_source = folder_name or custom_name or prompt
    slug = re.sub(r"[^a-z0-9]+", "-", slug_source.lower()).strip("-")[:40] or "app"
    if base:
        resolved_base = os.path.expanduser(base)
        os.makedirs(resolved_base, exist_ok=True)
        return os.path.join(resolved_base, slug)
    return os.path.join(tempfile.mkdtemp(prefix="omnistackai-studio-"), slug)


def _build(
    prompt: str,
    *,
    pack_id: str | None = None,
    pack_version: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    configuration_changes: list[dict] | None = None,
    ai_features: list[str] | None = None,
    ai_delta_prompt: str | None = None,
    ai_delta_provider: object | None = None,
    ecosystem_id: str | None = None,
    ecosystem_version: str | None = None,
    surface_slug: str | None = None,
    output_dir: str | None = None,
    folder_name: str | None = None,
    target_dir: str | None = None,
    direct_target_dir: str | None = None,
    hybrid_ui: bool = False,
    preview_manager: StudioPreviewManager | None = None,
    history: StudioBuildHistory | None = None,
    session_store: StudioSessionStore | None = None,
    workspace_store: StudioWorkspaceStore | None = None,
    workspace_id: str | None = None,
    provider_id: str | None = None,
    model_id: str | None = None,
    api_key: str | None = None,
    **extra_options,
) -> dict:
    """Build an app for one ``/api/build`` request.

    ``hybrid_ui`` (R-467) opts the plain-prompt and Ecosystem Pack paths into R-465's model-synthesized
    screens (``synthesize_screens=True`` + a ``ui_outcomes`` sink, surfaced in the returned payload). The
    Solution Pack path has no such parameter on ``build_solution_pack_project`` -- a request there is
    reported back honestly as ``hybrid_ui_active: False`` rather than silently ignored.

    ``session_store`` (R-468) starts a follow-up edit session for this build's Application IR -- but only
    for the plain-prompt and single-surface Ecosystem Pack paths, which produce exactly one IR; Solution
    Pack and "all surfaces" Ecosystem builds set ``editable_ir`` to None and are left un-editable.
    """
    editable_ir: ApplicationIR | None = None
    if ecosystem_id:
        from pathlib import Path
        from ..application_ir import ApplicationIR
        from ..solution_packs import DEFAULT_ECOSYSTEM_PACK_REGISTRY
        from ..intake.build_app import build_app_from_ir

        eco_pack = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get(ecosystem_id, version=ecosystem_version)
        if eco_pack is None:
            raise ValueError(f"Unknown Ecosystem Pack '{ecosystem_id}'")
        eco_pkg = eco_pack.to_package()

        target_dir = direct_target_dir or _target_dir_for(
            prompt,
            custom_dir=output_dir or target_dir,
            folder_name=folder_name,
            custom_name=custom_name,
        )

        eco_provider = None
        eco_model_id = None
        try:
            eco_provider, eco_model_id, _, _ = resolve_generation_provider_from_env()
        except Exception:
            pass

        if surface_slug and surface_slug != "all":
            surface = next(
                (s for s in eco_pkg.surfaces if s.slug == surface_slug or s.surface_kind == surface_slug),
                None,
            )
            if surface is None:
                raise ValueError(f"Surface '{surface_slug}' not found in ecosystem '{ecosystem_id}'")

            surface_ir = surface.to_application_ir()
            if custom_name:
                surface_ir = ApplicationIR(
                    name=custom_name,
                    description=custom_description or surface_ir.description,
                    entities=surface_ir.entities,
                    apis=surface_ir.apis,
                    screens=surface_ir.screens,
                    roles=surface_ir.roles,
                    fixtures=surface_ir.fixtures,
                    project_strategy=surface_ir.project_strategy,
                )
            elif custom_description:
                surface_ir = ApplicationIR(
                    name=surface_ir.name,
                    description=custom_description,
                    entities=surface_ir.entities,
                    apis=surface_ir.apis,
                    screens=surface_ir.screens,
                    roles=surface_ir.roles,
                    fixtures=surface_ir.fixtures,
                    project_strategy=surface_ir.project_strategy,
                )

            # R-467: hybrid UI only actually runs when a provider resolved -- report that honestly
            # rather than silently no-op'ing (build_app_from_ir treats synthesize_screens=True with
            # provider=None as a no-op by design).
            single_hybrid_active = bool(hybrid_ui and eco_provider is not None)
            single_ui_outcomes: list = []
            build_res = build_app_from_ir(
                surface_ir,
                target_dir,
                author_name=_AUTHOR_NAME,
                author_email=_AUTHOR_EMAIL,
                prompt=prompt,
                overwrite=True,
                provider=eco_provider,
                model_id=eco_model_id,
                synthesize_screens=single_hybrid_active,
                ui_outcomes=(single_ui_outcomes if single_hybrid_active else None),
            )
            root = Path(target_dir)
            files = []
            if root.is_dir():
                for path in sorted(root.rglob("*")):
                    if not path.is_file():
                        continue
                    rel = path.relative_to(root)
                    if rel.parts and rel.parts[0] == ".git":
                        continue
                    files.append(str(rel))

            payload = {
                "prompt": prompt,
                "name": surface_ir.name,
                "description": surface_ir.description,
                "entities": [entity.name for entity in surface_ir.entities],
                "file_count": build_res.file_count,
                "target_dir": target_dir,
                "commit_sha": build_res.commit_sha,
                "files": files,
                "ecosystem_id": eco_pkg.ecosystem_id,
                "ecosystem_version": eco_pkg.version,
                "surface_slug": surface.slug,
                "surface_kind": surface.surface_kind,
                "base_pack_id": eco_pkg.base_pack_id,
                "ir_sha256": surface.ir_sha256,
                "verify_targets": list(surface.verify_targets),
                "is_ecosystem": False,
                "hybrid_ui_requested": hybrid_ui,
                "hybrid_ui_active": single_hybrid_active,
            }
            if single_hybrid_active:
                payload["ui_outcomes"] = [outcome.to_dict() for outcome in single_ui_outcomes]
            editable_ir = surface_ir  # R-468: a single-surface build has exactly one IR to edit
        else:
            os.makedirs(target_dir, exist_ok=True)
            surface_results = []
            total_files = 0
            all_entities = set()
            used_slugs: dict[str, int] = {}
            all_hybrid_active = bool(hybrid_ui and eco_provider is not None)

            for surface in eco_pkg.surfaces:
                surface_ir = surface.to_application_ir()
                for e in surface_ir.entities:
                    all_entities.add(e.name)
                base_slug = surface.slug
                count = used_slugs.get(base_slug, 0)
                used_slugs[base_slug] = count + 1
                unique_slug = base_slug if count == 0 else f"{base_slug}-{count + 1}"
                surface_target_dir = os.path.join(target_dir, unique_slug)

                surface_ui_outcomes: list = []
                build_res = build_app_from_ir(
                    surface_ir,
                    surface_target_dir,
                    author_name=_AUTHOR_NAME,
                    author_email=_AUTHOR_EMAIL,
                    prompt=prompt,
                    overwrite=True,
                    provider=eco_provider,
                    model_id=eco_model_id,
                    synthesize_screens=all_hybrid_active,
                    ui_outcomes=(surface_ui_outcomes if all_hybrid_active else None),
                )
                total_files += build_res.file_count
                surface_entry = {
                    "surface_kind": surface.surface_kind,
                    "app_name": surface.app_name,
                    "slug": surface.slug,
                    "target_dir": surface_target_dir,
                    "file_count": build_res.file_count,
                    "commit_sha": build_res.commit_sha,
                    "verify_targets": list(surface.verify_targets),
                    "ir_sha256": surface.ir_sha256,
                }
                if all_hybrid_active:
                    surface_entry["ui_outcomes"] = [outcome.to_dict() for outcome in surface_ui_outcomes]
                surface_results.append(surface_entry)

            payload = {
                "prompt": prompt,
                "name": eco_pkg.display_name,
                "description": eco_pkg.description,
                "entities": sorted(all_entities),
                "file_count": total_files,
                "target_dir": target_dir,
                "commit_sha": surface_results[0]["commit_sha"] if surface_results else "",
                "files": [f"{s['slug']} ({s['file_count']} files)" for s in surface_results],
                "ecosystem_id": eco_pkg.ecosystem_id,
                "ecosystem_version": eco_pkg.version,
                "domain": eco_pkg.domain,
                "base_pack_id": eco_pkg.base_pack_id,
                "surface_count": len(surface_results),
                "surfaces": surface_results,
                "is_ecosystem": True,
                "hybrid_ui_requested": hybrid_ui,
                "hybrid_ui_active": all_hybrid_active,
            }
    elif pack_id:
        from pathlib import Path
        from ..solution_packs import (
            DEFAULT_SOLUTION_PACK_REGISTRY,
            ChangeArea,
            ChangeOperation,
            ChangeSource,
            SolutionPackChange,
            apply_solution_pack_manifest,
            build_solution_pack_project,
            create_solution_pack_manifest,
        )

        pack = DEFAULT_SOLUTION_PACK_REGISTRY.get(pack_id, version=pack_version)
        if pack is None:
            raise ValueError(f"Unknown Solution Pack '{pack_id}'")
        rec = DEFAULT_SOLUTION_PACK_REGISTRY.recommend(
            pack.domains[0],
            required_targets=pack.targets,
        )
        changes: list[SolutionPackChange] = []
        if custom_name:
            changes.append(
                SolutionPackChange(
                    change_id="config-custom-name",
                    source=ChangeSource.CONFIGURATION,
                    operation=ChangeOperation.UPDATE,
                    area=ChangeArea.PROJECT,
                    target="project:name",
                    summary="Update project name",
                    acceptance_criteria=("Project name matches custom name.",),
                    desired_text=custom_name,
                )
            )
        if custom_description:
            changes.append(
                SolutionPackChange(
                    change_id="config-custom-description",
                    source=ChangeSource.CONFIGURATION,
                    operation=ChangeOperation.UPDATE,
                    area=ChangeArea.PROJECT,
                    target="project:description",
                    summary="Update project description",
                    acceptance_criteria=("Project description matches custom description.",),
                    desired_text=custom_description,
                )
            )

        feature_items: list[str] = []
        if ai_features:
            feature_items.extend(str(f).strip() for f in ai_features if str(f).strip())
        if ai_delta_prompt and str(ai_delta_prompt).strip():
            for line in str(ai_delta_prompt).splitlines():
                line = line.strip()
                if line and line not in feature_items:
                    feature_items.append(line)

        for idx, item in enumerate(feature_items):
            cid = f"ai-delta-{idx + 1}"
            clean_item = re.sub(r"[^a-zA-Z0-9]+", "-", item).strip("-").lower()
            slug = clean_item[:30] if clean_item else f"feature-{idx + 1}"
            changes.append(
                SolutionPackChange(
                    change_id=cid,
                    source=ChangeSource.AI_DELTA,
                    operation=ChangeOperation.ADD,
                    area=ChangeArea.CAPABILITY,
                    target=f"capability:{slug}",
                    summary=item[:240],
                    acceptance_criteria=(f"{item[:200]} is supported.",),
                )
            )

        manifest = create_solution_pack_manifest(
            rec,
            changes=tuple(changes),
        )

        pack_provider = None
        pack_model_id = None
        has_ai_deltas = any(c.source is ChangeSource.AI_DELTA for c in manifest.changes)
        proposal = None
        if has_ai_deltas:
            from ..solution_packs.ai_delta import generate_ai_delta_proposal

            if ai_delta_provider is not None:
                pack_provider = ai_delta_provider
                pack_model_id = None
            else:
                pack_provider, pack_model_id, _, _ = resolve_generation_provider_from_env()

            base_ir = DEFAULT_SOLUTION_PACK_REGISTRY.load_ir(pack.pack_id, pack.version)
            maybe_coro = generate_ai_delta_proposal(
                manifest,
                base_ir,
                pack_provider,
                model_id=pack_model_id,
            )
            if asyncio.iscoroutine(maybe_coro):
                proposal = asyncio.run(maybe_coro)
            else:
                proposal = maybe_coro
        else:
            try:
                pack_provider, pack_model_id, _, _ = resolve_generation_provider_from_env()
            except Exception:
                pass

        app_result = apply_solution_pack_manifest(manifest, proposal=proposal)
        target_dir = direct_target_dir or _target_dir_for(
            prompt,
            custom_dir=output_dir or target_dir,
            folder_name=folder_name,
            custom_name=custom_name,
        )
        build_result = build_solution_pack_project(
            app_result,
            target_dir,
            author_name=_AUTHOR_NAME,
            author_email=_AUTHOR_EMAIL,
            overwrite=True,
            provider=pack_provider,
            prompt=prompt,
            model_id=pack_model_id,
        )
        root = Path(build_result.target_dir)
        files: list[str] = []
        if root.is_dir():
            for path in sorted(root.rglob("*")):
                if not path.is_file():
                    continue
                rel = path.relative_to(root)
                if rel.parts and rel.parts[0] == ".git":
                    continue
                files.append(str(rel))
        payload = {
            "prompt": prompt,
            "name": build_result.app_name,
            "description": app_result.ir.description,
            "entities": [entity.name for entity in app_result.ir.entities],
            "file_count": build_result.file_count,
            "target_dir": build_result.target_dir,
            "commit_sha": build_result.commit_sha,
            "files": files,
            "pack_id": build_result.pack_id,
            "pack_version": build_result.pack_version,
            "base_ir_sha256": build_result.base_ir_sha256,
            "derived_ir_sha256": build_result.derived_ir_sha256,
            "applied_configuration_change_ids": list(build_result.applied_configuration_change_ids),
            "applied_ai_delta_change_ids": list(build_result.applied_ai_delta_change_ids),
            "unapplied_ai_delta_change_ids": list(build_result.unapplied_ai_delta_change_ids),
            "verify_targets": list(build_result.verify_targets),
            # R-467: build_solution_pack_project has no synthesize_screens/ui_outcomes parameter -- a
            # requested hybrid_ui is reported honestly as inactive here, never silently ignored.
            "hybrid_ui_requested": hybrid_ui,
            "hybrid_ui_active": False,
        }
    else:
        usage_ledger = UsageLedger()
        provider, eff_model_id, max_output, request_timeout = resolve_generation_provider_from_env(
            usage_ledger=usage_ledger,
            provider_id=provider_id,
            model_id=model_id,
            api_key=api_key,
        )
        chosen_dir = direct_target_dir or _target_dir_for(
            prompt,
            custom_dir=output_dir or target_dir,
            folder_name=folder_name,
            custom_name=custom_name,
        )
        plain_ui_outcomes: list = []
        result = asyncio.run(
            build_app_from_prompt(
                prompt,
                provider,
                chosen_dir,
                model_id=eff_model_id,
                author_name=_AUTHOR_NAME,
                author_email=_AUTHOR_EMAIL,
                max_output_tokens=max_output,
                timeout_seconds=request_timeout,
                overwrite=True,
                synthesize_screens=hybrid_ui,
                ui_outcomes=(plain_ui_outcomes if hybrid_ui else None),
            )
        )
        # A provider is already mandatory on this path, so a requested hybrid_ui is always honored.
        payload = app_build_result_to_dict(
            result,
            ui_outcomes=(plain_ui_outcomes if hybrid_ui else None),
            usage=_usage_summary_to_dict(usage_ledger),
        )
        payload["hybrid_ui_requested"] = hybrid_ui
        payload["hybrid_ui_active"] = hybrid_ui
        editable_ir = result.ir  # R-468: a plain-prompt build has exactly one IR to edit

    if history is not None:
        payload["id"] = history.record(payload)
        if session_store is not None and editable_ir is not None:
            session_store.begin(payload["id"], editable_ir, payload["target_dir"])
            # R-476: without this, GET /api/build/{id}/turns would return an empty history for a
            # build that has never been edited yet, even though a real build happened - a chat UI
            # (R-477) hydrating from /turns after a page refresh would silently lose the very
            # first message. Only _edit() recorded turns before this fix.
            session_store.record_turn(payload["id"], "user", prompt)
            session_store.record_turn(
                payload["id"], "assistant", f"Built {payload.get('name', 'the app')}."
            )
    if workspace_store is not None and workspace_id:
        payload["id"] = workspace_id
        if editable_ir is not None:
            workspace_store.save_ir(workspace_id, editable_ir)
        workspace_store.append_turn(workspace_id, "user", prompt)
        workspace_store.append_turn(
            workspace_id, "assistant", f"Built {payload.get('name', 'the app')}."
        )
        workspace_store.save_state(workspace_id, payload)
    if preview_manager is None:
        payload["preview"] = {
            "status": "disabled",
            "message": "Build-only mode: start the explicit Studio preview command to run generated code.",
        }
    else:
        if payload.get("is_ecosystem") and payload.get("surfaces"):
            payload["preview"] = preview_manager.replace_ecosystem(
                ecosystem_id=str(payload.get("ecosystem_id", "ecosystem")),
                surfaces=payload["surfaces"],
            )
        else:
            payload["preview"] = preview_manager.replace(payload["target_dir"])
    return payload


class StreamingBuildNotSupportedError(Exception):
    """Raised for a streaming build request naming a build kind R-484 doesn't stream yet (Solution
    Pack, Ecosystem, or hybrid_ui) - reported as a clean, honest rejection rather than silently
    falling back to a blocking build or guessing. The caller (server.py) checks for this BEFORE any
    SSE framing begins, so the response is a normal JSON 400, never a broken half-open stream."""


async def _build_stream(
    prompt: str,
    *,
    pack_id: str | None = None,
    ecosystem_id: str | None = None,
    hybrid_ui: bool = False,
    custom_name: str | None = None,
    custom_description: str | None = None,
    output_dir: str | None = None,
    folder_name: str | None = None,
    target_dir: str | None = None,
    direct_target_dir: str | None = None,
    preview_manager: StudioPreviewManager | None = None,
    history: StudioBuildHistory | None = None,
    session_store: StudioSessionStore | None = None,
    workspace_store: StudioWorkspaceStore | None = None,
    workspace_id: str | None = None,
    context: dict | None = None,
    provider_id: str | None = None,
    model_id: str | None = None,
    api_key: str | None = None,
    **extra_options,
) -> AsyncIterator[dict]:
    """Streaming twin of `_build` (R-484), scoped to the plain-prompt, non-`hybrid_ui` path only -
    the same scope precedent `_edit`/R-476 already set for its own single-IR-only build kinds.

    Yields `{"phase": "generating_ir", "delta": "..."}` events as the IR streams in from the model,
    then one final `{"phase": "done", ...}` event carrying the exact same payload shape `_build`
    itself returns for a plain-prompt build - including history recording, turn recording (R-476),
    and preview handling (reusing that logic unchanged, not duplicated).
    """
    if pack_id or ecosystem_id or hybrid_ui:
        raise StreamingBuildNotSupportedError(
            "streaming is only supported for a plain-prompt, non-hybrid_ui build today"
        )

    usage_ledger = UsageLedger()
    provider, eff_model_id, max_output, request_timeout = resolve_generation_provider_from_env(
        usage_ledger=usage_ledger,
        provider_id=provider_id,
        model_id=model_id,
        api_key=api_key,
    )
    chosen_dir = direct_target_dir or _target_dir_for(
        prompt,
        custom_dir=output_dir or target_dir,
        folder_name=folder_name,
        custom_name=custom_name,
    )

    from .logs import StudioLogManager
    log_mgr = StudioLogManager() if (workspace_store is not None and workspace_id) else None
    if log_mgr is not None:
        log_mgr.append_build_log(workspace_id, "info", "start", f"Starting build for: {prompt[:120]}")

    result = None
    try:
        async for item in build_app_from_prompt_stream(
            prompt,
            provider,
            chosen_dir,
            model_id=eff_model_id,
            author_name=_AUTHOR_NAME,
            author_email=_AUTHOR_EMAIL,
            max_output_tokens=max_output,
            timeout_seconds=request_timeout,
            overwrite=True,
            context=context,
        ):
            if workspace_store is not None and workspace_id and workspace_store.is_cancelled(workspace_id):
                if log_mgr is not None:
                    log_mgr.append_build_log(workspace_id, "warn", "cancelled", "Build cancelled by user")
                yield {"phase": "cancelled", "usage": _usage_summary_to_dict(usage_ledger)}
                return

            if isinstance(item, str):
                yield {"phase": "generating_ir", "delta": item}
            else:
                result = item
    except Exception as error:
        if log_mgr is not None:
            log_mgr.append_build_log(workspace_id, "error", "error", f"Build failed: {error}")
        raise

    if workspace_store is not None and workspace_id and workspace_store.is_cancelled(workspace_id):
        if log_mgr is not None:
            log_mgr.append_build_log(workspace_id, "warn", "cancelled", "Build cancelled by user")
        yield {"phase": "cancelled", "usage": _usage_summary_to_dict(usage_ledger)}
        return

    assert result is not None  # build_app_from_prompt_stream always yields exactly one result last

    payload = app_build_result_to_dict(result, usage=_usage_summary_to_dict(usage_ledger))
    payload["hybrid_ui_requested"] = False
    payload["hybrid_ui_active"] = False
    editable_ir = result.ir

    trunc_note = " (Note: Context was truncated due to length limits.)" if result.context_truncated else ""
    if history is not None:
        payload["id"] = history.record(payload)
        if session_store is not None:
            session_store.begin(payload["id"], editable_ir, payload["target_dir"])
            session_store.record_turn(payload["id"], "user", prompt)
            session_store.record_turn(
                payload["id"], "assistant", f"Built {payload.get('name', 'the app')}.{trunc_note}"
            )
    if workspace_store is not None and workspace_id:
        payload["id"] = workspace_id
        if editable_ir is not None:
            workspace_store.save_ir(workspace_id, editable_ir)
        workspace_store.append_turn(workspace_id, "user", prompt)
        workspace_store.append_turn(
            workspace_id, "assistant", f"Built {payload.get('name', 'the app')}.{trunc_note}"
        )
        workspace_store.save_state(workspace_id, payload)
    if preview_manager is None:
        payload["preview"] = {
            "status": "disabled",
            "message": "Build-only mode: start the explicit Studio preview command to run generated code.",
        }
    else:
        payload["preview"] = preview_manager.replace(payload["target_dir"])

    if log_mgr is not None:
        log_mgr.append_build_log(workspace_id, "info", "done", f"Built {payload.get('name', 'the app')} ({payload.get('file_count', 0)} files)")

    yield {"phase": "done", **payload}


def _preview_recorded_build(
    build_id: str,
    history: StudioBuildHistory,
    preview_manager: StudioPreviewManager,
    surface_slug: str | None = None,
) -> dict:
    entry = history.get(build_id)
    if entry is None or not entry.get("target_dir"):
        return {"status": "error", "message": "That build is no longer available in this session."}
    if entry.get("is_ecosystem") and entry.get("surfaces"):
        return preview_manager.replace_ecosystem(
            ecosystem_id=str(entry.get("ecosystem_id", "ecosystem")),
            surfaces=entry["surfaces"],
            active_surface_slug=surface_slug,
        )
    return preview_manager.replace(entry["target_dir"])


def _resolve_build_dir(build_id: str, history: StudioBuildHistory) -> str:
    """The recorded ``target_dir`` for ``build_id``, or a ``BuildNotFoundError`` (R-467)."""
    entry = history.get(build_id)
    if entry is None or not entry.get("target_dir"):
        raise BuildNotFoundError(f"build '{build_id}' is not available in this session")
    return entry["target_dir"]


def _list_build_files(build_id: str, history: StudioBuildHistory) -> dict:
    return list_build_files(_resolve_build_dir(build_id, history))


def _read_build_file(build_id: str, path: str, history: StudioBuildHistory) -> dict:
    return read_build_file(_resolve_build_dir(build_id, history), path)


def _turns(build_id: str, session_store: StudioSessionStore) -> dict:
    return session_store.turns_view(build_id)


def _provider_status() -> dict:
    """A live model-fabric status view for the console's Settings page (R-482).

    `platform_overview()` is real, tested, and metadata-only (never a key value) but was previously
    only ever exported to a static build-time JSON snapshot for the public /fabric page - this is
    the first time it's served live. Adds `activeNow`: which provider would actually run the next
    real build/edit, resolved via `resolve_generation_provider_from_env()` - a function that always
    succeeds (it falls through to local Ollama, never raises for "nothing configured"), so the only
    failure mode here would be a genuinely unexpected error, reported honestly rather than crashing
    the whole status view.

    Resolves `activeNow` BEFORE calling `platform_overview()`, not after - `resolve_generation_
    provider_from_env()` lazily loads `.env` into `os.environ` on its first-ever call in this
    process (`load_dotenv=True` by default), so calling it first ensures `platform_overview()`'s own
    `os.environ` reads see the same, fully-loaded environment. Getting this backwards was a real bug
    caught live during this task's own manual smoke test: in a process where no build had happened
    yet, the providers list showed every cloud provider as "Needs key" (read before .env loaded)
    while `activeNow` correctly named the real configured provider (read after) - an honest,
    internally-inconsistent response, not a crash, but wrong. Fixed by simply reordering the two
    calls rather than reaching into `_load_dotenv_if_needed` (a private helper of a different
    module) directly.
    """
    active_now: dict | None = None
    active_now_error: str | None = None
    try:
        provider, model_id, _max_output, _timeout = resolve_generation_provider_from_env()
        active_now = {"providerId": provider.provider_id, "modelId": model_id}
    except Exception as error:
        active_now_error = str(error)

    overview = platform_overview()
    overview["activeNow"] = active_now
    overview["activeNowError"] = active_now_error
    return overview


def _check_build_problems(build_id: str, history: StudioBuildHistory, problems_store: StudioProblemsStore) -> dict:
    """Run a fresh `tsc` check for `build_id` and remember the result (R-480)."""
    root_dir = _resolve_build_dir(build_id, history)
    report = check_build_problems(root_dir)
    problems_store.set(build_id, report)
    return report


def _get_build_problems(build_id: str, history: StudioBuildHistory, problems_store: StudioProblemsStore) -> dict:
    """The last stored problems report for `build_id`, or `ProblemsNotCheckedError` (R-480)."""
    _resolve_build_dir(build_id, history)  # still 404 for an unknown build, not "not checked yet"
    report = problems_store.get(build_id)
    if report is None:
        raise ProblemsNotCheckedError(f"build '{build_id}' has not been checked for problems yet")
    return report


async def _edit(
    build_id: str,
    prompt: str,
    *,
    history: StudioBuildHistory,
    session_store: StudioSessionStore,
    provider_id: str | None = None,
    model_id: str | None = None,
    api_key: str | None = None,
    **extra_options,
) -> dict:
    """Apply one follow-up prompt to an existing build as a further commit on the same repo (R-468).

    Additive only: the model proposes new entities/apis/screens (`generate_app_delta_proposal`), which are
    merged onto the session's current IR (`apply_app_delta`), diffed against it (`plan_edit`, unmodified
    from R-237), and applied as one new commit (`commit_edit`, unmodified) -- or, if the delta produced no
    file changes, reported back with no commit. Never called for a Solution Pack or "all surfaces"
    Ecosystem build (`_build` only starts a session for the two single-IR build kinds).
    """
    entry = history.get(build_id)
    if entry is None:
        raise BuildNotFoundError(f"build '{build_id}' is not available in this session")
    if entry.get("pack_id") or entry.get("is_ecosystem"):
        raise EditNotSupportedError(
            "editing is not yet supported for Solution Pack builds or multi-surface Ecosystem builds"
        )
    session = session_store.get(build_id)
    if session is None:
        raise BuildNotFoundError(f"build '{build_id}' session has expired in this server session; rebuild to continue editing")

    # R-476: without usage_ledger, an edit's real cost was never recorded anywhere - the response
    # had no "usage" key at all, so the control-plane's Job API proxy would debit 0 credits for
    # every edit regardless of what it actually cost. Mirrors _build()'s own exact pattern.
    usage_ledger = UsageLedger()
    provider, eff_model_id, _max_output, timeout = resolve_generation_provider_from_env(
        usage_ledger=usage_ledger,
        provider_id=provider_id,
        model_id=model_id,
        api_key=api_key,
    )
    proposal = await generate_app_delta_proposal(session.ir, prompt, provider, model_id=eff_model_id, timeout_seconds=timeout)
    new_ir = apply_app_delta(session.ir, proposal)
    diff = plan_edit(session.ir, new_ir)

    if diff.is_empty():
        session_store.record_turn(build_id, "user", prompt)
        session_store.record_turn(build_id, "assistant", "No file changes were needed for that request.")
        return {
            "id": build_id,
            "diff": {"added": [], "modified": [], "deleted": [], "summary": diff.summary()},
            "entities": [entity.name for entity in session.ir.entities],
            "file_count": entry.get("file_count", 0),
            "commit_sha": entry.get("commit_sha", ""),
            "rationale": proposal.rationale,
            "turns": session_store.turns_view(build_id)["turns"],
            "usage": _usage_summary_to_dict(usage_ledger),
        }

    result = commit_edit(
        diff, session.target_dir, author_name=_AUTHOR_NAME, author_email=_AUTHOR_EMAIL,
        message=f"edit: {prompt.strip()[:72]}",
    )
    session_store.advance(build_id, new_ir)
    session_store.record_turn(build_id, "user", prompt)
    session_store.record_turn(build_id, "assistant", diff.summary())

    file_count = len(assemble_project(new_ir).files())
    entities = [entity.name for entity in new_ir.entities]
    history.update(build_id, {"file_count": file_count, "commit_sha": result.commit_sha, "entities": entities})

    return {
        "id": build_id,
        "diff": {
            "added": list(diff.added()),
            "modified": list(diff.modified()),
            "deleted": list(diff.deleted()),
            "summary": diff.summary(),
        },
        "entities": entities,
        "file_count": file_count,
        "commit_sha": result.commit_sha,
        "rationale": proposal.rationale,
        "usage": _usage_summary_to_dict(usage_ledger),
        "turns": session_store.turns_view(build_id)["turns"],
    }


def _open_path(path: str) -> bool:
    """Open a directory in the OS file browser, best-effort. Never raises; no command is echoed."""
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", path])
        elif sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]  # noqa: SIM115 (Windows-only)
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except OSError:
        return False


def _open_recorded_build(build_id: str, history: StudioBuildHistory) -> dict:
    entry = history.get(build_id)
    if entry is None or not entry.get("target_dir"):
        return {"status": "error", "message": "That build is no longer available in this session."}
    if _open_path(entry["target_dir"]):
        return {"status": "opened", "message": "Opened the generated project folder."}
    return {"status": "error", "message": "Could not open the project folder on this machine."}


def _workspace_build(
    ws_id: str,
    prompt: str,
    *,
    workspace_store: StudioWorkspaceStore,
    preview_manager: StudioPreviewManager | None = None,
    **options,
) -> dict:
    with workspace_store.lock(ws_id):
        workspace_store.ensure_workspace(ws_id)
        repo_dir = str(workspace_store.repo_path(ws_id))
        return _build(
            prompt,
            direct_target_dir=repo_dir,
            workspace_store=workspace_store,
            workspace_id=ws_id,
            preview_manager=preview_manager,
            **options,
        )


async def _workspace_build_stream(
    ws_id: str,
    prompt: str,
    *,
    workspace_store: StudioWorkspaceStore,
    preview_manager: StudioPreviewManager | None = None,
    **options,
) -> AsyncIterator[dict]:
    workspace_store.clear_cancelled(ws_id)
    with workspace_store.lock(ws_id):
        workspace_store.ensure_workspace(ws_id)
        repo_dir = str(workspace_store.repo_path(ws_id))
        async for event in _build_stream(
            prompt,
            direct_target_dir=repo_dir,
            workspace_store=workspace_store,
            workspace_id=ws_id,
            preview_manager=preview_manager,
            **options,
        ):
            yield event


async def _workspace_edit(
    ws_id: str,
    prompt: str,
    *,
    workspace_store: StudioWorkspaceStore,
    context: dict | None = None,
    provider_id: str | None = None,
    model_id: str | None = None,
    api_key: str | None = None,
    **options,
) -> dict:
    with workspace_store.lock(ws_id):
        ir = workspace_store.load_ir(ws_id)
        if ir is None:
            raise BuildNotFoundError(f"workspace '{ws_id}' not found or has no IR; build first")
        repo_dir = str(workspace_store.repo_path(ws_id))
        if not os.path.isdir(repo_dir):
            raise BuildNotFoundError(f"workspace '{ws_id}' repo directory does not exist")

        usage_ledger = UsageLedger()
        provider, eff_model_id, _max_output, timeout = resolve_generation_provider_from_env(
            usage_ledger=usage_ledger,
            provider_id=provider_id,
            model_id=model_id,
            api_key=api_key,
        )
        proposal = await generate_app_delta_proposal(
            ir, prompt, provider, model_id=eff_model_id, timeout_seconds=timeout, context=context
        )
        new_ir = apply_app_delta(ir, proposal)
        diff = plan_edit(ir, new_ir)

        trunc_note = " (Note: Context was truncated due to length limits.)" if proposal.context_truncated else ""
        if diff.is_empty():
            workspace_store.append_turn(ws_id, "user", prompt)
            workspace_store.append_turn(
                ws_id, "assistant", f"No file changes were needed for that request.{trunc_note}"
            )
            state = workspace_store.get_state(ws_id) or {}
            return {
                "id": ws_id,
                "diff": {"added": [], "modified": [], "deleted": [], "summary": diff.summary()},
                "entities": [entity.name for entity in ir.entities],
                "file_count": state.get("file_count", 0),
                "commit_sha": state.get("commit_sha", ""),
                "rationale": proposal.rationale,
                "context_truncated": proposal.context_truncated,
                "active_skills": list(proposal.active_skills),
                "truncated_skills": list(proposal.truncated_skills),
                "turns": workspace_store.get_turns(ws_id),
                "usage": _usage_summary_to_dict(usage_ledger),
            }

        result = commit_edit(
            diff, repo_dir, author_name=_AUTHOR_NAME, author_email=_AUTHOR_EMAIL,
            message=f"edit: {prompt.strip()[:72]}",
        )
        workspace_store.save_ir(ws_id, new_ir)
        workspace_store.append_turn(ws_id, "user", prompt)
        workspace_store.append_turn(ws_id, "assistant", f"{diff.summary()}{trunc_note}")

        file_count = len(assemble_project(new_ir).files())
        state = workspace_store.get_state(ws_id) or {}
        state["file_count"] = file_count
        state["commit_sha"] = result.commit_sha
        state["entities"] = [entity.name for entity in new_ir.entities]
        workspace_store.save_state(ws_id, state)

        return {
            "id": ws_id,
            "commit_sha": result.commit_sha,
            "entities": [entity.name for entity in new_ir.entities],
            "file_count": file_count,
            "diff": {
                "added": list(diff.added_files.keys()),
                "modified": list(diff.modified_files.keys()),
                "deleted": list(diff.deleted_files),
                "summary": diff.summary(),
            },
            "rationale": proposal.rationale,
            "context_truncated": proposal.context_truncated,
            "active_skills": list(proposal.active_skills),
            "truncated_skills": list(proposal.truncated_skills),
            "turns": workspace_store.get_turns(ws_id),
            "usage": _usage_summary_to_dict(usage_ledger),
        }


def _preview_enabled() -> bool:
    return os.environ.get("OMNISTACKAI_STUDIO_LIVE_PREVIEW", "0").strip().lower() in {
        "1", "true", "yes", "on"
    }


def main() -> None:
    host = os.environ.get("OMNISTACKAI_STUDIO_HOST", "127.0.0.1")
    port = int(os.environ.get("OMNISTACKAI_STUDIO_PORT", "4173"))
    preview_manager = StudioPreviewManager() if _preview_enabled() else None
    history = StudioBuildHistory()
    session_store = StudioSessionStore()
    problems_store = StudioProblemsStore()
    workspace_store = StudioWorkspaceStore()

    def build(prompt: str, **options) -> dict:
        return _build(prompt, preview_manager=preview_manager, history=history, session_store=session_store, **options)

    def delete_build(build_id: str) -> dict:
        removed = history.remove(build_id)
        return {"removed": removed, **history.list()}

    def edit_build(build_id: str, prompt: str, **options) -> dict:
        return asyncio.run(_edit(build_id, prompt, history=history, session_store=session_store, **options))

    def workspace_build(ws_id: str, prompt: str, **options) -> dict:
        return _workspace_build(ws_id, prompt, workspace_store=workspace_store, preview_manager=preview_manager, **options)

    def workspace_build_stream(ws_id: str, prompt: str, **options) -> AsyncIterator[dict]:
        return _workspace_build_stream(ws_id, prompt, workspace_store=workspace_store, preview_manager=preview_manager, **options)

    def workspace_edit(ws_id: str, prompt: str, **options) -> dict:
        return asyncio.run(_workspace_edit(ws_id, prompt, workspace_store=workspace_store, **options))

    def workspace_preview(
        ws_id: str,
        on_phase: Callable[[str], None] | None = None,
        env: Mapping[str, str] | None = None,
    ) -> dict:
        if preview_manager is None:
            return {
                "status": "disabled",
                "message": "This server runs in build-only mode. Restart it with ./scripts/omnistack.sh up to run your app.",
            }
        repo_dir = str(workspace_store.repo_path(ws_id))
        if not os.path.isdir(repo_dir):
            raise BuildNotFoundError(f"workspace '{ws_id}' has no repo to preview")
        return preview_manager.start_workspace(ws_id, repo_dir, on_phase=on_phase, env=env)

    def workspace_preview_status(ws_id: str) -> dict:
        if preview_manager is None:
            return {
                "status": "disabled",
                "message": "This server runs in build-only mode. Restart it with ./scripts/omnistack.sh up to run your app.",
            }
        return preview_manager.workspace_status(ws_id)

    def workspace_preview_stop(ws_id: str) -> dict:
        if preview_manager is None:
            return {
                "status": "disabled",
                "message": "This server runs in build-only mode. Restart it with ./scripts/omnistack.sh up to run your app.",
            }
        return preview_manager.stop_workspace(ws_id)

    def workspace_problems_check(ws_id: str) -> dict:
        repo_dir = str(workspace_store.repo_path(ws_id))
        if not os.path.isdir(repo_dir):
            raise BuildNotFoundError(f"workspace '{ws_id}' has no repo")
        report = check_build_problems(repo_dir)
        problems_store.set(ws_id, report)
        return report

    def workspace_problems_get(ws_id: str) -> dict:
        repo_dir = str(workspace_store.repo_path(ws_id))
        if not os.path.isdir(repo_dir):
            raise BuildNotFoundError(f"workspace '{ws_id}' has no repo")
        report = problems_store.get(ws_id)
        if report is None:
            raise ProblemsNotCheckedError(f"workspace '{ws_id}' has not been checked for problems yet")
        return report

    from .logs import StudioLogManager
    log_manager = StudioLogManager()

    def workspace_cancel(ws_id: str) -> dict:
        workspace_store.set_cancelled(ws_id)
        return {"status": "cancelling", "workspace_id": ws_id}

    def workspace_logs(ws_id: str, source: str = "build", since: int | None = None, limit: int = 500) -> dict:
        return log_manager.read_logs(ws_id, source=source, since=since, limit=limit)

    def workspace_logs_stream(ws_id: str, source: str = "build", since: int | None = None) -> AsyncIterator[dict]:
        return log_manager.stream_logs(ws_id, source=source, since=since)

    def workspace_logs_clear(ws_id: str, source: str | None = None) -> dict:
        return log_manager.clear_logs(ws_id, source=source)

    control_kwargs: dict = {
        "history_fn": history.list,
        "delete_build_fn": delete_build,
        # R-467/R-468: file browsing and editing need no toolchain or running preview -- wired in
        # build-only mode too.
        "file_tree_fn": lambda build_id: _list_build_files(build_id, history),
        "read_file_fn": lambda build_id, path: _read_build_file(build_id, path, history),
        "edit_fn": edit_build,
        # R-480: checking/reading problems needs the build's own installed node_modules/tsc (from a
        # prior live-preview install), but not a *currently running* preview -- wired in build-only
        # mode too, same reasoning as file browsing and editing above.
        "problems_check_fn": lambda build_id: _check_build_problems(build_id, history, problems_store),
        "problems_get_fn": lambda build_id: _get_build_problems(build_id, history, problems_store),
        # R-482: needs only env vars + one optional lightweight local ping, never a toolchain or
        # running preview - wired in build-only mode too, same reasoning as the routes above.
        "providers_fn": _provider_status,
        # R-484: a plain-prompt, non-hybrid_ui build only needs the same model + disk access every
        # other build-only-mode route above already has - wired unconditionally, not gated behind
        # preview_manager.
        "build_stream_fn": lambda prompt: _build_stream(
            prompt, history=history, session_store=session_store, preview_manager=preview_manager
        ),
        "turns_fn": lambda build_id: _turns(build_id, session_store),
        # F-01 / R-499: Persistent workspace capabilities
        "workspace_store": workspace_store,
        "workspace_build_fn": workspace_build,
        "workspace_build_stream_fn": workspace_build_stream,
        "workspace_edit_fn": workspace_edit,
        "workspace_preview_fn": workspace_preview,
        "workspace_preview_status_fn": workspace_preview_status,
        "workspace_preview_stop_fn": workspace_preview_stop,
        "workspace_problems_check_fn": workspace_problems_check,
        "workspace_problems_get_fn": workspace_problems_get,
        "workspace_cancel_fn": workspace_cancel,
        "workspace_logs_fn": workspace_logs,
        "workspace_logs_stream_fn": workspace_logs_stream,
        "workspace_logs_clear_fn": workspace_logs_clear,
    }
    if preview_manager is not None:
        control_kwargs.update(
            status_fn=preview_manager.status,
            stop_fn=preview_manager.stop,
            restart_fn=preview_manager.restart,
            switch_surface_fn=preview_manager.switch_surface,
            get_ecosystem_auth_fn=preview_manager.get_ecosystem_auth,
            get_ecosystem_state_fn=preview_manager.get_ecosystem_state,
            get_ecosystem_events_fn=preview_manager.get_ecosystem_events,
            dispatch_ecosystem_event_fn=preview_manager.dispatch_ecosystem_event,
            get_ecosystem_telemetry_fn=preview_manager.get_ecosystem_telemetry,
            get_ecosystem_deployment_fn=preview_manager.get_ecosystem_deployment,
            to_compose_yaml_fn=preview_manager.to_compose_yaml,
            get_ecosystem_sync_fn=preview_manager.get_ecosystem_sync,
            push_sync_mutations_fn=preview_manager.push_sync_mutations,
            pull_sync_changes_fn=preview_manager.pull_sync_changes,
            simulate_sync_conflict_fn=preview_manager.simulate_sync_conflict,
            get_ecosystem_cicd_fn=preview_manager.get_ecosystem_cicd,
            to_workflow_yaml_fn=preview_manager.to_workflow_yaml,
            simulate_cicd_run_fn=preview_manager.simulate_cicd_run,
            get_ecosystem_verification_fn=preview_manager.get_ecosystem_verification,
            simulate_ecosystem_verification_fn=preview_manager.simulate_ecosystem_verification,
            get_ecosystem_recovery_fn=preview_manager.get_ecosystem_recovery,
            simulate_ecosystem_recovery_fn=preview_manager.simulate_ecosystem_recovery,
            get_ecosystem_capacity_fn=preview_manager.get_ecosystem_capacity,
            simulate_ecosystem_capacity_fn=preview_manager.simulate_ecosystem_capacity,
            get_ecosystem_alerting_fn=preview_manager.get_ecosystem_alerting,
            simulate_ecosystem_alerting_fn=preview_manager.simulate_ecosystem_alerting,
            get_ecosystem_sla_fn=preview_manager.get_ecosystem_sla,
            simulate_ecosystem_sla_fn=preview_manager.simulate_ecosystem_sla,
            get_ecosystem_governance_fn=preview_manager.get_ecosystem_governance,
            simulate_ecosystem_governance_fn=preview_manager.simulate_ecosystem_governance,
            get_ecosystem_docs_fn=preview_manager.get_ecosystem_docs,
            export_ecosystem_docs_fn=preview_manager.export_ecosystem_docs,
            preview_build_fn=lambda build_id, surface_slug=None: _preview_recorded_build(
                build_id, history, preview_manager, surface_slug=surface_slug
            ),
            open_dir_fn=lambda build_id: _open_recorded_build(build_id, history),
        )

    server = create_studio_server(build, host=host, port=port, **control_kwargs)
    print(f"OmniStackAI Studio -> http://{host}:{port}")
    if preview_manager is None:
        print("Build-only mode: generated code is not executed.")
    else:
        print("Trusted-local preview mode: generated code will run on this machine.")
    print("Type an app description and click Build. Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping studio.")
    finally:
        server.server_close()
        if preview_manager is not None:
            preview_manager.stop()


if __name__ == "__main__":
    main()
