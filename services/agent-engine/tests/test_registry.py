from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest import TestCase

from omnistackai_agent_engine.model_gateway import (
    DuplicateProviderError,
    FinishReason,
    GenerateRequest,
    GenerateResponse,
    HealthStatus,
    InvalidProviderError,
    ModelDescriptor,
    ModelProvider,
    ProviderHealth,
    ProviderRegistry,
    StreamEvent,
    TokenUsage,
    UnknownProviderError,
)


class FakeProvider:
    def __init__(self, provider_id: str) -> None:
        self._provider_id = provider_id

    @property
    def provider_id(self) -> str:
        return self._provider_id

    async def health(self) -> ProviderHealth:
        return ProviderHealth(self.provider_id, HealthStatus.HEALTHY, datetime.now(UTC), "ok")

    async def discover_models(self) -> tuple[ModelDescriptor, ...]:
        return ()

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        return GenerateResponse(
            request.request_id,
            request.model,
            "ok",
            FinishReason.STOP,
            TokenUsage(1, 1),
            1,
        )

    async def stream(self, request: GenerateRequest) -> AsyncIterator[StreamEvent]:
        yield StreamEvent(request.request_id, 0, "ok", True, TokenUsage(1, 1))


class ProviderRegistryTests(TestCase):
    def test_provider_is_runtime_substitutable(self) -> None:
        self.assertIsInstance(FakeProvider("local-test"), ModelProvider)

    def test_registry_order_is_deterministic(self) -> None:
        registry = ProviderRegistry()
        registry.register(FakeProvider("z-provider"))
        registry.register(FakeProvider("a-provider"))

        self.assertEqual(registry.provider_ids(), ("a-provider", "z-provider"))
        registered_ids = tuple(provider.provider_id for provider in registry.providers())
        self.assertEqual(registered_ids, registry.provider_ids())
        self.assertEqual(registry.get("a-provider").provider_id, "a-provider")
        self.assertEqual(len(registry), 2)

    def test_duplicate_provider_is_rejected_with_stable_error(self) -> None:
        registry = ProviderRegistry()
        registry.register(FakeProvider("local-test"))

        with self.assertRaises(DuplicateProviderError) as raised:
            registry.register(FakeProvider("local-test"))
        self.assertEqual(raised.exception.code, "duplicate_provider")

    def test_unknown_and_invalid_provider_ids_are_distinct(self) -> None:
        registry = ProviderRegistry()
        with self.assertRaises(UnknownProviderError) as unknown:
            registry.get("missing")
        self.assertEqual(unknown.exception.code, "unknown_provider")

        with self.assertRaises(InvalidProviderError) as invalid:
            registry.get("NOT VALID")
        self.assertEqual(invalid.exception.code, "invalid_provider")

    def test_non_provider_is_rejected(self) -> None:
        with self.assertRaises(InvalidProviderError):
            ProviderRegistry().register(object())
