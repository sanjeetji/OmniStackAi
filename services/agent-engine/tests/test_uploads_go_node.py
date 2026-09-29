"""PC-105: uploads in the Go and Node (Express and Hono) backends.

The same contract as the Python backend (PC-102). The live proof (CHANGELOG) ran the 19 upload
checks - real files accepted, a program renamed .pdf, a macro document named .docx, wrong types,
oversize and empty files refused, crafted keys 404 - against each generated API on the local disk
and on S3 (moto), plus OpenDocument parts, the sign-in requirement and a link import through
Companion. These tests keep the generated code in that shape.
"""

import json
from dataclasses import replace
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import ApplicationIR, example_ir
from omnistackai_agent_engine.codegen.assembler import assemble_project

_PORTAL = Path(__file__).parent / "fixtures" / "ir" / "hiring_portal.json"


def _portal(backend: str, hono: bool = False):
    ir = ApplicationIR.from_dict(json.loads(_PORTAL.read_text(encoding="utf-8")))
    ir = replace(ir, project_strategy=replace(ir.project_strategy, backend_strategy=backend))
    if hono:
        ir = replace(ir, description=ir.description + " (hono)")
    return {f.path: f.content for f in assemble_project(ir).files()}


def _api(files: dict, suffix: str) -> str:
    return files[f"services/api/{suffix}"]


class GoReceivesAndServesFiles(TestCase):
    def setUp(self) -> None:
        self.files = _portal("go")

    def test_the_routes_are_registered_and_uploading_needs_sign_in(self) -> None:
        main = _api(self.files, "main.go")
        self.assertIn('mux.HandleFunc("POST /uploads", handlers.RequireAuth(handlers.Upload))', main)
        self.assertIn('mux.HandleFunc("GET /files/{key...}", handlers.ServeFile)', main)

    def test_each_field_keeps_its_own_rules(self) -> None:
        handlers = _api(self.files, "internal/handlers/uploads.go")
        self.assertIn('"Customer.resume":   {Folder: "customer/resume", Extensions: []string{"pdf", "doc", "docx"}, MaxBytes: 10485760', handlers)
        self.assertIn("io.LimitReader(part, policy.MaxBytes+1)", handlers, "an oversize file is never read whole")
        self.assertIn("uploads.Matches(ext, tmp, size)", handlers)

    def test_content_is_checked_not_the_name(self) -> None:
        checks = _api(self.files, "internal/uploads/checks.go")
        self.assertIn('"vbaproject.bin"', checks)
        self.assertIn('"docx": "word/document.xml"', checks)
        self.assertIn("zip.NewReader(f, size)", checks)

    def test_storage_is_r2_s3_or_the_disk_and_needs_only_keys(self) -> None:
        storage = _api(self.files, "internal/storage/storage.go")
        for setting in ("S3_ENDPOINT", "S3_BUCKET", "STORAGE_PREFIX", "LOCAL_STORAGE_DIR", "STORAGE_DRIVER"):
            self.assertIn(f'"{setting}"', storage)
        self.assertIn("aws.RequestChecksumCalculationWhenRequired", storage, "R2 refuses the newer checksums")
        self.assertIn("s3.WithPresignExpires(5*time.Minute)", storage)
        self.assertIn('!strings.HasPrefix(target, s.root+string(os.PathSeparator))', storage)
        self.assertIn("github.com/aws/aws-sdk-go-v2/service/s3", _api(self.files, "go.mod"))

    def test_the_local_disk_answer_is_never_sniffed(self) -> None:
        self.assertIn('w.Header().Set("X-Content-Type-Options", "nosniff")', _api(self.files, "internal/handlers/uploads.go"))


class NodeReceivesAndServesFiles(TestCase):
    def test_express_and_hono_mount_the_same_routes(self) -> None:
        express = _portal("node")
        hono = _portal("node", hono=True)
        self.assertIn("app.use(uploadsRouter);", _api(express, "src/app.ts"))
        self.assertIn("router.post('/uploads', requireAuth, async (req: Request, res: Response)", _api(express, "src/uploads/router.ts"))
        self.assertIn("app.route('/', uploadsRouter);", _api(hono, "src/app.ts"))
        self.assertIn("router.post('/uploads', requireAuth, async (c)", _api(hono, "src/uploads/router.ts"))
        self.assertIn("Readable.fromWeb(", _api(hono, "src/uploads/router.ts"))

    def test_the_rules_and_the_key_pattern(self) -> None:
        receive = _api(_portal("node"), "src/uploads/receive.ts")
        self.assertIn('"Customer.resume": {', receive)
        self.assertIn("const KEY = /^[a-z0-9_]+\\/[a-z0-9_]+\\/[0-9a-f]{32}\\/", receive, "slashes escaped in the regex literal")
        self.assertIn("refuse(413, `This field accepts files up to", receive)
        self.assertIn("if (!(await matches(ext, tmp)))", receive)

    def test_content_checks_and_storage(self) -> None:
        files = _portal("node")
        checks = _api(files, "src/uploads/checks.ts")
        self.assertIn("endsWith('vbaproject.bin')", checks)
        self.assertIn("storedEntry(whole, mimetype)", checks, "OpenDocument's mimetype part is read")
        storage = _api(files, "src/storage.ts")
        self.assertIn("requestChecksumCalculation: 'WHEN_REQUIRED'", storage)
        self.assertIn("{ expiresIn: 300 }", storage)
        package = json.loads(_api(files, "package.json"))
        for dependency in ("@aws-sdk/client-s3", "@aws-sdk/s3-request-presigner", "busboy"):
            self.assertIn(dependency, package["dependencies"])
        self.assertIn("S3_BUCKET=", _api(files, ".env.example"))


class AppsWithoutFilesAreUnchanged(TestCase):
    def test_no_upload_code_without_an_attachment_field(self) -> None:
        for backend in ("go", "node"):
            blog = example_ir("minimal-blog")
            files = {f.path for f in assemble_project(replace(blog, project_strategy=replace(blog.project_strategy, backend_strategy=backend))).files()}
            self.assertFalse([p for p in files if "/uploads" in p or p.endswith("storage.go") or p.endswith("storage.ts")], backend)
