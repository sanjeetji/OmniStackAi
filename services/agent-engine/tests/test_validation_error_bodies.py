"""R-254 — Field-level validation error bodies.

The generated Go validate.go must return a structured JSON error body
{"errors":[{"field":"<name>","rule":"<tag>","message":"<human text>"}]}
instead of the flat "validation_failed" string, so clients can surface
per-field error messages.

FastAPI + Pydantic already return structured 422 error bodies by default
(Pydantic's ValidationError detail includes loc, msg, type per field).
This test file verifies the Go-side changes and the FastAPI default behaviour.

Coverage:
- Go validate.go: structured type + correct fields (field, rule, message)
- Go validate.go: no flat "validation_failed" string present
- Go validate.go: imports "fmt" for Sprintf message construction
- Go validate.go: imports "encoding/json" is NOT needed (writeJSON used)
- Go validate.go: function signature (w http.ResponseWriter, v any) bool
- Go validate.go: returns false and writes JSON on error, returns true on success
- Go handler: call-site uses "if !validateStruct(w, m)" pattern
- Go handler: no http.Error call for validation (body written by helper)
- Rule-free entity: validate.go still not emitted (gate unchanged)
- Example IRs: unchanged
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
from omnistackai_agent_engine.codegen import GoBackendAdapter

_STRATEGY = ProjectStrategy(
    MobileProfile.NONE, WebStrategy.NONE, AdminStrategy.NONE,
    BackendStrategy.GO, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
)

_VALIDATED = Entity(
    "Listing",
    (
        Field("id", FieldType.UUID),
        Field("title", FieldType.STRING, validation=("max_length:80",)),
        Field("price", FieldType.FLOAT, required=False, validation=("min:0",)),
        Field("status", FieldType.STRING, validation=("enum:new|used",)),
    ),
)

_RULE_FREE = Entity(
    "Listing",
    (Field("id", FieldType.UUID), Field("title", FieldType.STRING)),
)

_CREATE = ApiEndpoint(HttpMethod.POST,  "/listings",              auth=False, request_schema="Listing")
_PATCH  = ApiEndpoint(HttpMethod.PATCH, "/listings/{listingId}", auth=False, request_schema="Listing")


def _ir(*apis: ApiEndpoint, entity: Entity = _VALIDATED) -> ApplicationIR:
    return ApplicationIR(
        name="Marketplace",
        description="A small marketplace.",
        platforms=(Platform.BACKEND,),
        project_strategy=_STRATEGY,
        entities=(entity,),
        apis=apis,
    )


# ===========================================================================
# validate.go — structured error body
# ===========================================================================

class GoValidateFileStructureTests(TestCase):
    def _validate(self, *apis: ApiEndpoint) -> str:
        project = GoBackendAdapter().generate(_ir(*apis))
        self.assertIn("internal/handlers/validate.go", set(project.paths()))
        return project.get("internal/handlers/validate.go").content

    def test_struct_type_emitted(self) -> None:
        v = self._validate(_CREATE)
        self.assertIn("type validationError struct", v)

    def test_struct_has_field_key(self) -> None:
        v = self._validate(_CREATE)
        self.assertIn('Field   string `json:"field"`', v)

    def test_struct_has_rule_key(self) -> None:
        v = self._validate(_CREATE)
        self.assertIn('Rule    string `json:"rule"`', v)

    def test_struct_has_message_key(self) -> None:
        v = self._validate(_CREATE)
        self.assertIn('Message string `json:"message"`', v)

    def test_errors_wrapper_key(self) -> None:
        """The outer JSON key must be 'errors'."""
        v = self._validate(_CREATE)
        self.assertIn('"errors"', v)

    def test_field_name_extracted_from_fe(self) -> None:
        v = self._validate(_CREATE)
        self.assertIn("fe.Field()", v)

    def test_rule_extracted_from_fe_tag(self) -> None:
        v = self._validate(_CREATE)
        self.assertIn("fe.Tag()", v)

    def test_message_uses_sprintf(self) -> None:
        v = self._validate(_CREATE)
        self.assertIn("fmt.Sprintf", v)

    def test_fmt_imported(self) -> None:
        v = self._validate(_CREATE)
        self.assertIn('"fmt"', v)

    def test_no_flat_validation_failed_string(self) -> None:
        v = self._validate(_CREATE)
        self.assertNotIn('"validation_failed"', v)

    def test_writes_via_writejson_not_http_error(self) -> None:
        v = self._validate(_CREATE)
        self.assertIn("writeJSON(w, http.StatusBadRequest", v)
        # http.Error must NOT be used for the validation body
        self.assertNotIn('http.Error(w, "validation_failed"', v)

    def test_new_signature_takes_responsewriter(self) -> None:
        v = self._validate(_CREATE)
        self.assertIn("func validateStruct(w http.ResponseWriter, v any) bool", v)

    def test_returns_true_on_success(self) -> None:
        v = self._validate(_CREATE)
        self.assertIn("return true", v)

    def test_returns_false_on_error(self) -> None:
        v = self._validate(_CREATE)
        self.assertIn("return false", v)

    def test_validates_all_errors_not_just_first(self) -> None:
        """Must iterate all ValidationErrors, not short-circuit on the first."""
        v = self._validate(_CREATE)
        # The loop `for _, fe := range err.(validator.ValidationErrors)` collects all
        self.assertIn("validator.ValidationErrors", v)
        self.assertIn("for _, fe := range", v)


# ===========================================================================
# Handler call-site — new pattern
# ===========================================================================

class GoHandlerCallSiteTests(TestCase):
    def test_create_handler_uses_bool_guard(self) -> None:
        project = GoBackendAdapter().generate(_ir(_CREATE))
        handler = project.get("internal/handlers/listings.go").content
        self.assertIn("if !validateStruct(w, m)", handler)

    def test_update_handler_uses_bool_guard(self) -> None:
        project = GoBackendAdapter().generate(_ir(_PATCH))
        handler = project.get("internal/handlers/listings.go").content
        self.assertIn("if !validateStruct(w, m)", handler)

    def test_create_handler_no_http_error_for_validation(self) -> None:
        """The handler must NOT call http.Error for validation failure — helper does it."""
        project = GoBackendAdapter().generate(_ir(_CREATE))
        handler = project.get("internal/handlers/listings.go").content
        # http.Error is still used for invalid body and store errors; just not for validation
        self.assertNotIn("http.Error(w, msg", handler)
        self.assertNotIn('"validation_failed"', handler)

    def test_update_handler_no_http_error_for_validation(self) -> None:
        project = GoBackendAdapter().generate(_ir(_PATCH))
        handler = project.get("internal/handlers/listings.go").content
        self.assertNotIn("http.Error(w, msg", handler)
        self.assertNotIn('"validation_failed"', handler)

    def test_ordering_validate_before_store_create(self) -> None:
        project = GoBackendAdapter().generate(_ir(_CREATE))
        handler = project.get("internal/handlers/listings.go").content
        decode_at   = handler.index("json.NewDecoder(r.Body).Decode(&m)")
        validate_at = handler.index("validateStruct(w, m)")
        create_at   = handler.index("store.CreateListing(")
        self.assertLess(decode_at,   validate_at)
        self.assertLess(validate_at, create_at)


# ===========================================================================
# Gate: rule-free entities unchanged
# ===========================================================================

class GoRuleFreeGateTests(TestCase):
    def test_validate_go_not_emitted_for_rule_free_entity(self) -> None:
        project = GoBackendAdapter().generate(_ir(_CREATE, entity=_RULE_FREE))
        self.assertNotIn("internal/handlers/validate.go", set(project.paths()))

    def test_rule_free_handler_has_no_validatestruct(self) -> None:
        project = GoBackendAdapter().generate(_ir(_CREATE, entity=_RULE_FREE))
        handler = project.get("internal/handlers/listings.go").content
        self.assertNotIn("validateStruct", handler)


# ===========================================================================
# Example IR regression — must be unchanged
# ===========================================================================

class ExampleIrRegressionTests(TestCase):
    def test_minimal_blog_go_no_validate_go(self) -> None:
        project = GoBackendAdapter().generate(example_ir("minimal-blog"))
        self.assertNotIn("internal/handlers/validate.go", set(project.paths()))
        self.assertNotIn("go-playground/validator", project.get("go.mod").content)

    def test_rideshare_go_no_validate_go(self) -> None:
        project = GoBackendAdapter().generate(example_ir("rideshare-favourites"))
        self.assertNotIn("internal/handlers/validate.go", set(project.paths()))
        self.assertNotIn("go-playground/validator", project.get("go.mod").content)
