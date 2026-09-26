"""Unit tests for dynamic generation provider resolution (Groq and Ollama)."""

import unittest
from unittest.mock import patch

from omnistackai_agent_engine.intake.provider_resolution import resolve_generation_provider_from_env
from omnistackai_agent_engine.model_gateway.accounting import UsageLedger
from omnistackai_agent_engine.model_gateway.ollama import OllamaProvider
from omnistackai_agent_engine.model_gateway.recording import RecordingProvider


class TestProviderResolution(unittest.TestCase):
    def test_default_falls_back_to_ollama(self) -> None:
        with patch.dict("os.environ", {"OMNISTACKAI_CLOUD_PROVIDER": "none"}, clear=True):
            provider, model_id, max_output, timeout = resolve_generation_provider_from_env(load_dotenv=False)
            self.assertIsInstance(provider, OllamaProvider)
            self.assertEqual(model_id, "qwen2.5-coder:14b")
            self.assertGreater(max_output, 0)
            self.assertGreater(timeout, 0)

    def test_groq_resolution_when_key_present(self) -> None:
        env = {
            "OMNISTACKAI_CLOUD_PROVIDER": "groq",
            "GROQ_API_KEY": "gsk_dummy_test_key_12345",
        }
        with patch.dict("os.environ", env, clear=True):
            provider, model_id, max_output, timeout = resolve_generation_provider_from_env(load_dotenv=False)
            self.assertEqual(getattr(provider, "provider_id", ""), "groq")
            self.assertEqual(model_id, "openai/gpt-oss-120b")
            self.assertEqual(max_output, 4096)
            self.assertEqual(timeout, 120.0)

    def test_missing_key_falls_back_to_ollama(self) -> None:
        env = {
            "OMNISTACKAI_CLOUD_PROVIDER": "groq",
            "GROQ_API_KEY": "",  # Empty key
        }
        with patch.dict("os.environ", env, clear=True):
            provider, model_id, max_output, timeout = resolve_generation_provider_from_env(load_dotenv=False)
            self.assertIsInstance(provider, OllamaProvider)

    def test_default_usage_ledger_is_none_and_provider_stays_unwrapped(self) -> None:
        with patch.dict("os.environ", {"OMNISTACKAI_CLOUD_PROVIDER": "none"}, clear=True):
            provider, _, _, _ = resolve_generation_provider_from_env(load_dotenv=False)
            self.assertNotIsInstance(provider, RecordingProvider)
            self.assertIsInstance(provider, OllamaProvider)

    def test_ollama_fallback_wrapped_in_recording_provider_when_ledger_given(self) -> None:
        ledger = UsageLedger()
        with patch.dict("os.environ", {"OMNISTACKAI_CLOUD_PROVIDER": "none"}, clear=True):
            provider, model_id, _, _ = resolve_generation_provider_from_env(
                load_dotenv=False, usage_ledger=ledger
            )
            self.assertIsInstance(provider, RecordingProvider)
            self.assertEqual(provider.provider_id, "ollama-local")
            self.assertEqual(model_id, "qwen2.5-coder:14b")
            self.assertEqual(len(ledger), 0)  # resolution alone makes no generate() call

    def test_groq_resolution_wrapped_in_recording_provider_when_ledger_given(self) -> None:
        ledger = UsageLedger()
        env = {
            "OMNISTACKAI_CLOUD_PROVIDER": "groq",
            "GROQ_API_KEY": "gsk_dummy_test_key_12345",
        }
        with patch.dict("os.environ", env, clear=True):
            provider, model_id, _, _ = resolve_generation_provider_from_env(
                load_dotenv=False, usage_ledger=ledger
            )
            self.assertIsInstance(provider, RecordingProvider)
            self.assertEqual(provider.provider_id, "groq")
            self.assertEqual(model_id, "openai/gpt-oss-120b")


if __name__ == "__main__":
    unittest.main()
