"""Deterministic registry for vendor-neutral model providers."""

from __future__ import annotations

from .contracts import ModelProvider, validate_provider_id
from .errors import DuplicateProviderError, InvalidProviderError, UnknownProviderError


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ModelProvider] = {}

    def register(self, provider: object) -> None:
        if not isinstance(provider, ModelProvider):
            raise InvalidProviderError("provider does not implement the ModelProvider contract")

        try:
            provider_id = validate_provider_id(provider.provider_id)
        except (TypeError, ValueError) as error:
            raise InvalidProviderError("provider exposes an invalid provider_id") from error

        if provider_id in self._providers:
            raise DuplicateProviderError(f"provider_id is already registered: {provider_id}")
        self._providers[provider_id] = provider

    def get(self, provider_id: str) -> ModelProvider:
        try:
            validated_id = validate_provider_id(provider_id)
        except (TypeError, ValueError) as error:
            raise InvalidProviderError("provider_id is invalid") from error

        try:
            return self._providers[validated_id]
        except KeyError as error:
            raise UnknownProviderError(f"provider_id is not registered: {validated_id}") from error

    def provider_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))

    def providers(self) -> tuple[ModelProvider, ...]:
        return tuple(self._providers[provider_id] for provider_id in self.provider_ids())

    def __len__(self) -> int:
        return len(self._providers)
