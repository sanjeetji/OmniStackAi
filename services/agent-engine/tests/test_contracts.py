from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from unittest import TestCase

from omnistackai_agent_engine.model_gateway import (
    CapabilityStatus,
    ChatRole,
    GenerateRequest,
    HealthStatus,
    Message,
    ModelCapabilities,
    ModelDescriptor,
    ModelRef,
    ProviderHealth,
    StreamEvent,
    TokenUsage,
)


def capabilities() -> ModelCapabilities:
    return ModelCapabilities(
        text=CapabilityStatus.VERIFIED,
        streaming=CapabilityStatus.VERIFIED,
        tool_calling=CapabilityStatus.UNVERIFIED,
        structured_output=CapabilityStatus.UNVERIFIED,
        vision=CapabilityStatus.UNSUPPORTED,
        embeddings=CapabilityStatus.UNSUPPORTED,
    )


class ContractValidationTests(TestCase):
    def test_records_are_immutable(self) -> None:
        model = ModelRef(provider_id="local-test", model_id="coder:1")
        with self.assertRaises(FrozenInstanceError):
            model.model_id = "changed"  # type: ignore[misc]

    def test_model_ref_rejects_invalid_identifiers(self) -> None:
        for provider_id in ("", "Uppercase", "has space"):
            with self.subTest(provider_id=provider_id), self.assertRaises(ValueError):
                ModelRef(provider_id=provider_id, model_id="coder:1")
        with self.assertRaises(ValueError):
            ModelRef(provider_id="local-test", model_id=" surrounded ")

    def test_descriptor_enforces_context_budget(self) -> None:
        with self.assertRaisesRegex(ValueError, "fit the context window"):
            ModelDescriptor(
                model=ModelRef("local-test", "coder:1"),
                capabilities=capabilities(),
                context_window_tokens=4_096,
                safe_input_tokens=3_500,
                max_output_tokens=1_000,
            )

    def test_descriptor_requires_platform_record_types(self) -> None:
        with self.assertRaisesRegex(TypeError, "ModelRef"):
            ModelDescriptor("model", capabilities(), 4_096, 3_000, 1_000)  # type: ignore[arg-type]

    def test_request_requires_messages_and_bounded_timeout(self) -> None:
        model = ModelRef("local-test", "coder:1")
        with self.assertRaisesRegex(ValueError, "non-empty tuple"):
            GenerateRequest("request-1", model, (), 100, 3.0)
        with self.assertRaisesRegex(ValueError, "positive finite"):
            GenerateRequest(
                "request-1",
                model,
                (Message(ChatRole.USER, "hello"),),
                100,
                float("inf"),
            )

    def test_usage_is_non_negative_and_cached_is_bounded(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-negative"):
            TokenUsage(input_tokens=-1, output_tokens=0)
        with self.assertRaisesRegex(ValueError, "must not exceed"):
            TokenUsage(input_tokens=2, output_tokens=1, cached_input_tokens=3)
        self.assertEqual(TokenUsage(3, 2, 1).total_tokens, 5)

    def test_health_requires_timezone_and_stable_detail_code(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            ProviderHealth("local-test", HealthStatus.HEALTHY, datetime.now(), "ok")
        health = ProviderHealth("local-test", HealthStatus.HEALTHY, datetime.now(UTC), "ok")
        self.assertEqual(health.detail_code, "ok")
        with self.assertRaisesRegex(ValueError, "machine-stable"):
            ProviderHealth(
                "local-test",
                HealthStatus.UNAVAILABLE,
                datetime.now(UTC),
                "connection failed: secret detail",
            )

    def test_usage_only_appears_on_final_stream_event(self) -> None:
        with self.assertRaisesRegex(ValueError, "final stream event"):
            StreamEvent("request-1", 0, "partial", False, TokenUsage(1, 1))
