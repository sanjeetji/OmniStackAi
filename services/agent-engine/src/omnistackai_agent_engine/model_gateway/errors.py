"""Stable platform-owned registry errors."""


class ProviderRegistryError(Exception):
    code = "provider_registry_error"


class InvalidProviderError(ProviderRegistryError):
    code = "invalid_provider"


class DuplicateProviderError(ProviderRegistryError):
    code = "duplicate_provider"


class UnknownProviderError(ProviderRegistryError):
    code = "unknown_provider"


class ModelProviderError(Exception):
    """Base error safe to expose at the platform provider boundary."""

    code = "model_provider_error"


class InvalidProviderConfigurationError(ModelProviderError):
    code = "invalid_provider_configuration"


class UnknownModelError(ModelProviderError):
    code = "unknown_model"


class UnsupportedModelRequestError(ModelProviderError):
    code = "unsupported_model_request"


class ProviderUnavailableError(ModelProviderError):
    code = "provider_unavailable"


class ProviderTimeoutError(ModelProviderError):
    code = "provider_timeout"


class ProviderHTTPError(ModelProviderError):
    """A non-success HTTP status from a provider.

    R-466: carries the status code and any parsed ``Retry-After`` hint (seconds) so callers can pace
    instead of aborting; the message stays bounded and never contains a credential.
    """

    code = "provider_http_error"

    def __init__(
        self,
        message: str = "",
        *,
        status_code: int | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds


class ProviderRateLimitedError(ProviderHTTPError):
    """HTTP 429: the provider asked us to slow down. The cloud adapter honours the hint (bounded)."""

    code = "provider_rate_limited"


class ProviderResponseError(ModelProviderError):
    code = "provider_response_error"


class ProviderResponseTooLargeError(ModelProviderError):
    code = "provider_response_too_large"


class ModelProfileMismatchError(ModelProviderError):
    code = "model_profile_mismatch"


class MissingCredentialError(ModelProviderError):
    code = "missing_credential"


class ModelGatewayError(Exception):
    """Base error safe to expose at the platform model-gateway routing boundary."""

    code = "model_gateway_error"


class InvalidRoutingTaskError(ModelGatewayError):
    code = "invalid_routing_task"


class DeterministicWorkNotRoutableError(ModelGatewayError):
    code = "deterministic_work_not_routable"


class NoEligibleProviderError(ModelGatewayError):
    code = "no_eligible_provider"


class ContextBudgetExceededError(ModelGatewayError):
    code = "context_budget_exceeded"


class CloudProviderSelectionError(ModelGatewayError):
    code = "cloud_provider_selection_error"


class AllProvidersFailedError(ModelGatewayError):
    code = "all_providers_failed"
