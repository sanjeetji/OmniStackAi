from unittest import TestCase

from omnistackai_agent_engine.application_ir import (
    IR_SCHEMA_VERSION,
    AcceptanceCriterion,
    AdminStrategy,
    ApiEndpoint,
    ApplicationIR,
    BackendStrategy,
    DatabaseStrategy,
    Entity,
    Field,
    FieldType,
    HttpMethod,
    InvalidIRError,
    MobileProfile,
    Platform,
    ProjectStrategy,
    Relation,
    RelationKind,
    RepoStrategy,
    Role,
    Screen,
    UnsupportedIRVersionError,
    WebStrategy,
)


def _strategy() -> ProjectStrategy:
    return ProjectStrategy(
        mobile_profile=MobileProfile.NONE,
        web_strategy=WebStrategy.NEXTJS,
        admin_strategy=AdminStrategy.NONE,
        backend_strategy=BackendStrategy.GO,
        database_strategy=DatabaseStrategy.POSTGRES,
        repo_strategy=RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
    )


def _ir() -> ApplicationIR:
    return ApplicationIR(
        name="Rideshare Favourites",
        description="Customers can favourite drivers.",
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=_strategy(),
        roles=(Role("customer", ("read", "write")), Role("admin")),
        entities=(
            Entity(
                "Driver",
                (Field("id", FieldType.UUID), Field("name", FieldType.STRING)),
            ),
            Entity(
                "FavouriteDriver",
                (Field("id", FieldType.UUID), Field("created_at", FieldType.DATETIME, required=False)),
                relations=(Relation("driver", "Driver", RelationKind.MANY_TO_ONE),),
            ),
        ),
        apis=(
            ApiEndpoint(HttpMethod.POST, "/favourites/drivers/{driverId}", auth=True),
            ApiEndpoint(HttpMethod.GET, "/favourites/drivers", auth=True, response_schema="FavouriteDriver"),
        ),
        screens=(Screen("favourites", "customer", components=("list",), actions=("add", "remove")),),
        acceptance_criteria=(AcceptanceCriterion("fav_001", "add/remove is idempotent"),),
    )


class ConstructionTests(TestCase):
    def test_valid_ir_builds(self) -> None:
        ir = _ir()
        self.assertEqual(ir.schema_version, IR_SCHEMA_VERSION)
        self.assertEqual(len(ir.entities), 2)
        self.assertEqual(ir.apis[0].method, HttpMethod.POST)

    def test_platforms_required(self) -> None:
        with self.assertRaises(InvalidIRError):
            ApplicationIR("A", "d", (), _strategy())

    def test_entity_requires_a_field(self) -> None:
        with self.assertRaises(InvalidIRError):
            Entity("Empty", ())

    def test_bad_identifiers_rejected(self) -> None:
        with self.assertRaises(InvalidIRError):
            Role("Not Valid")
        with self.assertRaises(InvalidIRError):
            Field("BadName", FieldType.STRING)
        with self.assertRaises(InvalidIRError):
            Entity("bad name!", (Field("id", FieldType.UUID),))

    def test_bad_api_path_rejected(self) -> None:
        with self.assertRaises(InvalidIRError):
            ApiEndpoint(HttpMethod.GET, "no-leading-slash")

    def test_bad_enum_rejected(self) -> None:
        with self.assertRaises(InvalidIRError):
            ApiEndpoint("FETCH", "/x")  # type: ignore[arg-type]


class UniquenessTests(TestCase):
    def test_duplicate_entity_names_rejected(self) -> None:
        entity = Entity("Driver", (Field("id", FieldType.UUID),))
        with self.assertRaises(InvalidIRError):
            ApplicationIR("A", "d", (Platform.BACKEND,), _strategy(), entities=(entity, entity))

    def test_duplicate_field_names_rejected(self) -> None:
        with self.assertRaises(InvalidIRError):
            Entity("Driver", (Field("id", FieldType.UUID), Field("id", FieldType.STRING)))

    def test_duplicate_role_ids_rejected(self) -> None:
        with self.assertRaises(InvalidIRError):
            ApplicationIR("A", "d", (Platform.WEB,), _strategy(), roles=(Role("x"), Role("x")))

    def test_duplicate_api_method_path_rejected(self) -> None:
        api = ApiEndpoint(HttpMethod.GET, "/x")
        with self.assertRaises(InvalidIRError):
            ApplicationIR("A", "d", (Platform.BACKEND,), _strategy(), apis=(api, api))


class CrossReferenceTests(TestCase):
    def test_relation_to_unknown_entity_rejected(self) -> None:
        entity = Entity(
            "FavouriteDriver",
            (Field("id", FieldType.UUID),),
            relations=(Relation("driver", "Driver", RelationKind.MANY_TO_ONE),),
        )
        with self.assertRaises(InvalidIRError):
            ApplicationIR("A", "d", (Platform.BACKEND,), _strategy(), entities=(entity,))

    def test_screen_with_unknown_role_rejected(self) -> None:
        with self.assertRaises(InvalidIRError):
            ApplicationIR(
                "A", "d", (Platform.WEB,), _strategy(),
                roles=(Role("customer"),), screens=(Screen("s", "ghost"),),
            )


class SerializationTests(TestCase):
    def test_roundtrip_is_lossless(self) -> None:
        ir = _ir()
        restored = ApplicationIR.from_dict(ir.to_dict())
        self.assertEqual(restored.to_dict(), ir.to_dict())
        self.assertEqual(restored, ir)

    def test_json_shape_uses_plain_values(self) -> None:
        doc = _ir().to_dict()
        self.assertEqual(doc["schema_version"], IR_SCHEMA_VERSION)
        self.assertEqual(doc["platforms"], ["web", "backend"])
        self.assertEqual(doc["apis"][0]["method"], "POST")
        self.assertEqual(doc["entities"][1]["relations"][0]["kind"], "many_to_one")

    def test_unknown_version_is_rejected(self) -> None:
        doc = _ir().to_dict()
        doc["schema_version"] = IR_SCHEMA_VERSION + 1
        with self.assertRaises(UnsupportedIRVersionError):
            ApplicationIR.from_dict(doc)

    def test_construction_with_wrong_version_is_rejected(self) -> None:
        with self.assertRaises(UnsupportedIRVersionError):
            ApplicationIR("A", "d", (Platform.WEB,), _strategy(), schema_version=99)

    def test_structurally_invalid_document_is_rejected(self) -> None:
        doc = _ir().to_dict()
        del doc["name"]
        with self.assertRaises(InvalidIRError):
            ApplicationIR.from_dict(doc)
