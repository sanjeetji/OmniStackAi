"""Explicit local-Ollama proof for R-432 ecosystem refinement.

This module is never imported or executed by ``task verify``. It uses the existing loopback-only
``ModelProvider`` adapter and prints parsed, bounded data only (never raw model text or environment values).
"""

from __future__ import annotations

import asyncio
import json
import sys

from ..model_gateway.ollama import OLLAMA_PROVIDER_ID
from ..model_gateway.errors import ModelProviderError
from ._ollama import build_ollama_provider_from_env
from .errors import IntakeError
from .scope_refinement import plan_refined_ecosystem, refine_ecosystem

_DEFAULT_PROMPT = "Build a pet boarding marketplace connecting owners with trusted caregivers"


async def _run(prompt: str) -> None:
    provider, model_id, max_output, request_timeout = build_ollama_provider_from_env()
    result = await refine_ecosystem(
        prompt,
        provider,
        model_id=model_id,
        max_output_tokens=max_output,
        timeout_seconds=request_timeout,
    )
    plan = plan_refined_ecosystem(result)
    print(f"Source: {result.source}")
    if result.source == "model":
        print(f"Model:  {OLLAMA_PROVIDER_ID}/{model_id}")
    print("--- Tailored ecosystem ---")
    print(
        json.dumps(
            {"refinement": result.to_dict(), "plan": plan.to_dict()},
            indent=2,
            sort_keys=True,
        )
    )


def main() -> None:
    prompt = " ".join(sys.argv[1:]).strip() or _DEFAULT_PROMPT
    try:
        asyncio.run(_run(prompt))
    except (IntakeError, ModelProviderError) as error:
        raise SystemExit(
            f"Ecosystem refinement failed: {error}\n"
            "No fallback was presented as refined. Check local Ollama or use a clearer description."
        ) from error


if __name__ == "__main__":
    main()
