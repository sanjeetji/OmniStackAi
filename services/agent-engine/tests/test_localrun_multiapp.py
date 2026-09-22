"""R-520 (Phase T, T-2): multi-app project runner (localrun/multiapp.py).

Plan composition is pure. The execution tests launch real local processes (tiny Python HTTP
servers standing in for `pnpm run dev`) on free loopback ports, so readiness, failure cleanup and
process-group shutdown are exercised for real. No network beyond loopback, no model calls.
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

from omnistackai_agent_engine.localrun.multiapp import (
    MultiAppRunError,
    ProjectManifestError,
    allocate_ports,
    base_environment,
    build_multiapp_plan,
    load_project_manifest,
    project_db_name,
    start_multiapp,
)

PROJECT = "3f2b8c1a-9d4e-4b7a-8c21-0a1b2c3d4e5f"

MANIFEST = {
    "schema_version": 1,
    "name": "Corner Shop",
    "apps": [
        {"id": "web", "name": "Storefront", "kind": "web", "path": "apps/web"},
        {"id": "courier", "name": "Courier", "kind": "pwa", "path": "apps/courier"},
        {"id": "api", "name": "API", "kind": "api", "path": "services/api"},
    ],
    "demo_users": [],
}


def _make_repo(root: Path, manifest: dict = MANIFEST, *, workspace: bool = True) -> Path:
    for app in manifest["apps"]:
        app_dir = root / app["path"]
        app_dir.mkdir(parents=True, exist_ok=True)
        (app_dir / "package.json").write_text('{"scripts": {"dev": "node x"}}', encoding="utf-8")
    api = root / "services" / "api"
    (api / "migrations").mkdir(parents=True, exist_ok=True)
    (api / "seed").mkdir(parents=True, exist_ok=True)
    (api / "migrations" / "002_orders.sql").write_text("SELECT 2;", encoding="utf-8")
    (api / "migrations" / "001_init.sql").write_text("SELECT 1;", encoding="utf-8")
    (api / "seed" / "001_demo.sql").write_text("SELECT 3;", encoding="utf-8")
    if workspace:
        (root / "pnpm-workspace.yaml").write_text("packages:\n  - apps/*\n  - services/*\n", encoding="utf-8")
    (root / "omnistack.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


class ManifestTests(unittest.TestCase):
    def test_no_manifest_means_prompt_built_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(load_project_manifest(tmp))

    def test_valid_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(Path(tmp))
            self.assertEqual([a["id"] for a in load_project_manifest(repo)["apps"]], ["web", "courier", "api"])

    def test_invalid_manifests(self) -> None:
        cases = {
            "not json": "{",
            "schema": json.dumps({**MANIFEST, "schema_version": 2}),
            "escape": json.dumps({**MANIFEST, "apps": [{"id": "web", "name": "W", "kind": "web", "path": "../x"}]}),
            "kind": json.dumps({**MANIFEST, "apps": [{"id": "web", "name": "W", "kind": "desktop", "path": "apps/web"}]}),
            "two apis": json.dumps({**MANIFEST, "apps": [
                {"id": "api", "name": "A", "kind": "api", "path": "services/api"},
                {"id": "api2", "name": "B", "kind": "api", "path": "apps/web"},
            ]}),
        }
        for label, content in cases.items():
            with self.subTest(case=label), tempfile.TemporaryDirectory() as tmp:
                repo = _make_repo(Path(tmp))
                (repo / "omnistack.json").write_text(content, encoding="utf-8")
                with self.assertRaises(ProjectManifestError):
                    load_project_manifest(repo)

    def test_app_needs_package_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(Path(tmp))
            (repo / "apps" / "web" / "package.json").unlink()
            with self.assertRaises(ProjectManifestError):
                load_project_manifest(repo)


class PlanTests(unittest.TestCase):
    def _plan(self, repo: Path, **kwargs):
        return build_multiapp_plan(
            repo,
            MANIFEST,
            project_id=PROJECT,
            ports=[4101, 4102, 4103],
            db_password="pg-pass",
            jwt_secret="jwt-secret-value",
            **kwargs,
        )

    def test_apps_with_a_build_are_served_from_it_not_from_a_dev_server(self) -> None:
        """R-530: a dev server's hot-reload socket cannot pass the preview proxy, and a Turbopack
        dev app never hydrates without it, so anything buildable is built and served."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(Path(tmp))
            for app in ("apps/web", "apps/courier"):
                (repo / app / "package.json").write_text(
                    '{"scripts": {"dev": "next dev", "build": "next build", "start": "next start"}}', encoding="utf-8"
                )
            plan = self._plan(repo)
            web, courier, api = plan.apps
            self.assertEqual(web.command, ("pnpm", "run", "start"))
            self.assertEqual(courier.command, ("pnpm", "run", "start"))
            self.assertEqual(api.command, ("pnpm", "run", "dev"), "the API has no build script")

            builds = [step for step in plan.setup if step.args[:2] == ("run", "build")]
            self.assertEqual([step.cwd for step in builds], [web.cwd, courier.cwd])
            # Next inlines NEXT_PUBLIC_* and the base path at build time, so the build must carry
            # exactly the environment the app will run with.
            self.assertEqual(dict(builds[0].env)["NEXT_PUBLIC_API_URL"], f"/preview/{PROJECT}/api")
            self.assertEqual(dict(builds[0].env)["BASE_PATH"], f"/preview/{PROJECT}/web")
            install = next(i for i, step in enumerate(plan.setup) if step.args[:1] == ("install",))
            self.assertLess(install, plan.setup.index(builds[0]), "dependencies are installed before the build")

    def test_apps_without_a_build_fall_back_to_the_dev_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = self._plan(_make_repo(Path(tmp)))  # fixtures ship a dev script only
            self.assertEqual([app.command for app in plan.apps], [("pnpm", "run", "dev")] * 3)
            self.assertEqual([s for s in plan.setup if s.args[:2] == ("run", "build")], [])

    def test_apps_get_ports_paths_and_env_by_kind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = self._plan(_make_repo(Path(tmp)))
            web, courier, api = plan.apps
            self.assertEqual((web.port, courier.port, api.port), (4101, 4102, 4103))
            self.assertEqual(web.public_path, f"/preview/{PROJECT}/web")
            self.assertEqual(api.public_path, f"/preview/{PROJECT}/api")
            self.assertEqual(web.command, ("pnpm", "run", "dev"))

            web_env = dict(web.env)
            self.assertEqual(web_env["PORT"], "4101")
            self.assertEqual(web_env["BASE_PATH"], f"/preview/{PROJECT}/web")
            self.assertEqual(web_env["API_URL"], "http://127.0.0.1:4103")
            self.assertEqual(web_env["NEXT_PUBLIC_API_URL"], f"/preview/{PROJECT}/api")
            self.assertNotIn("DATABASE_URL", web_env)
            self.assertNotIn("JWT_SECRET", web_env)

            api_env = dict(api.env)
            self.assertEqual(api_env["PORT"], "4103")
            self.assertEqual(api_env["JWT_SECRET"], "jwt-secret-value")
            self.assertTrue(api_env["DATABASE_URL"].endswith(f"/{project_db_name(PROJECT)}"))
            self.assertEqual(api.health_url, "http://127.0.0.1:4103/health")
            self.assertEqual(web.health_url, f"http://127.0.0.1:4101/preview/{PROJECT}/web")

    def test_setup_recreates_db_then_migrations_then_seeds_then_one_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = self._plan(_make_repo(Path(tmp)))
            labels = [step.label for step in plan.setup]
            db = project_db_name(PROJECT)
            self.assertEqual(
                labels,
                [
                    f"drop database {db} (if it exists)",
                    f"create database {db}",
                    "apply migration migrations/001_init.sql",
                    "apply migration migrations/002_orders.sql",
                    "load seed data seed/001_demo.sql",
                    "install dependencies (pnpm workspace)",
                ],
            )
            self.assertTrue(plan.setup[0].tolerate_failure)
            self.assertEqual(plan.setup[-1].cwd, plan.repo_dir)

    def test_without_workspace_each_app_installs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = self._plan(_make_repo(Path(tmp), workspace=False))
            installs = [s.label for s in plan.setup if s.program == "pnpm"]
            self.assertEqual(installs, [f"install dependencies for {a}" for a in ("web", "courier", "api")])

    def test_no_api_app_means_no_database(self) -> None:
        manifest = {**MANIFEST, "apps": [MANIFEST["apps"][0]]}
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(Path(tmp), manifest)
            plan = build_multiapp_plan(repo, manifest, project_id=PROJECT, ports=[4101])
            self.assertFalse(any(s.program == "docker" for s in plan.setup))
            self.assertNotIn("API_URL", dict(plan.apps[0].env))

    def test_to_dict_masks_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            text = json.dumps(self._plan(_make_repo(Path(tmp))).to_dict())
            self.assertNotIn("pg-pass", text)
            self.assertNotIn("jwt-secret-value", text)

    def test_too_few_ports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                build_multiapp_plan(_make_repo(Path(tmp)), MANIFEST, project_id=PROJECT, ports=[1])

    def test_allocate_ports_are_distinct(self) -> None:
        ports = allocate_ports(4)
        self.assertEqual(len(set(ports)), 4)

    def test_db_name_is_safe(self) -> None:
        self.assertEqual(project_db_name(PROJECT), "tpl_3f2b8c1a9d4e4b7a")


