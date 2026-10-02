"""Dynamic model provider resolution for intake and code generation.

Resolves the active ModelProvider from environment configuration:
- If OMNISTACKAI_CLOUD_PROVIDER is set to a supported cloud provider (e.g. 'groq', 'openai',
  'anthropic') and its API key is present, returns that cloud provider for high-speed,
  cloud-scale inference.
- Otherwise, cleanly falls back to local Ollama (OMNISTACKAI_OLLAMA_MODEL) for zero-cost,
  fully-local offline execution.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from ..model_gateway.accounting import UsageLedger
from ..model_gateway.bootstrap import _cloud_descriptor, build_gateway_from_env
from ..model_gateway.cloud import create_cloud_provider, resolve_provider_specs
from ..model_gateway.contracts import ModelProvider
from ..model_gateway.recording import RecordingProvider
from ._ollama import build_ollama_provider_from_env

logger = logging.getLogger(__name__)


def _load_dotenv_if_needed() -> None:
    """Load key-value pairs from .env into os.environ if not already set."""
    curr = Path(__file__).resolve().parent
    for _ in range(6):
        env_file = curr / ".env"
        if env_file.is_file():
            try:
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k and k not in os.environ:
                        os.environ[k] = v
            except Exception:
                pass
            break
        curr = curr.parent


def prefers_local() -> bool:
    """OMNISTACKAI_PREFER_LOCAL: build on the local model (PC-014: plan, repair and pages alike)."""
    return os.environ.get("OMNISTACKAI_PREFER_LOCAL", "").strip().lower() in ("1", "true", "yes")


def is_ollama_ready(base_url: str | None = None, *, timeout: float = 1.5) -> bool:
    """Check if local Ollama daemon is reachable and responding."""
    import urllib.request
    url = (base_url or os.environ.get("OMNISTACKAI_OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
    try:
        req = urllib.request.Request(f"{url}/api/tags", headers={"User-Agent": "omnistackai"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def ollama_ready_patiently(tries: int = 3, timeout: float = 5.0) -> bool:
    """PC-014, found live: with local preferred, one 1.5 s check that lost a race sent a build's
    pages to the cloud. When the person asked for local, Ollama gets a few patient tries first."""
    import time as _time

    for attempt in range(tries):
        if is_ollama_ready(timeout=timeout):
            return True
        if attempt < tries - 1:
            _time.sleep(1.0)
    return False


def resolve_generation_provider_from_env(
    *,
    load_dotenv: bool = True,
    prefer_local: bool | None = None,
    usage_ledger: UsageLedger | None = None,
    provider_id: str | None = None,
    model_id: str | None = None,
    api_key: str | None = None,
    task: str = "plan",
    max_output_tokens: int | None = None,
) -> tuple[ModelProvider, str, int, float]:
    """Resolve (provider, model_id, max_output_tokens, request_timeout_seconds).

    ``max_output_tokens`` (PC-098) replaces the output budget of an explicitly named cloud provider,
    for a job whose answers are longer than a plan's (a whole page).

    Smart dual-engine routing:
    - If explicit provider_id is passed, uses that provider with optional model_id and api_key.
    - If prefer_local is explicitly True or OMNISTACKAI_PREFER_LOCAL is '1'/'true',
      uses local Ollama if reachable; otherwise falls over to cloud.
    - If cloud provider is specified (e.g. Groq) and valid, uses cloud;
      otherwise falls back to local Ollama.

    If usage_ledger is given, the resolved provider is wrapped in a RecordingProvider so every
    real generate() call it makes is recorded (tokens, cost, success/failure) into that ledger.
    Default None keeps today's unchanged behavior (a raw, unwrapped provider).

    ``task`` (PC-085) names the job — ``plan`` or ``code`` — so the default chain is ordered by the
    model scorecard for that job. An explicit ``provider_id`` (a pinned project) is never re-routed.
    """
    if load_dotenv:
        _load_dotenv_if_needed()

    if provider_id:
        p_id = provider_id.strip().lower()
        if p_id in ("ollama", "local"):
            provider, default_model, max_output, timeout = build_ollama_provider_from_env()
            eff_model = (model_id or default_model).strip()
            return _maybe_record(provider, usage_ledger), eff_model, max_output, timeout
        specs = resolve_provider_specs()
        if p_id in specs:
            spec = specs[p_id]
            eff_key = (api_key or os.environ.get(spec.key_env, "")).strip()
            if eff_key:
                eff_model = (model_id or os.environ.get(spec.model_env, "") or spec.default_model).strip()
                desc = _cloud_descriptor(spec.provider_id, eff_model)
                if max_output_tokens:
                    from dataclasses import replace as _replace

                    desc = _replace(
                        desc,
                        max_output_tokens=int(max_output_tokens),
                        safe_input_tokens=max(1, min(desc.safe_input_tokens, desc.context_window_tokens - int(max_output_tokens))),
                    )
                rate_limit_retries = int(os.environ.get("OMNISTACKAI_RATE_LIMIT_RETRIES", "2"))
                max_retry_after = float(os.environ.get("OMNISTACKAI_MAX_RETRY_AFTER_SECONDS", "60.0"))
                provider = create_cloud_provider(
                    spec,
                    api_key=eff_key,
                    descriptor=desc,
                    rate_limit_retries=rate_limit_retries,
                    max_retry_after_seconds=max_retry_after,
                )
                timeout = float(os.environ.get("OMNISTACKAI_CLOUD_TIMEOUT_SECONDS", "120.0"))
                logger.info("Resolved explicit provider '%s' with model '%s'", p_id, eff_model)
                return _maybe_record(provider, usage_ledger), eff_model, desc.max_output_tokens, timeout
            else:
                logger.warning("Explicit provider '%s' requested but no API key was provided or configured in %s", p_id, spec.key_env)

    env_prefer_local = prefer_local
    if env_prefer_local is None:
        raw_pref = os.environ.get("OMNISTACKAI_PREFER_LOCAL", "").strip().lower()
        if raw_pref in ("1", "true", "yes"):
            env_prefer_local = True

    cloud_selection = (os.environ.get("OMNISTACKAI_CLOUD_PROVIDER", "") or "").strip().lower()
    if cloud_selection == "gemini":
        cloud_selection = "google"

    # If preference is local and Ollama is online, use Ollama immediately
    if env_prefer_local and ollama_ready_patiently():
        logger.info("Local Ollama is ready and preferred; routing to Ollama")
        provider, default_model, max_output, timeout = build_ollama_provider_from_env()
        eff_model = (model_id or default_model).strip()
        return _maybe_record(provider, usage_ledger), eff_model, max_output, timeout

    if cloud_selection and cloud_selection != "none":
        try:
            boot = build_gateway_from_env()
            if boot.cloud_tier_provider_id:
                provider = boot.registry.get(boot.cloud_tier_provider_id)
                # Resolve active model id
                desc = getattr(provider, "descriptor", None) or getattr(provider, "_descriptor", None)
                profiles = getattr(provider, "profiles", lambda: ())()
                if desc is not None:
                    model_id = desc.model.model_id
                    max_output = desc.max_output_tokens
                elif profiles:
                    model_id = profiles[0].descriptor.model.model_id
                    max_output = profiles[0].descriptor.max_output_tokens
                else:
                    model_id = os.environ.get("OMNISTACKAI_GROQ_MODEL", "openai/gpt-oss-120b")
                    max_output = int(os.environ.get("OMNISTACKAI_CLOUD_MAX_OUTPUT_TOKENS", "4096"))

                timeout = float(os.environ.get("OMNISTACKAI_CLOUD_TIMEOUT_SECONDS", "120.0"))
                logger.info(
                    "Resolved active cloud generation provider '%s' with model '%s'",
                    boot.cloud_tier_provider_id,
                    model_id,
                )
                provider, model_id, max_output = _with_fallbacks(
                    provider, model_id, max_output, boot.cloud_tier_provider_id, task
                )
                return _maybe_record(provider, usage_ledger), model_id, max_output, timeout
        except Exception as err:
            logger.warning(
                "Failed to bootstrap cloud provider '%s' (%s); falling back to Ollama",
                cloud_selection,
                err,
            )

    provider, model_id, max_output, timeout = build_ollama_provider_from_env()
    return _maybe_record(provider, usage_ledger), model_id, max_output, timeout


def _with_fallbacks(
    primary: ModelProvider, model_id: str, max_output: int, primary_id: str | None, task: str = "plan"
) -> tuple[ModelProvider, str, int]:
    """Wrap the build provider in OMNISTACKAI_FALLBACK_PROVIDERS (founder, 2026-09-26).

    Only the tiered router read that setting before, so a rate-limited primary failed the build.
    A named provider without a key is skipped with a log line rather than failing the build.
    PC-085: the chain is then ordered by the model scorecard for ``task``, best first; with no
    scorecard it stays in configured order. Returns the provider and the model it tries first.
    """
    from ..model_gateway.fallback import ChainEntry, FallbackChainProvider

    names = [n.strip().lower() for n in (os.environ.get("OMNISTACKAI_FALLBACK_PROVIDERS", "") or "").split(",") if n.strip()]
    if not names:
        return primary, model_id, max_output
    entries = [ChainEntry(primary, model_id, max_output)]
    specs = resolve_provider_specs()
    for name in names:
        name = "google" if name == "gemini" else name
        if name == (primary_id or "") or (name == "google" and primary_id == "google-gemini"):
            continue
        try:
            if name in ("ollama", "local"):
                local, local_model, local_max, local_timeout = build_ollama_provider_from_env()
                entries.append(ChainEntry(local, local_model, local_max, local_timeout))
                continue
            spec = specs.get(name)
            key = os.environ.get(spec.key_env, "").strip() if spec else ""
            if spec is None or not key:
                logger.warning("fallback provider %r skipped: not configured", name)
                continue
            fallback_model = (os.environ.get(spec.model_env, "") or spec.default_model).strip()
            descriptor = _cloud_descriptor(spec.provider_id, fallback_model)
            entries.append(ChainEntry(
                create_cloud_provider(spec, api_key=key, descriptor=descriptor,
                                      rate_limit_retries=0, max_retry_after_seconds=1.0),
                fallback_model, descriptor.max_output_tokens,
            ))
        except Exception as error:  # noqa: BLE001 - one bad fallback must not break the build
            logger.warning("fallback provider %r skipped: %s", name, error)
    if len(entries) == 1:
        return primary, model_id, max_output
    from ..model_gateway.evals import rank_chain

    keys = [f"{e.provider.provider_id}:{e.model_id}" for e in entries]
    order = rank_chain(keys, task)
    if order != list(range(len(entries))):
        logger.info("%s jobs routed by model scorecard: %s", task, " -> ".join(keys[i] for i in order))
    entries = [entries[i] for i in order]
    return FallbackChainProvider(entries), entries[0].model_id, entries[0].max_output_tokens


def _maybe_record(provider: ModelProvider, usage_ledger: UsageLedger | None) -> ModelProvider:
    return provider if usage_ledger is None else RecordingProvider(provider, usage_ledger)


#: PC-098: the models that can write a whole page, most capable first. Groq is last: its free tier
#: refuses any request over ~8,000 tokens (prompt plus answer), and a grounded page needs more.
PAGE_PROVIDER_ORDER = ("google", "anthropic", "openai", "deepseek", "mistral", "nvidia", "groq")
PAGE_PROVIDER_ENV = "OMNISTACKAI_PAGE_PROVIDER"
PAGE_MODEL_ENV = "OMNISTACKAI_PAGE_MODEL"
PAGE_MAX_OUTPUT_ENV = "OMNISTACKAI_PAGE_MAX_OUTPUT_TOKENS"


def page_output_budget() -> int:
    """The answer budget for one page: room for a full page plus a model's own reasoning.

    Measured in PC-097: at the platform-wide 4,096 every provider's answers arrived truncated.
    """
    try:
        return max(1024, int(os.environ.get(PAGE_MAX_OUTPUT_ENV, "16384")))
    except ValueError:
        return 16384


def page_provider_choice(provider_id: str | None = None) -> str | None:
    """Which provider writes pages: the project's own (pinned or the user's key), else the
    operator's choice, else the first configured one in PAGE_PROVIDER_ORDER; None means the
    build's own default resolution (for example a local model)."""
    if provider_id:
        return provider_id.strip().lower()
    if prefers_local() and ollama_ready_patiently():
        return None  # PC-014: the default resolution, which stays on the local model
    chosen = (os.environ.get(PAGE_PROVIDER_ENV) or "").strip().lower()
    if chosen:
        return "google" if chosen == "gemini" else chosen
    specs = resolve_provider_specs()
    for candidate in PAGE_PROVIDER_ORDER:
        spec = specs.get(candidate)
        if spec is not None and os.environ.get(spec.key_env, "").strip():
            return candidate
    return None


