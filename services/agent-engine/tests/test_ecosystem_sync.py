"""Tests for Solution Pack Ecosystem Data Sync, Conflict Resolution, and Offline-First Sync Protocol."""

from datetime import datetime, timezone
import io
import json
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen

from omnistackai_agent_engine.solution_packs.ecosystem_sync import (
    ConflictStrategy,
    EcosystemSyncContract,
    EcosystemSyncEngine,
    SyncCheckpoint,
    SyncConflict,
    SyncEntitySpec,
    SyncMutation,
    resolve_sync_conflict,
    synthesize_ecosystem_sync,
)


class FakePlan:
    has_web = True
    web_url = "http://127.0.0.1:3000"
    api_url = None
    backend_kind = "none"


class FakeSession:
    plan = FakePlan()
    web_ready = True
    api_ready = False

    def is_alive(self):
        return True

    def stop(self):
        pass


class TestEcosystemSyncContracts(unittest.TestCase):
    def test_sync_contracts_roundtrip(self):
        spec = SyncEntitySpec(
            entity_name="Article",
            sync_mode="bidirectional",
            conflict_strategy="field_merge",
            source_of_truth_surface="admin-web",
            immutable_fields=("id", "created_at"),
        )
        spec_dict = spec.to_dict()
        restored_spec = SyncEntitySpec.from_dict(spec_dict)
        self.assertEqual(restored_spec, spec)

        mut = SyncMutation(
            mutation_id="mut-001",
            entity_name="Article",
            record_id="rec-123",
            action="update",
            payload={"title": "Hello World", "views": 42},
            timestamp="2026-09-14T12:00:00Z",
            surface_slug="consumer-web",
            client_mutation_id="client-mut-99",
            version=1,
            base_version=0,
        )
        mut_dict = mut.to_dict()
        restored_mut = SyncMutation.from_dict(mut_dict)
        self.assertEqual(restored_mut, mut)

        chk = SyncCheckpoint(
            surface_slug="consumer-web",
            last_synced_version=5,
            last_synced_at="2026-09-14T12:05:00Z",
        )
        chk_dict = chk.to_dict()
        restored_chk = SyncCheckpoint.from_dict(chk_dict)
        self.assertEqual(restored_chk, chk)

        contract = EcosystemSyncContract(
            ecosystem_id="test-eco",
            version="1.0.0",
            sync_entities=(spec,),
            surface_policies={"consumer-web": "bidirectional", "admin-web": "bidirectional"},
            default_strategy="last_write_wins",
            offline_queue_max_size=500,
        )
        contract_dict = contract.to_dict()
        restored_contract = EcosystemSyncContract.from_dict(contract_dict)
        self.assertEqual(restored_contract, contract)

    def test_resolve_conflict_last_write_wins(self):
        m1 = SyncMutation(
            mutation_id="mut-01",
            entity_name="Post",
            record_id="p-1",
            action="update",
            payload={"title": "Old Title"},
            timestamp="2026-09-14T10:00:00Z",
            surface_slug="web",
        )
        m2 = SyncMutation(
            mutation_id="mut-02",
            entity_name="Post",
            record_id="p-1",
            action="update",
            payload={"title": "New Title"},
            timestamp="2026-09-14T11:00:00Z",
            surface_slug="mobile",
        )

        resolved, winner = resolve_sync_conflict(m1, m2, strategy="last_write_wins")
        self.assertEqual(winner, "mobile")
        self.assertEqual(resolved, {"title": "New Title"})

    def test_resolve_conflict_source_of_truth(self):
        m_admin = SyncMutation(
            mutation_id="mut-01",
            entity_name="Order",
            record_id="ord-1",
            action="update",
            payload={"status": "CANCELLED_BY_ADMIN"},
            timestamp="2026-09-14T10:00:00Z",
            surface_slug="admin",
        )
        m_user = SyncMutation(
            mutation_id="mut-02",
            entity_name="Order",
            record_id="ord-1",
            action="update",
            payload={"status": "COMPLETED_BY_USER"},
            timestamp="2026-09-14T11:00:00Z",
            surface_slug="user-web",
        )

        resolved, winner = resolve_sync_conflict(
            m_user,
            m_admin,
            strategy="source_of_truth",
            authoritative_surface="admin",
        )
        self.assertEqual(winner, "admin")
        self.assertEqual(resolved["status"], "CANCELLED_BY_ADMIN")

    def test_resolve_conflict_field_merge(self):
        m_author = SyncMutation(
            mutation_id="mut-01",
            entity_name="Post",
            record_id="p-1",
            action="update",
            payload={"id": "p-1", "created_at": "2026-01-01", "content": "Updated content by author"},
            timestamp="2026-09-14T10:00:00Z",
            surface_slug="author-app",
        )
        m_editor = SyncMutation(
            mutation_id="mut-02",
            entity_name="Post",
            record_id="p-1",
            action="update",
            payload={"id": "p-1", "created_at": "2026-01-01", "title": "Polished title by editor"},
            timestamp="2026-09-14T11:00:00Z",
            surface_slug="editorial-app",
        )

        resolved, winner = resolve_sync_conflict(
            m_author,
            m_editor,
            strategy="field_merge",
        )
        self.assertEqual(resolved["id"], "p-1")
        self.assertEqual(resolved["content"], "Updated content by author")
        self.assertEqual(resolved["title"], "Polished title by editor")


