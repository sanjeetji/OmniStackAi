"""PC-009: one user's project cannot reach another's, or the platform's.

Offline checks of what each isolation layer promises. The live proof — run against this machine's
PostgreSQL and Docker — is recorded in the CHANGELOG entry for PC-009:

* app A opening app B's database, or the platform's: "User does not have CONNECT privilege";
* app A creating a database: "permission denied"; app A is not a superuser.
"""

import os
import tempfile
from pathlib import Path
from unittest import TestCase, mock

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.intake.build_app import build_app_from_ir
from omnistackai_agent_engine.localrun.plan import build_run_plan

DB = {"db_password": "platform-owner-secret", "db_user": "omnistackai", "maintenance_db": "omnistackai"}


def _workspace(tmp: str, workspace_id: str) -> str:
    repo = Path(tmp) / workspace_id / "repo"
    with mock.patch.dict(os.environ, {"OMNISTACKAI_BUILD_VERIFY": "off"}):
        build_app_from_ir(example_ir("minimal-blog"), str(repo), author_name="t", author_email="t@example.com",
                          overwrite=True)
    return str(repo)


class EachProjectHasItsOwnDatabase(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.plans = [build_run_plan(_workspace(cls.tmp.name, ws), **DB)
                     for ws in ("7f1c2a90-aaaa", "e2b4c6d8-bbbb")]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def _database_url(self, plan) -> str:
        api = next(s for s in plan.steps if s.background and "uvicorn" in s.program)
        return dict(api.env)["DATABASE_URL"]

    def test_two_workspaces_never_share_a_database(self) -> None:
        # Every workspace keeps its code in a folder named `repo`; both previewed into "repo" before.
        names = {plan.db_name for plan in self.plans}
        self.assertEqual(len(names), 2)
        self.assertNotIn("repo", names)
        self.assertEqual(self.plans[0].db_name, "app_7f1c2a90_aaaa", "a leading digit gets a prefix")

    def test_the_app_never_holds_the_platform_credentials(self) -> None:
        for plan in self.plans:
            url = self._database_url(plan)
            with self.subTest(db=plan.db_name):
                self.assertNotIn("platform-owner-secret", url)
                self.assertTrue(url.startswith(f"postgresql://{plan.db_name}:"))

    def test_each_role_is_unprivileged_and_owns_only_its_database(self) -> None:
        sql = " ".join(" ".join(s.args) for s in self.plans[0].steps if s.program == "docker")
        role = self.plans[0].db_name
        self.assertIn(f'CREATE ROLE "{role}" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION', sql)
        self.assertIn(f'CREATE DATABASE "{role}" OWNER "{role}"', sql)
        self.assertIn(f'REVOKE CONNECT ON DATABASE "{role}" FROM PUBLIC', sql)
        self.assertIn('REVOKE CONNECT ON DATABASE "omnistackai" FROM PUBLIC', sql)

    def test_migrations_run_as_the_app_so_it_owns_its_tables(self) -> None:
        for step in self.plans[0].steps:
            if step.label.startswith("apply migration"):
                self.assertEqual(step.args[step.args.index("-U") + 1], self.plans[0].db_name)

    def test_passwords_differ_per_project_and_are_stable(self) -> None:
        a, b = (self._database_url(p) for p in self.plans)
        self.assertNotEqual(a.split("@")[0], b.split("@")[0])
        again = build_run_plan(self.plans[0].repo_dir, **DB)
        self.assertEqual(self._database_url(again), a)


class OnlyTheControlPlaneMayCallTheStudio(TestCase):
    """The Studio acts on whatever workspace it is asked about; ownership is checked in the control
    plane. With a service token set, a caller without it gets nothing."""

    def _serve(self, token: str):
        import threading

        from omnistackai_agent_engine.studio.server import create_studio_server

        with mock.patch.dict(os.environ, {"OMNISTACKAI_STUDIO_TOKEN": token}):
            server = create_studio_server(build_fn=lambda prompt, **opts: {"ok": True}, host="127.0.0.1", port=0,
                                          status_fn=lambda: {"status": "idle"})
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_address[1]}"

    def _get(self, url: str, token: str | None = None) -> int:
        import urllib.error
        import urllib.request

        request = urllib.request.Request(url, headers={"X-OmniStack-Studio-Token": token} if token else {})
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status
        except urllib.error.HTTPError as error:
            return error.code

    def test_without_the_token_nothing_is_served(self) -> None:
        base = self._serve("the-service-token")
        self.assertEqual(self._get(base + "/api/preview"), 401)
        self.assertEqual(self._get(base + "/api/preview", "wrong"), 401)
        self.assertEqual(self._get(base + "/api/preview", "the-service-token"), 200)

    def test_the_health_check_stays_open(self) -> None:
        self.assertEqual(self._get(self._serve("the-service-token") + "/healthz"), 200)

    def test_single_operator_mode_is_unchanged(self) -> None:
        self.assertEqual(self._get(self._serve("") + "/api/preview"), 200)


