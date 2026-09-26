"""PC-047: NVIDIA is a first-class model provider, configured from the founder's .env names.

The founder put three names in .env — NVIDIA_API_KEY, OMNISTACKAI_NVIDIA_MODEL and
NVIDIA_MODEL_BASE_URL — and asked that builds be able to use them. Every name is honoured as
written, so the existing file works unchanged.

The base-URL override is the one new mechanism. It is the obvious way to point a key at a host of
one's choosing, so the adapter's HTTPS-only rule is what keeps it safe: an `http://` override is
refused rather than used, and the key never travels in a URL.

Everything here is offline. The one real call lives outside `task verify` (see the task record).
"""

import asyncio
import json
import logging
from unittest import TestCase
from unittest.mock import patch

from omnistackai_agent_engine.model_gateway import (
    DEFAULT_PRICE_BOOK,
    ChatRole,
    GenerateRequest,
    InvalidProviderConfigurationError,
    Message,
    OpenAICompatibleProvider,
    PROVIDER_SPECS,
    TokenUsage,
    build_gateway_from_env,
    create_cloud_provider,
    platform_overview,
)
from omnistackai_agent_engine.model_gateway.cloud import configured_base_url
from omnistackai_agent_engine.intake.provider_resolution import resolve_generation_provider_from_env

from test_provider_catalog import BASE_ENV, _CapturingOpener, _descriptor

FAKE_KEY = "nvapi-unit-test-key-do-not-use"
MODEL = "nvidia/nemotron-3-ultra-550b-a55b"


def _ok_opener() -> _CapturingOpener:
    return _CapturingOpener(
        {
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 1},
        }
    )


def _request(descriptor):
    return GenerateRequest(
        request_id="req-nv",
        model=descriptor.model,
        messages=(Message(ChatRole.USER, "hello"),),
        max_output_tokens=16,
        timeout_seconds=5.0,
    )


class TheSpecUsesTheFoundersNames(TestCase):
    def test_nvidia_is_a_builtin_openai_compatible_provider(self) -> None:
        spec = PROVIDER_SPECS["nvidia"]
        self.assertEqual(spec.kind, "openai")
        self.assertEqual(spec.base_url, "https://integrate.api.nvidia.com/v1")
        self.assertEqual(spec.default_model, MODEL)

    def test_the_env_names_are_exactly_the_ones_in_the_founders_env(self) -> None:
        spec = PROVIDER_SPECS["nvidia"]
        self.assertEqual(spec.key_env, "NVIDIA_API_KEY")
        self.assertEqual(spec.model_env, "OMNISTACKAI_NVIDIA_MODEL")
        self.assertEqual(spec.base_url_env, "NVIDIA_MODEL_BASE_URL")


class TheBaseUrlOverride(TestCase):
    def test_unset_means_the_default(self) -> None:
        self.assertEqual(configured_base_url(PROVIDER_SPECS["nvidia"], {}), "https://integrate.api.nvidia.com/v1")

    def test_set_means_the_override(self) -> None:
        env = {"NVIDIA_MODEL_BASE_URL": "https://nim.internal.example/v1"}
        self.assertEqual(configured_base_url(PROVIDER_SPECS["nvidia"], env), "https://nim.internal.example/v1")

    def test_a_provider_without_an_override_name_ignores_the_env(self) -> None:
        # Only a spec that names an override variable can be redirected.
        env = {"NVIDIA_MODEL_BASE_URL": "https://elsewhere.example/v1"}
        self.assertEqual(configured_base_url(PROVIDER_SPECS["deepseek"], env), PROVIDER_SPECS["deepseek"].base_url)

    def test_requests_go_to_the_override(self) -> None:
        spec = PROVIDER_SPECS["nvidia"]
        descriptor = _descriptor(spec.provider_id, MODEL)
        opener = _ok_opener()
        with patch.dict("os.environ", {"NVIDIA_MODEL_BASE_URL": "https://nim.internal.example/v1"}, clear=True):
            provider = create_cloud_provider(spec, api_key=FAKE_KEY, descriptor=descriptor, opener=opener)
        asyncio.run(provider.generate(_request(descriptor)))
        self.assertTrue(opener.requests[0].full_url.startswith("https://nim.internal.example/v1/chat/completions"))

    def test_a_plain_http_override_is_refused_not_used(self) -> None:
        # The override is the way to aim a key at a chosen host; HTTPS-only is what keeps it safe.
        spec = PROVIDER_SPECS["nvidia"]
        with patch.dict("os.environ", {"NVIDIA_MODEL_BASE_URL": "http://nim.internal.example/v1"}, clear=True):
            with self.assertRaises(InvalidProviderConfigurationError):
                create_cloud_provider(spec, api_key=FAKE_KEY, descriptor=_descriptor("nvidia", MODEL))