class TestEcosystemSyncEngine(unittest.TestCase):
    def test_sync_engine_push_and_pull(self):
        contract = EcosystemSyncContract(
            ecosystem_id="blog-eco",
            version="1.0.0",
            sync_entities=(
                SyncEntitySpec(
                    entity_name="Post",
                    sync_mode="bidirectional",
                    conflict_strategy="field_merge",
                    source_of_truth_surface="admin",
                ),
            ),
            surface_policies={"web": "bidirectional", "admin": "bidirectional"},
        )
        engine = EcosystemSyncEngine(contract)

        # 1. Surface A pushes initial creation
        m1 = SyncMutation(
            mutation_id="m-01",
            entity_name="Post",
            record_id="p-100",
            action="create",
            payload={"id": "p-100", "title": "First Post", "draft": True},
            timestamp="2026-09-14T10:00:00Z",
            surface_slug="web",
        )
        accepted, conflicts = engine.push_mutations("web", [m1])
        self.assertEqual(len(accepted), 1)
        self.assertEqual(len(conflicts), 0)
        self.assertEqual(engine.current_version, 1)
        self.assertEqual(engine.get_entity_state("Post", "p-100"), {"id": "p-100", "title": "First Post", "draft": True})

        # 2. Surface B pulls changes from version 0
        pulled, checkpoint = engine.pull_changes("admin", since_version=0)
        self.assertEqual(len(pulled), 1)
        self.assertEqual(pulled[0].record_id, "p-100")
        self.assertEqual(checkpoint.last_synced_version, 1)

        # 3. Surface B pushes an update
        m2 = SyncMutation(
            mutation_id="m-02",
            entity_name="Post",
            record_id="p-100",
            action="update",
            payload={"id": "p-100", "title": "First Post", "draft": False, "published_by": "admin"},
            timestamp="2026-09-14T10:05:00Z",
            surface_slug="admin",
            version=1,
        )
        accepted, conflicts = engine.push_mutations("admin", [m2])
        self.assertEqual(len(accepted), 1)
        self.assertEqual(len(conflicts), 0)
        self.assertEqual(engine.current_version, 2)

        # 4. Surface A pushes concurrent mutation based on stale version 1
        m3 = SyncMutation(
            mutation_id="m-03",
            entity_name="Post",
            record_id="p-100",
            action="update",
            payload={"id": "p-100", "title": "Renamed by Web", "draft": True},
            timestamp="2026-09-14T10:04:00Z",
            surface_slug="web",
            version=1,
        )
        accepted, conflicts = engine.push_mutations("web", [m3])
        self.assertEqual(len(conflicts), 1)
        conflict = conflicts[0]
        self.assertEqual(conflict.entity_name, "Post")
        self.assertEqual(conflict.record_id, "p-100")
        self.assertEqual(conflict.winning_surface, "admin")
        self.assertEqual(engine.conflict_count, 1)

    def test_sync_engine_delete(self):
        contract = EcosystemSyncContract(
            ecosystem_id="test-delete",
            version="1.0.0",
            sync_entities=(SyncEntitySpec(entity_name="Item"),),
            surface_policies={"web": "bidirectional"},
        )
        engine = EcosystemSyncEngine(contract)

        m1 = SyncMutation(
            mutation_id="m1",
            entity_name="Item",
            record_id="item-1",
            action="create",
            payload={"name": "Widget"},
            timestamp="2026-09-14T10:00:00Z",
            surface_slug="web",
        )
        engine.push_mutations("web", [m1])
        self.assertEqual(engine.get_entity_state("Item", "item-1"), {"name": "Widget"})

        m2 = SyncMutation(
            mutation_id="m2",
            entity_name="Item",
            record_id="item-1",
            action="delete",
            payload={},
            timestamp="2026-09-14T10:01:00Z",
            surface_slug="web",
        )
        engine.push_mutations("web", [m2])
        self.assertIsNone(engine.get_entity_state("Item", "item-1"))

    def test_sync_engine_simulate_conflict(self):
        contract = EcosystemSyncContract(
            ecosystem_id="sim-eco",
            version="1.0.0",
            sync_entities=(
                SyncEntitySpec(entity_name="Profile", conflict_strategy="field_merge"),
            ),
            surface_policies={"mobile": "bidirectional", "web": "bidirectional"},
        )
        engine = EcosystemSyncEngine(contract)

        conflict = engine.simulate_conflict(
            entity_name="Profile",
            record_id="prof-1",
            local_surface="mobile",
            remote_surface="web",
            local_updates={"bio": "Mobile bio update", "avatar": "mobile.png"},
            remote_updates={"display_name": "Web Name", "avatar": "web.png"},
            strategy="field_merge",
        )
        self.assertEqual(conflict.entity_name, "Profile")
        self.assertEqual(conflict.record_id, "prof-1")
        self.assertIn("bio", conflict.resolved_payload)
        self.assertIn("display_name", conflict.resolved_payload)

    def test_synthesize_ecosystem_sync(self):
        surfaces = [
            {
                "slug": "rideshare-consumer",
                "surface_kind": "web",
                "ir_dict": {
                    "entities": [{"name": "RideRequest"}, {"name": "PassengerProfile"}],
                },
            },
            {
                "slug": "rideshare-driver",
                "surface_kind": "mobile",
                "ir_dict": {
                    "entities": [{"name": "RideRequest"}, {"name": "DriverLocation"}],
                },
            },
            {
                "slug": "rideshare-admin",
                "surface_kind": "admin",
                "ir_dict": {
                    "entities": [{"name": "RideRequest"}, {"name": "TripAudit"}],
                },
            },
        ]

        contract = synthesize_ecosystem_sync(
            ecosystem_id="rideshare-eco",
            surfaces=surfaces,
            version="1.0.0",
        )

        self.assertEqual(contract.ecosystem_id, "rideshare-eco")
        self.assertIn("rideshare-consumer", contract.surface_policies)
        self.assertIn("rideshare-admin", contract.surface_policies)

        ride_spec = next(s for s in contract.sync_entities if s.entity_name == "RideRequest")
        self.assertEqual(ride_spec.source_of_truth_surface, "rideshare-admin")
        self.assertEqual(ride_spec.conflict_strategy, "field_merge")

    def test_sync_engine_thread_safety(self):
        contract = EcosystemSyncContract(
            ecosystem_id="threaded-eco",
            version="1.0.0",
            sync_entities=(SyncEntitySpec(entity_name="Counter"),),
            surface_policies={"surf-a": "bidirectional", "surf-b": "bidirectional"},
        )
        engine = EcosystemSyncEngine(contract)

        def worker(surface: str, count: int):
            for i in range(count):
                mut = SyncMutation(
                    mutation_id=f"{surface}-{i}",
                    entity_name="Counter",
                    record_id="c-1",
                    action="update",
                    payload={"val": i},
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    surface_slug=surface,
                )
                engine.push_mutations(surface, [mut])
                engine.pull_changes(surface, since_version=0)

        t1 = threading.Thread(target=worker, args=("surf-a", 25))
        t2 = threading.Thread(target=worker, args=("surf-b", 25))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(engine.current_version, 50)
        self.assertEqual(engine.mutation_count, 50)