class TheOnlyWayOutIsTheAllowlist(TestCase):
    """The egress proxy's decisions (R-071). Live, from inside an isolated preview: the control
    plane, the platform database, the internet and 169.254.169.254 were unreachable; the proxy
    answered 403 for example.com and the metadata address and 200 for registry.npmjs.org."""

    def setUp(self) -> None:
        from omnistackai_agent_engine.localrun import egress_proxy

        self.proxy = egress_proxy
        self.allowed = egress_proxy.DEFAULT_ALLOW + (".example.org",)

    def _resolver(self, ip: str):
        import socket

        return lambda host, port, type=None: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]

    def test_package_registries_are_allowed(self) -> None:
        address, reason = self.proxy.decide("registry.npmjs.org", 443, self.allowed, resolve=self._resolver("104.16.1.1"))
        self.assertEqual((address, reason), ("104.16.1.1", "allowed"))

    def test_anything_else_is_refused(self) -> None:
        self.assertIsNone(self.proxy.decide("example.com", 443, self.allowed, resolve=self._resolver("93.184.216.34"))[0])

    def test_only_web_ports(self) -> None:
        self.assertIsNone(self.proxy.decide("registry.npmjs.org", 22, self.allowed, resolve=self._resolver("104.16.1.1"))[0])

    def test_an_allowed_name_pointing_inside_is_refused(self) -> None:
        for inside in ("127.0.0.1", "10.0.0.5", "172.17.0.1", "192.168.1.1", "169.254.169.254"):
            with self.subTest(ip=inside):
                address, reason = self.proxy.decide("registry.npmjs.org", 443, self.allowed, resolve=self._resolver(inside))
                self.assertIsNone(address)
                self.assertEqual(reason, "host resolves to a non-public address")

    def test_subdomain_entries(self) -> None:
        self.assertTrue(self.proxy.host_allowed("api.example.org", self.allowed))
        self.assertFalse(self.proxy.host_allowed("example.org.evil.com", self.allowed))


class MultiTenantPreviewsAreContained(TestCase):
    def test_multi_tenant_mode_never_runs_an_app_on_the_host(self) -> None:
        from omnistackai_agent_engine.localrun import engines

        with mock.patch.dict(os.environ, {"OMNISTACKAI_TENANCY": "multi", "OMNISTACKAI_PREVIEW_ENGINE": "local"}):
            self.assertEqual(engines.resolve_engine(), engines.CONTAINER)

    def test_limits_bound_every_preview(self) -> None:
        from omnistackai_agent_engine.localrun import sandbox

        flags = " ".join(sandbox.limits())
        for expected in ("--memory 2g", "--cpus 2", "--pids-limit 1024", "--cap-drop ALL",
                         "--security-opt no-new-privileges"):
            self.assertIn(expected, flags)

    def test_the_gateway_only_relays_inbound(self) -> None:
        from omnistackai_agent_engine.localrun import sandbox

        calls = []
        with mock.patch.object(sandbox, "_docker",
                               side_effect=lambda *a, **k: calls.append(a) or mock.Mock(returncode=0, stderr="")):
            sandbox.start_gateway("omnistackai-preview-x", [41000, 41001])
        run = next(c for c in calls if c[0] == "run")
        self.assertIn("127.0.0.1:41000:41000", run)
        self.assertIn("41001:omnistackai-preview-x:41001", run)
        self.assertIn(("network", "connect", sandbox.NETWORK, "omnistackai-preview-x-gw"), calls)

    def test_the_preview_network_has_no_route_out(self) -> None:
        from omnistackai_agent_engine.localrun import sandbox

        calls = []
        with mock.patch.object(sandbox, "_docker",
                               side_effect=lambda *a, **k: calls.append(a) or mock.Mock(returncode=1 if a[0] == "network" and a[1] == "inspect" else 0, stderr="")):
            sandbox.ensure_network()
        self.assertIn("--internal", next(c for c in calls if c[:2] == ("network", "create")))


