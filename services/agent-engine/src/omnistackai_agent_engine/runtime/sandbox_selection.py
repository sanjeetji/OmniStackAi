"""Provider-selection surface over the real `SandboxLifecycleProvider` drivers (R-490).

R-486..R-489 each built a real, independently-tested driver (E2B, Vercel Sandbox, Daytona,
gVisor); this is the missing piece that makes them genuinely pluggable and switchable via
configuration - the founder's explicit ask across this whole sequence.

A deliberately separate concern from `tier.py`/`bootstrap.py`, which resolve the *older*,
pure-planning `RuntimeProvider`/`DeploymentProvider` system (still using the placeholder-URL stub
`CloudSandboxProvider`) - untouched by this task, exactly as it was untouched by every driver task
before it. Mirrors `bootstrap.py`'s own established shape
(`build_runtime_from_env(selection=None) -> RuntimeSetup`) for consistency.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass

from .contracts import SandboxLifecycleProvider
from .daytona import DaytonaSandboxProvider
from .e2b import E2BSandboxProvider
from .errors import SandboxSelectionError
from .gvisor import GVisorSandboxProvider
from .vercel_sandbox import VercelSandboxProvider

# name -> constructor. Each real driver's own `.active` property already defines what "available"
# means for it (an env-key check for the three cloud drivers; a live local Docker capability check
# for gvisor) - this registry does not duplicate that logic, only names the four real options.
_SANDBOX_LIFECYCLE_PROVIDERS: dict[str, Callable[[], SandboxLifecycleProvider]] = {
    "gvisor": GVisorSandboxProvider,
    "e2b": E2BSandboxProvider,
    "vercel-sandbox": VercelSandboxProvider,
    "daytona": DaytonaSandboxProvider,
}


@dataclass(frozen=True, slots=True)
class SandboxSetup:
    active: tuple[str, ...]  # every registered provider whose .active is true right now
    selected: str | None  # None when sandboxing is disabled (the default)
    provider: SandboxLifecycleProvider | None  # None when selected is None


def build_sandbox_from_env(
    selection: str | None = None,
    *,
    providers: dict[str, SandboxLifecycleProvider] | None = None,
) -> SandboxSetup:
    """Resolves which real `SandboxLifecycleProvider` (if any) is selected.

    Reads `OMNISTACKAI_SANDBOX_PROVIDER` (default `"none"` - sandboxing off, the same conservative
    default `OMNISTACKAI_DEPLOY_PROVIDER` already uses, so this is a zero-behavior-change addition
    until an operator explicitly opts in) when `selection` is not passed explicitly. Passing
    `selection` explicitly is the concrete "switch per user base" mechanism the founder asked
    about: a caller can compute it per request (e.g. from a user's plan) rather than relying only
    on the one global env var.

    `providers` is an injectable override so tests never make a real network/Docker call just to
    exercise selection logic - production callers omit it and get the four real drivers.
    """

    candidates = providers if providers is not None else {name: ctor() for name, ctor in _SANDBOX_LIFECYCLE_PROVIDERS.items()}
    active = tuple(name for name, provider in sorted(candidates.items()) if provider.active)

    if selection is None:
        selection = os.environ.get("OMNISTACKAI_SANDBOX_PROVIDER", "none")
    selection = (selection or "none").strip().lower()

    if selection == "none":
        return SandboxSetup(active, None, None)
    if selection not in _SANDBOX_LIFECYCLE_PROVIDERS:
        raise SandboxSelectionError(
            f"OMNISTACKAI_SANDBOX_PROVIDER must be one of none, {', '.join(sorted(_SANDBOX_LIFECYCLE_PROVIDERS))}"
        )
    provider = candidates[selection]
    if not provider.active:
        raise SandboxSelectionError(f"sandbox provider {selection!r} is selected but is not active")
    return SandboxSetup(active, selection, provider)
