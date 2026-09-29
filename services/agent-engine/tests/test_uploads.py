"""PC-102: file uploads in generated apps.

What a field accepts follows the requirement; the API checks a file's real content (never only its
name) and size; files go to Cloudflare R2 / AWS S3 or the local disk, chosen from the platform's
.env with no code change for production; cloud drives come through Uppy Companion. The live proof
(CHANGELOG) ran the generated API against Postgres with local-disk and S3-compatible storage, a
Companion web-link import and the admin console in a browser; these tests keep the generated code
in that shape and run its checks offline.
"""

import io
import json
import os
import tempfile
import types
import zipfile
from pathlib import Path
from unittest import TestCase, mock

from omnistackai_agent_engine.application_ir import ApplicationIR, example_ir
from omnistackai_agent_engine.application_ir.ir import Field, FieldType
from omnistackai_agent_engine.codegen.assembler import assemble_project
from omnistackai_agent_engine.codegen.upload_policy import FORBIDDEN, policy_for
from omnistackai_agent_engine.codegen.uploads import python_upload_files
from omnistackai_agent_engine.localrun.upload_env import production_settings, resolve_store, upload_environment

_HIRING = Path(__file__).parent / "fixtures" / "ir" / "hiring_portal.json"


def _hiring() -> ApplicationIR:
    return ApplicationIR.from_dict(json.loads(_HIRING.read_text(encoding="utf-8")))


def _policy(name: str, *rules: str):
    return policy_for(Field(name, FieldType.ATTACHMENT, validation=rules))


def _module(source: str, name: str) -> types.ModuleType:
    module = types.ModuleType(name)
    exec(compile(source, name, "exec"), module.__dict__)  # noqa: S102 - our own generated code
    return module


class WhatAFieldAcceptsFollowsTheRequirement(TestCase):
    def test_the_plan_can_say_it(self) -> None:
        policy = _policy("brochure", "accept:presentations|pdf", "max_size_mb:25", "max_files:3")
        self.assertEqual(policy.extensions, ("pptx", "ppt", "odp", "pdf"))
        self.assertEqual((policy.max_size_mb, policy.max_files), (25, 3))

    def test_otherwise_the_name_decides(self) -> None:
        self.assertEqual(_policy("resume").extensions, ("pdf", "doc", "docx"))
        self.assertEqual(_policy("product_photos").max_files, 8)
        self.assertIn("png", _policy("avatar").extensions)
        self.assertEqual(_policy("avatar").max_size_mb, 2)
        self.assertIn("xlsx", _policy("invoice").extensions)
        self.assertIn("dcm", _policy("chest_ct_scan").extensions)
        # Whole words, not substrings: "contract_scan" is a document, not a CT scan.
        self.assertNotIn("dcm", _policy("contract_scan").extensions)

    def test_programs_and_web_pages_are_never_accepted(self) -> None:
        policy = _policy("file", "accept:exe|svg|html|js|docm|pdf", "max_size_mb:900")
        self.assertEqual(policy.extensions, ("pdf",))
        self.assertEqual(policy.max_size_mb, 100, "uploads pass through the API, so one file is capped")
        self.assertTrue({"exe", "svg", "html", "js", "docm"} <= FORBIDDEN)

    def test_the_form_says_it_in_words(self) -> None:
        self.assertEqual(_policy("resume").describe(), "PDF, DOC or DOCX, up to 10 MB")
        self.assertIn("up to 8 files", _policy("gallery_images").describe())