class ARequestLooksRight(TestCase):
    def test_it_hits_chat_completions_with_a_bearer_key_never_in_the_url(self) -> None:
        spec = PROVIDER_SPECS["nvidia"]
        descriptor = _descriptor(spec.provider_id, MODEL)
        opener = _ok_opener()
        with patch.dict("os.environ", {}, clear=True):
            provider = create_cloud_provider(spec, api_key=FAKE_KEY, descriptor=descriptor, opener=opener)
        self.assertIsInstance(provider, OpenAICompatibleProvider)
        response = asyncio.run(provider.generate(_request(descriptor)))
        self.assertEqual(response.text, "ok")
        sent = opener.requests[0]
        self.assertEqual(sent.full_url, "https://integrate.api.nvidia.com/v1/chat/completions")
        self.assertNotIn(FAKE_KEY, sent.full_url)
        self.assertEqual(sent.headers.get("Authorization"), f"Bearer {FAKE_KEY}")
        self.assertEqual(json.loads(sent.data)["model"], MODEL)

    def test_the_key_is_not_logged(self) -> None:
        spec = PROVIDER_SPECS["nvidia"]
        descriptor = _descriptor(spec.provider_id, MODEL)
        with patch.dict("os.environ", {}, clear=True), self.assertLogs(level=logging.DEBUG) as logs:
            logging.getLogger("omnistackai.test").debug("capture on")
            provider = create_cloud_provider(spec, api_key=FAKE_KEY, descriptor=descriptor, opener=_ok_opener())
            asyncio.run(provider.generate(_request(descriptor)))
        self.assertNotIn(FAKE_KEY, "\n".join(logs.output))


class ItCanBeSelectedEveryWayAProviderCanBe(TestCase):
    def test_as_the_cloud_tier(self) -> None:
        env = {**BASE_ENV, "NVIDIA_API_KEY": FAKE_KEY, "OMNISTACKAI_CLOUD_PROVIDER": "nvidia"}
        with patch.dict("os.environ", env, clear=True):
            boot = build_gateway_from_env()
        self.assertIn("nvidia", boot.registered_provider_ids)
        self.assertEqual(boot.cloud_tier_provider_id, "nvidia")

    def test_as_an_explicit_per_project_provider(self) -> None:
        env = {**BASE_ENV, "NVIDIA_API_KEY": FAKE_KEY, "OMNISTACKAI_NVIDIA_MODEL": MODEL}
        with patch.dict("os.environ", env, clear=True):
            _provider, model_id, _max_out, _timeout = resolve_generation_provider_from_env(
                load_dotenv=False, provider_id="nvidia"
            )
        self.assertEqual(model_id, MODEL)

    def test_it_stays_inactive_without_a_key(self) -> None:
        with patch.dict("os.environ", dict(BASE_ENV), clear=True):
            boot = build_gateway_from_env()
        self.assertNotIn("nvidia", boot.registered_provider_ids)


class ItIsVisibleAndHonestAboutCost(TestCase):
    def test_the_console_overview_lists_it(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            overview = platform_overview()
        self.assertIn("nvidia", {p["providerId"] for p in overview["providers"]})

    def test_it_is_unpriced_rather_than_guessed(self) -> None:
        # No per-token price was verified. A guessed one would mis-charge credits; None is honest.
        self.assertIsNone(DEFAULT_PRICE_BOOK.cost_for("nvidia", MODEL, TokenUsage(1000, 1000)))
