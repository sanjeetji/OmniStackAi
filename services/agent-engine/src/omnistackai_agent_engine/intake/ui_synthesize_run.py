"""Opt-in live HYBRID build: prompt -> IR -> owned Git repo whose UI is LLM-synthesized (R-465).

The hybrid engine: the model writes every page over the deterministic, typed data layer (real generated
hooks/types/api + design tokens), with a bounded validation->feedback->retry loop and a deterministic
template fallback per file. Excluded from static repository verification (`task verify` never runs this).

    task agent-engine:ui:synthesize -- "Create a food delivery app with restaurants and couriers"

The provider comes from OMNISTACKAI_CLOUD_PROVIDER (e.g. groq / google; a paid, per-generation model) with
local-Ollama fallback; the output directory from OMNISTACKAI_APP_OUT_DIR, or a fresh temp dir. No secrets
are printed.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile

from ..codegen import UiSynthesisOutcome
from ..model_gateway.errors import ModelProviderError
from .build_app import build_app_from_ir
from .errors import IntakeError
from .nl_to_ir import generate_ir
from .provider_resolution import resolve_generation_provider_from_env

_MAX_ERROR_CHARS = 400

_DEFAULT_PROMPT = "Create a food delivery app where customers order from restaurants and couriers deliver"
_AUTHOR_NAME = "sanjeetji"
_AUTHOR_EMAIL = "sk698166@gmail.com"


def _print_outcomes(outcomes: list[UiSynthesisOutcome]) -> None:
    print("\n--- UI synthesis outcomes (per file) ---")
    print(f"  {'path':<34} {'mode':<14} {'attempts':<9} {'model':<28} last_reason")
    for outcome in outcomes:
        print(
            f"  {outcome.path:<34} {outcome.mode:<14} {outcome.attempts:<9} "
            f"{outcome.model_id[:27]:<28} {outcome.last_reason[:60]}"
        )
    synthesized = sum(1 for o in outcomes if o.mode == "llm")
    print(f"  => {synthesized}/{len(outcomes)} files written by the model; the rest fell back to templates.")


def main() -> None:
    target_dir = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else tempfile.mkdtemp(prefix="omnistackai-hybrid-")
    prompt = " ".join(sys.argv[2:]).strip() or _DEFAULT_PROMPT

    provider, model_id, max_output, request_timeout = resolve_generation_provider_from_env()
    provider_name = getattr(provider, "provider_id", "provider")
    print(f"Prompt: {prompt}")
    print(f"Model:  {provider_name}/{model_id}")
    if provider_name == "ollama":
        print(
            "WARNING: local Ollama selected. The grounded UI prompt plus the repair transcript can exceed the "
            "local context window; for the hybrid engine set OMNISTACKAI_CLOUD_PROVIDER=groq (or google)."
        )

    print("Step 1/2: compiling the description into an Application IR ...")
    try:
        intake = asyncio.run(
            generate_ir(
                prompt,
                provider,
                model_id=model_id,
                max_output_tokens=max_output,
                timeout_seconds=request_timeout,
            )
        )
    except IntakeError as error:
        raise SystemExit(
            f"Intake failed: {error}\n"
            "The model did not return a valid Application IR. Try a clearer, more specific description."
        ) from error
    except ModelProviderError as error:
        # Provider/transport failures (HTTP 429 rate limits, timeouts, ...) exit cleanly — no traceback.
        detail = str(error)[:_MAX_ERROR_CHARS]
        raise SystemExit(
            f"Model provider error during intake ({type(error).__name__}): {detail}\n"
            "If this is a rate limit (HTTP 429), your provider tier's tokens-per-minute budget is smaller than the "
            "grounded prompts need: wait a minute, pick a model your account lists with a larger limit "
            "(OMNISTACKAI_GROQ_MODEL=...), switch provider (OMNISTACKAI_CLOUD_PROVIDER=google with GOOGLE_API_KEY), "
            "or upgrade the provider tier."
        ) from error

    print("Step 2/2: synthesizing the UI with the model over the deterministic data layer (repair loop on) ...")
    outcomes: list[UiSynthesisOutcome] = []
    result = build_app_from_ir(
        intake.ir,
        target_dir,
        author_name=_AUTHOR_NAME,
        author_email=_AUTHOR_EMAIL,
        prompt=prompt,
        overwrite=True,
        provider=provider,
        model_id=model_id,
        synthesize_screens=True,
        ui_outcomes=outcomes,
    )

    print(f"\nApp:          {result.ir.name}")
    print(f"Entities:     {', '.join(e.name for e in result.ir.entities) or '(none)'}")
    print(f"Generated {result.file_count} files into an owned Git repo at:\n  {result.target_dir}")
    print(f"First commit: {result.commit_sha[:12]}  (author: {_AUTHOR_NAME})")
    _print_outcomes(outcomes)
    print(f"\nTypecheck it:  cd {result.target_dir}/apps/web && pnpm install --ignore-scripts && ./node_modules/.bin/tsc --noEmit")


if __name__ == "__main__":
    main()
