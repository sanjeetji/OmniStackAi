"""R-252 — the generated Go backend enforces the R-251 validate tags on create.

When a wired CREATE handler's entity carries validation rules, the Go backend must declare the
go-playground validator in its own go.mod, emit internal/handlers/validate.go, and call validateStruct
on the decoded body before the store.Create call. Rule-free projects stay byte-identical to R-251.
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

_GO_STRATEGY = ProjectStrategy(
    MobileProfile.NONE, WebStrategy.NONE, AdminStrategy.NONE,
    BackendStrategy.GO, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
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
    (Field("id", FieldType.UUID), Field("title", FieldType.STRING)),
)


def _ir(entity: Entity, *apis: ApiEndpoint) -> ApplicationIR:
    return ApplicationIR(
        name="Marketplace",
        description="A small marketplace of listings.",
        platforms=(Platform.BACKEND,),
        project_strategy=_GO_STRATEGY,
        entities=(entity,),
        apis=apis,
    )


_CREATE = ApiEndpoint(HttpMethod.POST, "/listings", auth=False, request_schema="Listing")
_LIST = ApiEndpoint(HttpMethod.GET, "/listings", auth=False, response_schema="Listing")


class GoValidationEnforcementTests(TestCase):
    def test_enforcement_emitted_when_create_entity_has_rules(self) -> None:
        project = GoBackendAdapter().generate(_ir(_VALIDATED_LISTING, _CREATE))
        paths = set(project.paths())

        gomod = project.get("go.mod").content
        self.assertIn("require github.com/go-playground/validator/v10 v10.22.1", gomod)

        self.assertIn("internal/handlers/validate.go", paths)
        validate = project.get("internal/handlers/validate.go").content
        self.assertIn('"github.com/go-playground/validator/v10"', validate)
        self.assertIn("var validate = validator.New()", validate)
        # R-254: structured JSON body — new signature
        self.assertIn("func validateStruct(w http.ResponseWriter, v any) bool", validate)
        self.assertIn("http.StatusBadRequest", validate)
        self.assertIn('"errors"', validate)              # structured key, not flat string
        self.assertIn("fe.Field()", validate)             # per-field info
        self.assertIn("fe.Tag()", validate)               # rule name
        self.assertNotIn('"validation_failed"', validate) # old flat string gone

    def test_create_handler_validates_after_decode_before_store(self) -> None:
        project = GoBackendAdapter().generate(_ir(_VALIDATED_LISTING, _CREATE))
        handler = project.get("internal/handlers/listings.go").content
        # R-254: new call is validateStruct(w, m) returning bool
        self.assertIn("validateStruct(w, m)", handler)
        decode_at   = handler.index("json.NewDecoder(r.Body).Decode(&m)")
        validate_at = handler.index("validateStruct(w, m)")
        create_at   = handler.index("store.CreateListing(")
        self.assertLess(decode_at, validate_at)
        self.assertLess(validate_at, create_at)
        # On failure handler returns immediately (no http.Error — body already written by helper).
        self.assertIn("if !validateStruct(w, m)", handler)
        self.assertNotIn("http.Error(w, msg", handler)

    def test_rule_free_project_emits_no_enforcement(self) -> None:
        project = GoBackendAdapter().generate(_ir(_RULE_FREE_LISTING, _CREATE))
        paths = set(project.paths())
        self.assertNotIn("internal/handlers/validate.go", paths)
        self.assertNotIn("validator/v10", project.get("go.mod").content)
        handler = project.get("internal/handlers/listings.go").content
        self.assertNotIn("validateStruct", handler)
        # The create handler is still wired to the store — only the validation guard is absent.
        self.assertIn("store.CreateListing(", handler)

    def test_rules_without_create_emit_no_enforcement_but_keep_tags(self) -> None:
        project = GoBackendAdapter().generate(_ir(_VALIDATED_LISTING, _LIST))
        paths = set(project.paths())
        self.assertNotIn("internal/handlers/validate.go", paths)
        self.assertNotIn("validator/v10", project.get("go.mod").content)
        # The models still carry the declarative R-251 tags even without enforcement.
        models = project.get("internal/models/models.go").content
        self.assertIn('validate:"max=80"', models)

    def test_example_irs_emit_no_enforcement(self) -> None:
        for name in ("minimal-blog", "rideshare-favourites"):
            project = GoBackendAdapter().generate(example_ir(name))
            self.assertNotIn(
                "internal/handlers/validate.go", set(project.paths()), f"{name} should not enforce"
            )
            self.assertNotIn("validator/v10", project.get("go.mod").content, f"{name} go.mod")
