import json
from unittest import TestCase
from unittest.mock import patch

from omnistackai_agent_engine.model_gateway import (
    ChatRole,
    FinishReason,
    Message,
    ModelRef,
    TokenUsage,
    UsageLedger,
    platform_overview,
)


class OverviewTests(TestCase):
    def test_lists_local_and_all_supported_cloud_providers(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            overview = platform_overview()
        provider_ids = {p["providerId"] for p in overview["providers"]}
        self.assertIn("ollama-local", provider_ids)
        self.assertEqual(
            provider_ids,
            {"ollama-local", "anthropic", "openai", "google-gemini", "openrouter", "groq"},
        )
        local = next(p for p in overview["providers"] if p["providerId"] == "ollama-local")
        self.assertEqual(local["tier"], "local")
        self.assertTrue(local["active"])
        # Cloud providers are inactive without a key.
        cloud = [p for p in overview["providers"] if p["tier"] == "cloud"]
        self.assertTrue(all(p["active"] is False for p in cloud))

    def test_routing_ladder_and_price_book_present(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            overview = platform_overview()
        self.assertEqual([r["level"] for r in overview["routingLadder"]], ["L0", "L1", "L2", "L3", "L4"])
        prices = {(r["providerId"], r["modelId"]) for r in overview["priceBook"]}
        self.assertIn(("ollama-local", "*"), prices)
        self.assertIn(("anthropic", "claude-sonnet-5"), prices)
        self.assertEqual(overview["routingMode"], "balanced")

    def test_active_flag_without_leaking_the_key(self) -> None:
        secret = "sk-super-secret-value-xyz"
        env = {"ANTHROPIC_API_KEY": secret, "OMNISTACKAI_CLOUD_PROVIDER": "anthropic"}
        with patch.dict("os.environ", env, clear=True):
            overview = platform_overview()
        anthropic = next(p for p in overview["providers"] if p["providerId"] == "anthropic")
        self.assertTrue(anthropic["active"])
        self.assertEqual(overview["cloudTierSelected"], "anthropic")
        # The key value must never appear anywhere in the serialized snapshot.
        self.assertNotIn(secret, json.dumps(overview))

    def test_model_override_is_reflected(self) -> None:
        with patch.dict("os.environ", {"OMNISTACKAI_OPENAI_MODEL": "gpt-custom"}, clear=True):
            overview = platform_overview()
        openai = next(p for p in overview["providers"] if p["providerId"] == "openai")
        self.assertEqual(openai["defaultModel"], "gpt-custom")

    def test_usage_summary_is_serialized_from_the_ledger(self) -> None:
        ledger = UsageLedger()
        ledger.record_call(
            request_id="r", provider_id="ollama-local", model_id="qwen2.5-coder:14b",
            tier="local", complexity="L2", usage=TokenUsage(10, 5), latency_ms=7, success=True,
            finish_reason=FinishReason.STOP.value,
        )
        with patch.dict("os.environ", {}, clear=True):
            overview = platform_overview(ledger=ledger)
        usage = overview["usage"]
        self.assertEqual(usage["totalCalls"], 1)
        self.assertEqual(usage["successfulCalls"], 1)
        self.assertEqual(usage["totalCostUsd"], "0.000000")
        self.assertEqual(usage["breakdowns"][0]["providerId"], "ollama-local")

    def test_snapshot_is_json_serializable(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            json.dumps(platform_overview())  # must not raise
        # Message/ModelRef imports kept to assert the public API stays importable.
        self.assertEqual(Message(ChatRole.USER, "x").role, ChatRole.USER)
        self.assertEqual(ModelRef("openai", "gpt-4o").provider_id, "openai")
