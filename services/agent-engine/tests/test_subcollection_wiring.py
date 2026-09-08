from unittest import TestCase

from omnistackai_agent_engine.application_ir import (
    ApiEndpoint,
    Entity,
    Field,
    FieldType,
    HttpMethod,
    Relation,
    RelationKind,
    example_ir,
)
from omnistackai_agent_engine.codegen import GoBackendAdapter, PythonBackendAdapter
from omnistackai_agent_engine.codegen.route_wiring import Op, fk_relations, wire_endpoint

# child entity with exactly one FK relation (Comment -> post)
_FK = {"Comment": ("post",), "Post": ()}
_ENTITIES = frozenset({"Comment", "Post"})


class ListByMappingTests(TestCase):
    def test_subcollection_get_maps_to_list_by(self) -> None:
        api = ApiEndpoint(HttpMethod.GET, "/posts/{postId}/comments", auth=False, response_schema="Comment")
        w = wire_endpoint(api, _ENTITIES, _FK)
        self.assertEqual((w.op, w.entity, w.table, w.id_param, w.relation), (Op.LIST_BY, "Comment", "comment", "postId", "post"))

    def test_not_wired_without_fk_map(self) -> None:
        api = ApiEndpoint(HttpMethod.GET, "/posts/{postId}/comments", auth=False, response_schema="Comment")
        self.assertIsNone(wire_endpoint(api, _ENTITIES))  # no fk map -> stays a scaffold

    def test_not_wired_when_child_has_multiple_fk_relations(self) -> None:
        api = ApiEndpoint(HttpMethod.GET, "/posts/{postId}/comments", auth=False, response_schema="Comment")
        self.assertIsNone(wire_endpoint(api, _ENTITIES, {"Comment": ("post", "author")}))  # ambiguous

    def test_get_by_id_still_wins_over_list_by(self) -> None:
        api = ApiEndpoint(HttpMethod.GET, "/comments/{commentId}", auth=False, response_schema="Comment")
        self.assertEqual(wire_endpoint(api, _ENTITIES, _FK).op, Op.GET)


class FkRelationsHelperTests(TestCase):
    def test_fk_relations_lists_only_fk_kinds(self) -> None:
        ir = example_ir("minimal-blog")  # Comment has a many_to_one 'post'
        self.assertEqual(fk_relations(ir)["Comment"], ("post",))
        self.assertEqual(fk_relations(ir)["Post"], ())


class FilteredRepositoryEmissionTests(TestCase):
    def test_python_repository_has_filtered_list(self) -> None:
        content = PythonBackendAdapter().generate(example_ir("minimal-blog")).get("app/repositories/comment.py").content
        self.assertIn("async def list_comment_by_post(post_id: str", content)
        self.assertIn("WHERE post_id = %s", content)

    def test_go_store_has_filtered_list(self) -> None:
        content = GoBackendAdapter().generate(example_ir("minimal-blog")).get("internal/store/comment.go").content
        self.assertIn("func ListCommentByPost(ctx context.Context, db *sql.DB, postID string, limit, offset int, sort, order string)", content)
        self.assertIn("WHERE post_id = $1", content)


class SubcollectionWiringTests(TestCase):
    def test_python_router_calls_filtered_list(self) -> None:
        posts = PythonBackendAdapter().generate(example_ir("minimal-blog")).get("app/routers/posts.py").content
        self.assertIn("await comment.list_comment_by_post(postId, limit=limit, offset=offset, sort=sort, order=order)", posts)

    def test_go_handler_calls_filtered_store(self) -> None:
        handlers = GoBackendAdapter().generate(example_ir("minimal-blog")).get("internal/handlers/posts.go").content
        self.assertIn('store.ListCommentByPost(r.Context(), h.DB, r.PathValue("postId"), limit, offset, sort, order)', handlers)


class ValueParameterizationTests(TestCase):
    def test_filter_value_is_parameterized_not_interpolated(self) -> None:
        entity = Entity("Comment", (Field("id", FieldType.UUID, True), Field("body", FieldType.TEXT, True)),
                        (Relation("post", "Post", RelationKind.MANY_TO_ONE),))
        # emitted SQL filters by a placeholder, not a formatted value
        from omnistackai_agent_engine.codegen.data_access import _go_filtered_lists, _python_filtered_lists
        py = _python_filtered_lists(entity, "comment")
        self.assertIn("WHERE post_id = %s", py)
        go = _go_filtered_lists(entity, "comment", "id, body", "&m.Id, &m.Body")
        self.assertIn("WHERE post_id = $1", go)
