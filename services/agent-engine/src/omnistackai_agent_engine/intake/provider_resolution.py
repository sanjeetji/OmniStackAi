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

from ..model_gateway.bootstrap import build_gateway_from_env
from ..model_gateway.contracts import ModelProvider
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
) -> tuple[ModelProvider, str, int, float]:
    """Resolve (provider, model_id, max_output_tokens, request_timeout_seconds).

    Smart dual-engine routing:
    - If prefer_local is explicitly True or OMNISTACKAI_PREFER_LOCAL is '1'/'true',
      uses local Ollama if reachable; otherwise falls over to cloud.
    - If cloud provider is specified (e.g. Groq) and valid, uses cloud;
      otherwise falls back to local Ollama.
    """
    if load_dotenv:
        _load_dotenv_if_needed()

    env_prefer_local = prefer_local
    if env_prefer_local is None:
        raw_pref = os.environ.get("OMNISTACKAI_PREFER_LOCAL", "").strip().lower()
        if raw_pref in ("1", "true", "yes"):
            env_prefer_local = True

    cloud_selection = (os.environ.get("OMNISTACKAI_CLOUD_PROVIDER", "") or "").strip().lower()

    # If preference is local and Ollama is online, use Ollama immediately
    if env_prefer_local and is_ollama_ready():
        logger.info("Local Ollama is ready and preferred; routing to Ollama")
        return build_ollama_provider_from_env()

    if cloud_selection and cloud_selection != "none":
        try:
            boot = build_gateway_from_env()
            if boot.cloud_tier_provider_id:
                provider = boot.registry.get(boot.cloud_tier_provider_id)
                # Resolve active model id
                profiles = getattr(provider, "profiles", lambda: ())()
                if profiles:
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
                return provider, model_id, max_output, timeout
        except Exception as err:
            logger.warning(
                "Failed to bootstrap cloud provider '%s' (%s); falling back to Ollama",
                cloud_selection,
                err,
            )

    return build_ollama_provider_from_env()