class BaseEnvironmentTests(unittest.TestCase):
    def test_apps_never_inherit_model_keys(self) -> None:
        source = {
            "PATH": "/usr/bin",
            "HOME": "/home/me",
            "OPENAI_API_KEY": "sk-live",
            "OMNISTACKAI_SECRETS_KEY": "k",
            "DOCKER_CONTEXT": "colima",
            "npm_config_registry": "https://registry.npmjs.org/",
        }
        app_env = base_environment(source=source)
        self.assertEqual(app_env, {"PATH": "/usr/bin", "HOME": "/home/me"})
        setup_env = base_environment(for_setup=True, source=source)
        self.assertEqual(setup_env["DOCKER_CONTEXT"], "colima")
        self.assertIn("npm_config_registry", setup_env)
        self.assertNotIn("OPENAI_API_KEY", setup_env)


_SERVER = textwrap.dedent(
    """
    import http.server, os, sys
    health = sys.argv[1]
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            code = 200 if self.path.startswith(health) else 404
            body = f"{os.environ.get('BASE_PATH', '')}|{os.environ.get('OPENAI_API_KEY', '')}".encode()
            self.send_response(code)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *a):
            pass
    http.server.HTTPServer(("127.0.0.1", int(os.environ["PORT"])), H).serve_forever()
    """
)


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # A zombie still answers kill(0); treat it as gone.
    try:
        waited, _ = os.waitpid(pid, os.WNOHANG)
        return waited == 0
    except ChildProcessError:
        return True


