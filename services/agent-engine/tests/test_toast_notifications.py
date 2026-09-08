"""Tests for Task R-279: Global Notification Toast System & Action Feedback in Generated Next.js Web App."""

import unittest

from omnistackai_agent_engine.application_ir.ir import (
    AdminStrategy,
    ApiEndpoint,
    ApplicationIR,
    BackendStrategy,
    DatabaseStrategy,
    Entity,
    Field,
    FieldType,
    HttpMethod,
    MobileProfile,
    Platform,
    ProjectStrategy,
    Relation,
    RelationKind,
    RepoStrategy,
    Role,
    Screen,
    WebStrategy,
)
from omnistackai_agent_engine.application_ir.examples import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_screen_page,
    render_toast_component,
)


def _make_test_ir(with_delete: bool = True, description: str = "Test Description") -> ApplicationIR:
    post_entity = Entity(
        name="Post",
        fields=(
            Field("id", FieldType.STRING, required=True),
            Field("title", FieldType.STRING, required=True),
            Field("content", FieldType.TEXT, required=True),
            Field(
                "status",
                FieldType.STRING,
                required=True,
                validation=("enum:draft|published|archived",),
            ),
            Field("is_featured", FieldType.BOOL, required=True),
        ),
    )
    comment_entity = Entity(
        name="Comment",
        fields=(
            Field("id", FieldType.STRING, required=True),
            Field("post_id", FieldType.STRING, required=True),
            Field("body", FieldType.TEXT, required=True),
        ),
        relations=(
            Relation("post", "Post", RelationKind.MANY_TO_ONE),
        ),
    )
    entities = (post_entity, comment_entity)
    apis = [
        ApiEndpoint(HttpMethod.GET, "/posts", response_schema="Post"),
        ApiEndpoint(HttpMethod.POST, "/posts", request_schema="Post", response_schema="Post"),
        ApiEndpoint(HttpMethod.GET, "/posts/{id}", response_schema="Post"),
        ApiEndpoint(HttpMethod.PUT, "/posts/{id}", request_schema="Post", response_schema="Post"),
        ApiEndpoint(HttpMethod.GET, "/comments", response_schema="Comment"),
    ]
    if with_delete:
        apis.append(ApiEndpoint(HttpMethod.DELETE, "/posts/{id}", response_schema="Post"))
        apis.append(ApiEndpoint(HttpMethod.DELETE, "/comments/{id}", response_schema="Comment"))

    screens = (
        Screen(
            "posts",
            "admin",
            components=("list",),
            actions=("view", "delete") if with_delete else ("view",),
            navigation=("post_form",),
        ),
        Screen(
            "post_detail",
            "admin",
            components=("detail",),
            actions=("view", "delete") if with_delete else ("view",),
            navigation=("posts",),
        ),
        Screen(
            "post_form",
            "admin",
            components=("form",),
            actions=("create", "update"),
            navigation=("posts",),
        ),
    )

    return ApplicationIR(
        name="BlogApp",
        description=description,
        platforms=(Platform.WEB,),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE,
            WebStrategy.NEXTJS,
            AdminStrategy.NONE,
            BackendStrategy.PYTHON,
            DatabaseStrategy.POSTGRES,
            RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        roles=(Role("admin"),),
        entities=entities,
        apis=tuple(apis),
        screens=screens,
    )


class ToastNotificationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = _make_test_ir()
        self.adapter = NextjsWebAdapter()
        self.project = self.adapter.generate(self.ir)
        self.toast_content = render_toast_component()
        self.layout_content = self.project.get("app/layout.tsx").content

    def test_toast_component_is_client_component(self) -> None:
        self.assertTrue(self.toast_content.startswith('"use client";'))

    def test_toast_component_exports_types_and_provider(self) -> None:
        self.assertIn('export type ToastType = "success" | "error" | "info";', self.toast_content)
        self.assertIn("export interface ToastItem {", self.toast_content)
        self.assertIn("export interface ToastContextValue {", self.toast_content)
        self.assertIn("export function ToastProvider({ children }: { children: React.ReactNode }) {", self.toast_content)
        self.assertIn("export function useToast(): ToastContextValue {", self.toast_content)

    def test_toast_component_has_viewport_and_aria_live(self) -> None:
        self.assertIn('aria-live="polite"', self.toast_content)
        self.assertIn('position: "fixed"', self.toast_content)
        self.assertIn("bottom: 24", self.toast_content)
        self.assertIn("right: 24", self.toast_content)
        self.assertIn("zIndex: 9999", self.toast_content)

    def test_toast_component_has_distinct_status_accents(self) -> None:
        # Success status
        self.assertIn("#a7f3d0", self.toast_content)
        self.assertIn("#15803d", self.toast_content)
        self.assertIn("✓", self.toast_content)
        # Error status
        self.assertIn("#fecaca", self.toast_content)
        self.assertIn("#b91c1c", self.toast_content)
        self.assertIn("✕", self.toast_content)
        # Info status
        self.assertIn("#bfdbfe", self.toast_content)
        self.assertIn("#1d4ed8", self.toast_content)
        self.assertIn("ℹ", self.toast_content)

    def test_toast_component_has_dismiss_button_and_auto_timer(self) -> None:
        self.assertIn('aria-label="Dismiss notification"', self.toast_content)
        self.assertIn("&times;", self.toast_content)
        self.assertIn("setTimeout", self.toast_content)
        self.assertIn("clearTimeout", self.toast_content)

    def test_toast_provider_in_generated_files(self) -> None:
        self.assertIn("components/toast.tsx", set(self.project.paths()))
        file = self.project.get("components/toast.tsx")
        self.assertEqual(file.content, self.toast_content)

    def test_layout_imports_and_wraps_toast_provider(self) -> None:
        self.assertIn('import { ToastProvider } from "../components/toast";', self.layout_content)
        self.assertIn("<ToastProvider>", self.layout_content)
        self.assertIn("</ToastProvider>", self.layout_content)
        self.assertIn("<Navbar />", self.layout_content)
        self.assertIn("{children}", self.layout_content)

    def test_collection_screen_wires_use_toast(self) -> None:
        screen = next(s for s in self.ir.screens if s.id == "posts")
        content = render_screen_page(screen, self.ir)
        self.assertIn('import { useToast } from "../components/toast";', content)
        self.assertIn("const { toast } = useToast();", content)

    def test_collection_screen_csv_export_triggers_toast(self) -> None:
        screen = next(s for s in self.ir.screens if s.id == "posts")
        content = render_screen_page(screen, self.ir)
        self.assertIn('toast.info("Exported CSV successfully");', content)

    def test_collection_screen_delete_actions_trigger_toast(self) -> None:
        screen = next(s for s in self.ir.screens if s.id == "posts")
        content = render_screen_page(screen, self.ir)
        # Single delete feedback
        self.assertIn('toast.success("Post deleted successfully");', content)
        self.assertIn('toast.error(err instanceof Error ? err.message : "Failed to delete Post");', content)
        # Batch delete feedback
        self.assertIn("toast.success(`Deleted ${count} ${count === 1 ? \"Post\" : \"Posts\"} successfully`);", content)
        self.assertIn('toast.error(err instanceof Error ? err.message : "Failed to delete selected items");', content)

    def test_detail_screen_wires_use_toast_and_feedback(self) -> None:
        screen = next(s for s in self.ir.screens if s.id == "post_detail")
        content = render_screen_page(screen, self.ir)
        self.assertIn('import { useToast } from "../components/toast";', content)
        self.assertIn("const { toast } = useToast();", content)
        self.assertIn('toast.info("Exported JSON successfully");', content)
        self.assertIn('toast.success("Post deleted successfully");', content)
        self.assertIn('toast.error(err instanceof Error ? err.message : "Failed to delete Post");', content)

    def test_form_screen_wires_use_toast_and_feedback(self) -> None:
        screen = next(s for s in self.ir.screens if s.id == "post_form")
        content = render_screen_page(screen, self.ir)
        self.assertIn('import { useToast } from "../components/toast";', content)
        self.assertIn("const { toast } = useToast();", content)
        self.assertIn('toast.success(isEdit ? "Post updated successfully" : "Post created successfully");', content)
        self.assertIn('toast.error(err instanceof Error ? err.message : (isEdit ? "Failed to update Post" : "Failed to create Post"));', content)
        self.assertIn('toast.info("Form reset to original values");', content)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        ir1 = _make_test_ir(description="Alpha description")
        ir2 = _make_test_ir(description="Beta description 98765")
        p1 = self.adapter.generate(ir1)
        p2 = self.adapter.generate(ir2)

        # components/toast.tsx must be 100% byte-identical
        self.assertEqual(
            p1.get("components/toast.tsx").content,
            p2.get("components/toast.tsx").content,
        )

        # Screens must be 100% byte-identical
        for screen in ir1.screens:
            self.assertEqual(
                render_screen_page(screen, ir1),
                render_screen_page(screen, ir2),
            )

    def test_demo_projects_generate_toast_component(self) -> None:
        for name in ("minimal-blog", "rideshare-favourites"):
            ex = example_ir(name)
            proj = self.adapter.generate(ex)
            self.assertIn("components/toast.tsx", set(proj.paths()))
            self.assertIn("<ToastProvider>", proj.get("app/layout.tsx").content)


if __name__ == "__main__":
    unittest.main()
