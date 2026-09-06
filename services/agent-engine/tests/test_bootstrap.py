from unittest import TestCase
from unittest.mock import patch

from omnistackai_agent_engine.model_gateway import (
    ChatRole,
    CloudProviderSelectionError,
    Message,
    NoEligibleProviderError,
    RoutingTask,
    TaskComplexity,
    build_gateway_from_env,
)

BASE_ENV = {
    "OMNISTACKAI_OLLAMA_BASE_URL": "http://127.0.0.1:11434",
    "OMNISTACKAI_OLLAMA_MODEL": "qwen2.5-coder:14b",
}


def _task(complexity: TaskComplexity) -> RoutingTask:
    return RoutingTask(
        request_id="req-1",
        messages=(Message(ChatRole.USER, "do the work"),),
        max_output_tokens=64,
        timeout_seconds=5.0,
        complexity=complexity,
    )


def _env(**extra: str) -> dict[str, str]:
    return {**BASE_ENV, **extra}


class BootstrapTests(TestCase):
    def test_no_cloud_key_registers_only_local_and_refuses_high_risk(self) -> None:
        with patch.dict("os.environ", _env(), clear=True):
            boot = build_gateway_from_env()
        self.assertEqual(boot.registered_provider_ids, ("ollama-local",))
        self.assertIsNone(boot.cloud_tier_provider_id)
        self.assertEqual(boot.gateway.resolve(_task(TaskComplexity.L2)).provider_id, "ollama-local")
        with self.assertRaises(NoEligibleProviderError):
            boot.gateway.resolve(_task(TaskComplexity.L3))

    def test_selected_cloud_key_enables_high_risk_routing(self) -> None:
        env = _env(ANTHROPIC_API_KEY="fake-key", OMNISTACKAI_CLOUD_PROVIDER="anthropic")
        with patch.dict("os.environ", env, clear=True):
            boot = build_gateway_from_env()
        self.assertIn("anthropic", boot.registered_provider_ids)
        self.assertIn("ollama-local", boot.registered_provider_ids)
        self.assertEqual(boot.cloud_tier_provider_id, "anthropic")
        self.assertEqual(boot.gateway.resolve(_task(TaskComplexity.L2)).provider_id, "ollama-local")
        self.assertEqual(boot.gateway.resolve(_task(TaskComplexity.L3)).provider_id, "anthropic")

    def test_keys_without_selection_register_but_stay_off_the_cloud_tier(self) -> None:
        env = _env(ANTHROPIC_API_KEY="k1", OPENAI_API_KEY="k2", GROQ_API_KEY="k3")
        with patch.dict("os.environ", env, clear=True):
            boot = build_gateway_from_env()
        self.assertEqual(
            set(boot.registered_provider_ids),
            {"ollama-local", "anthropic", "openai", "groq"},
        )
        self.assertIsNone(boot.cloud_tier_provider_id)
        with self.assertRaises(NoEligibleProviderError):
            boot.gateway.resolve(_task(TaskComplexity.L3))

    def test_selecting_provider_without_key_is_a_configuration_error(self) -> None:
        with patch.dict("os.environ", _env(OMNISTACKAI_CLOUD_PROVIDER="anthropic"), clear=True):
            with self.assertRaises(CloudProviderSelectionError):
                build_gateway_from_env()

    def test_unknown_selection_is_rejected(self) -> None:
        with patch.dict("os.environ", _env(OMNISTACKAI_CLOUD_PROVIDER="bogus"), clear=True):
            with self.assertRaises(CloudProviderSelectionError):
                build_gateway_from_env()

    def test_model_override_is_applied(self) -> None:
        env = _env(
            OPENAI_API_KEY="k", OMNISTACKAI_CLOUD_PROVIDER="openai",
            OMNISTACKAI_OPENAI_MODEL="gpt-custom-test",
        )
        with patch.dict("os.environ", env, clear=True):
            boot = build_gateway_from_env()
        self.assertEqual(boot.gateway.resolve(_task(TaskComplexity.L3)).model.model_id, "gpt-custom-test")


class FallbackWiringTests(TestCase):
    def test_no_chain_leaves_default_unchanged(self) -> None:
        with patch.dict("os.environ", _env(), clear=True):
            boot = build_gateway_from_env()
        self.assertEqual(boot.fallback_provider_ids, ())
        self.assertFalse(boot.breaker_enabled)

    def test_env_chain_builds_registered_providers_and_attaches_breaker(self) -> None:
        env = _env(
            ANTHROPIC_API_KEY="k1", OPENAI_API_KEY="k2",
            OMNISTACKAI_FALLBACK_PROVIDERS="ollama, anthropic, openai",
            OMNISTACKAI_CIRCUIT_FAILURE_THRESHOLD="2", OMNISTACKAI_CIRCUIT_COOLDOWN_SECONDS="45",
        )
        with patch.dict("os.environ", env, clear=True):
            boot = build_gateway_from_env()
        self.assertEqual(boot.fallback_provider_ids, ("ollama-local", "anthropic", "openai"))
        self.assertTrue(boot.breaker_enabled)
        self.assertEqual(boot.breaker_failure_threshold, 2)
        self.assertEqual(boot.breaker_cooldown_seconds, 45.0)

    def test_unknown_fallback_name_is_rejected(self) -> None:
        with patch.dict("os.environ", _env(OMNISTACKAI_FALLBACK_PROVIDERS="mystery"), clear=True):
            with self.assertRaises(CloudProviderSelectionError):
                build_gateway_from_env()

    def test_fallback_provider_without_key_is_rejected(self) -> None:
        with patch.dict("os.environ", _env(OMNISTACKAI_FALLBACK_PROVIDERS="anthropic"), clear=True):
            with self.assertRaises(CloudProviderSelectionError):
                build_gateway_from_env()
