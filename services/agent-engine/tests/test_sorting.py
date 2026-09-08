"""Tests for R-258: Query Parameter Sorting (sort & order) with SQL injection whitelist protection."""

from unittest import TestCase

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import NextjsWebAdapter
from omnistackai_agent_engine.codegen.backend_go import GoBackendAdapter
from omnistackai_agent_engine.codegen.backend_python import PythonBackendAdapter


class GoSortingStoreTests(TestCase):
    def setUp(self) -> None:
        self.project = GoBackendAdapter().generate(example_ir("minimal-blog"))
        self.post_store = self.project.get("internal/store/post.go").content
        self.comment_store = self.project.get("internal/store/comment.go").content

    def test_store_imports_fmt_and_strings(self) -> None:
        self.assertIn('"fmt"', self.post_store)
        self.assertIn('"strings"', self.post_store)

    def test_list_entity_store_whitelists_sort_fields(self) -> None:
        self.assertIn('col := "id"', self.post_store)
        self.assertIn("switch sort {", self.post_store)
        self.assertIn('case "id":', self.post_store)
        self.assertIn('case "title":', self.post_store)
        self.assertIn('case "body":', self.post_store)
        self.assertIn('case "published":', self.post_store)

    def test_list_entity_store_validates_order_direction(self) -> None:
        self.assertIn('dir := "ASC"', self.post_store)
        self.assertIn('if strings.ToLower(order) == "desc"', self.post_store)
        self.assertIn('dir = "DESC"', self.post_store)

    def test_list_entity_store_formats_validated_query(self) -> None:
        self.assertIn('fmt.Sprintf("SELECT id, title, body, published FROM post ORDER BY %s %s LIMIT $1 OFFSET $2", col, dir)', self.post_store)

    def test_subcollection_store_has_sort_whitelist_and_order(self) -> None:
        self.assertIn('col := "id"', self.comment_store)
        self.assertIn('case "id":', self.comment_store)
        self.assertIn('case "body":', self.comment_store)
        self.assertIn('fmt.Sprintf("SELECT id, body FROM comment WHERE post_id = $1 ORDER BY %s %s LIMIT $2 OFFSET $3", col, dir)', self.comment_store)


class GoSortingHandlerTests(TestCase):
    def setUp(self) -> None:
        self.project = GoBackendAdapter().generate(example_ir("minimal-blog"))
        self.shared = self.project.get("internal/handlers/handlers.go").content
        self.posts_handler = self.project.get("internal/handlers/posts.go").content

    def test_parse_sort_helper_emitted(self) -> None:
        self.assertIn("func parseSort(r *http.Request) (string, string)", self.shared)
        self.assertIn('sort := r.URL.Query().Get("sort")', self.shared)
        self.assertIn('if sort == "" {\n\t\tsort = "id"\n\t}', self.shared)
        self.assertIn('order := r.URL.Query().Get("order")', self.shared)
        self.assertIn('if strings.ToLower(order) == "desc" {\n\t\torder = "desc"\n\t} else {\n\t\torder = "asc"\n\t}', self.shared)

    def test_handlers_parse_sort_and_pass_to_store(self) -> None:
        self.assertIn("sort, order := parseSort(r)", self.posts_handler)
        self.assertIn("store.ListPost(r.Context(), h.DB, limit, offset, sort, order)", self.posts_handler)
        self.assertIn('store.ListCommentByPost(r.Context(), h.DB, r.PathValue("postId"), limit, offset, sort, order)', self.posts_handler)


class PythonSortingRepositoryTests(TestCase):
    def setUp(self) -> None:
        self.project = PythonBackendAdapter().generate(example_ir("minimal-blog"))
        self.post_repo = self.project.get("app/repositories/post.py").content
        self.comment_repo = self.project.get("app/repositories/comment.py").content

    def test_repository_declares_allowed_sort_fields(self) -> None:
        self.assertIn("ALLOWED_SORT_FIELDS = ['id', 'title', 'body', 'published']", self.post_repo)

    def test_repository_whitelists_column_and_validates_order(self) -> None:
        self.assertIn('sort_col = sort if sort in ALLOWED_SORT_FIELDS else "id"', self.post_repo)
        self.assertIn('sort_dir = "DESC" if order.lower() == "desc" else "ASC"', self.post_repo)
        self.assertIn('ORDER BY {sort_col} {sort_dir} LIMIT %s OFFSET %s', self.post_repo)

    def test_subcollection_repository_whitelists_sort_and_order(self) -> None:
        self.assertIn('sort_col = sort if sort in ALLOWED_SORT_FIELDS else "id"', self.comment_repo)
        self.assertIn('sort_dir = "DESC" if order.lower() == "desc" else "ASC"', self.comment_repo)
        self.assertIn('WHERE post_id = %s ORDER BY {sort_col} {sort_dir} LIMIT %s OFFSET %s', self.comment_repo)


class PythonSortingRouterTests(TestCase):
    def setUp(self) -> None:
        self.project = PythonBackendAdapter().generate(example_ir("minimal-blog"))
        self.posts_router = self.project.get("app/routers/posts.py").content

    def test_router_declares_sort_and_order_query_parameters(self) -> None:
        self.assertIn('async def get_posts(response: Response, limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc") -> list[dict]:', self.posts_router)
        self.assertIn("return await post.list_post(limit=limit, offset=offset, sort=sort, order=order)", self.posts_router)

    def test_subcollection_router_passes_sort_and_order(self) -> None:
        self.assertIn('async def get_posts_postid_comments(postId: str, response: Response, limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc") -> list[dict]:', self.posts_router)
        self.assertIn("return await comment.list_comment_by_post(postId, limit=limit, offset=offset, sort=sort, order=order)", self.posts_router)


class NextJsSortingClientTests(TestCase):
    def test_list_method_includes_sort_and_order_types(self) -> None:
        project = NextjsWebAdapter().generate(example_ir("rideshare-favourites"))
        api_ts = project.get("lib/api.ts").content
        self.assertIn('options?: ApiOptions & { params?: { limit?: number; offset?: number; sort?: string; order?: "asc" | "desc" } }', api_ts)

    def test_subcollection_list_method_includes_sort_and_order_types(self) -> None:
        project = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        api_ts = project.get("lib/api.ts").content
        self.assertIn("export async function listCommentsByPost(postId: string,", api_ts)
        self.assertIn('options?: ApiOptions & { params?: { limit?: number; offset?: number; sort?: string; order?: "asc" | "desc" } }', api_ts)
