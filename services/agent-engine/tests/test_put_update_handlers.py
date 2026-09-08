"""R-256 — PUT/update handlers: full-replace update path in Go and FastAPI backends.

When a PUT /entities/{id} endpoint's request_schema names a known repo entity, both backends must
emit a real, wired update handler and repository function — not a 501 scaffold. The handler decodes
the body, validates (reusing validateStruct) if the entity has rules, calls
store.Update<Entity> / update_<table>, and returns 404 on not-found or 200 with the updated row.

Coverage:
- Go handler: decode -> validate (if rules) -> store.Update -> 404 / 200
- Go validation ordering: validate BEFORE store.Update
- Go rule-free: no validateStruct call in PUT update handler
- Python router: @router.put route -> update_<table> -> 404 on None
- Negative wiring: no path param, no entity, mismatched entity -> 501
- Example IRs unchanged
"""

from unittest import TestCase

from omnistackai_agent_engine.application_ir import (
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
    RepoStrategy,
    WebStrategy,
    example_ir,
)
from omnistackai_agent_engine.codegen import GoBackendAdapter, PythonBackendAdapter
from omnistackai_agent_engine.codegen.route_wiring import Op, wire_endpoint

_GO_STRATEGY = ProjectStrategy(
    MobileProfile.NONE, WebStrategy.NONE, AdminStrategy.NONE,
    BackendStrategy.GO, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)

_PY_STRATEGY = ProjectStrategy(
    MobileProfile.NONE, WebStrategy.NONE, AdminStrategy.NONE,
    BackendStrategy.PYTHON, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)

_VALIDATED_LISTING = Entity(
    "Listing",
    (
        Field("id", FieldType.UUID),
        Field("title", FieldType.STRING, validation=("max_length:80",)),
        Field("price", FieldType.FLOAT, required=False, validation=("min:0",)),
        Field("status", FieldType.STRING, validation=("enum:new|used",)),
    ),
)

_RULE_FREE_LISTING = Entity(
    "Listing",
    (
        Field("id", FieldType.UUID),
        Field("title", FieldType.STRING),
        Field("price", FieldType.FLOAT, required=False),
        Field("status", FieldType.STRING),
    ),
)

_PUT = ApiEndpoint(
    HttpMethod.PUT,
    "/listings/{listingId}",
    auth=False,
    request_schema="Listing",
    response_schema="Listing",
)


def _ir_go(entity: Entity, *apis: ApiEndpoint) -> ApplicationIR:
    return ApplicationIR(
        name="Marketplace",
        description="A small marketplace of listings.",
        platforms=(Platform.BACKEND,),
        project_strategy=_GO_STRATEGY,
        entities=(entity,),
        apis=apis or (_PUT,),
    )


def _ir_py(entity: Entity, *apis: ApiEndpoint) -> ApplicationIR:
    return ApplicationIR(
        name="Marketplace",
        description="A small marketplace of listings.",
        platforms=(Platform.BACKEND,),
        project_strategy=_PY_STRATEGY,
        entities=(entity,),
        apis=apis or (_PUT,),
    )


class PutRouteWiringTests(TestCase):
    def test_put_wires_to_update_op(self) -> None:
        w = wire_endpoint(_PUT, frozenset({"Listing"}))
        self.assertIsNotNone(w)
        self.assertEqual(w.op, Op.UPDATE)
        self.assertEqual(w.entity, "Listing")
        self.assertEqual(w.table, "listing")
        self.assertEqual(w.id_param, "listingId")

    def test_put_without_path_param_stays_unwired(self) -> None:
        api = ApiEndpoint(HttpMethod.PUT, "/listings", auth=False, request_schema="Listing")
        self.assertIsNone(wire_endpoint(api, frozenset({"Listing"})))

    def test_put_with_unknown_schema_stays_unwired(self) -> None:
        api = ApiEndpoint(HttpMethod.PUT, "/listings/{id}", auth=False, request_schema="Unknown")
        self.assertIsNone(wire_endpoint(api, frozenset({"Listing"})))

    def test_put_with_multiple_params_stays_unwired(self) -> None:
        api = ApiEndpoint(HttpMethod.PUT, "/categories/{catId}/listings/{id}", auth=False, request_schema="Listing")
        self.assertIsNone(wire_endpoint(api, frozenset({"Listing"})))


class GoPutHandlerTests(TestCase):
    def test_put_handler_emitted(self) -> None:
        project = GoBackendAdapter().generate(_ir_go(_VALIDATED_LISTING))
        handler = project.get("internal/handlers/listings.go").content
        self.assertIn("func (h *Handlers) PutListingsListingId(w http.ResponseWriter, r *http.Request)", handler)

    def test_put_handler_calls_update_store(self) -> None:
        project = GoBackendAdapter().generate(_ir_go(_VALIDATED_LISTING))
        handler = project.get("internal/handlers/listings.go").content
        self.assertIn("store.UpdateListing(r.Context(), h.DB, id, m)", handler)

    def test_validated_entity_calls_validatestruct_in_put_handler(self) -> None:
        project = GoBackendAdapter().generate(_ir_go(_VALIDATED_LISTING))
        handler = project.get("internal/handlers/listings.go").content
        self.assertIn("validateStruct(w, m)", handler)

    def test_validate_called_before_store_update(self) -> None:
        project = GoBackendAdapter().generate(_ir_go(_VALIDATED_LISTING))
        handler = project.get("internal/handlers/listings.go").content
        decode_at = handler.index("json.NewDecoder(r.Body).Decode(&m)")
        validate_at = handler.index("validateStruct(w, m)")
        update_at = handler.index("store.UpdateListing(")
        self.assertLess(decode_at, validate_at, "validate must come after decode")
        self.assertLess(validate_at, update_at, "validate must come before store.Update")

    def test_rule_free_entity_omits_validatestruct(self) -> None:
        project = GoBackendAdapter().generate(_ir_go(_RULE_FREE_LISTING))
        handler = project.get("internal/handlers/listings.go").content
        self.assertNotIn("validateStruct", handler)
        self.assertIn("store.UpdateListing(", handler)


class PythonPutRouterTests(TestCase):
    def test_put_router_emits_put_decorator(self) -> None:
        project = PythonBackendAdapter().generate(_ir_py(_VALIDATED_LISTING))
        router = project.get("app/routers/listings.py").content
        self.assertIn('@router.put("/listings/{listingId}")', router)

    def test_put_router_calls_update_repo(self) -> None:
        project = PythonBackendAdapter().generate(_ir_py(_VALIDATED_LISTING))
        router = project.get("app/routers/listings.py").content
        self.assertIn("async def put_listings_listingid(listingId: str, payload: Listing) -> dict:", router)
        self.assertIn("await listing.update_listing(listingId, payload.model_dump())", router)

    def test_put_router_raises_404_on_none(self) -> None:
        project = PythonBackendAdapter().generate(_ir_py(_VALIDATED_LISTING))
        router = project.get("app/routers/listings.py").content
        self.assertIn('raise HTTPException(status_code=404, detail="not_found")', router)


class ExampleIrRegressionTests(TestCase):
    def test_minimal_blog_unchanged(self) -> None:
        project = PythonBackendAdapter().generate(example_ir("minimal-blog"))
        posts = project.get("app/routers/posts.py").content
        self.assertNotIn("@router.put", posts)

    def test_rideshare_favourites_unchanged(self) -> None:
        project = GoBackendAdapter().generate(example_ir("rideshare-favourites"))
        drivers = project.get("internal/handlers/drivers.go").content
        self.assertNotIn("PutDrivers", drivers)
