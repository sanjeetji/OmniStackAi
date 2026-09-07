import asyncio
import json
from unittest import TestCase
from unittest.mock import patch

from omnistackai_agent_engine.model_gateway import (
    CapabilityStatus,
    ChatRole,
    DEFAULT_PRICE_BOOK,
    GenerateRequest,
    InvalidProviderConfigurationError,
    Message,
    ModelCapabilities,
    ModelDescriptor,
    ModelRef,
    OpenAICompatibleProvider,
    PROVIDER_SPECS,
    TokenUsage,
    build_gateway_from_env,
    create_cloud_provider,
    custom_provider_specs_from_env,
    platform_overview,
    resolve_provider_specs,
)

NEW_BUILTINS = ("deepseek", "xai", "mistral", "together", "fireworks")
FAKE_KEY = "unit-test-key-do-not-use"

BASE_ENV = {
    "OMNISTACKAI_OLLAMA_BASE_URL": "http://127.0.0.1:11434",
    "OMNISTACKAI_OLLAMA_MODEL": "qwen2.5-coder:14b",
}


def _descriptor(provider_id: str, model_id: str) -> ModelDescriptor:
    return ModelDescriptor(
        ModelRef(provider_id, model_id),
        ModelCapabilities(
            text=CapabilityStatus.UNVERIFIED,
            streaming=CapabilityStatus.UNVERIFIED,
            tool_calling=CapabilityStatus.UNSUPPORTED,
            structured_output=CapabilityStatus.UNSUPPORTED,
            vision=CapabilityStatus.UNSUPPORTED,
            embeddings=CapabilityStatus.UNSUPPORTED,
        ),
        8192,
        6144,
        1024,
    )


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body
        self.status = 200

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def read(self, _n: int = -1) -> bytes:
        return self._body


class _CapturingOpener:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode()
        self.requests: list = []

    def open(self, request, timeout=None):  # noqa: ANN001
        self.requests.append(request)
        return _FakeResponse(self._body)


class NewBuiltinSpecTests(TestCase):
    def test_new_providers_are_openai_compatible_with_https_and_distinct_keys(self) -> None:
        for name in NEW_BUILTINS:
            self.assertIn(name, PROVIDER_SPECS, name)
            spec = PROVIDER_SPECS[name]
            self.assertEqual(spec.kind, "openai", name)
            self.assertTrue(spec.base_url.startswith("https://"), name)
            self.assertTrue(spec.key_env and spec.model_env and spec.default_model, name)

    def test_all_key_envs_are_unique(self) -> None:
        key_envs = [spec.key_env for spec in PROVIDER_SPECS.values()]
        self.assertEqual(len(key_envs), len(set(key_envs)))


class AdapterConstructionTests(TestCase):
    def test_new_spec_builds_openai_adapter_and_dispatches(self) -> None:
        spec = PROVIDER_SPECS["deepseek"]
        descriptor = _descriptor(spec.provider_id, spec.default_model)
        opener = _CapturingOpener(
            {
                "choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 1},
            }
        )
        provider = create_cloud_provider(spec, api_key=FAKE_KEY, descriptor=descriptor, opener=opener)
        self.assertIsInstance(provider, OpenAICompatibleProvider)
        request = GenerateRequest(
            request_id="req-1",
            model=descriptor.model,
            messages=(Message(ChatRole.USER, "hello"),),
            max_output_tokens=16,
            timeout_seconds=5.0,
        )
        response = asyncio.run(provider.generate(request))
        self.assertEqual(response.text, "hi")
        # the request targets the deepseek base URL + chat completions, and never carries the key in the URL
        sent = opener.requests[0]
        self.assertTrue(sent.full_url.startswith("https://api.deepseek.com/v1/chat/completions"))
        self.assertNotIn(FAKE_KEY, sent.full_url)
        self.assertEqual(sent.headers.get("Authorization"), f"Bearer {FAKE_KEY}")