class StartMultiAppTests(unittest.TestCase):
    """Real processes on free loopback ports."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _make_repo(self.root)
        (self.root / "server.py").write_text(_SERVER, encoding="utf-8")
        self.plan = build_multiapp_plan(
            self.root, MANIFEST, project_id=PROJECT, ports=allocate_ports(3), jwt_secret="s"
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _with_commands(self, commands: dict[str, tuple[str, ...]]):
        apps = tuple(dataclasses.replace(a, command=commands.get(a.id, a.command)) for a in self.plan.apps)
        return dataclasses.replace(self.plan, apps=apps, setup=())

    def _server_cmd(self, health: str) -> tuple[str, ...]:
        return (sys.executable, str(self.root / "server.py"), health)

    def test_all_apps_ready_then_stop_kills_whole_process_groups(self) -> None:
        pid_file = self.root / "grandchild.pid"
        web_path = f"/preview/{PROJECT}/web"
        # The courier "dev script" spawns a long-lived grandchild, like pnpm -> next.
        courier_cmd = (
            "/bin/sh",
            "-c",
            f"sleep 300 & echo $! > {pid_file}; exec {sys.executable} {self.root / 'server.py'} /preview/",
        )
        plan = self._with_commands({
            "web": self._server_cmd(web_path),
            "courier": courier_cmd,
            "api": self._server_cmd("/health"),
        })
        phases: list[str] = []
        ready: list[str] = []
        os.environ["OPENAI_API_KEY"] = "sk-should-not-leak"
        try:
            session = start_multiapp(
                plan, on_phase=phases.append, on_app_ready=ready.append, health_timeout_seconds=20
            )
        finally:
            del os.environ["OPENAI_API_KEY"]
        try:
            self.assertEqual(phases, ["start", "ready"])
            self.assertEqual(sorted(ready), ["api", "courier", "web"])
            self.assertTrue(session.is_alive())
            import urllib.request

            body = urllib.request.urlopen(f"http://127.0.0.1:{plan.apps[0].port}{web_path}", timeout=5).read()
            self.assertEqual(body.decode(), f"{web_path}|")  # BASE_PATH set, model key not inherited
            for _ in range(50):
                if pid_file.exists() and pid_file.read_text().strip():
                    break
                time.sleep(0.1)
            grandchild = int(pid_file.read_text().strip())
            self.assertTrue(_alive(grandchild))
        finally:
            session.stop()
        self.assertFalse(session.is_alive())
        for _ in range(30):
            if not _alive(grandchild):
                break
            time.sleep(0.1)
        self.assertFalse(_alive(grandchild), "stop must kill the whole process group")

    def test_app_that_exits_fails_startup_and_stops_the_others(self) -> None:
        plan = self._with_commands({
            "web": self._server_cmd(f"/preview/{PROJECT}/web"),
            "courier": (sys.executable, "-c", "raise SystemExit(3)"),
            "api": self._server_cmd("/health"),
        })
        with self.assertRaises(MultiAppRunError) as error:
            start_multiapp(plan, health_timeout_seconds=20)
        self.assertIn("courier", str(error.exception))

    def test_api_must_answer_health_200(self) -> None:
        plan = self._with_commands({
            "web": self._server_cmd(f"/preview/{PROJECT}/web"),
            "courier": self._server_cmd("/preview/"),
            "api": self._server_cmd("/nothing-here"),
        })
        with self.assertRaises(MultiAppRunError) as error:
            start_multiapp(plan, health_timeout_seconds=3)
        self.assertIn("api", str(error.exception))

    def test_setup_failure_and_cancellation(self) -> None:
        from omnistackai_agent_engine.localrun.plan import RunStep

        failing = dataclasses.replace(
            self.plan, setup=(RunStep(label="create database x", program=sys.executable, args=("-c", "raise SystemExit(1)")),)
        )
        with self.assertRaises(MultiAppRunError):
            start_multiapp(failing)
        with self.assertRaises(MultiAppRunError) as error:
            start_multiapp(self._with_commands({}), cancelled=lambda: True)
        self.assertIn("stopped", str(error.exception))


class StaleProcessReaperTests(unittest.TestCase):
    """R-527 live finding: after a Studio restart, the previous preview's `next dev` kept running
    (its own process group) and Next 16 refused the new start. Sessions now record their process
    groups, and the next start of the same project clears survivors."""

    def test_pid_file_is_written_and_removed_on_stop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = _make_repo(root / "repo")
            (repo / "server.py").write_text(_SERVER, encoding="utf-8")
            pid_file = root / "preview-pids.json"
            plan = build_multiapp_plan(repo, MANIFEST, project_id=PROJECT, ports=allocate_ports(3))
            apps = tuple(dataclasses.replace(a, command=(sys.executable, str(repo / "server.py"), "/")) for a in plan.apps)
            session = start_multiapp(dataclasses.replace(plan, apps=apps, setup=()), health_timeout_seconds=20, pid_file=pid_file)
            recorded = json.loads(pid_file.read_text(encoding="utf-8"))
            self.assertEqual(sorted(recorded), sorted(p.pid for p in session.processes.values()))
            session.stop()
            self.assertFalse(pid_file.exists())

    def test_reap_kills_recorded_node_like_groups_only(self) -> None:
        import subprocess

        from omnistackai_agent_engine.localrun.multiapp import reap_stale_processes

        with tempfile.TemporaryDirectory() as tmp:
            pid_file = Path(tmp) / "preview-pids.json"
            # A stand-in for an orphaned `next dev`: a process named node in its own session.
            node_like = subprocess.Popen(["/bin/sh", "-c", "exec -a node sleep 300"], start_new_session=True)
            unrelated = subprocess.Popen(["sleep", "300"], start_new_session=True)
            try:
                pid_file.write_text(json.dumps([node_like.pid, unrelated.pid, 999999]), encoding="utf-8")
                killed = reap_stale_processes(pid_file)
                self.assertEqual(killed, [node_like.pid])
                node_like.wait(timeout=5)
                self.assertIsNone(unrelated.poll(), "a process that is not node/pnpm/next is never killed")
                self.assertFalse(pid_file.exists())
            finally:
                for proc in (node_like, unrelated):
                    if proc.poll() is None:
                        proc.kill()
                        proc.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
