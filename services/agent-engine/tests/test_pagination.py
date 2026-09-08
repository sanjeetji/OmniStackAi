"""Tests for R-255: Query parameter pagination (limit & offset) in Go and FastAPI backends."""

from unittest import TestCase

from omnistackai_agent_engine.codegen import GoBackendAdapter, PythonBackendAdapter
from omnistackai_agent_engine.application_ir import example_ir


class GoPaginationSharedTests(TestCase):
    def test_shared_handlers_emits_parse_pagination(self) -> None:
        project = GoBackendAdapter().generate(example_ir("minimal-blog"))
        shared = project.get("internal/handlers/handlers.go").content
        self.assertIn('"strconv"', shared)
        self.assertIn("func parsePagination(r *http.Request) (int, int)", shared)
        self.assertIn("limit := 100", shared)
        self.assertIn("offset := 0", shared)
        self.assertIn('r.URL.Query().Get("limit")', shared)
        self.assertIn('r.URL.Query().Get("offset")', shared)
        self.assertIn("strconv.Atoi(v)", shared)


class GoPaginationStoreTests(TestCase):
    def setUp(self) -> None:
        self.project = GoBackendAdapter().generate(example_ir("minimal-blog"))

    def test_list_entity_store_takes_limit_and_offset(self) -> None:
        post_store = self.project.get("internal/store/post.go").content
        self.assertIn("func ListPost(ctx context.Context, db *sql.DB, limit, offset int, sort, order string) ([]models.Post, error)", post_store)
        self.assertIn("ORDER BY %s %s LIMIT $1 OFFSET $2", post_store)

    def test_list_entity_by_relation_store_takes_limit_and_offset(self) -> None:
        comment_store = self.project.get("internal/store/comment.go").content
        self.assertIn("func ListCommentByPost(ctx context.Context, db *sql.DB, postID string, limit, offset int, sort, order string) ([]models.Comment, error)", comment_store)
        self.assertIn("ORDER BY %s %s LIMIT $2 OFFSET $3", comment_store)


class GoPaginationHandlerTests(TestCase):
    def setUp(self) -> None:
        self.project = GoBackendAdapter().generate(example_ir("minimal-blog"))

    def test_list_handler_parses_pagination_and_passes_to_store(self) -> None:
        posts_handler = self.project.get("internal/handlers/posts.go").content
        self.assertIn("limit, offset := parsePagination(r)", posts_handler)
        self.assertIn("store.ListPost(r.Context(), h.DB, limit, offset, sort, order)", posts_handler)

    def test_list_by_handler_parses_pagination_and_passes_to_store(self) -> None:
        posts_handler = self.project.get("internal/handlers/posts.go").content
        self.assertIn('store.ListCommentByPost(r.Context(), h.DB, r.PathValue("postId"), limit, offset, sort, order)', posts_handler)


class PythonPaginationRouterTests(TestCase):
    def setUp(self) -> None:
        self.project = PythonBackendAdapter().generate(example_ir("minimal-blog"))

    def test_list_endpoint_declares_limit_and_offset(self) -> None:
        posts_router = self.project.get("app/routers/posts.py").content
        self.assertIn('async def get_posts(limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc") -> list[dict]:', posts_router)
        self.assertIn("return await post.list_post(limit=limit, offset=offset, sort=sort, order=order)", posts_router)

    def test_list_by_endpoint_declares_limit_and_offset(self) -> None:
        posts_router = self.project.get("app/routers/posts.py").content
        self.assertIn('async def get_posts_postid_comments(postId: str, limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc") -> list[dict]:', posts_router)
        self.assertIn("return await comment.list_comment_by_post(postId, limit=limit, offset=offset, sort=sort, order=order)", posts_router)


class PythonPaginationRepositoryTests(TestCase):
    def setUp(self) -> None:
        self.project = PythonBackendAdapter().generate(example_ir("minimal-blog"))

    def test_repository_list_uses_limit_and_offset_sql(self) -> None:
        post_repo = self.project.get("app/repositories/post.py").content
        self.assertIn('async def list_post(limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc") -> list[dict[str, Any]]:', post_repo)
        self.assertIn("ORDER BY {sort_col} {sort_dir} LIMIT %s OFFSET %s", post_repo)
        self.assertIn("(limit, offset)", post_repo)

    def test_repository_list_by_uses_limit_and_offset_sql(self) -> None:
        comment_repo = self.project.get("app/repositories/comment.py").content
        self.assertIn('async def list_comment_by_post(post_id: str, limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc") -> list[dict[str, Any]]:', comment_repo)
        self.assertIn("WHERE post_id = %s ORDER BY {sort_col} {sort_dir} LIMIT %s OFFSET %s", comment_repo)
        self.assertIn("(post_id, limit, offset)", comment_repo)


class ExampleIrPaginationRegressionTests(TestCase):
    def test_rideshare_favourites_go_pagination(self) -> None:
        project = GoBackendAdapter().generate(example_ir("rideshare-favourites"))
        drivers = project.get("internal/handlers/drivers.go").content
        self.assertIn("limit, offset := parsePagination(r)", drivers)
        self.assertIn("store.ListDriver(r.Context(), h.DB, limit, offset, sort, order)", drivers)

    def test_rideshare_favourites_python_pagination(self) -> None:
        project = PythonBackendAdapter().generate(example_ir("rideshare-favourites"))
        drivers = project.get("app/routers/drivers.py").content
        self.assertIn('async def get_drivers(limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc") -> list[dict]:', drivers)
        self.assertIn("return await driver.list_driver(limit=limit, offset=offset, sort=sort, order=order)", drivers)
