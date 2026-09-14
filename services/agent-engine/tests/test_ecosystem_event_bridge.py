"""Unit and integration tests for Ecosystem Cross-Surface Webhook and Event Bridge (R-448)."""

from __future__ import annotations

import json
import time
import unittest
from unittest.mock import MagicMock

from omnistackai_agent_engine.application_ir import (
    ApplicationIR,
    Entity,
    Field,
    FieldType,
    Platform,
    ProjectStrategy,
    Role,
    Screen,
)
from omnistackai_agent_engine.solution_packs.ecosystem_events import (
    EcosystemEventBridge,
    EcosystemEventBridgeContract,
    EcosystemEventPayload,
    EcosystemWebhookSubscription,
    WebhookRetryPolicy,
    sign_webhook_payload,
    synthesize_ecosystem_events,
    verify_webhook_signature,
)
from omnistackai_agent_engine.solution_packs.ecosystem_pack import (
    EcosystemSurfacePackage,
    parse_ecosystem_pack_package,
    synthesize_ecosystem_pack,
)
from omnistackai_agent_engine.solution_packs.ecosystem_registry import (
    DEFAULT_ECOSYSTEM_PACK_REGISTRY,
)
from omnistackai_agent_engine.studio.preview import StudioPreviewManager
from omnistackai_agent_engine.solution_packs.ecosystem_cli import run_events, build_parser


class TestWebhookHMACSigning(unittest.TestCase):
    def setUp(self) -> None:
        self.secret = "test-webhook-secret-xyz123"
        self.payload = b'{"event_id":"evt-123","event_type":"post.created","ecosystem_id":"eco-1"}'

    def test_sign_and_verify_success(self) -> None:
        sig = sign_webhook_payload(self.payload, self.secret)
        self.assertTrue(sig.startswith("sha256="))
        self.assertTrue(verify_webhook_signature(self.payload, sig, self.secret))

    def test_verify_tampered_payload_fails(self) -> None:
        sig = sign_webhook_payload(self.payload, self.secret)
        tampered = b'{"event_id":"evt-123","event_type":"post.created","ecosystem_id":"eco-tampered"}'
        self.assertFalse(verify_webhook_signature(tampered, sig, self.secret))

    def test_verify_wrong_secret_fails(self) -> None:
        sig = sign_webhook_payload(self.payload, self.secret)
        self.assertFalse(verify_webhook_signature(self.payload, sig, "wrong-secret"))

    def test_verify_malformed_sig_fails(self) -> None:
        self.assertFalse(verify_webhook_signature(self.payload, "invalid-sig", self.secret))
        self.assertFalse(verify_webhook_signature(self.payload, "", self.secret))


class TestEventBridgeContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.retry_policy = WebhookRetryPolicy(max_retries=3, backoff_seconds=1.0, timeout_seconds=5.0)
        self.subscription = EcosystemWebhookSubscription(
            subscription_id="sub-1",
            event_type="post.created",
            source_surface="writer-portal",
            target_surface="public-web",
            webhook_path="/api/webhooks/post-created",
            secret_ref="eco:webhook_secret",
            retry_policy=self.retry_policy,
            is_active=True,
        )
        self.contract = EcosystemEventBridgeContract(
            ecosystem_id="eco-test",
            version="1.0.0",
            signature_algorithm="HMAC-SHA256",
            signature_header="X-OmniStack-Signature",
            idempotency_header="X-Idempotency-Key",
            event_type_header="X-OmniStack-Event-Type",
            secret_ref="eco:webhook_secret",
            subscriptions=(self.subscription,),
            supported_events=("post.created", "post.updated"),
        )

    def test_to_dict_and_from_dict_roundtrip(self) -> None:
        d = self.contract.to_dict()
        reconstructed = EcosystemEventBridgeContract.from_dict(d)
        self.assertEqual(reconstructed.ecosystem_id, self.contract.ecosystem_id)
        self.assertEqual(reconstructed.version, self.contract.version)
        self.assertEqual(reconstructed.signature_header, self.contract.signature_header)
        self.assertEqual(reconstructed.supported_events, self.contract.supported_events)
        self.assertEqual(len(reconstructed.subscriptions), 1)
        sub = reconstructed.subscriptions[0]
        self.assertEqual(sub.subscription_id, "sub-1")
        self.assertEqual(sub.event_type, "post.created")
        self.assertEqual(sub.retry_policy.max_retries, 3)

    def test_event_payload_auto_idempotency_key(self) -> None:
        p1 = EcosystemEventPayload(
            event_id="evt-1",
            event_type="order.created",
            ecosystem_id="eco-1",
            source_surface="mobile",
            timestamp=1234567890.0,
            entity_name="Order",
            entity_id="ord-99",
            action="create",
            data={"amount": 100},
        )
        self.assertTrue(len(p1.idempotency_key) > 0)
        # Identical parameters yield same idempotency key
        p2 = EcosystemEventPayload(
            event_id="evt-2",
            event_type="order.created",
            ecosystem_id="eco-1",
            source_surface="mobile",
            timestamp=1234567890.0,
            entity_name="Order",
            entity_id="ord-99",
            action="create",
            data={"amount": 100},
        )
        self.assertEqual(p1.idempotency_key, p2.idempotency_key)