class TheApiChecksTheRealContent(TestCase):
    def setUp(self) -> None:
        files = dict(python_upload_files(_hiring(), has_auth=True))
        self.checks = _module(files["app/file_checks.py"], "file_checks")
        self.router = files["app/routers/uploads.py"]
        self.storage_source = files["app/storage.py"]

    def _is(self, extension: str, data: bytes) -> bool:
        return self.checks.matches(extension, io.BytesIO(data))

    def test_real_files_pass(self) -> None:
        self.assertTrue(self._is("pdf", b"%PDF-1.7\n..."))
        self.assertTrue(self._is("png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 20))
        self.assertTrue(self._is("jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 20))
        self.assertTrue(self._is("csv", b"sku,qty\nA1,4\n"))
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("word/document.xml", "<w/>")
        self.assertTrue(self._is("docx", buf.getvalue()))

    def test_disguises_fail(self) -> None:
        program = b"MZ\x90\x00" + b"\x00" * 100
        self.assertFalse(self._is("pdf", program), "a program renamed .pdf")
        self.assertFalse(self._is("png", b"%PDF-1.4"), "a PDF renamed .png")
        self.assertFalse(self._is("csv", b"a,b\x00\x00"), "binary data renamed .csv")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("word/document.xml", "<w/>")
            z.writestr("word/vbaProject.bin", "macro")
        self.assertFalse(self._is("docx", buf.getvalue()), "a macro document renamed .docx")
        xlsx_as_docx = io.BytesIO()
        with zipfile.ZipFile(xlsx_as_docx, "w") as z:
            z.writestr("xl/workbook.xml", "<x/>")
        self.assertFalse(self._is("docx", xlsx_as_docx.getvalue()), "a spreadsheet renamed .docx")

    def test_each_field_carries_its_own_rules_and_uploads_need_an_account(self) -> None:
        self.assertIn('"Customer.resume"', self.router)
        self.assertIn('"max_bytes": 10485760', self.router)
        self.assertIn('@router.post("/uploads", dependencies=[Depends(require_auth)])', self.router)
        compile(self.router, "uploads.py", "exec")

    def test_the_local_disk_keeps_files_inside_its_folder(self) -> None:
        storage = _module(self.storage_source, "storage")
        with tempfile.TemporaryDirectory() as root:
            store = storage.LocalStore(root)
            store.put("customer/resume/" + "a" * 32 + "/cv.pdf", io.BytesIO(b"%PDF-"), "application/pdf")
            self.assertTrue(store.exists("customer/resume/" + "a" * 32 + "/cv.pdf"))
            with self.assertRaises(ValueError):
                store.path("../../etc/passwd")

    def test_s3_is_chosen_only_when_its_keys_are_set(self) -> None:
        storage = _module(self.storage_source, "storage")
        with tempfile.TemporaryDirectory() as root, mock.patch.dict(os.environ, {"LOCAL_STORAGE_DIR": root}, clear=True):
            self.assertEqual(storage.get_store().kind, "local")
        storage._store = None
        with mock.patch.dict(os.environ, {"STORAGE_DRIVER": "s3"}, clear=True):
            with self.assertRaises(RuntimeError):
                storage.get_store()


class TheAppsOfferTheUploadWindow(TestCase):
    def setUp(self) -> None:
        self.project = assemble_project(_hiring())

    def test_web_forms_and_the_admin_console_use_it_with_each_fields_rules(self) -> None:
        pages = [f.content for f in self.project.files() if f.path.startswith("apps/web/app/") and "<FileUploader" in f.content]
        self.assertTrue(pages)
        self.assertIn('field="Customer.resume"', "".join(pages))
        admin = self.project.get("apps/admin/app/manage/customers/page.tsx").content
        self.assertIn('upload: { field: "Customer.resume", accept: ["pdf", "doc", "docx"], maxSizeMb: 10, maxFiles: 1', admin)

    def test_the_window_is_inline_and_shows_the_servers_reason(self) -> None:
        uploader = self.project.get("apps/admin/components/file-uploader.tsx").content
        self.assertIn('import Dashboard from "@uppy/react/dashboard";', uploader)
        self.assertNotIn("DashboardModal", uploader, "a modal is blocked by the drawer the form sits in")
        self.assertIn("shouldRetry: (xhr) => xhr.status === 0 || xhr.status >= 500", uploader)
        self.assertIn("onAfterResponse", uploader)
        self.assertNotIn("uppy.destroy()", uploader, "React's development double-mount would destroy it")

    def test_packages_and_settings(self) -> None:
        package = json.loads(self.project.get("apps/web/package.json").content)
        self.assertEqual(package["dependencies"]["@uppy/core"], "6.1.0")
        for path in ("apps/web/.env.example", "services/api/.env.example"):
            self.assertNotIn("minioadmin", self.project.get(path).content)
        self.assertIn("S3_BUCKET=", self.project.get("services/api/.env.example").content)

    def test_companion_ships_with_apps_that_take_files_only(self) -> None:
        paths = {f.path for f in self.project.files()}
        self.assertIn("services/companion/index.js", paths)
        index = self.project.get("services/companion/index.js").content
        self.assertIn("uploadUrls", index)
        self.assertIn("process.exit(0)", index, "unconfigured, it stops cleanly instead of restarting forever")
        self.assertNotIn("services/companion/index.js", {f.path for f in assemble_project(example_ir("minimal-blog")).files()})


class ThePlatformChoosesTheStore(TestCase):
    R2_DEV = {"OMNISTACKAI_R2_DEV_ACCOUNT_ID": "acct", "OMNISTACKAI_R2_DEV_ACCESS_KEY_ID": "id",
              "OMNISTACKAI_R2_DEV_SECRET_ACCESS_KEY": "dev-secret", "OMNISTACKAI_R2_DEV_BUCKET": "omnistackai-dev"}
    R2_PROD = {"OMNISTACKAI_R2_PROD_ACCOUNT_ID": "acct", "OMNISTACKAI_R2_PROD_ACCESS_KEY_ID": "id",
               "OMNISTACKAI_R2_PROD_SECRET_ACCESS_KEY": "prod-secret", "OMNISTACKAI_R2_PROD_BUCKET": "omnistackai-prod"}
    S3 = {"OMNISTACKAI_S3_REGION": "ap-south-1", "OMNISTACKAI_S3_ACCESS_KEY_ID": "AKIA",
          "OMNISTACKAI_S3_SECRET_ACCESS_KEY": "s3-secret", "OMNISTACKAI_S3_BUCKET": "files"}

    def test_the_founders_order(self) -> None:
        self.assertEqual(resolve_store({})[0], "local")
        self.assertEqual(resolve_store(self.R2_DEV)[0], "r2-dev")
        name, settings = resolve_store({**self.R2_DEV, **self.R2_PROD, "OMNISTACKAI_STORAGE_TARGET": "prod"})
        self.assertEqual((name, settings["S3_ENDPOINT"]), ("r2-prod", "https://acct.r2.cloudflarestorage.com"))
        self.assertEqual(resolve_store({**self.S3, "OMNISTACKAI_STORAGE_TARGET": "prod"})[0], "s3")
        self.assertEqual(resolve_store({**self.R2_DEV, "OMNISTACKAI_STORAGE_TARGET": "prod"})[0], "local",
                         "a live app never writes to the development bucket")
        partial = {**self.R2_PROD, "OMNISTACKAI_R2_PROD_BUCKET": "", "OMNISTACKAI_STORAGE_TARGET": "prod"}
        self.assertEqual(resolve_store(partial)[0], "local", "a store counts only with all of its keys")

    def test_publishing_is_production_and_carries_only_keys(self) -> None:
        app, compose = production_settings({**self.R2_DEV, **self.S3})
        self.assertEqual((compose["STORAGE"], app["S3_BUCKET"]), ("s3", "files"))
        self.assertEqual(compose["UPLOAD_SOURCES"], "camera")

    def test_cloud_sources_appear_with_their_keys_and_every_secret_is_masked(self) -> None:
        source = {**self.R2_DEV, "OMNISTACKAI_COMPANION_SECRET": "companion-secret",
                  "OMNISTACKAI_GOOGLE_DRIVE_CLIENT_ID": "gid", "OMNISTACKAI_GOOGLE_DRIVE_CLIENT_SECRET": "drive-secret",
                  "OMNISTACKAI_DROPBOX_APP_KEY": "dkey"}  # Dropbox without its secret: not offered
        env = upload_environment(project_key="p1", api_url="http://127.0.0.1:9000", has_companion=True, source=source)
        self.assertEqual(dict(env.web)["NEXT_PUBLIC_UPLOAD_SOURCES"], "camera,url,google-drive")
        self.assertEqual(set(env.secrets), {"dev-secret", "companion-secret", "drive-secret"})
        self.assertEqual(dict(env.companion)["COMPANION_UPLOAD_URLS"], "http://127.0.0.1:9000/uploads")

    def test_the_preview_plan_masks_them(self) -> None:
        from omnistackai_agent_engine.localrun.plan import build_run_plan

        with tempfile.TemporaryDirectory() as tmp:
            for f in assemble_project(_hiring()).files():
                target = Path(tmp) / f.path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(f.content)
            with mock.patch.dict(os.environ, self.R2_DEV):
                plan = build_run_plan(tmp)
        rendered = json.dumps(plan.to_dict())
        self.assertNotIn("dev-secret", rendered)
        self.assertIn("S3_BUCKET", rendered)


class PublishingCarriesUploads(TestCase):
    def test_the_bundle_keeps_files_and_serves_companion_on_the_apps_domain(self) -> None:
        from omnistackai_agent_engine.publish.bundle import Layout, caddyfile, compose

        layout = Layout("hiring", "python", ("web", "admin"), has_companion=True)
        stack = compose(layout)
        self.assertIn("      - uploads:/data/uploads", stack)
        self.assertIn("  companion:", stack)
        self.assertIn("NEXT_PUBLIC_UPLOAD_SOURCES: ${UPLOAD_SOURCES:-camera}", stack)
        self.assertIn("handle /companion/* {", caddyfile(layout))
        self.assertNotIn("companion", compose(Layout("blog", "python", ("web",))))


class ThePlannerIsTold(TestCase):
    def test_the_prompt_asks_for_rules_from_the_requirement(self) -> None:
        source = Path(__file__).parents[1].joinpath("src/omnistackai_agent_engine/intake/nl_to_ir.py").read_text()
        self.assertIn("the types the requirement needs, never one fixed type", source)


class EachProjectHasItsOwnFolder(TestCase):
    """Found checking the founder's keys: every project shared the bucket with no folder of its own,
    so a deleted project's files could not be found. Now projects/<project>/... and a clean-up."""

    R2 = ThePlatformChoosesTheStore.R2_DEV

    def test_previews_and_published_apps_write_under_the_projects_folder(self) -> None:
        env = upload_environment(project_key="app_4ec4", api_url="http://x", has_companion=False, source=self.R2)
        self.assertEqual(dict(env.api)["STORAGE_PREFIX"], "projects/app_4ec4")
        prod = {**ThePlatformChoosesTheStore.R2_PROD}
        app, _ = production_settings(prod, project_key="app_4ec4")
        self.assertEqual(app["STORAGE_PREFIX"], "projects/app_4ec4")

    def test_the_generated_storage_puts_every_key_under_the_prefix(self) -> None:
        source = dict(python_upload_files(_hiring(), has_auth=False))["app/storage.py"]
        self.assertIn('self.prefix = _env("STORAGE_PREFIX").strip("/")', source)
        self.assertEqual(source.count("self._key(key)"), 3, "put, exists and the signed link")

    def test_deleting_a_project_removes_its_files_and_only_its_files(self) -> None:
        from omnistackai_agent_engine.localrun.upload_env import purge_project_files

        with tempfile.TemporaryDirectory() as root:
            mine, other = Path(root, "app_1", "a.pdf"), Path(root, "app_2", "b.pdf")
            for path in (mine, other):
                path.parent.mkdir(parents=True)
                path.write_bytes(b"%PDF-")
            report = purge_project_files("app_1", {"OMNISTACKAI_LOCAL_STORAGE_DIR": root})
            self.assertEqual(report, {"local": "deleted"})
            self.assertFalse(mine.exists())
            self.assertTrue(other.exists())
            self.assertEqual(purge_project_files("app_2", {"OMNISTACKAI_LOCAL_STORAGE_DIR": root}, only=("r2-prod",)), {},
                             "unpublishing touches production storage only")
            self.assertTrue(other.exists())

    def test_the_bucket_client_never_deletes_without_a_project_folder_and_hides_its_key(self) -> None:
        from omnistackai_agent_engine.localrun import s3_lite

        target = s3_lite.S3Target("https://acct.r2.cloudflarestorage.com", "auto", "b", "id", "very-secret")
        self.assertNotIn("very-secret", repr(target))
        for prefix in ("", "/", "projects"):
            with self.assertRaises(s3_lite.S3Error):
                s3_lite.delete_prefix(target, prefix)

    def test_the_bucket_client_lists_every_page_and_deletes_each_key(self) -> None:
        from omnistackai_agent_engine.localrun import s3_lite

        pages = [
            b'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><Contents><Key>projects/p/a</Key></Contents>'
            b"<NextContinuationToken>t</NextContinuationToken></ListBucketResult>",
            b'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><Contents><Key>projects/p/b</Key></Contents></ListBucketResult>',
        ]
        calls = []

        def fake(target, method, key="", query=None, **_):
            calls.append((method, key, dict(query or {})))
            return pages.pop(0) if method == "GET" else b""

        target = s3_lite.S3Target("https://e", "auto", "b", "id", "s")
        with mock.patch.object(s3_lite, "_request", fake):
            self.assertEqual(s3_lite.delete_prefix(target, "projects/p/"), 2)
        self.assertEqual(calls[1][2]["continuation-token"], "t")
        self.assertEqual([c[1] for c in calls if c[0] == "DELETE"], ["projects/p/a", "projects/p/b"])
