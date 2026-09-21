"""R-519 (Phase T, T-1): template format, catalogue and "use template" instantiation.

A template is a hand-built golden repository plus a `template.json` manifest under
`templates/catalog/<slug>/`. The original is read-only and identical for every user; "use template"
copies it into the user's own project workspace with its own git history. These tests use the
`fixtures/templates/corner-shop` fixture and mutated copies of it. No model or network calls.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from omnistackai_agent_engine.studio.server import create_studio_server
from omnistackai_agent_engine.studio.session import EditNotSupportedError
from omnistackai_agent_engine.studio.templates import (
    TemplateCatalog,
    TemplateNotFoundError,
    TemplateTargetNotEmptyError,
    default_catalog_root,
    instantiate_template,
    template_digest,
    validate_template,
)
from omnistackai_agent_engine.studio.workspace import StudioWorkspaceStore

FIXTURES = Path(__file__).parent / "fixtures" / "templates"
SLUG = "corner-shop"


def _copy_fixture(dest_root: Path, slug: str = SLUG) -> Path:
    target = dest_root / slug
    shutil.copytree(FIXTURES / SLUG, target)
    if slug != SLUG:
        _edit_manifest(target, slug=slug)
    return target


def _edit_manifest(template_dir: Path, **changes) -> None:
    path = template_dir / "template.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for key, value in changes.items():
        if value is _DELETE:
            data.pop(key, None)
        else:
            data[key] = value
    path.write_text(json.dumps(data), encoding="utf-8")


_DELETE = object()


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


class ValidateTemplateTests(unittest.TestCase):
    def test_fixture_is_valid(self) -> None:
        self.assertEqual(validate_template(FIXTURES / SLUG), [])

    def _errors_after(self, mutate) -> list[str]:  # noqa: ANN001
        with tempfile.TemporaryDirectory() as tmp:
            template_dir = _copy_fixture(Path(tmp))
            mutate(template_dir)
            return validate_template(template_dir)

    def _assert_error(self, mutate, needle: str) -> None:  # noqa: ANN001
        errors = self._errors_after(mutate)
        self.assertTrue(any(needle in e for e in errors), f"expected {needle!r} in {errors}")

    def test_missing_manifest(self) -> None:
        self._assert_error(lambda d: (d / "template.json").unlink(), "template.json")

    def test_manifest_not_json(self) -> None:
        self._assert_error(lambda d: (d / "template.json").write_text("{", encoding="utf-8"), "not valid JSON")

    def test_slug_must_match_directory(self) -> None:
        self._assert_error(lambda d: _edit_manifest(d, slug="other-shop"), "slug")

    def test_unknown_schema_version(self) -> None:
        self._assert_error(lambda d: _edit_manifest(d, schema_version=2), "schema_version")

    def test_version_must_be_semver(self) -> None:
        self._assert_error(lambda d: _edit_manifest(d, version="v1"), "version")

    def test_category_must_be_known(self) -> None:
        self._assert_error(lambda d: _edit_manifest(d, category="gaming"), "category")

    def test_required_text_fields(self) -> None:
        for field in ("name", "tagline", "description"):
            with self.subTest(field=field):
                self._assert_error(lambda d, f=field: _edit_manifest(d, **{f: _DELETE}), field)

    def test_app_path_must_exist(self) -> None:
        def mutate(d: Path) -> None:
            data = json.loads((d / "template.json").read_text(encoding="utf-8"))
            data["apps"][0]["path"] = "apps/missing"
            (d / "template.json").write_text(json.dumps(data), encoding="utf-8")

        self._assert_error(mutate, "apps/missing")

    def test_app_path_cannot_escape_repo(self) -> None:
        def mutate(d: Path) -> None:
            data = json.loads((d / "template.json").read_text(encoding="utf-8"))
            data["apps"][0]["path"] = "../media"
            (d / "template.json").write_text(json.dumps(data), encoding="utf-8")

        self._assert_error(mutate, "../media")

    def test_app_kind_must_be_known(self) -> None:
        def mutate(d: Path) -> None:
            data = json.loads((d / "template.json").read_text(encoding="utf-8"))
            data["apps"][0]["kind"] = "desktop"
            (d / "template.json").write_text(json.dumps(data), encoding="utf-8")

        self._assert_error(mutate, "kind")

    def test_duplicate_app_ids(self) -> None:
        def mutate(d: Path) -> None:
            data = json.loads((d / "template.json").read_text(encoding="utf-8"))
            data["apps"][1]["id"] = "web"
            (d / "template.json").write_text(json.dumps(data), encoding="utf-8")

        self._assert_error(mutate, "duplicate")

    def test_api_app_needs_sql_migrations(self) -> None:
        self._assert_error(
            lambda d: shutil.rmtree(d / "repo" / "services" / "api" / "migrations"), "migrations"
        )

    def test_demo_user_role_must_be_declared(self) -> None:
        def mutate(d: Path) -> None:
            data = json.loads((d / "template.json").read_text(encoding="utf-8"))
            data["demo_users"][0]["role"] = "driver"
            (d / "template.json").write_text(json.dumps(data), encoding="utf-8")

        self._assert_error(mutate, "driver")

    def test_cover_must_exist(self) -> None:
        self._assert_error(lambda d: _edit_manifest(d, cover="media/nope.png"), "media/nope.png")

    def test_repo_rejects_real_env_file(self) -> None:
        self._assert_error(
            lambda d: (d / "repo" / ".env").write_text("SECRET=1\n", encoding="utf-8"), ".env"
        )

    def test_repo_rejects_node_modules_and_git(self) -> None:
        for name in ("node_modules", ".git"):
            with self.subTest(name=name):
                self._assert_error(
                    lambda d, n=name: (d / "repo" / "apps" / "web" / n).mkdir(), name
                )

    def test_omnistack_json_is_reserved(self) -> None:
        self._assert_error(
            lambda d: (d / "repo" / "omnistack.json").write_text("{}", encoding="utf-8"), "omnistack.json"
        )

    def test_at_most_one_api_app(self) -> None:
        def mutate(d: Path) -> None:
            data = json.loads((d / "template.json").read_text(encoding="utf-8"))
            data["apps"][0]["kind"] = "api"
            (d / "template.json").write_text(json.dumps(data), encoding="utf-8")
            (d / "repo" / "apps" / "web" / "migrations").mkdir()
            (d / "repo" / "apps" / "web" / "migrations" / "001.sql").write_text("SELECT 1;", encoding="utf-8")

        self._assert_error(mutate, "at most one api app")

    def test_app_needs_package_json(self) -> None:
        self._assert_error(lambda d: (d / "repo" / "apps" / "admin" / "package.json").unlink(), "package.json")

    def test_repo_rejects_symlinks(self) -> None:
        self._assert_error(
            lambda d: (d / "repo" / "link").symlink_to("/etc/hosts"), "symlink"
        )


class TemplateDigestTests(unittest.TestCase):
    def test_digest_is_stable_and_content_sensitive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            template_dir = _copy_fixture(Path(tmp))
            first = template_digest(template_dir / "repo")
            self.assertTrue(first.startswith("sha256:"))
            self.assertEqual(first, template_digest(FIXTURES / SLUG / "repo"))
            (template_dir / "repo" / "README.md").write_text("changed\n", encoding="utf-8")
            self.assertNotEqual(first, template_digest(template_dir / "repo"))


class TemplateCatalogTests(unittest.TestCase):
    def test_lists_only_valid_templates_sorted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _copy_fixture(root)
            _copy_fixture(root, "alpha-shop")
            broken = _copy_fixture(root, "broken-shop")
            _edit_manifest(broken, category="gaming")
            (root / "README.md").write_text("docs, not a template\n", encoding="utf-8")

            catalog = TemplateCatalog(root)
            slugs = [t["slug"] for t in catalog.list()]
            self.assertEqual(slugs, ["alpha-shop", "corner-shop"])
            self.assertIn("broken-shop", catalog.errors())

    def test_summary_hides_demo_passwords_detail_includes_them(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _copy_fixture(Path(tmp))
            catalog = TemplateCatalog(Path(tmp))
            summary = catalog.list()[0]
            self.assertNotIn("demo_users", summary)
            self.assertEqual(summary["apps"][0]["kind"], "web")
            self.assertEqual(summary["app_kinds"], ["web", "admin", "api"])
            detail = catalog.get(SLUG)
            self.assertEqual(detail["demo_users"][0]["email"], "asha@corner-shop.test")
            self.assertEqual(detail["digest"], template_digest(FIXTURES / SLUG / "repo"))
            self.assertEqual(detail["file_count"], 17)

    def test_unknown_or_invalid_slug_is_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _copy_fixture(Path(tmp))
            catalog = TemplateCatalog(Path(tmp))
            for slug in ("nope", "../corner-shop", ""):
                with self.subTest(slug=slug):
                    with self.assertRaises(TemplateNotFoundError):
                        catalog.get(slug)

    def test_missing_root_is_an_empty_catalog(self) -> None:
        catalog = TemplateCatalog(Path("/nonexistent/omnistack-templates"))
        self.assertEqual(catalog.list(), [])

    def test_default_root_is_the_repository_catalog(self) -> None:
        self.assertEqual(default_catalog_root().parts[-2:], ("templates", "catalog"))

    def test_every_shipped_template_is_valid(self) -> None:
        """A template in templates/catalog that fails validation would silently vanish from the
        marketplace, so the shipped catalogue must be valid in full."""

        root = default_catalog_root()
        for entry in sorted(root.iterdir()) if root.is_dir() else []:
            if entry.is_dir() and not entry.name.startswith((".", "_")):
                with self.subTest(template=entry.name):
                    self.assertEqual(validate_template(entry), [])


class InstantiateTemplateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        _copy_fixture(root / "catalog")
        self.catalog = TemplateCatalog(root / "catalog")
        self.store = StudioWorkspaceStore(root / "workspaces")
        self.original = root / "catalog" / SLUG / "repo"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_use_template_creates_an_owned_project_copy(self) -> None:
        ws_id = "4f9c1d2e-0000-4000-8000-000000000001"
        result = instantiate_template(self.catalog, self.store, ws_id, SLUG)

        repo = self.store.repo_path(ws_id)
        self.assertEqual(result["id"], ws_id)
        self.assertEqual(result["file_count"], 18)  # the 17 template files + omnistack.json
        self.assertEqual(result["name"], "Corner Shop")
        self.assertEqual(result["entities"], ["Product", "Order"])
        self.assertEqual(result["template"]["slug"], SLUG)
        self.assertEqual(result["template"]["version"], "1.0.0")
        self.assertEqual(result["template"]["digest"], template_digest(self.original))

        # A real, independent git repo with exactly one commit that names the template.
        self.assertEqual(_git(repo, "rev-parse", "HEAD"), result["commit_sha"])
        log = _git(repo, "log", "--format=%s").splitlines()
        self.assertEqual(log, ["Template: Corner Shop v1.0.0"])
        self.assertEqual(_git(repo, "status", "--porcelain"), "")
        self.assertTrue((repo / "services" / "api" / "migrations" / "001_init.sql").is_file())

        # The copy describes itself (R-520): apps and demo logins, committed with the code.
        manifest = json.loads((repo / "omnistack.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["template"], {"slug": SLUG, "version": "1.0.0"})
        self.assertEqual([a["id"] for a in manifest["apps"]], ["web", "admin", "api"])
        self.assertEqual(manifest["demo_users"][0]["email"], "asha@corner-shop.test")
        self.assertIn("omnistack.json", _git(repo, "ls-files").splitlines())

        state = self.store.get_state(ws_id)
        self.assertEqual(state["kind"], "template")
        self.assertEqual(state["template"]["slug"], SLUG)
        self.assertEqual(state["commit_sha"], result["commit_sha"])
        turns = self.store.get_turns(ws_id)
        self.assertEqual([t["role"] for t in turns], ["assistant"])
        self.assertIn("Corner Shop", turns[0]["text"])

    def test_editing_the_copy_never_changes_the_original(self) -> None:
        before = template_digest(self.original)
        ws_a = "4f9c1d2e-0000-4000-8000-00000000000a"
        ws_b = "4f9c1d2e-0000-4000-8000-00000000000b"
        instantiate_template(self.catalog, self.store, ws_a, SLUG)
        (self.store.repo_path(ws_a) / "README.md").write_text("my shop\n", encoding="utf-8")

        self.assertEqual(template_digest(self.original), before)
        second = instantiate_template(self.catalog, self.store, ws_b, SLUG)
        self.assertEqual(second["template"]["digest"], before)
        self.assertIn(
            "Corner Shop (test fixture)",
            (self.store.repo_path(ws_b) / "README.md").read_text(encoding="utf-8"),
        )

    def test_refuses_a_workspace_that_already_has_code(self) -> None:
        ws_id = "4f9c1d2e-0000-4000-8000-000000000002"
        instantiate_template(self.catalog, self.store, ws_id, SLUG)
        with self.assertRaises(TemplateTargetNotEmptyError):
            instantiate_template(self.catalog, self.store, ws_id, SLUG)

    def test_unknown_template(self) -> None:
        with self.assertRaises(TemplateNotFoundError):
            instantiate_template(self.catalog, self.store, "4f9c1d2e-0000-4000-8000-000000000003", "nope")
        self.assertFalse(self.store.exists("4f9c1d2e-0000-4000-8000-000000000003"))


class TemplateWorkspaceGuardTests(unittest.TestCase):
    """A template project must not be overwritten by a prompt build or run through the IR edit path."""

    def test_prompt_build_and_ir_edit_are_refused(self) -> None:
        import asyncio

        from omnistackai_agent_engine.studio.live_serve import (
            _workspace_build,
            _workspace_edit,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _copy_fixture(root / "catalog")
            store = StudioWorkspaceStore(root / "workspaces")
            ws_id = "4f9c1d2e-0000-4000-8000-000000000004"
            instantiate_template(TemplateCatalog(root / "catalog"), store, ws_id, SLUG)
            head = _git(store.repo_path(ws_id), "rev-parse", "HEAD")

            with self.assertRaises(EditNotSupportedError) as edit_error:
                asyncio.run(_workspace_edit(ws_id, "add a wishlist", workspace_store=store))
            self.assertIn("template", str(edit_error.exception))
            with self.assertRaises(EditNotSupportedError):
                _workspace_build(ws_id, "a todo app", workspace_store=store)
            self.assertEqual(_git(store.repo_path(ws_id), "rev-parse", "HEAD"), head)


class TemplateRoutesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        _copy_fixture(root / "catalog")
        self.store = StudioWorkspaceStore(root / "workspaces")
        self.server = create_studio_server(
            lambda prompt, **_: {},
            port=0,
            workspace_store=self.store,
            template_catalog=TemplateCatalog(root / "catalog"),
        )
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self._tmp.cleanup()

    def _call(self, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(self.base + path, data=data, method=method)
        request.add_header("Content-Type", "application/json")
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def test_list_and_detail(self) -> None:
        status, data = self._call("GET", "/api/templates")
        self.assertEqual(status, 200)
        self.assertEqual([t["slug"] for t in data["templates"]], [SLUG])
        status, data = self._call("GET", f"/api/templates/{SLUG}")
        self.assertEqual(status, 200)
        self.assertEqual(data["name"], "Corner Shop")
        status, _ = self._call("GET", "/api/templates/nope")
        self.assertEqual(status, 404)

    def test_from_template(self) -> None:
        ws_id = "4f9c1d2e-0000-4000-8000-000000000005"
        status, data = self._call("POST", f"/api/workspaces/{ws_id}/from-template", {"slug": SLUG})
        self.assertEqual(status, 201)
        self.assertEqual(data["template"]["slug"], SLUG)
        status, _ = self._call("POST", f"/api/workspaces/{ws_id}/from-template", {"slug": SLUG})
        self.assertEqual(status, 409)
        status, _ = self._call("POST", "/api/workspaces/x/from-template", {"slug": "nope"})
        self.assertEqual(status, 404)
        status, _ = self._call("POST", "/api/workspaces/x/from-template", {})
        self.assertEqual(status, 400)

    def test_routes_404_when_catalog_disabled(self) -> None:
        server = create_studio_server(lambda prompt, **_: {}, port=0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with self.assertRaises(HTTPError) as error:
                urlopen(base + "/api/templates", timeout=10)
            self.assertEqual(error.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()


class TemplateAssetTests(unittest.TestCase):
    """R-523: covers and screenshots are served, but only the files the manifest declares."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        template = _copy_fixture(root / "catalog")
        (template / "media" / "shot-1.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
        _edit_manifest(template, screenshots=["media/shot-1.png"])
        self.catalog = TemplateCatalog(root / "catalog")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_declared_assets_resolve_with_content_type(self) -> None:
        path, content_type = self.catalog.asset(SLUG, "media/cover.svg")
        self.assertEqual(path.name, "cover.svg")
        self.assertEqual(content_type, "image/svg+xml")
        self.assertEqual(self.catalog.asset(SLUG, "media/shot-1.png")[1], "image/png")

    def test_undeclared_or_escaping_paths_are_not_found(self) -> None:
        for rel in ("template.json", "repo/README.md", "../corner-shop/template.json", "media/../template.json", ""):
            with self.subTest(rel=rel):
                with self.assertRaises(TemplateNotFoundError):
                    self.catalog.asset(SLUG, rel)
        with self.assertRaises(TemplateNotFoundError):
            self.catalog.asset("nope", "media/cover.svg")

    def test_http_route(self) -> None:
        server = create_studio_server(lambda prompt, **_: {}, port=0, template_catalog=self.catalog)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            base = f"http://127.0.0.1:{server.server_port}/api/templates/{SLUG}/assets"
            with urlopen(f"{base}/media/cover.svg", timeout=10) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers["Content-Type"], "image/svg+xml")
                self.assertIn(b"<svg", response.read())
            for bad in ("/template.json", "/repo/README.md", "/media/%2e%2e/template.json"):
                with self.subTest(path=bad):
                    with self.assertRaises(HTTPError) as error:
                        urlopen(base + bad, timeout=10)
                    self.assertEqual(error.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()