def resolve_page_provider_from_env(
    *,
    usage_ledger: UsageLedger | None = None,
    provider_id: str | None = None,
    model_id: str | None = None,
    api_key: str | None = None,
) -> tuple[ModelProvider, str, int, float]:
    """The provider that writes pages (PC-098), with a page-sized answer budget.

    A project that names its own provider (pinned, or the user's own key) keeps it and its billing.
    """
    _load_dotenv_if_needed()
    chosen = page_provider_choice(provider_id)
    if chosen is None:
        return resolve_generation_provider_from_env(usage_ledger=usage_ledger, load_dotenv=False)
    eff_model = model_id if provider_id else (os.environ.get(PAGE_MODEL_ENV) or "").strip() or None
    return resolve_generation_provider_from_env(
        usage_ledger=usage_ledger,
        load_dotenv=False,
        provider_id=chosen,
        model_id=eff_model,
        api_key=api_key if provider_id else None,
        max_output_tokens=page_output_budget(),
    )


#: PC-098: the free page-writing chain, best first. Measured on this machine (2026-09-28): Gemini's
#: free tier gives each model its own daily quota (gemini-3-flash-preview: 20 requests), so two
#: Gemini models come first; OpenRouter only with a ":free" model (founder rule); NVIDIA is slow but
#: capable; the local model is unlimited and last. Groq's free tier cannot take a page request.
DEFAULT_PAGE_CHAIN = (
    "google:gemini-3.8-flash",
    "google:gemini-3.5-flash-lite",
    "openrouter:qwen/qwen3.8-27b:free",
    "nvidia",
    "ollama",
)
PAGE_CHAIN_ENV = "OMNISTACKAI_PAGE_CHAIN"
PAGE_CLOUD_TIMEOUT_ENV = "OMNISTACKAI_PAGE_CLOUD_TIMEOUT_SECONDS"
PAGE_LOCAL_TIMEOUT_ENV = "OMNISTACKAI_PAGE_LOCAL_TIMEOUT_SECONDS"
PAGE_LOCAL_CONTEXT_ENV = "OMNISTACKAI_PAGE_LOCAL_CONTEXT_TOKENS"
PAGE_LOCAL_OUTPUT_ENV = "OMNISTACKAI_PAGE_LOCAL_OUTPUT_TOKENS"


