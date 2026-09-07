"""Single-knob tier switch over the runtime/deploy providers.

`OMNISTACKAI_TIER` selects the operating tier; explicit `OMNISTACKAI_RUNTIME_PROVIDER` /
`OMNISTACKAI_DEPLOY_PROVIDER` override within tier 2. Change the tier (or a selector) and the resolved
providers change — that is what `resolve_platform` and `platform_status` report. Pure and offline:
resolving never runs, deploys, or reads a secret value. All env reads use os.environ.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from .bootstrap import DeploySetup, RuntimeSetup, build_deploy_from_env, build_runtime_from_env
from .contracts import DeploymentProvider, RuntimeProvider
from .drivers import deploy_driver, sandbox_driver
from .errors import RuntimeSelectionError
from .local import LOCAL_PROVIDER_ID, LocalRuntimeProvider
from .providers import DEPLOY_SPECS, RUNTIME_SPECS

VALID_TIERS = (0, 1, 2)


@dataclass(frozen=True, slots=True)
class PlatformSetup:
    tier: int
    runtime: RuntimeSetup
    deploy: DeploySetup
    runtime_provider: RuntimeProvider
    deploy_provider: DeploymentProvider | None


def resolve_tier() -> int:
    raw = (os.environ.get("OMNISTACKAI_TIER", "0") or "0").strip()
    if raw not in ("0", "1", "2"):
        raise RuntimeSelectionError("OMNISTACKAI_TIER must be 0, 1, or 2")
    return int(raw)


def _selections(tier: int) -> tuple[str, str]:
    if tier in (0, 1):
        return LOCAL_PROVIDER_ID, "none"  # local run, no deploy
    runtime = (os.environ.get("OMNISTACKAI_RUNTIME_PROVIDER", "local") or "local").strip().lower()
    deploy = (os.environ.get("OMNISTACKAI_DEPLOY_PROVIDER", "none") or "none").strip().lower()
    return runtime, deploy


def resolve_platform() -> PlatformSetup:
    tier = resolve_tier()
    runtime_selection, deploy_selection = _selections(tier)
    runtime_setup = build_runtime_from_env(runtime_selection)
    deploy_setup = build_deploy_from_env(deploy_selection)

    runtime_provider: RuntimeProvider = (
        LocalRuntimeProvider() if runtime_setup.selected == LOCAL_PROVIDER_ID
        else sandbox_driver(runtime_setup.selected)
    )
    deploy_provider: DeploymentProvider | None = (
        None if deploy_setup.selected is None else deploy_driver(deploy_setup.selected)
    )
    return PlatformSetup(tier, runtime_setup, deploy_setup, runtime_provider, deploy_provider)


def platform_status() -> dict[str, object]:
    setup = resolve_platform()
    sandbox_keys = [n for n, s in sorted(RUNTIME_SPECS.items()) if os.environ.get(s.key_env, "").strip()]
    deploy_keys = [n for n, s in sorted(DEPLOY_SPECS.items()) if os.environ.get(s.key_env, "").strip()]
    return {
        "tier": setup.tier,
        "runtime": setup.runtime_provider.id,
        "deploy": setup.deploy_provider.id if setup.deploy_provider else "none",
        "sandbox_keys_present": sandbox_keys,
        "deploy_keys_present": deploy_keys,
    }


def format_status() -> str:
    status = platform_status()
    return "\n".join([
        f"Tier:         {status['tier']}",
        f"Runtime:      {status['runtime']}",
        f"Deploy:       {status['deploy']}",
        f"Sandbox keys: {', '.join(status['sandbox_keys_present']) or 'none'}",  # type: ignore[arg-type]
        f"Deploy keys:  {', '.join(status['deploy_keys_present']) or 'none'}",  # type: ignore[arg-type]
    ])