class CustomProviderTests(TestCase):
    def _env(self, **extra: str) -> dict[str, str]:
        return {
            "OMNISTACKAI_CUSTOM_PROVIDERS": "myco",
            "OMNISTACKAI_CUSTOM_MYCO_BASE_URL": "https://llm.myco.internal/v1",
            "OMNISTACKAI_CUSTOM_MYCO_MODEL": "myco-large",
            **extra,
        }

    def test_valid_custom_provider_parses(self) -> None:
        specs = custom_provider_specs_from_env(self._env())
        self.assertIn("myco", specs)
        spec = specs["myco"]
        self.assertEqual(spec.kind, "openai")
        self.assertEqual(spec.base_url, "https://llm.myco.internal/v1")
        self.assertEqual(spec.default_model, "myco-large")
        self.assertEqual(spec.key_env, "OMNISTACKAI_CUSTOM_MYCO_API_KEY")

    def test_collision_with_builtin_errors(self) -> None:
        env = {"OMNISTACKAI_CUSTOM_PROVIDERS": "openai"}
        with self.assertRaises(InvalidProviderConfigurationError):
            custom_provider_specs_from_env(env)

    def test_non_https_base_url_errors(self) -> None:
        env = self._env(OMNISTACKAI_CUSTOM_MYCO_BASE_URL="http://insecure.internal/v1")
        with self.assertRaises(InvalidProviderConfigurationError):
            custom_provider_specs_from_env(env)

    def test_missing_model_errors(self) -> None:
        env = self._env(OMNISTACKAI_CUSTOM_MYCO_MODEL="")
        with self.assertRaises(InvalidProviderConfigurationError):
            custom_provider_specs_from_env(env)

    def test_bad_id_errors(self) -> None:
        env = {"OMNISTACKAI_CUSTOM_PROVIDERS": "Bad Id"}
        with self.assertRaises(InvalidProviderConfigurationError):
            custom_provider_specs_from_env(env)

    def test_resolve_merges_builtins_and_custom(self) -> None:
        specs = resolve_provider_specs(self._env())
        self.assertIn("myco", specs)
        self.assertIn("openai", specs)
        self.assertIn("deepseek", specs)


class BootstrapCatalogTests(TestCase):
    def _env(self, **extra: str) -> dict[str, str]:
        return {**BASE_ENV, **extra}

    def test_new_builtin_registers_and_selects_as_cloud_tier(self) -> None:
        env = self._env(DEEPSEEK_API_KEY=FAKE_KEY, OMNISTACKAI_CLOUD_PROVIDER="deepseek")
        with patch.dict("os.environ", env, clear=True):
            boot = build_gateway_from_env()
        self.assertIn("deepseek", boot.registered_provider_ids)
        self.assertEqual(boot.cloud_tier_provider_id, "deepseek")

    def test_custom_provider_registers_selects_and_chains(self) -> None:
        env = self._env(
            OMNISTACKAI_CUSTOM_PROVIDERS="myco",
            OMNISTACKAI_CUSTOM_MYCO_BASE_URL="https://llm.myco.internal/v1",
            OMNISTACKAI_CUSTOM_MYCO_MODEL="myco-large",
            OMNISTACKAI_CUSTOM_MYCO_API_KEY=FAKE_KEY,
            OMNISTACKAI_CLOUD_PROVIDER="myco",
            OMNISTACKAI_FALLBACK_PROVIDERS="myco,ollama",
        )
        with patch.dict("os.environ", env, clear=True):
            boot = build_gateway_from_env()
        self.assertIn("myco", boot.registered_provider_ids)
        self.assertEqual(boot.cloud_tier_provider_id, "myco")
        self.assertEqual(boot.fallback_provider_ids, ("myco", "ollama-local"))

    def test_declared_custom_without_key_is_inactive(self) -> None:
        env = self._env(
            OMNISTACKAI_CUSTOM_PROVIDERS="myco",
            OMNISTACKAI_CUSTOM_MYCO_BASE_URL="https://llm.myco.internal/v1",
            OMNISTACKAI_CUSTOM_MYCO_MODEL="myco-large",
        )
        with patch.dict("os.environ", env, clear=True):
            boot = build_gateway_from_env()
        self.assertNotIn("myco", boot.registered_provider_ids)


class OverviewAndPriceTests(TestCase):
    def test_overview_lists_new_and_custom_without_leaking_keys(self) -> None:
        env = {
            **BASE_ENV,
            "DEEPSEEK_API_KEY": FAKE_KEY,
            "OMNISTACKAI_CUSTOM_PROVIDERS": "myco",
            "OMNISTACKAI_CUSTOM_MYCO_BASE_URL": "https://llm.myco.internal/v1",
            "OMNISTACKAI_CUSTOM_MYCO_MODEL": "myco-large",
            "OMNISTACKAI_CUSTOM_MYCO_API_KEY": FAKE_KEY,
        }
        with patch.dict("os.environ", env, clear=True):
            snapshot = platform_overview()
        ids = {p["providerId"] for p in snapshot["providers"]}
        self.assertIn("deepseek", ids)
        self.assertIn("myco", ids)
        by_id = {p["providerId"]: p for p in snapshot["providers"]}
        self.assertTrue(by_id["deepseek"]["active"])  # key present
        self.assertTrue(by_id["myco"]["active"])
        self.assertNotIn(FAKE_KEY, json.dumps(snapshot))

    def test_priced_new_provider_and_unpriced_custom(self) -> None:
        self.assertIsNotNone(DEFAULT_PRICE_BOOK.get("deepseek", "deepseek-chat"))
        self.assertIsNotNone(
            DEFAULT_PRICE_BOOK.cost_for("deepseek", "deepseek-chat", TokenUsage(1000, 1000))
        )
        self.assertIsNone(DEFAULT_PRICE_BOOK.get("myco", "myco-large"))
