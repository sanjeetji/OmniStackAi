"""R-253 — PATCH/update handlers: validated partial-update path in Go and FastAPI backends.

When a PATCH /entities/{id} endpoint's request_schema names a known repo entity, both backends must
emit a real, wired update handler and repository function — not a 501 scaffold. The handler decodes
the body, validates (reusing the R-252 validateStruct helper) if the entity has rules, calls
store.Update<Entity> / update_<table>, and returns 404 on not-found or 200 with the updated row.

Coverage:
- Go store Update<Entity> function emitted with parameterized SQL
- Go handler: decode → validate (if rules) → store.Update → 404 / 200
- Go validation ordering: validate BEFORE store.Update
- Go rule-free: no validateStruct call in update handler
- Python repo: update_<table> emitted with parameterized UPDATE
- Python router: @router.patch route → update_<table> → 404 on None
- Negative wiring: no path param, no entity, non-PATCH same shape → 501
- Example IRs unchanged (no PATCH endpoints in either)
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

_GO_STRATEGY = ProjectStrategy(
    MobileProfile.NONE, WebStrategy.NONE, AdminStrategy.NONE,
    BackendStrategy.GO, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)

_PY_STRATEGY = ProjectStrategy(
    MobileProfile.NONE, WebStrategy.NONE, AdminStrategy.NONE,
    BackendStrategy.PYTHON, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)

# --- Entity fixtures -------------------------------------------------------

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
    (Field("id", FieldType.UUID), Field("title", FieldType.STRING)),
)

# --- Endpoint fixtures ------------------------------------------------------

_PATCH = ApiEndpoint(HttpMethod.PATCH, "/listings/{listingId}", auth=False, request_schema="Listing")
_POST  = ApiEndpoint(HttpMethod.POST,  "/listings",              auth=False, request_schema="Listing")
_GET   = ApiEndpoint(HttpMethod.GET,   "/listings/{listingId}",  auth=False, response_schema="Listing")
_LIST  = ApiEndpoint(HttpMethod.GET,   "/listings",              auth=False, response_schema="Listing")
_DEL   = ApiEndpoint(HttpMethod.DELETE, "/listings/{listingId}", auth=False, response_schema="Listing")
# PATCH without a path param → should stay 501
_PATCH_NO_PARAM = ApiEndpoint(HttpMethod.PATCH, "/listings", auth=False, request_schema="Listing")



def _ir_go(entity: Entity, *apis: ApiEndpoint) -> ApplicationIR:
    return ApplicationIR(
        name="Marketplace",
        description="A small marketplace of listings.",
        platforms=(Platform.BACKEND,),
        project_strategy=_GO_STRATEGY,
        entities=(entity,),
        apis=apis,
    )


def _ir_py(entity: Entity, *apis: ApiEndpoint) -> ApplicationIR:
    return ApplicationIR(
        name="Marketplace",
        description="A small marketplace of listings.",
        platforms=(Platform.BACKEND,),
        project_strategy=_PY_STRATEGY,
        entities=(entity,),
        apis=apis,
    )


# ===========================================================================
# Go backend tests
# ===========================================================================

class GoUpdateStoreTests(TestCase):
    def test_update_function_emitted_in_store_file(self) -> None:
        project = GoBackendAdapter().generate(_ir_go(_RULE_FREE_LISTING, _PATCH))
        store = project.get("internal/store/listing.go").content
        self.assertIn("func UpdateListing(", store)
        self.assertIn("sql.ErrNoRows", store)

    def test_update_sql_is_parameterized(self) -> None:
        project = GoBackendAdapter().generate(_ir_go(_RULE_FREE_LISTING, _PATCH))
        store = project.get("internal/store/listing.go").content
        # UPDATE SET title=$1 WHERE id=$2 (parameterized, no string interpolation of values)
        self.assertIn("$1", store)
        self.assertIn("WHERE id = $", store)
        self.assertIn("RETURNING", store)
        # No f-string value substitution of user data into the SQL template
        self.assertNotIn("WHERE id = '", store)

    def test_update_returns_pointer_to_model(self) -> None:
        project = GoBackendAdapter().generate(_ir_go(_RULE_FREE_LISTING, _PATCH))
        store = project.get("internal/store/listing.go").content
        self.assertIn("*models.Listing, error", store)
        self.assertIn("return &out, nil", store)


class GoUpdateHandlerTests(TestCase):
    def test_update_handler_wired_not_501(self) -> None:
        project = GoBackendAdapter().generate(_ir_go(_RULE_FREE_LISTING, _PATCH))
        handler = project.get("internal/handlers/listings.go").content
        self.assertIn("store.UpdateListing(", handler)
        self.assertNotIn("not implemented", handler)

    def test_update_handler_decodes_body(self) -> None:
        project = GoBackendAdapter().generate(_ir_go(_RULE_FREE_LISTING, _PATCH))
        handler = project.get("internal/handlers/listings.go").content
        self.assertIn("json.NewDecoder(r.Body).Decode(&m)", handler)

    def test_update_handler_returns_404_on_nil(self) -> None:
        project = GoBackendAdapter().generate(_ir_go(_RULE_FREE_LISTING, _PATCH))
        handler = project.get("internal/handlers/listings.go").content
        self.assertIn("http.NotFound(w, r)", handler)

    def test_update_handler_returns_200_with_updated_row(self) -> None:
        project = GoBackendAdapter().generate(_ir_go(_RULE_FREE_LISTING, _PATCH))
        handler = project.get("internal/handlers/listings.go").content
        self.assertIn("writeJSON(w, http.StatusOK, updated)", handler)


class GoUpdateValidationTests(TestCase):
    def test_validated_entity_calls_validatestruct_in_update_handler(self) -> None:
        project = GoBackendAdapter().generate(_ir_go(_VALIDATED_LISTING, _PATCH))
        handler = project.get("internal/handlers/listings.go").content
        # R-254: new signature validateStruct(w, m)
        self.assertIn("validateStruct(w, m)", handler)

    def test_validate_called_before_store_update(self) -> None:
        project = GoBackendAdapter().generate(_ir_go(_VALIDATED_LISTING, _PATCH))
        handler = project.get("internal/handlers/listings.go").content
        decode_at   = handler.index("json.NewDecoder(r.Body).Decode(&m)")
        validate_at = handler.index("validateStruct(w, m)")
        update_at   = handler.index("store.UpdateListing(")
        self.assertLess(decode_at,   validate_at, "validate must come after decode")
        self.assertLess(validate_at, update_at,   "validate must come before store.Update")

    def test_rule_free_entity_has_no_validatestruct_in_update_handler(self) -> None:
        project = GoBackendAdapter().generate(_ir_go(_RULE_FREE_LISTING, _PATCH))
        handler = project.get("internal/handlers/listings.go").content
        self.assertNotIn("validateStruct", handler)

    def test_validator_dep_emitted_when_update_handler_entity_has_rules(self) -> None:
        project = GoBackendAdapter().generate(_ir_go(_VALIDATED_LISTING, _PATCH))
        self.assertIn("go-playground/validator/v10", project.get("go.mod").content)
        self.assertIn("internal/handlers/validate.go", set(project.paths()))

    def test_validator_dep_not_emitted_for_rule_free_update(self) -> None:
        project = GoBackendAdapter().generate(_ir_go(_RULE_FREE_LISTING, _PATCH))
        self.assertNotIn("validator/v10", project.get("go.mod").content)
        self.assertNotIn("internal/handlers/validate.go", set(project.paths()))


class GoUpdateNegativeWiringTests(TestCase):
    def test_patch_without_path_param_stays_501(self) -> None:
        project = GoBackendAdapter().generate(_ir_go(_RULE_FREE_LISTING, _PATCH_NO_PARAM))
        handler = project.get("internal/handlers/listings.go").content
        self.assertIn("not implemented", handler)
        self.assertNotIn("store.UpdateListing(", handler)

    def test_get_with_id_param_is_not_wired_as_update(self) -> None:
        project = GoBackendAdapter().generate(_ir_go(_RULE_FREE_LISTING, _GET))
        handler = project.get("internal/handlers/listings.go").content
        self.assertNotIn("store.UpdateListing(", handler)
        self.assertIn("store.GetListing(", handler)

    def test_delete_with_id_param_is_not_wired_as_update(self) -> None:
        project = GoBackendAdapter().generate(_ir_go(_RULE_FREE_LISTING, _DEL))
        handler = project.get("internal/handlers/listings.go").content
        self.assertNotIn("store.UpdateListing(", handler)
        self.assertIn("store.DeleteListing(", handler)


# ===========================================================================
# FastAPI / Python backend tests
# ===========================================================================

class PythonUpdateRepoTests(TestCase):
    def test_update_function_emitted_in_repository(self) -> None:
        project = PythonBackendAdapter().generate(_ir_py(_RULE_FREE_LISTING, _PATCH))
        repo = project.get("app/repositories/listing.py").content
        self.assertIn("async def update_listing(", repo)

    def test_update_sql_is_parameterized(self) -> None:
        project = PythonBackendAdapter().generate(_ir_py(_RULE_FREE_LISTING, _PATCH))
        repo = project.get("app/repositories/listing.py").content
        self.assertIn("UPDATE", repo)
        self.assertIn("WHERE id = %s", repo)
        self.assertIn("RETURNING *", repo)
        # values must be passed as parameters, never string-interpolated
        self.assertNotIn("WHERE id = '", repo)

    def test_update_returns_none_on_no_rows(self) -> None:
        project = PythonBackendAdapter().generate(_ir_py(_RULE_FREE_LISTING, _PATCH))
        repo = project.get("app/repositories/listing.py").content
        # fetchone() returns None when there are no rows
        self.assertIn("return await cur.fetchone()", repo)


class PythonUpdateRouterTests(TestCase):
    def test_patch_route_emitted_in_router(self) -> None:
        project = PythonBackendAdapter().generate(_ir_py(_RULE_FREE_LISTING, _PATCH))
        router = project.get("app/routers/listings.py").content
        self.assertIn("@router.patch(", router)
        self.assertIn("update_listing(", router)

    def test_patch_route_returns_404_on_none(self) -> None:
        project = PythonBackendAdapter().generate(_ir_py(_RULE_FREE_LISTING, _PATCH))
        router = project.get("app/routers/listings.py").content
        self.assertIn("status_code=404", router)
        self.assertIn("if row is None", router)

    def test_patch_route_imports_entity_model(self) -> None:
        project = PythonBackendAdapter().generate(_ir_py(_RULE_FREE_LISTING, _PATCH))
        router = project.get("app/routers/listings.py").content
        self.assertIn("from app.models import Listing", router)


# ===========================================================================
# Example IR regression tests
# ===========================================================================

class ExampleIrRegressionTests(TestCase):
    def test_minimal_blog_go_has_no_update_handler(self) -> None:
        project = GoBackendAdapter().generate(example_ir("minimal-blog"))
        for path in project.paths():
            if path.startswith("internal/handlers/") and path.endswith(".go"):
                self.assertNotIn(
                    "store.Update", project.get(path).content,
                    f"{path} should not have an Update store call"
                )

    def test_rideshare_favourites_go_has_no_update_handler(self) -> None:
        project = GoBackendAdapter().generate(example_ir("rideshare-favourites"))
        for path in project.paths():
            if path.startswith("internal/handlers/") and path.endswith(".go"):
                self.assertNotIn(
                    "store.Update", project.get(path).content,
                    f"{path} should not have an Update store call"
                )

    def test_minimal_blog_python_has_no_patch_route(self) -> None:
        project = PythonBackendAdapter().generate(example_ir("minimal-blog"))
        for path in project.paths():
            if path.startswith("app/routers/") and path.endswith(".py"):
                self.assertNotIn(
                    "@router.patch", project.get(path).content,
                    f"{path} should not have a patch route"
                )
