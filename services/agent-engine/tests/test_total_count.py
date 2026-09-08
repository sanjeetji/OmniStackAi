"""Tests for total count queries and X-Total-Count header across Go, Python, and Next.js [R-259]."""

from unittest import TestCase

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import GoBackendAdapter, NextjsWebAdapter, PythonBackendAdapter


class PythonTotalCountRepositoryTests(TestCase):
    def setUp(self) -> None:
        self.project = PythonBackendAdapter().generate(example_ir("minimal-blog"))
        self.post_repo = self.project.get("app/repositories/post.py").content
        self.comment_repo = self.project.get("app/repositories/comment.py").content

    def test_python_repo_declares_count_method(self) -> None:
        self.assertIn("async def count_post() -> int:", self.post_repo)
        self.assertIn('SELECT COUNT(*) AS count FROM {TABLE}', self.post_repo)

    def test_python_repo_declares_count_by_relation_method(self) -> None:
        self.assertIn("async def count_comment_by_post(post_id: str) -> int:", self.comment_repo)
        self.assertIn('SELECT COUNT(*) AS count FROM {TABLE} WHERE post_id = %s', self.comment_repo)


class PythonTotalCountRouterTests(TestCase):
    def setUp(self) -> None:
        self.project = PythonBackendAdapter().generate(example_ir("minimal-blog"))
        self.posts_router = self.project.get("app/routers/posts.py").content
        self.main_py = self.project.get("app/main.py").content

    def test_router_imports_response_and_sets_total_count_header(self) -> None:
        self.assertIn("from fastapi import APIRouter, Depends, HTTPException, Response", self.posts_router)
        self.assertIn("total = await post.count_post()", self.posts_router)
        self.assertIn('response.headers["X-Total-Count"] = str(total)', self.posts_router)

    def test_router_sets_total_count_header_on_subcollection_list(self) -> None:
        self.assertIn("total = await comment.count_comment_by_post(postId)", self.posts_router)
        self.assertIn('response.headers["X-Total-Count"] = str(total)', self.posts_router)

    def test_python_cors_exposes_x_total_count_header(self) -> None:
        self.assertIn('expose_headers=["X-Total-Count"]', self.main_py)


class GoTotalCountStoreTests(TestCase):
    def setUp(self) -> None:
        self.project = GoBackendAdapter().generate(example_ir("minimal-blog"))
        self.post_store = self.project.get("internal/store/post.go").content
        self.comment_store = self.project.get("internal/store/comment.go").content

    def test_go_store_declares_count_method(self) -> None:
        self.assertIn("func CountPost(ctx context.Context, db *sql.DB) (int, error)", self.post_store)
        self.assertIn("SELECT COUNT(*) FROM post", self.post_store)

    def test_go_store_declares_count_by_relation_method(self) -> None:
        self.assertIn("func CountCommentByPost(ctx context.Context, db *sql.DB, postID string) (int, error)", self.comment_store)
        self.assertIn("SELECT COUNT(*) FROM comment WHERE post_id = $1", self.comment_store)


class GoTotalCountHandlerTests(TestCase):
    def setUp(self) -> None:
        self.project = GoBackendAdapter().generate(example_ir("minimal-blog"))
        self.posts_handler = self.project.get("internal/handlers/posts.go").content
        self.main_go = self.project.get("main.go").content

    def test_handler_sets_x_total_count_header(self) -> None:
        self.assertIn("total, err := store.CountPost(r.Context(), h.DB)", self.posts_handler)
        self.assertIn('w.Header().Set("X-Total-Count", strconv.Itoa(total))', self.posts_handler)

    def test_subcollection_handler_sets_x_total_count_header(self) -> None:
        self.assertIn('total, err := store.CountCommentByPost(r.Context(), h.DB, r.PathValue("postId"))', self.posts_handler)
        self.assertIn('w.Header().Set("X-Total-Count", strconv.Itoa(total))', self.posts_handler)

    def test_go_cors_exposes_x_total_count_header(self) -> None:
        self.assertIn('w.Header().Set("Access-Control-Expose-Headers", "X-Total-Count")', self.main_go)


class NextJsTotalCountClientTests(TestCase):
    def setUp(self) -> None:
        self.project = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        self.api_ts = self.project.get("lib/api.ts").content

    def test_paginated_result_interface_exported(self) -> None:
        self.assertIn("export interface PaginatedResult<T> {", self.api_ts)
        self.assertIn("data: T;", self.api_ts)
        self.assertIn("total: number;", self.api_ts)

    def test_request_with_meta_extracts_x_total_count_header(self) -> None:
        self.assertIn("async function requestWithMeta<T>(path: string, options: ApiOptions = {}, body?: unknown): Promise<PaginatedResult<T>>", self.api_ts)
        self.assertIn('const totalHeader = res.headers.get("X-Total-Count");', self.api_ts)
        self.assertIn("const total = totalHeader ? parseInt(totalHeader, 10) : 0;", self.api_ts)
        self.assertIn("return { data, total };", self.api_ts)

    def test_list_with_count_helpers_generated(self) -> None:
        self.assertIn("export async function listPostsWithCount(", self.api_ts)
        self.assertIn("Promise<PaginatedResult<Post[]>>", self.api_ts)
        self.assertIn('return requestWithMeta<Post[]>("/posts", { method: "GET", ...options });', self.api_ts)

    def test_list_by_with_count_helpers_generated(self) -> None:
        self.assertIn("export async function listCommentsByPostWithCount(", self.api_ts)
        self.assertIn("Promise<PaginatedResult<Comment[]>>", self.api_ts)
        self.assertIn('return requestWithMeta<Comment[]>(`/posts/${encodeURIComponent(postId)}/comments`, { method: "GET", ...options });', self.api_ts)

    def test_backward_compatible_list_methods_preserved(self) -> None:
        self.assertIn("export async function listPosts(", self.api_ts)
        self.assertIn("Promise<Post[]>", self.api_ts)
        self.assertIn("export async function listCommentsByPost(", self.api_ts)
        self.assertIn("Promise<Comment[]>", self.api_ts)
