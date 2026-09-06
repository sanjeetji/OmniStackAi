"""Stable platform-owned registry errors."""


class ProviderRegistryError(Exception):
    code = "provider_registry_error"


class InvalidProviderError(ProviderRegistryError):
    code = "invalid_provider"


class DuplicateProviderError(ProviderRegistryError):
    code = "duplicate_provider"


class UnknownProviderError(ProviderRegistryError):
    code = "unknown_provider"
