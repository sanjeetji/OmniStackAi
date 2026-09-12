"""Opt-in live builder: compile a description into a real owned Git repo via local Ollama.

Excluded from static repository verification. Usage (via the Task wrapper):

    task agent-engine:app:build -- "Build a task tracker with projects and tasks"

The output directory comes from OMNISTACKAI_APP_OUT_DIR, or a fresh temp dir. Requires a
running local Ollama; no secrets, no cloud.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

from ..model_gateway.ollama import OLLAMA_PROVIDER_ID
from ._ollama import build_ollama_provider_from_env
from .build_app import build_app_from_prompt
from .errors import IntakeError

_DEFAULT_PROMPT = "Build a simple blog with posts and comments."
_AUTHOR_NAME = "sanjeetji"
_AUTHOR_EMAIL = "sk698166@gmail.com"


async def _run(target_dir: str, prompt: str) -> None:
    provider, model_id, max_output, request_timeout = build_ollama_provider_from_env()
    print(f"Prompt: {prompt}")
    print(f"Model:  {OLLAMA_PROVIDER_ID}/{model_id}")
    print("Compiling description -> Application IR -> owned Git repo ...")
    result = await build_app_from_prompt(
        prompt,
        provider,
        target_dir,
        model_id=model_id,
        author_name=_AUTHOR_NAME,
        author_email=_AUTHOR_EMAIL,
        max_output_tokens=max_output,
        timeout_seconds=request_timeout,
        overwrite=True,
    )
    print(f"\nApp:          {result.ir.name}")
    print(f"Description:  {result.ir.description}")
    print(f"Entities:     {', '.join(e.name for e in result.ir.entities) or '(none)'}")
    print(f"Generated {result.file_count} files into an owned Git repo at:\n  {result.target_dir}")
    print(f"First commit: {result.commit_sha[:12]}  (author: {_AUTHOR_NAME})")
    root = Path(result.target_dir)
    print("\n--- File tree ---")
    for path in sorted(
        p for p in root.rglob("*") if p.is_file() and ".git/" not in str(p.relative_to(root))
    ):
        print(f"  {path.relative_to(root)}")
    print(f"\nOpen the repo:  cd {result.target_dir} && git log --stat")


def main() -> None:
    target_dir = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else tempfile.mkdtemp(
        prefix="omnistackai-app-"
    )
    prompt = " ".join(sys.argv[2:]).strip() or _DEFAULT_PROMPT
    try:
        asyncio.run(_run(target_dir, prompt))
    except IntakeError as error:
        raise SystemExit(
            f"Build failed: {error}\n"
            "The local model did not return a valid Application IR. Try a clearer, more specific "
            "description, or a stronger local model (OMNISTACKAI_OLLAMA_MODEL)."
        ) from error


if __name__ == "__main__":
    main()
