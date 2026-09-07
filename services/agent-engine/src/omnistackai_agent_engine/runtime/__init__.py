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
from .local import LOCAL_PROVIDER_ID, LocalRuntimeProvider, run_preview
from .providers import DEPLOY_SPECS, RUNTIME_SPECS, ProviderSpec

__all__ = [
    "Command",
    "DEPLOY_SPECS",
    "DeployPlan",
    "DeploySelectionError",
    "DeploySetup",
    "DeploymentProvider",
    "LOCAL_PROVIDER_ID",
    "LocalRuntimeProvider",
    "PreviewPlan",
    "PreviewStep",
    "ProviderSpec",
    "RUNTIME_SPECS",
    "RuntimeProvider",
    "RuntimeProviderError",
    "RuntimeSelectionError",
    "RuntimeSetup",
    "UnsupportedRuntimeTargetError",
    "build_deploy_from_env",
    "build_runtime_from_env",
    "run_preview",
]
