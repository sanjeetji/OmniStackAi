"""Opt-in live studio: serve the chat-to-create UI backed by the local Ollama build path.

Excluded from static verification. Start it with:

    task agent-engine:studio:serve

then open http://127.0.0.1:4173, type a description, and click Build. Each request compiles
the description into an Application IR and materializes a real owned Git repo on disk. The
output directory comes from OMNISTACKAI_APP_OUT_DIR (a per-build subfolder) or a temp dir.
Requires a running local Ollama; no secrets, no cloud.
"""

from __future__ import annotations

import asyncio
import os
import re
import tempfile

from ..intake._ollama import build_ollama_provider_from_env
from ..intake.build_app import app_build_result_to_dict, build_app_from_prompt
from .server import create_studio_server

_AUTHOR_NAME = "sanjeetji"
_AUTHOR_EMAIL = "sk698166@gmail.com"


def _target_dir_for(prompt: str) -> str:
    base = os.environ.get("OMNISTACKAI_APP_OUT_DIR")
    slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower()).strip("-")[:40] or "app"
    if base:
        return os.path.join(base, slug)
    return os.path.join(tempfile.mkdtemp(prefix="omnistackai-studio-"), slug)


def _build(prompt: str) -> dict:
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
    return app_build_result_to_dict(result)


def main() -> None:
    host = os.environ.get("OMNISTACKAI_STUDIO_HOST", "127.0.0.1")
    port = int(os.environ.get("OMNISTACKAI_STUDIO_PORT", "4173"))
    server = create_studio_server(_build, host=host, port=port)
    print(f"OmniStackAI Studio -> http://{host}:{port}")
    print("Type an app description and click Build. Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping studio.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
