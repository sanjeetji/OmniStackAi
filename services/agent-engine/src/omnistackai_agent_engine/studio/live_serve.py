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
    preview_manager: StudioPreviewManager | None = None,
    history: StudioBuildHistory | None = None,
) -> dict:
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
        payload["preview"] = preview_manager.replace(result.target_dir)
    return payload


def _preview_recorded_build(
    build_id: str, history: StudioBuildHistory, preview_manager: StudioPreviewManager
) -> dict:
    entry = history.get(build_id)
    if entry is None or not entry.get("target_dir"):
        return {"status": "error", "message": "That build is no longer available in this session."}
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

    def build(prompt: str) -> dict:
        return _build(prompt, preview_manager=preview_manager, history=history)

    def delete_build(build_id: str) -> dict:
        removed = history.remove(build_id)
        return {"removed": removed, **history.list()}

    control_kwargs: dict = {"history_fn": history.list, "delete_build_fn": delete_build}
    if preview_manager is not None:
        control_kwargs.update(
            status_fn=preview_manager.status,
            stop_fn=preview_manager.stop,
            restart_fn=preview_manager.restart,
            preview_build_fn=lambda build_id: _preview_recorded_build(
                build_id, history, preview_manager
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
