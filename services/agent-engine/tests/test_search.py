"""Tests for Full-Text / Keyword Search Filtering on LIST Endpoints [R-261]."""

from unittest import TestCase

from omnistackai_agent_engine.application_ir import (
    ApiEndpoint,
    ApplicationIR,
    Entity,
    Field,
    FieldType,
    HttpMethod,
    ProjectStrategy,
    example_ir,
)
from omnistackai_agent_engine.codegen import (
    GoBackendAdapter,
    NextjsWebAdapter,
    PythonBackendAdapter,
    render_openapi,
)


class GoSearchStoreTests(TestCase):
    def setUp(self) -> None:
        self.project = GoBackendAdapter().generate(example_ir("minimal-blog"))
        self.post_store = self.project.get("internal/store/post.go").content
        self.comment_store = self.project.get("internal/store/comment.go").content

    def test_list_entity_store_accepts_q_and_filters_text_fields(self) -> None:
        # Post is filterable (published), so search flows through the R-282 postFilters helper.
        self.assertIn("func ListPost(ctx context.Context, db *sql.DB, limit, offset int, sort, order, q string, filters map[string]string) ([]models.Post, error)", self.post_store)
        self.assertIn('conds = append(conds, "(title ILIKE $1 OR body ILIKE $1)")', self.post_store)
        self.assertIn('args = append(args, "%"+q+"%")', self.post_store)
        self.assertIn("rows, err := db.QueryContext(ctx, query, args...)", self.post_store)

    def test_count_entity_store_accepts_q_and_filters_text_fields(self) -> None:
        self.assertIn("func CountPost(ctx context.Context, db *sql.DB, q string, filters map[string]string) (int, error)", self.post_store)
        self.assertIn('err := db.QueryRowContext(ctx, fmt.Sprintf("SELECT COUNT(*) FROM post%s", where), args...).Scan(&count)', self.post_store)

    def test_subcollection_store_accepts_q_and_combines_with_relation(self) -> None:
        self.assertIn("func ListCommentByPost(ctx context.Context, db *sql.DB, postID string, limit, offset int, sort, order, q string) ([]models.Comment, error)", self.comment_store)
        self.assertIn("WHERE post_id = $1 AND (body ILIKE $2)", self.comment_store)
        self.assertIn('rows, err = db.QueryContext(ctx, query, postID, "%"+q+"%", limit, offset)', self.comment_store)

        self.assertIn("func CountCommentByPost(ctx context.Context, db *sql.DB, postID string, q string) (int, error)", self.comment_store)
        self.assertIn("SELECT COUNT(*) FROM comment WHERE post_id = $1 AND (body ILIKE $2)", self.comment_store)

    def test_entity_with_no_text_fields_omits_search_clause(self) -> None:
        from dataclasses import replace
        ir = replace(
            example_ir("minimal-blog"),
            name="NumericApp",
            entities=(
                Entity(
                    "Counter",
                    (
                        Field("id", FieldType.UUID),
                        Field("count", FieldType.INT),
                        Field("active", FieldType.BOOL),
                    ),
                ),
            ),
            apis=(ApiEndpoint(HttpMethod.GET, "/counters", response_schema="Counter"),),
        )
        counter_store = GoBackendAdapter().generate(ir).get("internal/store/counter.go").content
        # Counter has no text fields (no ILIKE) but is filterable (active bool) — R-282 filters map present.
        self.assertIn("func ListCounter(ctx context.Context, db *sql.DB, limit, offset int, sort, order, q string, filters map[string]string) ([]models.Counter, error)", counter_store)
        self.assertNotIn("ILIKE", counter_store)


class GoSearchHandlerTests(TestCase):
    def setUp(self) -> None:
        self.project = GoBackendAdapter().generate(example_ir("minimal-blog"))
        self.shared = self.project.get("internal/handlers/handlers.go").content
        self.posts_handler = self.project.get("internal/handlers/posts.go").content

    def test_parse_search_helper_emitted(self) -> None:
        self.assertIn("func parseSearch(r *http.Request) string", self.shared)
        self.assertIn('return strings.TrimSpace(r.URL.Query().Get("q"))', self.shared)

    def test_handlers_extract_q_and_pass_to_store(self) -> None:
        self.assertIn("q := parseSearch(r)", self.posts_handler)
        # Post is filterable (published) — R-282 threads a filters map into the store calls.
        self.assertIn("total, err := store.CountPost(r.Context(), h.DB, q, filters)", self.posts_handler)
        self.assertIn("items, err := store.ListPost(r.Context(), h.DB, limit, offset, sort, order, q, filters)", self.posts_handler)

    def test_subcollection_handlers_pass_q_to_store(self) -> None:
        self.assertIn('total, err := store.CountCommentByPost(r.Context(), h.DB, r.PathValue("postId"), q)', self.posts_handler)
        self.assertIn('items, err := store.ListCommentByPost(r.Context(), h.DB, r.PathValue("postId"), limit, offset, sort, order, q)', self.posts_handler)


