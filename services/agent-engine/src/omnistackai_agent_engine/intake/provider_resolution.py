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


def is_ollama_ready(base_url: str | None = None) -> bool:
    """Check if local Ollama daemon is reachable and responding."""
    import urllib.request
    url = (base_url or os.environ.get("OMNISTACKAI_OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
    try:
        req = urllib.request.Request(f"{url}/api/tags", headers={"User-Agent": "omnistackai"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def resolve_generation_provider_from_env(
    *,
    load_dotenv: bool = True,
    prefer_local: bool | None = None,
    usage_ledger: UsageLedger | None = None,
    provider_id: str | None = None,
    model_id: str | None = None,
    api_key: str | None = None,
) -> tuple[ModelProvider, str, int, float]:
    """Resolve (provider, model_id, max_output_tokens, request_timeout_seconds).

    Smart dual-engine routing:
    - If explicit provider_id is passed, uses that provider with optional model_id and api_key.
    - If prefer_local is explicitly True or OMNISTACKAI_PREFER_LOCAL is '1'/'true',
      uses local Ollama if reachable; otherwise falls over to cloud.
    - If cloud provider is specified (e.g. Groq) and valid, uses cloud;
      otherwise falls back to local Ollama.

    If usage_ledger is given, the resolved provider is wrapped in a RecordingProvider so every
    real generate() call it makes is recorded (tokens, cost, success/failure) into that ledger.
    Default None keeps today's unchanged behavior (a raw, unwrapped provider).
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
    if env_prefer_local and is_ollama_ready():
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
                    model_id = os.environ.get("OMNISTACKAI_GROQ_MODEL", "llama-3.3-70b-versatile")
                    max_output = int(os.environ.get("OMNISTACKAI_CLOUD_MAX_OUTPUT_TOKENS", "4096"))

                timeout = float(os.environ.get("OMNISTACKAI_CLOUD_TIMEOUT_SECONDS", "120.0"))
                logger.info(
                    "Resolved active cloud generation provider '%s' with model '%s'",
                    boot.cloud_tier_provider_id,
                    model_id,
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


def _maybe_record(provider: ModelProvider, usage_ledger: UsageLedger | None) -> ModelProvider:
    return provider if usage_ledger is None else RecordingProvider(provider, usage_ledger)