class TestEcosystemEventBridge(unittest.TestCase):
    def setUp(self) -> None:
        self.retry_policy = WebhookRetryPolicy(max_retries=1, backoff_seconds=0.1, timeout_seconds=1.0)
        self.sub1 = EcosystemWebhookSubscription(
            subscription_id="sub-1",
            event_type="post.created",
            source_surface="writer-portal",
            target_surface="public-web",
            webhook_path="/api/webhooks/post-created",
            secret_ref="eco:secret",
            retry_policy=self.retry_policy,
            is_active=True,
        )
        self.sub2 = EcosystemWebhookSubscription(
            subscription_id="sub-2",
            event_type="post.deleted",
            source_surface="writer-portal",
            target_surface="public-web",
            webhook_path="/api/webhooks/post-deleted",
            secret_ref="eco:secret",
            retry_policy=self.retry_policy,
            is_active=False,  # Inactive subscription should not receive events
        )
        self.contract = EcosystemEventBridgeContract(
            ecosystem_id="eco-blog",
            version="1.0.0",
            signature_algorithm="HMAC-SHA256",
            signature_header="X-OmniStack-Signature",
            idempotency_header="X-Idempotency-Key",
            event_type_header="X-OmniStack-Event-Type",
            secret_ref="eco:secret",
            subscriptions=(self.sub1, self.sub2),
            supported_events=("post.created", "post.deleted"),
        )
        self.bridge = EcosystemEventBridge(self.contract, secret="test-secret-key")

    def test_dispatch_matching_active_subscription(self) -> None:
        payload = EcosystemEventPayload(
            event_id="evt-101",
            event_type="post.created",
            ecosystem_id="eco-blog",
            source_surface="writer-portal",
            timestamp=time.time(),
            entity_name="Post",
            entity_id="p-1",
            action="create",
            data={"title": "New Post"},
        )
        records = self.bridge.dispatch(payload)
        self.assertEqual(len(records), 1)
        rec = records[0]
        self.assertEqual(rec.subscription_id, "sub-1")
        self.assertEqual(rec.event_id, "evt-101")
        self.assertEqual(rec.target_surface, "public-web")
        self.assertEqual(rec.status, "simulated")
        self.assertEqual(rec.status_code, 200)

        # Verify delivery log
        logs = self.bridge.get_delivery_log()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["delivery_id"], rec.delivery_id)

    def test_dispatch_inactive_subscription_ignored(self) -> None:
        payload = EcosystemEventPayload(
            event_id="evt-102",
            event_type="post.deleted",
            ecosystem_id="eco-blog",
            source_surface="writer-portal",
            timestamp=time.time(),
            entity_name="Post",
            entity_id="p-1",
            action="delete",
            data={},
        )
        records = self.bridge.dispatch(payload)
        self.assertEqual(len(records), 0)

    def test_delivery_log_capping(self) -> None:
        for i in range(120):
            payload = EcosystemEventPayload(
                event_id=f"evt-{i}",
                event_type="post.created",
                ecosystem_id="eco-blog",
                source_surface="writer-portal",
                timestamp=time.time(),
                entity_name="Post",
                entity_id=f"p-{i}",
                action="create",
                data={},
            )
            self.bridge.dispatch(payload)

        logs = self.bridge.get_delivery_log()
        self.assertEqual(len(logs), 100)  # Capped at 100
        # Newest first: logs[0] is evt-119, logs[-1] is evt-20
        self.assertEqual(logs[0]["event_id"], "evt-119")
        self.assertEqual(logs[-1]["event_id"], "evt-20")

        self.bridge.clear_delivery_log()
        self.assertEqual(len(self.bridge.get_delivery_log()), 0)