class PythonSearchRepositoryTests(TestCase):
    def setUp(self) -> None:
        self.project = PythonBackendAdapter().generate(example_ir("minimal-blog"))
        self.post_repo = self.project.get("app/repositories/post.py").content
        self.comment_repo = self.project.get("app/repositories/comment.py").content

    def test_list_repo_accepts_q_and_filters_text_fields(self) -> None:
        # Post is filterable (published), so search flows through the R-282 _list_filters helper.
        self.assertIn('async def list_post(limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc", q: str | None = None, published=None) -> list[dict[str, Any]]:', self.post_repo)
        self.assertIn('conditions.append("(title ILIKE %s OR body ILIKE %s)")', self.post_repo)
        self.assertIn('params.extend([f"%{q}%"] * 2)', self.post_repo)
        self.assertIn("await cur.execute(sql, (*params, limit, offset))", self.post_repo)

    def test_count_repo_accepts_q_and_filters_text_fields(self) -> None:
        self.assertIn("async def count_post(q: str | None = None, published=None) -> int:", self.post_repo)
        self.assertIn('await cur.execute(f"SELECT COUNT(*) AS count FROM {TABLE}{where}", tuple(params))', self.post_repo)

    def test_subcollection_repo_accepts_q(self) -> None:
        self.assertIn('async def list_comment_by_post(post_id: str, limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc", q: str | None = None) -> list[dict[str, Any]]:', self.comment_repo)
        self.assertIn("WHERE post_id = %s AND (body ILIKE %s)", self.comment_repo)
        self.assertIn("async def count_comment_by_post(post_id: str, q: str | None = None) -> int:", self.comment_repo)
        self.assertIn("SELECT COUNT(*) AS count FROM {TABLE} WHERE post_id = %s AND (body ILIKE %s)", self.comment_repo)


class PythonSearchRouterTests(TestCase):
    def setUp(self) -> None:
        self.project = PythonBackendAdapter().generate(example_ir("minimal-blog"))
        self.posts_router = self.project.get("app/routers/posts.py").content

    def test_router_accepts_q_and_forwards_to_repo(self) -> None:
        self.assertIn('async def get_posts(response: Response, limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc", q: str | None = None, published: bool | None = None) -> list[dict]:', self.posts_router)
        self.assertIn("total = await post.count_post(q=q, published=published)", self.posts_router)
        self.assertIn("return await post.list_post(limit=limit, offset=offset, sort=sort, order=order, q=q, published=published)", self.posts_router)

    def test_subcollection_router_forwards_q(self) -> None:
        self.assertIn('async def get_posts_postid_comments(postId: str, response: Response, limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc", q: str | None = None) -> list[dict]:', self.posts_router)
        self.assertIn("total = await comment.count_comment_by_post(postId, q=q)", self.posts_router)
        self.assertIn("return await comment.list_comment_by_post(postId, limit=limit, offset=offset, sort=sort, order=order, q=q)", self.posts_router)


class NextJsSearchClientTests(TestCase):
    def setUp(self) -> None:
        self.project = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        self.api_ts = self.project.get("lib/api.ts").content

    def test_list_posts_options_include_q(self) -> None:
        self.assertIn('export async function listPosts(options?: ApiOptions & { params?: { limit?: number; offset?: number; sort?: string; order?: "asc" | "desc"; q?: string } }): Promise<Post[]>', self.api_ts)
        self.assertIn('export async function listPostsWithCount(options?: ApiOptions & { params?: { limit?: number; offset?: number; sort?: string; order?: "asc" | "desc"; q?: string } }): Promise<PaginatedResult<Post[]>>', self.api_ts)

    def test_list_subcollection_options_include_q(self) -> None:
        self.assertIn('export async function listCommentsByPost(postId: string, options?: ApiOptions & { params?: { limit?: number; offset?: number; sort?: string; order?: "asc" | "desc"; q?: string } }): Promise<Comment[]>', self.api_ts)
        self.assertIn('export async function listCommentsByPostWithCount(postId: string, options?: ApiOptions & { params?: { limit?: number; offset?: number; sort?: string; order?: "asc" | "desc"; q?: string } }): Promise<PaginatedResult<Comment[]>>', self.api_ts)


class OpenApiSearchTests(TestCase):
    def setUp(self) -> None:
        self.spec = render_openapi(example_ir("minimal-blog"))

    def test_list_endpoints_declare_q_query_parameter(self) -> None:
        list_op = self.spec["paths"]["/posts"]["get"]
        param_names = [p["name"] for p in list_op["parameters"]]
        self.assertIn("q", param_names)

        q_param = next(p for p in list_op["parameters"] if p["name"] == "q")
        self.assertEqual(q_param["in"], "query")
        self.assertFalse(q_param["required"])
        self.assertEqual(q_param["schema"]["type"], "string")
        self.assertIn("Search query", q_param["description"])

    def test_subcollection_list_declares_q_query_parameter(self) -> None:
        sub_op = self.spec["paths"]["/posts/{postId}/comments"]["get"]
        param_names = [p["name"] for p in sub_op["parameters"]]
        self.assertIn("q", param_names)
