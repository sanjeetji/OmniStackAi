"""Tests for R-504 AI model configuration, BYOK resolution, and call tracking."""

import unittest
from unittest.mock import patch

from omnistackai_agent_engine.intake.provider_resolution import resolve_generation_provider_from_env
from omnistackai_agent_engine.model_gateway.accounting import UsageLedger
from omnistackai_agent_engine.model_gateway.contracts import TokenUsage
from omnistackai_agent_engine.model_gateway.recording import RecordingProvider
from omnistackai_agent_engine.studio.live_serve import _usage_summary_to_dict


class TestStudioWorkspaceAI(unittest.TestCase):
    def test_usage_summary_to_dict_includes_calls(self) -> None:
        ledger = UsageLedger()
        ledger.record_call(
            request_id="req-123",
            provider_id="groq",
            model_id="llama-3.3-70b-versatile",
            tier="production",
            complexity="moderate",
            usage=TokenUsage(input_tokens=100, output_tokens=50),
            latency_ms=350,
            success=True,
        )
        ledger.record_call(
            request_id="req-124",
            provider_id="groq",
            model_id="llama-3.3-70b-versatile",
            tier="production",
            complexity="complex",
            usage=None,
            latency_ms=120,
            success=False,
            error_code="rate_limit_exceeded",
        )

        res = _usage_summary_to_dict(ledger)
        self.assertEqual(res["total_calls"], 2)
        self.assertEqual(res["successful_calls"], 1)
        self.assertEqual(res["failed_calls"], 1)
        self.assertIn("calls", res)
        self.assertEqual(len(res["calls"]), 2)

        c1 = res["calls"][0]
        self.assertEqual(c1["request_id"], "req-123")
        self.assertEqual(c1["provider_id"], "groq")
        self.assertEqual(c1["model_id"], "llama-3.3-70b-versatile")
        self.assertEqual(c1["input_tokens"], 100)
        self.assertEqual(c1["output_tokens"], 50)
        self.assertEqual(c1["latency_ms"], 350)
        self.assertTrue(c1["success"])
        self.assertIsNone(c1["error_code"])
        self.assertGreaterEqual(c1["cost_micros_usd"], 0)

        c2 = res["calls"][1]
        self.assertEqual(c2["request_id"], "req-124")
        self.assertFalse(c2["success"])
        self.assertEqual(c2["error_code"], "rate_limit_exceeded")
        self.assertEqual(c2["cost_micros_usd"], 0)

    def test_resolve_explicit_openai_provider_and_key(self) -> None:
        ledger = UsageLedger()
        provider, model_id, max_output, timeout = resolve_generation_provider_from_env(
            load_dotenv=False,
            usage_ledger=ledger,
            provider_id="openai",
            model_id="gpt-4o",
            api_key="sk-test-openai-key-12345",
        )
        self.assertIsInstance(provider, RecordingProvider)
        self.assertEqual(provider.provider_id, "openai")
        self.assertEqual(model_id, "gpt-4o")
        self.assertGreater(max_output, 0)
        self.assertGreater(timeout, 0)

    def test_resolve_explicit_anthropic_provider_and_key(self) -> None:
        ledger = UsageLedger()
        provider, model_id, max_output, timeout = resolve_generation_provider_from_env(
            load_dotenv=False,
            usage_ledger=ledger,
            provider_id="anthropic",
            model_id="claude-3-5-sonnet-20241022",
            api_key="sk-ant-test-key-12345",
        )
        self.assertIsInstance(provider, RecordingProvider)
        self.assertEqual(provider.provider_id, "anthropic")
        self.assertEqual(model_id, "claude-3-5-sonnet-20241022")

    def test_resolve_explicit_ollama_provider(self) -> None:
        ledger = UsageLedger()
        provider, model_id, max_output, timeout = resolve_generation_provider_from_env(
            load_dotenv=False,
            usage_ledger=ledger,
            provider_id="ollama",
            model_id="codellama:13b",
        )
        self.assertIsInstance(provider, RecordingProvider)
        self.assertEqual(provider.provider_id, "ollama-local")
        self.assertEqual(model_id, "codellama:13b")


if __name__ == "__main__":
    unittest.main()