class TestEcosystemEventSynthesis(unittest.TestCase):
    def _make_surfaces(self) -> tuple[dict, ...]:
        surf_admin = {
            "surface_kind": "admin",
            "app_name": "Admin Portal",
            "slug": "admin-portal",
            "ir_dict": {
                "entities": [{"name": "Post"}],
            },
        }
        surf_public = {
            "surface_kind": "customer",
            "app_name": "Public Web",
            "slug": "public-web",
            "ir_dict": {
                "entities": [{"name": "Post"}],
            },
        }
        return (surf_admin, surf_public)

    def test_synthesize_events_contract(self) -> None:
        surfaces = self._make_surfaces()
        contract = synthesize_ecosystem_events("blog-eco", surfaces)

        self.assertEqual(contract.ecosystem_id, "blog-eco")
        self.assertEqual(contract.signature_algorithm, "HMAC-SHA256")
        self.assertEqual(contract.signature_header, "X-OmniStack-Signature")
        self.assertEqual(contract.idempotency_header, "X-Idempotency-Key")
        self.assertTrue(len(contract.supported_events) > 0)
        self.assertTrue("post.created" in contract.supported_events)
        self.assertTrue("post.updated" in contract.supported_events)

        # Cross-surface subscription exists from admin-portal to public-web
        subs = [s for s in contract.subscriptions if s.target_surface == "public-web"]
        self.assertTrue(len(subs) > 0)
        self.assertEqual(subs[0].source_surface, "admin-portal")
        self.assertTrue(subs[0].is_active)


class TestEcosystemPackageWithEventBridge(unittest.TestCase):
    def test_synthesize_pack_includes_event_bridge(self) -> None:
        pkg = synthesize_ecosystem_pack("minimal-blog")
        self.assertIsNotNone(pkg.event_bridge)
        assert pkg.event_bridge is not None
        self.assertEqual(pkg.event_bridge.ecosystem_id, pkg.ecosystem_id)
        self.assertTrue(len(pkg.event_bridge.supported_events) > 0)
        self.assertTrue(len(pkg.event_bridge.subscriptions) > 0)

        # Serialization round-trip
        data = pkg.to_dict()
        self.assertIn("event_bridge", data)
        parsed = parse_ecosystem_pack_package(json.dumps(data).encode("utf-8"))
        self.assertIsNotNone(parsed.event_bridge)
        assert parsed.event_bridge is not None
        self.assertEqual(parsed.event_bridge.ecosystem_id, pkg.ecosystem_id)
        self.assertEqual(len(parsed.event_bridge.subscriptions), len(pkg.event_bridge.subscriptions))

    def test_registry_get_event_bridge(self) -> None:
        eco = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get("minimal-blog-ecosystem")
        self.assertIsNotNone(eco)
        assert eco is not None
        bridge = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_event_bridge("minimal-blog-ecosystem")
        self.assertIsNotNone(bridge)
        assert bridge is not None
        self.assertEqual(bridge.ecosystem_id, "minimal-blog-ecosystem")
        self.assertTrue(len(bridge.supported_events) > 0)


