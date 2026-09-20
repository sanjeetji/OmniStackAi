"""Unit tests for F-07 SEO & AI search: codegen, deterministic audit, and workspace updates."""

import tempfile
import unittest
from pathlib import Path

from omnistackai_agent_engine.application_ir import (
    AdminStrategy,
    ApplicationIR,
    BackendStrategy,
    DatabaseStrategy,
    Entity,
    Field,
    FieldType,
    MobileProfile,
    Platform,
    ProjectStrategy,
    RepoStrategy,
    Role,
    Screen,
    WebStrategy,
)
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter
from omnistackai_agent_engine.seo.audit import audit_files_seo, audit_project_seo
from omnistackai_agent_engine.studio.workspace import StudioWorkspaceStore


def _sample_ir() -> ApplicationIR:
    return ApplicationIR(
        name="TaskMaster Pro",
        description="A high-performance task management application for engineering teams.",
        platforms=(Platform.WEB,),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE,
            WebStrategy.NEXTJS,
            AdminStrategy.NONE,
            BackendStrategy.GO,
            DatabaseStrategy.POSTGRES,
            RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        roles=(Role("member"),),
        entities=(
            Entity(
                "Task",
                (
                    Field("id", FieldType.UUID),
                    Field("title", FieldType.STRING),
                    Field("completed", FieldType.BOOL, required=False),
                ),
            ),
        ),
        screens=(
            Screen("tasks", "member"),
            Screen("pricing", "member"),
        ),
    )


class TestSEOCodegen(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = _sample_ir()
        self.adapter = NextjsWebAdapter()
        self.project = self.adapter.generate(self.ir)

    def test_seo_files_generated(self) -> None:
        paths = set(self.project.paths())
        self.assertIn("app/sitemap.ts", paths)
        self.assertIn("app/robots.ts", paths)
        self.assertIn("public/llms.txt", paths)
        self.assertIn("app/opengraph-image.tsx", paths)
        self.assertIn("app/tasks/layout.tsx", paths)
        self.assertIn("app/pricing/layout.tsx", paths)

    def test_sitemap_content(self) -> None:
        content = self.project.get("app/sitemap.ts").content
        self.assertIn("MetadataRoute.Sitemap", content)
        self.assertIn("url: baseUrl", content)
        self.assertIn("${baseUrl}/tasks", content)
        self.assertIn("${baseUrl}/pricing", content)

    def test_robots_content(self) -> None:
        content = self.project.get("app/robots.ts").content
        self.assertIn("MetadataRoute.Robots", content)
        self.assertIn("NEXT_PUBLIC_DISCOURAGE_SEARCH", content)
        self.assertIn("sitemap: `${baseUrl}/sitemap.xml`", content)

    def test_llms_txt_content(self) -> None:
        content = self.project.get("public/llms.txt").content
        self.assertIn("# TaskMaster Pro", content)
        self.assertIn("## Routes", content)
        self.assertIn("- `/`: Home overview and dashboard", content)
        self.assertIn("- `/tasks`: Tasks", content)
        self.assertIn("## Content Policy", content)

    def test_opengraph_image_content(self) -> None:
        content = self.project.get("app/opengraph-image.tsx").content
        self.assertIn('from "next/og"', content)
        self.assertIn("TaskMaster Pro", content)
        self.assertIn("ImageResponse", content)

    def test_root_layout_metadata_and_json_ld(self) -> None:
        content = self.project.get("app/layout.tsx").content
        self.assertIn("metadataBase:", content)
        self.assertIn("TaskMaster Pro", content)
        self.assertIn('type="application/ld+json"', content)
        self.assertIn('"@type": "WebSite"', content)
        self.assertIn('"@type": "Organization"', content)

    def test_screen_layout_metadata(self) -> None:
        tasks_layout = self.project.get("app/tasks/layout.tsx").content
        self.assertIn('title: "Tasks"', tasks_layout)
        self.assertIn("openGraph:", tasks_layout)
        self.assertIn('canonical: "/tasks"', tasks_layout)


class TestSEOAudit(unittest.TestCase):
    def test_audit_passes_on_generated_project(self) -> None:
        ir = _sample_ir()
        project = NextjsWebAdapter().generate(ir)
        files = {f.path: f.content for f in project.files()}

        report = audit_files_seo(files)
        # Should have high score and 0 critical errors
        self.assertGreaterEqual(report.score, 80)
        errors = [f for f in report.findings if f.severity == "error"]
        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")

    def test_audit_detects_flaws_on_broken_project(self) -> None:
        broken_files = {
            "app/page.tsx": "export default function Page() { return <div><p>No h1 heading here</p><img src='/pic.png' /></div>; }",
            "app/layout.tsx": 'export const metadata = { title: "App", description: "Short" };\nexport default function Layout({children}) { return <html><body>{children}</body></html>; }',
            # Missing sitemap.ts, robots.ts, llms.txt, opengraph-image.tsx
        }

        report = audit_files_seo(broken_files)
        finding_ids = {f.id for f in report.findings}

        self.assertIn("missing-llms-txt", finding_ids)
        self.assertIn("missing-sitemap", finding_ids)
        self.assertIn("missing-robots", finding_ids)
        self.assertIn("missing-og-image", finding_ids)
        self.assertIn("short-description", finding_ids)
        self.assertIn("missing-h1", finding_ids)
        self.assertIn("missing-image-alt", finding_ids)
        self.assertLess(report.score, 60)


class TestWorkspaceSEOUpdate(unittest.TestCase):
    def test_update_page_seo_creates_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = StudioWorkspaceStore(root_dir=tmp_dir)
            ws_id = "test-ws-seo"
            store.ensure_workspace(ws_id)
            repo_dir = store.repo_path(ws_id)

            # Initialize repo with git and a basic layout
            import subprocess
            subprocess.run(["git", "init", "-b", "main", str(repo_dir)], check=True, capture_output=True)

            app_dir = repo_dir / "app"
            app_dir.mkdir(parents=True, exist_ok=True)
            (app_dir / "layout.tsx").write_text(
                'export const metadata = { title: { default: "Initial" }, description: "Initial description." };\n'
                'export default function RootLayout({ children }) { return <html><body>{children}</body></html>; }',
                encoding="utf-8",
            )
            from omnistackai_agent_engine.git_service import commit_all
            commit_all(repo_dir, author_name="Tester", author_email="t@example.com", message="init")

            # Update page SEO for /pricing
            res = store.update_page_seo(
                ws_id,
                route="/pricing",
                title="Enterprise Pricing",
                description="Custom quotes and dedicated SLA for high-growth engineering teams.",
                noindex=False,
            )

            self.assertIn("commit_sha", res)
            self.assertTrue(len(res["commit_sha"]) > 0)

            # Check that app/pricing/layout.tsx was written
            pricing_layout = repo_dir / "app" / "pricing" / "layout.tsx"
            self.assertTrue(pricing_layout.is_file())
            content = pricing_layout.read_text(encoding="utf-8")
            self.assertIn("Enterprise Pricing", content)
            self.assertIn("dedicated SLA", content)
            self.assertIn('canonical: "/pricing"', content)


if __name__ == "__main__":
    unittest.main()
