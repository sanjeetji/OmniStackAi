"""Stable, boundary-safe errors for the runtime/deployment layer."""


class RuntimeProviderError(Exception):
    """Base error for runtime/deployment providers (safe to expose)."""

    code = "runtime_provider_error"


class UnsupportedRuntimeTargetError(RuntimeProviderError):
    code = "unsupported_runtime_target"


class RuntimeSelectionError(RuntimeProviderError):
    code = "runtime_selection_error"


class DeploySelectionError(RuntimeProviderError):
    code = "deploy_selection_error"


class SandboxSelectionError(RuntimeProviderError):
    """R-490: raised by build_sandbox_from_env() for an unknown provider name, or a real but
    currently-inactive one (mirrors RuntimeSelectionError/DeploySelectionError's own precedent:
    "selecting a keyless cloud provider is a clear error")."""

    code = "sandbox_selection_error"