class FakeSurfaceSession:
    def __init__(self, repo_dir: str, *, web_port: int = 3000, api_port: int = 8000) -> None:
        from omnistackai_agent_engine.localrun import RunPlan

        self.repo_dir = repo_dir
        self.plan = RunPlan(
            repo_dir=repo_dir,
            app_slug=repo_dir.split("/")[-1],
            db_name="test_db",
            backend_kind="python",
            has_web=True,
            api_url=f"http://127.0.0.1:{api_port}",
            web_url=f"http://127.0.0.1:{web_port}",
            db_password="secret-password",
        )
        self.api_ready = True
        self.web_ready = True
        self.alive = True
        self.stop_calls = 0

    def is_alive(self) -> bool:
        return self.alive

    def stop(self) -> None:
        self.stop_calls += 1
        self.alive = False


class TestStudioPreviewManagerEventBridge(unittest.TestCase):
    def setUp(self) -> None:
        port_counter = [36000]

        def start_fn(repo_dir: str, log=None):
            w_port = port_counter[0]
            a_port = port_counter[0] + 1000
            port_counter[0] += 1
            return FakeSurfaceSession(repo_dir, web_port=w_port, api_port=a_port)

        self.mgr = StudioPreviewManager(start_fn=start_fn)
        self.surfaces = [
            {
                "surface_kind": "admin",
                "app_name": "Author Studio",
                "slug": "author-studio",
                "target_dir": "/tmp/dummy-author",
            },
            {
                "surface_kind": "customer",
                "app_name": "Minimal Blog",
                "slug": "minimal-blog",
                "target_dir": "/tmp/dummy-blog",
            },
        ]

    def tearDown(self) -> None:
        self.mgr.stop()

    def test_preview_manager_events_lifecycle(self) -> None:
        preview = self.mgr.replace_ecosystem("minimal-blog-ecosystem", self.surfaces)
        self.assertTrue(preview.get("has_events"))
        self.assertTrue(preview.get("subscription_count", 0) > 0)
        self.assertTrue(preview.get("event_count", 0) > 0)

        # Fetch ecosystem events
        events_data = self.mgr.get_ecosystem_events()
        self.assertEqual(events_data["ecosystem_id"], "minimal-blog-ecosystem")
        self.assertTrue(len(events_data["supported_events"]) > 0)
        self.assertEqual(len(events_data["deliveries"]), 0)

        # Dispatch an event
        dispatch_res = self.mgr.dispatch_ecosystem_event(
            event_type="post.created",
            entity_name="Post",
            entity_id="123",
            action="create",
            data={"title": "Test Title"},
            source_surface="author-studio",
        )
        self.assertEqual(dispatch_res["status"], "ok")
        self.assertTrue(dispatch_res["delivery_count"] > 0)
        self.assertEqual(len(dispatch_res["deliveries"]), dispatch_res["delivery_count"])

        # Check that delivery is now recorded
        events_data2 = self.mgr.get_ecosystem_events()
        self.assertEqual(len(events_data2["deliveries"]), dispatch_res["delivery_count"])
        self.assertEqual(events_data2["deliveries"][0]["event_id"], dispatch_res["event"]["event_id"])


class TestEcosystemCliEvents(unittest.TestCase):
    def test_cli_events_text_output(self) -> None:
        import io
        from contextlib import redirect_stdout

        parser = build_parser()
        args = parser.parse_args(["events", "minimal-blog-ecosystem"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = run_events(args)
        self.assertEqual(ret, 0)
        out = buf.getvalue()
        self.assertIn("Ecosystem Event Bridge", out)
        self.assertIn("Signature Algorithm: HMAC-SHA256", out)
        self.assertIn("Supported Events", out)
        self.assertIn("Webhook Subscriptions", out)

    def test_cli_events_json_output(self) -> None:
        import io
        from contextlib import redirect_stdout

        parser = build_parser()
        args = parser.parse_args(["events", "minimal-blog-ecosystem", "--json"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = run_events(args)
        self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["ecosystem_id"], "minimal-blog-ecosystem")
        self.assertEqual(data["signature_algorithm"], "HMAC-SHA256")
        self.assertTrue(len(data["supported_events"]) > 0)
        self.assertTrue(len(data["subscriptions"]) > 0)


if __name__ == "__main__":
    unittest.main()
