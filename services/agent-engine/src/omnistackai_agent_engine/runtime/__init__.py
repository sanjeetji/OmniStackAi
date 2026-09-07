"""Runtime (preview/sandbox) and deployment provider layer.

Tier 0/1 uses the local provider (no keys). Tier 2/3 cloud providers activate by key presence.
"""

from .bootstrap import DeploySetup, RuntimeSetup, build_deploy_from_env, build_runtime_from_env
from .contracts import (
    Command,
    DeploymentProvider,
    DeployPlan,
    PreviewPlan,
    PreviewStep,
    RuntimeProvider,
)
from .errors import (
    DeploySelectionError,
    RuntimeProviderError,
    RuntimeSelectionError,
    UnsupportedRuntimeTargetError,
)
from .drivers import (
    CloudDeployProvider,
    CloudSandboxProvider,
    deploy_driver,
    run_deploy,
    sandbox_driver,
)
from .local import LOCAL_PROVIDER_ID, LocalRuntimeProvider, run_preview
from .providers import DEPLOY_SPECS, RUNTIME_SPECS, ProviderSpec
from .tier import (
    VALID_TIERS,
    PlatformSetup,
    format_status,
    platform_status,
    resolve_platform,
    resolve_tier,
)

__all__ = [
    "Command",
    "CloudDeployProvider",
    "CloudSandboxProvider",
    "DEPLOY_SPECS",
    "DeployPlan",
    "DeploySelectionError",
    "DeploySetup",
    "DeploymentProvider",
    "LOCAL_PROVIDER_ID",
    "LocalRuntimeProvider",
    "PlatformSetup",
    "PreviewPlan",
    "PreviewStep",
    "ProviderSpec",
    "RUNTIME_SPECS",
    "RuntimeProvider",
    "RuntimeProviderError",
    "RuntimeSelectionError",
    "RuntimeSetup",
    "UnsupportedRuntimeTargetError",
    "VALID_TIERS",
    "build_deploy_from_env",
    "build_runtime_from_env",
    "deploy_driver",
    "format_status",
    "platform_status",
    "resolve_platform",
    "resolve_tier",
    "run_deploy",
    "run_preview",
    "sandbox_driver",
]
