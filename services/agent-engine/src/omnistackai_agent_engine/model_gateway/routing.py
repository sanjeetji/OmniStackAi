"""PC-126: which model does which job, in what order, and which are out right now.

    scripts/models.sh            # the routing, from .env and the shared provider health
    scripts/models.sh --clear    # forget every mark (after adding credit, or a new key)

Jobs and where their order comes from:

* **plan** (the product plan, chat edits) - a paid key the owner has set first (Anthropic, OpenAI,
  DeepSeek, xAI, Mistral - PC-127), then ``OMNISTACKAI_CLOUD_PROVIDER``, then
  ``OMNISTACKAI_FALLBACK_PROVIDERS``, ranked by the model scorecard (PC-085) when one exists;
  ``OMNISTACKAI_PREFER_LOCAL=1`` keeps every call on this machine;
* **pages** (designing pages, and repairing them) - ``OMNISTACKAI_PAGE_CHAIN``, or the default:
  a paid key when its owner has added one (Anthropic, OpenAI), then the free tiers, then Ollama.

A provider without a key is never called and never billed. Never prints a key.
"""

from __future__ import annotations

import os
import sys

from . import health


def _configured(provider: str) -> bool:
    if provider in ("ollama", "local"):
        return True
    from ..intake.provider_resolution import resolve_provider_specs

    spec = resolve_provider_specs().get(provider)
    return bool(spec and os.environ.get(spec.key_env, "").strip())


def _model(provider: str, model: str | None) -> str:
    if model:
        return model
    if provider in ("ollama", "local"):
        return os.environ.get("OMNISTACKAI_OLLAMA_MODEL", "") or "(Ollama default)"
    from ..intake.provider_resolution import resolve_provider_specs

    spec = resolve_provider_specs().get(provider)
    return (os.environ.get(spec.model_env, "") or spec.default_model) if spec else ""


def plan_chain() -> list[tuple[str, str]]:
    if (os.environ.get("OMNISTACKAI_PREFER_LOCAL", "") or "").strip().lower() in ("1", "true", "yes"):
        return [("ollama", _model("ollama", None))]
    from ..intake.provider_resolution import paid_lead

    names = [paid_lead() or "", (os.environ.get("OMNISTACKAI_CLOUD_PROVIDER", "") or "").strip().lower()]
    names += [n.strip().lower() for n in (os.environ.get("OMNISTACKAI_FALLBACK_PROVIDERS", "") or "").split(",")]
    chain: list[tuple[str, str]] = []
    for name in names:
        name = "google" if name == "gemini" else name
        if name and name != "none" and name not in [p for p, _ in chain] and _configured(name):
            chain.append((name, _model(name, None)))
    if not any(p in ("ollama", "local") for p, _ in chain):
        chain.append(("ollama", _model("ollama", None)))  # the platform's own last resort
    return chain


def page_chain() -> list[tuple[str, str]]:
    from ..intake.provider_resolution import page_chain_spec

    return [(p, _model(p, m)) for p, m in page_chain_spec() if _configured(p)]


def report() -> str:
    marks = health.snapshot()
    lines = []
    for job, chain in (("Plans and chat edits", plan_chain()), ("Page design and repair", page_chain())):
        lines.append(f"{job}:")
        for position, (provider, model) in enumerate(chain, 1):
            mark = marks.get("google" if provider == "google" else provider)
            state = ""
            if mark:
                minutes = max(1, round(mark["back_in_seconds"] / 60))
                state = f"  - out ({mark['state'].replace('_', ' ')}), back in about {minutes} min"
            lines.append(f"  {position}. {provider} {model}{state}")
    if not health._path():
        lines.append("(provider health is not remembered in this shell; the Studio and the benchmark remember it)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    from ..intake.provider_resolution import _load_dotenv_if_needed

    _load_dotenv_if_needed()
    os.environ.setdefault(health.PATH_ENV, str(health.DEFAULT_FILE))
    args = argv if argv is not None else sys.argv[1:]
    if "--clear" in args:
        path = health._path()
        if path and path.exists():
            path.unlink()
        print("Every provider is marked available again.")
        return 0
    print(report())
    return 0


if __name__ == "__main__":
    sys.exit(main())