class TestEcosystemSyncIntegration(unittest.TestCase):
    def test_ecosystem_pack_package_with_sync_contract(self):
        from omnistackai_agent_engine.solution_packs import (
            DEFAULT_SOLUTION_PACK_REGISTRY,
            parse_ecosystem_pack_package,
            synthesize_ecosystem_pack,
        )

        pack = DEFAULT_SOLUTION_PACK_REGISTRY.get("minimal-blog")
        self.assertIsNotNone(pack)
        eco_pkg = synthesize_ecosystem_pack(pack, registry=DEFAULT_SOLUTION_PACK_REGISTRY)

        self.assertIsNotNone(eco_pkg.sync_contract)
        self.assertIsInstance(eco_pkg.sync_contract, EcosystemSyncContract)
        self.assertGreater(len(eco_pkg.sync_contract.sync_entities), 0)

        pkg_json = eco_pkg.to_json()
        parsed_pkg = parse_ecosystem_pack_package(pkg_json)
        self.assertEqual(parsed_pkg.ecosystem_id, eco_pkg.ecosystem_id)
        self.assertIsNotNone(parsed_pkg.sync_contract)
        self.assertEqual(parsed_pkg.sync_contract.ecosystem_id, eco_pkg.sync_contract.ecosystem_id)

    def test_ecosystem_registry_sync_contract(self):
        from omnistackai_agent_engine.solution_packs import DEFAULT_ECOSYSTEM_PACK_REGISTRY

        sync_contract = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_sync_contract("minimal-blog-ecosystem")
        self.assertIsNotNone(sync_contract)
        self.assertEqual(sync_contract.ecosystem_id, "minimal-blog-ecosystem")
        self.assertGreater(len(sync_contract.sync_entities), 0)

        pack = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get("minimal-blog-ecosystem")
        self.assertIsNotNone(pack)
        self.assertIsNotNone(pack.sync_contract)
        self.assertTrue(pack.to_dict()["has_sync_contract"])

    def test_studio_preview_manager_sync(self):
        from omnistackai_agent_engine.studio.preview import StudioPreviewManager

        manager = StudioPreviewManager(start_fn=lambda *args, **kwargs: FakeSession())
        surfaces = [
            {"slug": "web", "app_name": "Web", "surface_kind": "web"},
            {"slug": "admin", "app_name": "Admin", "surface_kind": "admin"},
        ]

        status = manager.replace_ecosystem("test-eco", surfaces=surfaces)
        self.assertTrue(status.get("has_sync"))
        self.assertGreaterEqual(status.get("sync_entity_count", 0), 1)

        sync_info = manager.get_ecosystem_sync()
        self.assertIsNotNone(sync_info)
        self.assertTrue(sync_info["is_ecosystem"])
        self.assertEqual(sync_info["ecosystem_id"], "test-eco")

        push_res = manager.push_sync_mutations("web", [
            {
                "mutation_id": "mut-push-1",
                "entity_name": "Item",
                "record_id": "rec-1",
                "action": "create",
                "payload": {"title": "Test Push"},
                "surface_slug": "web",
            }
        ])
        self.assertEqual(push_res["status"], "ok")
        self.assertEqual(len(push_res["accepted"]), 1)

        pull_res = manager.pull_sync_changes("admin", since_version=0)
        self.assertEqual(pull_res["status"], "ok")
        self.assertEqual(len(pull_res["mutations"]), 1)

        sim_res = manager.simulate_sync_conflict(
            entity_name="Item",
            record_id="rec-1",
            local_surface="web",
            remote_surface="admin",
            local_updates={"status": "draft"},
            remote_updates={"status": "published"},
            strategy="last_write_wins",
        )
        self.assertEqual(sim_res["status"], "ok")
        self.assertIn("conflict", sim_res)

    def test_studio_server_sync_endpoints(self):
        from omnistackai_agent_engine.studio.preview import StudioPreviewManager
        from omnistackai_agent_engine.studio.server import create_studio_server

        manager = StudioPreviewManager(start_fn=lambda *args, **kwargs: FakeSession())
        surfaces = [
            {"slug": "web", "app_name": "Web", "surface_kind": "web"},
            {"slug": "admin", "app_name": "Admin", "surface_kind": "admin"},
        ]
        manager.replace_ecosystem("test-eco", surfaces=surfaces)

        server = create_studio_server(
            build_fn=lambda p, **kw: {},
            port=0,
            get_ecosystem_sync_fn=manager.get_ecosystem_sync,
            push_sync_mutations_fn=manager.push_sync_mutations,
            pull_sync_changes_fn=manager.pull_sync_changes,
            simulate_sync_conflict_fn=manager.simulate_sync_conflict,
        )
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        port = server.server_address[1]
        base_url = f"http://127.0.0.1:{port}"

        try:
            # 1. GET /api/ecosystem/sync
            with urlopen(f"{base_url}/api/ecosystem/sync") as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode())
                self.assertTrue(data["is_ecosystem"])
                self.assertIn("sync_contract", data)

            # 2. POST /api/ecosystem/sync/push
            push_payload = {
                "surface_slug": "web",
                "mutations": [
                    {
                        "mutation_id": "mut-srv-1",
                        "entity_name": "Item",
                        "record_id": "itm-99",
                        "action": "create",
                        "payload": {"name": "Server Test Item"},
                        "surface_slug": "web",
                    }
                ],
            }
            req = Request(
                f"{base_url}/api/ecosystem/sync/push",
                data=json.dumps(push_payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                push_res = json.loads(resp.read().decode())
                self.assertEqual(push_res["status"], "ok")
                self.assertEqual(len(push_res["accepted"]), 1)

            # 3. GET /api/ecosystem/sync/pull
            with urlopen(f"{base_url}/api/ecosystem/sync/pull?surface_slug=admin&since_version=0") as resp:
                self.assertEqual(resp.status, 200)
                pull_res = json.loads(resp.read().decode())
                self.assertEqual(pull_res["status"], "ok")
                self.assertGreaterEqual(len(pull_res["mutations"]), 1)

            # 4. POST /api/ecosystem/sync/simulate
            sim_payload = {
                "entity_name": "Item",
                "record_id": "itm-99",
                "local_surface": "web",
                "remote_surface": "admin",
                "local_updates": {"title": "Web Title"},
                "remote_updates": {"title": "Admin Title"},
                "strategy": "last_write_wins",
            }
            req_sim = Request(
                f"{base_url}/api/ecosystem/sync/simulate",
                data=json.dumps(sim_payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req_sim) as resp:
                self.assertEqual(resp.status, 200)
                sim_res = json.loads(resp.read().decode())
                self.assertEqual(sim_res["status"], "ok")
                self.assertIn("conflict", sim_res)
        finally:
            server.shutdown()
            server.server_close()

    def test_cli_sync_subcommand(self):
        from omnistackai_agent_engine.solution_packs import ecosystem_cli

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = ecosystem_cli.main(["sync", "minimal-blog-ecosystem"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("Ecosystem Data Sync:", out)
        self.assertIn("minimal-blog-ecosystem", out)
        self.assertIn("Sync Entities", out)

        buf_json = io.StringIO()
        with patch("sys.stdout", buf_json):
            rc_json = ecosystem_cli.main(["sync", "minimal-blog-ecosystem", "--json"])
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["ecosystem_id"], "minimal-blog-ecosystem")
        self.assertGreater(len(parsed["sync_entities"]), 0)


if __name__ == "__main__":
    unittest.main()
