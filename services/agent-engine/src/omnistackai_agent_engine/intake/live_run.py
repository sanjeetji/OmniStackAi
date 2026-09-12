"""Opt-in live intake proof: compile a prompt into an Application IR via local Ollama.

Excluded from static repository verification (`task verify` never imports/runs this).
Run it with a real local Ollama model:

    task agent-engine:intake:run -- "Build a simple blog with posts and comments"

It builds an Ollama provider from the OMNISTACKAI_OLLAMA_* environment, compiles the
description into a validated IR, and prints the IR JSON. No secrets, no cloud; requires
a running local Ollama.
"""

from __future__ import annotations

import asyncio
import json
import sys

from ..model_gateway.ollama import OLLAMA_PROVIDER_ID
from ._ollama import build_ollama_provider_from_env
from .errors import IntakeError
from .nl_to_ir import generate_ir

_DEFAULT_PROMPT = "Build a simple blog with posts and comments."


async def _run(prompt: str) -> None:
    provider, model_id, max_output, request_timeout = build_ollama_provider_from_env()
    result = await generate_ir(
        prompt,
        provider,
        model_id=model_id,
        max_output_tokens=max_output,
        timeout_seconds=request_timeout,
    )
    print(f"Prompt: {prompt}")
    print(f"Model:  {OLLAMA_PROVIDER_ID}/{model_id}")
    print("--- Application IR ---")
    print(json.dumps(result.ir.to_dict(), indent=2, sort_keys=True))
    if result.issues:
        print("--- Warnings ---")
        for issue in result.issues:
            print(f"  [{issue.severity}] {issue.location}: {issue.message}")


def main() -> None:
    prompt = " ".join(sys.argv[1:]).strip() or _DEFAULT_PROMPT
    try:
        asyncio.run(_run(prompt))
    except IntakeError as error:
        raise SystemExit(
            f"Intake failed: {error}\n"
            "The local model did not return a valid Application IR. Try a clearer, more specific "
            "description, or a stronger local model (OMNISTACKAI_OLLAMA_MODEL)."
        ) from error


if __name__ == "__main__":
    main()