class FairShares(TestCase):
    """Per-user quotas (R-175): one person's loop cannot take the host."""

    def setUp(self) -> None:
        from omnistackai_agent_engine.studio.quotas import Quotas

        self.now = [1000.0]
        self.quotas = Quotas(clock=lambda: self.now[0])

    def test_a_third_preview_stops_the_users_oldest(self) -> None:
        self.assertEqual(self.quotas.admit_preview("u1", "ws-a"), [])
        self.now[0] += 1
        self.assertEqual(self.quotas.admit_preview("u1", "ws-b"), [])
        self.now[0] += 1
        self.assertEqual(self.quotas.admit_preview("u1", "ws-c"), ["ws-a"])
        self.assertEqual(self.quotas.admit_preview("u2", "ws-z"), [], "another user's previews are untouched")

    def test_a_full_host_refuses_with_a_reason(self) -> None:
        from omnistackai_agent_engine.studio.quotas import QuotaExceeded

        with mock.patch.dict(os.environ, {"OMNISTACKAI_MAX_PREVIEWS": "2"}):
            self.quotas.admit_preview("u1", "ws-a")
            self.quotas.admit_preview("u2", "ws-b")
            with self.assertRaises(QuotaExceeded) as refused:
                self.quotas.admit_preview("u3", "ws-c")
        self.assertIn("full", str(refused.exception))

    def test_builds_per_hour_with_a_retry_time(self) -> None:
        from omnistackai_agent_engine.studio.quotas import QuotaExceeded

        with mock.patch.dict(os.environ, {"OMNISTACKAI_BUILDS_PER_HOUR": "2"}):
            self.quotas.admit_build("u1")
            self.quotas.admit_build("u1")
            with self.assertRaises(QuotaExceeded) as refused:
                self.quotas.admit_build("u1")
            self.assertGreater(refused.exception.retry_after, 3000)
            self.quotas.admit_build("u2")  # someone else is not affected
            self.now[0] += 3601
            self.quotas.admit_build("u1")  # the window rolls

    def test_a_single_operator_is_never_limited(self) -> None:
        for _ in range(100):
            self.quotas.admit_build(None)

    def test_idle_previews_are_found(self) -> None:
        self.quotas.admit_preview("u1", "ws-a")
        self.quotas.admit_preview("u1", "ws-b")
        self.now[0] += 29 * 60
        self.quotas.touch("ws-b")
        self.now[0] += 2 * 60
        self.assertEqual(self.quotas.idle(), ["ws-a"])

    def test_the_preview_manager_stops_idle_previews_on_its_own(self) -> None:
        import time as _time

        from omnistackai_agent_engine.studio.preview import StudioPreviewManager, WorkspacePreviewSession

        manager = StudioPreviewManager(start_fn=lambda *a, **k: None)
        session = WorkspacePreviewSession("ws-a", "/tmp/x", status="ready", phase="ready", message="")
        session.session = mock.Mock()
        session.last_active_at = _time.time() - 31 * 60
        manager._workspaces["ws-a"] = session
        self.assertEqual(manager.reap_idle(), ["ws-a"])
        self.assertIsNone(session.session)


class TheUserIsBelievedOnlyWithTheToken(TestCase):
    def _user_seen(self, token_env: str, headers: dict) -> object:
        import threading
        import urllib.request

        from omnistackai_agent_engine.studio import quotas
        from omnistackai_agent_engine.studio.server import create_studio_server

        seen = []
        with mock.patch.dict(os.environ, {"OMNISTACKAI_STUDIO_TOKEN": token_env}):
            server = create_studio_server(build_fn=lambda prompt, **opts: {}, host="127.0.0.1", port=0,
                                          status_fn=lambda: seen.append(quotas.current_user.get()) or {"status": "idle"})
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        request = urllib.request.Request(f"http://127.0.0.1:{server.server_address[1]}/api/preview", headers=headers)
        urllib.request.urlopen(request, timeout=5).read()
        return seen[0]

    def test_from_the_control_plane(self) -> None:
        self.assertEqual(self._user_seen("tok", {"X-OmniStack-Studio-Token": "tok", "X-OmniStack-User": "usr-1"}), "usr-1")

    def test_ignored_without_a_token_configured(self) -> None:
        self.assertIsNone(self._user_seen("", {"X-OmniStack-User": "usr-1"}))


class ARefusedBuildSaysWhy(TestCase):
    def test_the_stream_carries_the_reason(self) -> None:
        # Found live: the refusal crashed ("cannot access free variable 'exceeded'").
        import asyncio

        from omnistackai_agent_engine.studio import live_serve
        from omnistackai_agent_engine.studio.quotas import QuotaExceeded

        with mock.patch.object(live_serve._QUOTAS, "admit_build", side_effect=QuotaExceeded("slow down", 90)):
            captured = {}

            def fake_serve(build, **kwargs):
                captured.update(kwargs)
                raise SystemExit

            with mock.patch.object(live_serve, "create_studio_server", side_effect=fake_serve), \
                    mock.patch.object(live_serve, "StudioPreviewManager"), self.assertRaises(SystemExit):
                live_serve.main()
            stream = captured["workspace_build_stream_fn"]("ws1", "a prompt")

            async def first():
                return [event async for event in stream]

            events = asyncio.run(first())
        self.assertEqual(events, [{"phase": "error", "error": "slow down", "quota": True, "retry_after": 90}])
