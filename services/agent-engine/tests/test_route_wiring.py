import ast
from unittest import TestCase

from omnistackai_agent_engine.application_ir import (
    ApiEndpoint,
    HttpMethod,
    example_ir,
)
from omnistackai_agent_engine.codegen import GoBackendAdapter, PythonBackendAdapter
from omnistackai_agent_engine.codegen.route_wiring import Op, wire_endpoint

ENTITIES = frozenset({"Post", "Comment"})


class WireEndpointTests(TestCase):
    def test_get_collection_is_list(self) -> None:
        w = wire_endpoint(ApiEndpoint(HttpMethod.GET, "/posts", auth=False, response_schema="Post"), ENTITIES)
        self.assertEqual((w.op, w.entity, w.table), (Op.LIST, "Post", "post"))

    def test_get_by_id_is_get(self) -> None:
        w = wire_endpoint(ApiEndpoint(HttpMethod.GET, "/posts/{postId}", response_schema="Post"), ENTITIES)
        self.assertEqual((w.op, w.id_param), (Op.GET, "postId"))

    def test_post_with_request_schema_is_create(self) -> None:
        w = wire_endpoint(ApiEndpoint(HttpMethod.POST, "/posts", request_schema="Post", response_schema="Post"), ENTITIES)
        self.assertEqual(w.op, Op.CREATE)

    def test_delete_by_id_is_delete(self) -> None:
        w = wire_endpoint(ApiEndpoint(HttpMethod.DELETE, "/posts/{postId}", response_schema="Post"), ENTITIES)
        self.assertEqual((w.op, w.id_param), (Op.DELETE, "postId"))

    def test_unknown_entity_is_not_wired(self) -> None:
        self.assertIsNone(wire_endpoint(ApiEndpoint(HttpMethod.GET, "/x", response_schema="Ghost"), ENTITIES))

    def test_subcollection_get_is_not_wired(self) -> None:
        # last segment is not a param -> ambiguous, stays a scaffold
        api = ApiEndpoint(HttpMethod.GET, "/posts/{postId}/comments", auth=False, response_schema="Comment")
        self.assertIsNone(wire_endpoint(api, ENTITIES))

    def test_post_without_request_schema_is_not_wired(self) -> None:
        api = ApiEndpoint(HttpMethod.POST, "/favourites/{id}", response_schema="Comment")
        self.assertIsNone(wire_endpoint(api, ENTITIES))


class PythonWiringTests(TestCase):
    def setUp(self) -> None:
        self.project = PythonBackendAdapter().generate(example_ir("minimal-blog"))

    def test_router_calls_repository_and_parses(self) -> None:
        posts = self.project.get("app/routers/posts.py").content
        ast.parse(posts)  # valid Python
        self.assertIn("from app.repositories import post", posts)
        self.assertIn("return await post.list_post(limit=limit, offset=offset, sort=sort, order=order, q=q)", posts)
        self.assertIn("from app.models import Post", posts)
        self.assertIn("await post.create_post(payload.model_dump())", posts)

    def test_subcollection_wired_to_filtered_list(self) -> None:
        # R-244: GET /posts/{postId}/comments -> parent-scoped list via the FK relation
        posts = self.project.get("app/routers/posts.py").content
        self.assertIn("await comment.list_comment_by_post(postId, limit=limit, offset=offset, sort=sort, order=order, q=q)", posts)

    def test_ambiguous_endpoint_stays_501(self) -> None:
        # POST /favourites/drivers/{driverId} has no request_schema -> genuinely ambiguous -> 501
        fav = PythonBackendAdapter().generate(example_ir("rideshare-favourites")).get("app/routers/favourites.py").content
        self.assertIn("status_code=501", fav)


class GoWiringTests(TestCase):
    def setUp(self) -> None:
        self.project = GoBackendAdapter().generate(example_ir("rideshare-favourites"))

    def test_shared_handlers_and_db_wiring(self) -> None:
        self.assertIn("internal/handlers/handlers.go", self.project.paths())
        shared = self.project.get("internal/handlers/handlers.go").content
        self.assertIn("type Handlers struct {", shared)
        main = self.project.get("main.go").content
        self.assertIn("db, err := store.Open()", main)
        self.assertIn("h := handlers.New(db)", main)

    def test_list_handler_calls_store(self) -> None:
        drivers = self.project.get("internal/handlers/drivers.go").content
        self.assertIn("func (h *Handlers) GetDrivers(", drivers)
        self.assertIn("store.ListDriver(r.Context(), h.DB, limit, offset, sort, order, q)", drivers)


class NonDbBackendUnchangedTests(TestCase):
    def test_no_db_go_backend_keeps_free_function_stubs(self) -> None:
        # an IR with APIs but no entities does not get the DB wiring
        ir = example_ir("minimal-blog")
        from dataclasses import replace
        ir_no_entities = replace(ir, entities=())
        project = GoBackendAdapter().generate(ir_no_entities)
        self.assertNotIn("internal/handlers/handlers.go", project.paths())
        self.assertNotIn("pgx", project.get("go.mod").content)
