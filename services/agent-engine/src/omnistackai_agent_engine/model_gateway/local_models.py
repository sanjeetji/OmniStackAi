"""PC-014: which local model to use, from what is installed and what the machine can hold.

Found in PC-084: `.env` named qwen2.5-coder:14b while only the 7b was installed, and every local
call failed with "model is not configured for this provider". The setting is now a wish, not a
fact: Ollama is asked what is installed; a configured model that is not there is replaced by the
best installed one that fits the machine, and the log says so; with none installed the message
names the model to pull. Nothing is ever downloaded on its own - a model is gigabytes.

The recommendation follows the machine's memory (on Apple silicon the GPU shares it). A q4 coder
model needs roughly its weights plus room for the context window, and the rest of the machine -
the platform, a browser, the generated app - needs the remainder.
"""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import urllib.request
from dataclasses import dataclass

#: (smallest machine memory in GB, model, approximate size on disk in GB) - largest first.
RECOMMENDATIONS: tuple[tuple[int, str, float], ...] = (
    (40, "qwen2.5-coder:32b", 20.0),
    (14, "qwen2.5-coder:14b", 9.0),
    (8, "qwen2.5-coder:7b", 4.7),
    (0, "qwen2.5-coder:3b", 1.9),
)
_CODE_FAMILIES = ("coder", "code", "deepseek", "qwen", "llama", "mistral", "gemma", "phi")


@dataclass(frozen=True)
class InstalledModel:
    name: str
    size_gb: float
    parameters_b: float  # billions, 0 when unknown


@dataclass(frozen=True)
class LocalChoice:
    model: str | None
    reason: str
    recommended: str
    memory_gb: float
    installed: tuple[InstalledModel, ...]


def machine_memory_gb() -> float:
    """Total physical memory in GB (0 when it cannot be read)."""
    try:
        if platform.system() == "Darwin":
            raw = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=3).stdout
            return int(raw.strip()) / 1024**3
        with open("/proc/meminfo", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) / 1024**2
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return 0.0


def recommend(memory_gb: float) -> tuple[str, float]:
    """The coder model this machine runs comfortably, and its size on disk."""
    for floor, model, size in RECOMMENDATIONS:
        if memory_gb >= floor:
            return model, size
    return RECOMMENDATIONS[-1][1], RECOMMENDATIONS[-1][2]


def _parameters(name: str, details: dict) -> float:
    raw = str(details.get("parameter_size") or "")
    match = re.search(r"([\d.]+)\s*[bB]", raw) or re.search(r":([\d.]+)b\b", name)
    return float(match.group(1)) if match else 0.0


def installed_models(base_url: str | None = None, timeout: float = 2.0) -> tuple[InstalledModel, ...] | None:
    """What Ollama has installed, or None when Ollama cannot be reached."""
    url = (base_url or os.environ.get("OMNISTACKAI_OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
    try:
        with urllib.request.urlopen(urllib.request.Request(f"{url}/api/tags"), timeout=timeout) as response:  # noqa: S310 - local
            payload = json.loads(response.read())
    except (OSError, ValueError):
        return None
    models = []
    for item in payload.get("models") or ():
        name = str(item.get("name") or item.get("model") or "")
        if name:
            models.append(InstalledModel(name, round(float(item.get("size") or 0) / 1024**3, 1),
                                         _parameters(name, item.get("details") or {})))
    return tuple(models)


def choose(configured: str, installed: tuple[InstalledModel, ...] | None, memory_gb: float) -> LocalChoice:
    """The model to run, and why."""
    recommended, recommended_size = recommend(memory_gb)
    if installed is None:
        return LocalChoice(configured, "Ollama is not running; using the configured model when it starts",
                           recommended, memory_gb, ())
    names = {m.name for m in installed}
    if configured in names or f"{configured}:latest" in names:
        return LocalChoice(configured, "the configured model is installed", recommended, memory_gb, installed)
    if not installed:
        return LocalChoice(None, f"no model is installed - run: ollama pull {recommended} (about {recommended_size:g} GB)",
                           recommended, memory_gb, installed)
    # The largest installed model that still fits, preferring coder models; then the smallest one.
    budget = max(memory_gb - 6.0, memory_gb * 0.6) if memory_gb else float("inf")
    fitting = [m for m in installed if not m.size_gb or m.size_gb <= budget]
    pool = fitting or sorted(installed, key=lambda m: m.size_gb)[:1]
    coders = [m for m in pool if "coder" in m.name or "code" in m.name] or [
        m for m in pool if any(f in m.name for f in _CODE_FAMILIES)] or pool
    best = max(coders, key=lambda m: (m.parameters_b, m.size_gb))
    return LocalChoice(best.name, f"{configured} is not installed; using {best.name}, the best installed model that fits "
                                  f"(recommended here: {recommended})", recommended, memory_gb, installed)


def local_report() -> str:
    """A few lines for `omnistack.sh status` and the CLI: installed, recommended, chosen."""
    configured = os.environ.get("OMNISTACKAI_OLLAMA_MODEL", "qwen2.5-coder:14b")
    memory = machine_memory_gb()
    choice = choose(configured, installed_models(), memory)
    installed = ", ".join(f"{m.name} ({m.size_gb:g} GB)" for m in choice.installed) or "none"
    lines = [
        f"machine memory: {memory:.0f} GB -> recommended model: {choice.recommended}",
        f"installed: {installed}",
        f"configured: {configured}; using: {choice.model or 'none'} ({choice.reason})",
    ]
    if choice.model and choice.model != choice.recommended and choice.installed and memory:
        rec_size = recommend(memory)[1]
        lines.append(f"for better results here: ollama pull {choice.recommended} (about {rec_size:g} GB), "
                     f"then set OMNISTACKAI_OLLAMA_MODEL={choice.recommended}")
    return "\n".join(lines)


def apply_installed_local_model(log=None) -> LocalChoice:
    """At start-up: run the model that is really installed (PC-014).

    Sets OMNISTACKAI_OLLAMA_MODEL for this process when the configured one is not installed, so every
    local call after it asks for a model Ollama has. Called once by the Studio, never by tests.
    """
    from ..intake.provider_resolution import _load_dotenv_if_needed

    _load_dotenv_if_needed()
    configured = os.environ.get("OMNISTACKAI_OLLAMA_MODEL", "qwen2.5-coder:14b")
    choice = choose(configured, installed_models(), machine_memory_gb())
    if choice.model and choice.model != configured:
        os.environ["OMNISTACKAI_OLLAMA_MODEL"] = choice.model
    if log is not None:
        log(f"local model: {choice.model or 'none'} - {choice.reason}")
    return choice


if __name__ == "__main__":  # python -m omnistackai_agent_engine.model_gateway.local_models
    print(local_report())
