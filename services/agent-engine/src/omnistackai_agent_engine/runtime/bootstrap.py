"""Build the runtime/deployment setup from the environment.

Local is always available (Tier 0/1). Each cloud provider is marked active only when its key env is
set (Tier 2/3), and selecting a keyless cloud provider is a clear error. Reads keys from the
environment only; never logs, stores, or returns a key value.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .errors import DeploySelectionError, RuntimeSelectionError
from .local import LOCAL_PROVIDER_ID, LocalRuntimeProvider
from .providers import DEPLOY_SPECS, RUNTIME_SPECS


def _key_present(key_env: str) -> bool:
    return bool(os.environ.get(key_env, "").strip())


@dataclass(frozen=True, slots=True)
class RuntimeSetup:
    local: LocalRuntimeProvider
    active_cloud: tuple[str, ...]
    selected: str  # "local" or a cloud provider name


@dataclass(frozen=True, slots=True)
class DeploySetup:
    active: tuple[str, ...]
    selected: str | None
    local: LocalRuntimeProvider = field(default_factory=LocalRuntimeProvider)


def build_runtime_from_env(selection: str | None = None) -> RuntimeSetup:
    active = tuple(name for name, spec in sorted(RUNTIME_SPECS.items()) if _key_present(spec.key_env))
    if selection is None:
        selection = os.environ.get("OMNISTACKAI_RUNTIME_PROVIDER", "local")
    selection = (selection or "local").strip().lower()
    if selection in ("", LOCAL_PROVIDER_ID):
        selected = LOCAL_PROVIDER_ID
    elif selection in RUNTIME_SPECS:
        if selection not in active:
            raise RuntimeSelectionError(
                f"runtime provider {selection!r} is selected but {RUNTIME_SPECS[selection].key_env} is not set"
            )
        selected = selection
    else:
        raise RuntimeSelectionError(
            f"OMNISTACKAI_RUNTIME_PROVIDER must be one of local, {', '.join(sorted(RUNTIME_SPECS))}"
        )
    return RuntimeSetup(LocalRuntimeProvider(), active, selected)


def build_deploy_from_env(selection: str | None = None) -> DeploySetup:
    active = tuple(name for name, spec in sorted(DEPLOY_SPECS.items()) if _key_present(spec.key_env))
    if selection is None:
        selection = os.environ.get("OMNISTACKAI_DEPLOY_PROVIDER", "none")
    selection = (selection or "none").strip().lower()
    if selection in ("", "none"):
        selected: str | None = None
    elif selection in DEPLOY_SPECS:
        if selection not in active:
            raise DeploySelectionError(
                f"deploy provider {selection!r} is selected but {DEPLOY_SPECS[selection].key_env} is not set"
            )
        selected = selection
    else:
        raise DeploySelectionError(
            f"OMNISTACKAI_DEPLOY_PROVIDER must be one of none, {', '.join(sorted(DEPLOY_SPECS))}"
        )
    return DeploySetup(active, selected)
