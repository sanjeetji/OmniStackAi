"""Opt-in live studio: serve the chat-to-create UI backed by the local Ollama build path.

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

from ..intake._ollama import build_ollama_provider_from_env
from ..intake.build_app import app_build_result_to_dict, build_app_from_prompt
from .history import StudioBuildHistory
from .preview import StudioPreviewManager
from .server import create_studio_server

_AUTHOR_NAME = "sanjeetji"
_AUTHOR_EMAIL = "sk698166@gmail.com"


def _target_dir_for(prompt: str) -> str:
    base = os.environ.get("OMNISTACKAI_APP_OUT_DIR")
    slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower()).strip("-")[:40] or "app"
    if base:
        return os.path.join(base, slug)
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
    preview_manager: StudioPreviewManager | None = None,
    history: StudioBuildHistory | None = None,
) -> dict:
    if ecosystem_id:
        from pathlib import Path
        from ..solution_packs import DEFAULT_ECOSYSTEM_PACK_REGISTRY
        from ..intake.build_app import build_app_from_ir

        eco_pack = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get(ecosystem_id, version=ecosystem_version)
        if eco_pack is None:
            raise ValueError(f"Unknown Ecosystem Pack '{ecosystem_id}'")
        eco_pkg = eco_pack.to_package()

        target_dir = _target_dir_for(prompt)

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

            build_res = build_app_from_ir(
                surface_ir,
                target_dir,
                author_name=_AUTHOR_NAME,
                author_email=_AUTHOR_EMAIL,
                prompt=prompt,
                overwrite=True,
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
            }
        else:
            os.makedirs(target_dir, exist_ok=True)
            surface_results = []
            total_files = 0
            all_entities = set()
            used_slugs: dict[str, int] = {}

            for surface in eco_pkg.surfaces:
                surface_ir = surface.to_application_ir()
                for e in surface_ir.entities:
                    all_entities.add(e.name)
                base_slug = surface.slug
                count = used_slugs.get(base_slug, 0)
                used_slugs[base_slug] = count + 1
                unique_slug = base_slug if count == 0 else f"{base_slug}-{count + 1}"
                surface_target_dir = os.path.join(target_dir, unique_slug)

                build_res = build_app_from_ir(
                    surface_ir,
                    surface_target_dir,
                    author_name=_AUTHOR_NAME,
                    author_email=_AUTHOR_EMAIL,
                    prompt=prompt,
                    overwrite=True,
                )
                total_files += build_res.file_count
                surface_results.append({
                    "surface_kind": surface.surface_kind,
                    "app_name": surface.app_name,
                    "slug": surface.slug,
                    "target_dir": surface_target_dir,
                    "file_count": build_res.file_count,
                    "commit_sha": build_res.commit_sha,
                    "verify_targets": list(surface.verify_targets),
                    "ir_sha256": surface.ir_sha256,
                })

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

        has_ai_deltas = any(c.source is ChangeSource.AI_DELTA for c in manifest.changes)
        proposal = None
        if has_ai_deltas:
            from ..solution_packs.ai_delta import generate_ai_delta_proposal

            if ai_delta_provider is not None:
                provider = ai_delta_provider
                model_id = None
            else:
                provider, model_id, _, _ = build_ollama_provider_from_env()

            base_ir = DEFAULT_SOLUTION_PACK_REGISTRY.load_ir(pack.pack_id, pack.version)
            maybe_coro = generate_ai_delta_proposal(
                manifest,
                base_ir,
                provider,
                model_id=model_id,
            )
            if asyncio.iscoroutine(maybe_coro):
                proposal = asyncio.run(maybe_coro)
            else:
                proposal = maybe_coro

        app_result = apply_solution_pack_manifest(manifest, proposal=proposal)
        target_dir = _target_dir_for(prompt)
        build_result = build_solution_pack_project(
            app_result,
            target_dir,
            author_name=_AUTHOR_NAME,
            author_email=_AUTHOR_EMAIL,
            overwrite=True,
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
        }
    else:
        provider, model_id, max_output, request_timeout = build_ollama_provider_from_env()
        result = asyncio.run(
            build_app_from_prompt(
                prompt,
                provider,
                _target_dir_for(prompt),
                model_id=model_id,
                author_name=_AUTHOR_NAME,
                author_email=_AUTHOR_EMAIL,
                max_output_tokens=max_output,
                timeout_seconds=request_timeout,
                overwrite=True,
            )
        )
        payload = app_build_result_to_dict(result)

    if history is not None:
        payload["id"] = history.record(payload)
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


def _preview_enabled() -> bool:
    return os.environ.get("OMNISTACKAI_STUDIO_LIVE_PREVIEW", "0").strip().lower() in {
        "1", "true", "yes", "on"
    }


def main() -> None:
    host = os.environ.get("OMNISTACKAI_STUDIO_HOST", "127.0.0.1")
    port = int(os.environ.get("OMNISTACKAI_STUDIO_PORT", "4173"))
    preview_manager = StudioPreviewManager() if _preview_enabled() else None
    history = StudioBuildHistory()

    def build(prompt: str, **options) -> dict:
        return _build(prompt, preview_manager=preview_manager, history=history, **options)

    def delete_build(build_id: str) -> dict:
        removed = history.remove(build_id)
        return {"removed": removed, **history.list()}

    control_kwargs: dict = {"history_fn": history.list, "delete_build_fn": delete_build}
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