def _env_number(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "") or default)
    except ValueError:
        return default


def page_chain_spec() -> list[tuple[str, str | None]]:
    """(provider, model) pairs in the order to try them; ``provider[:model]`` entries."""
    raw = (os.environ.get(PAGE_CHAIN_ENV) or "").strip()
    entries = [e.strip() for e in raw.split(",") if e.strip()] if raw else list(DEFAULT_PAGE_CHAIN)
    chosen = (os.environ.get(PAGE_PROVIDER_ENV) or "").strip().lower()
    if chosen and not raw:
        model = (os.environ.get(PAGE_MODEL_ENV) or "").strip()
        entries.insert(0, f"{chosen}:{model}" if model else chosen)
    spec: list[tuple[str, str | None]] = []
    for entry in entries:
        provider, _, model = entry.partition(":")
        provider = "google" if provider.lower() == "gemini" else provider.lower()
        if (provider, model or None) not in spec:
            spec.append((provider, model or None))
    return spec


def resolve_page_providers_from_env(
    *,
    usage_ledger: UsageLedger | None = None,
    provider_id: str | None = None,
    model_id: str | None = None,
    api_key: str | None = None,
) -> list[tuple[ModelProvider, str, int, float]]:
    """Every provider that may write pages, in the order to try them (PC-098).

    When one provider's limit is spent the next takes over, so free keys and a local model can
    design pages without a bill. A project's own provider (pinned, or the user's key) is the only
    one used - its billing is the user's.
    """
    _load_dotenv_if_needed()
    if provider_id:
        return [resolve_page_provider_from_env(usage_ledger=usage_ledger, provider_id=provider_id,
                                               model_id=model_id, api_key=api_key)]
    specs = resolve_provider_specs()
    cloud_timeout = _env_number(PAGE_CLOUD_TIMEOUT_ENV, 240.0)
    chain: list[tuple[ModelProvider, str, int, float]] = []
    spec_order = page_chain_spec()
    local = prefers_local()
    ready = ollama_ready_patiently() if local else False
    if local and ready:
        # PC-014: local preferred means every model call stays on this machine, pages included.
        spec_order = [("ollama", None)]
    # Ollama is only probed here when local is preferred; otherwise it is the chain's last resort and
    # is probed when reached. Logging "False" read as "Ollama is down" (found in PC-122's benchmark).
    logger.warning("page providers: %s (local preferred: %s, Ollama answering: %s)",
                ", ".join(p for p, _ in spec_order), local, ready if local else "checked when reached")
    for provider, model in spec_order:
        try:
            if provider in ("ollama", "local"):
                if not is_ollama_ready():
                    continue
                local, default_model, max_out, _t = build_ollama_provider_from_env(
                    context_window=int(_env_number(PAGE_LOCAL_CONTEXT_ENV, 16_384)),
                    max_output=int(_env_number(PAGE_LOCAL_OUTPUT_ENV, 6_144)),
                )
                chain.append((_maybe_record(local, usage_ledger), model or default_model, max_out,
                              _env_number(PAGE_LOCAL_TIMEOUT_ENV, 900.0)))
                continue
            spec = specs.get(provider)
            if spec is None or not os.environ.get(spec.key_env, "").strip():
                continue
            if provider == "openrouter" and not (model or "").endswith(":free"):
                logger.warning("page chain: OpenRouter is used with free models only; skipping %s", model)
                continue
            resolved = resolve_generation_provider_from_env(
                usage_ledger=usage_ledger, load_dotenv=False, provider_id=provider, model_id=model,
                max_output_tokens=page_output_budget(),
            )
            chain.append((resolved[0], resolved[1], resolved[2], cloud_timeout))
        except Exception as err:  # noqa: BLE001 - one unusable provider must not stop the others
            logger.warning("page provider %s unavailable: %s", provider, err)
    return chain or [resolve_generation_provider_from_env(usage_ledger=usage_ledger, load_dotenv=False)]
