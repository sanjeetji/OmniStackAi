from unittest import TestCase

from omnistackai_agent_engine.application_ir import (
    EXAMPLES,
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
    Role,
    Screen,
    Severity,
    WebStrategy,
    example_ir,
    has_errors,
    normalize_ir,
    validate_ir,
)
from omnistackai_agent_engine.codegen import (
    GoBackendAdapter,
    NextjsWebAdapter,
    PythonBackendAdapter,
)


def _strategy(web=WebStrategy.NEXTJS, admin=AdminStrategy.NONE, mobile=MobileProfile.NONE) -> ProjectStrategy:
    return ProjectStrategy(mobile, web, admin, BackendStrategy.GO, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO)


class ValidatorTests(TestCase):
    def test_clean_ir_has_no_errors(self) -> None:
        issues = validate_ir(example_ir("rideshare-favourites"))
        self.assertFalse(has_errors(issues))

    def test_unknown_schema_reference_is_an_error(self) -> None:
        ir = ApplicationIR(
            name="Demo", description="d", platforms=(Platform.WEB, Platform.BACKEND),
            project_strategy=_strategy(),
            entities=(Entity("Driver", (Field("id", FieldType.UUID),)),),
            apis=(ApiEndpoint(HttpMethod.GET, "/x", response_schema="Ghost"),),
        )
        issues = validate_ir(ir)
        self.assertTrue(has_errors(issues))
        self.assertEqual(issues[0].code, "unknown_schema_reference")
        self.assertEqual(issues[0].severity, Severity.ERROR)

    def test_strategy_without_platform_is_a_warning(self) -> None:
        # web_strategy set, but WEB not in platforms
        ir = ApplicationIR(
            name="Demo", description="d", platforms=(Platform.BACKEND,),
            project_strategy=_strategy(web=WebStrategy.NEXTJS),
        )
        issues = validate_ir(ir)
        self.assertFalse(has_errors(issues))
        self.assertTrue(any(i.code == "platform_strategy_mismatch" and i.severity == Severity.WARNING for i in issues))

    def test_platform_without_strategy_is_a_warning(self) -> None:
        # WEB in platforms, but web_strategy none
        ir = ApplicationIR(
            name="Demo", description="d", platforms=(Platform.WEB, Platform.BACKEND),
            project_strategy=_strategy(web=WebStrategy.NONE),
        )
        issues = validate_ir(ir)
        self.assertTrue(any(i.code == "platform_strategy_mismatch" for i in issues))

    def test_validate_is_deterministic(self) -> None:
        ir = example_ir("minimal-blog")
        self.assertEqual(validate_ir(ir), validate_ir(ir))


class NormalizerTests(TestCase):
    def _unsorted(self) -> ApplicationIR:
        return ApplicationIR(
            name="Demo", description="d",
            platforms=(Platform.BACKEND, Platform.WEB),
            project_strategy=_strategy(),
            roles=(Role("zeta"), Role("alpha")),
            entities=(Entity("Zebra", (Field("id", FieldType.UUID),)), Entity("Apple", (Field("id", FieldType.UUID),))),
            apis=(ApiEndpoint(HttpMethod.POST, "/z"), ApiEndpoint(HttpMethod.GET, "/a")),
            screens=(Screen("zzz", "alpha"), Screen("aaa", "alpha")),
        )

    def test_sorts_canonically_and_preserves_platform_order(self) -> None:
        norm = normalize_ir(self._unsorted())
        self.assertEqual(norm.platforms, (Platform.WEB, Platform.BACKEND))   # enum order
        self.assertEqual([r.id for r in norm.roles], ["alpha", "zeta"])
        self.assertEqual([e.name for e in norm.entities], ["Apple", "Zebra"])
        self.assertEqual([(a.method.value, a.path) for a in norm.apis], [("GET", "/a"), ("POST", "/z")])
        self.assertEqual([s.id for s in norm.screens], ["aaa", "zzz"])

    def test_idempotent_and_lossless(self) -> None:
        once = normalize_ir(self._unsorted())
        twice = normalize_ir(once)
        self.assertEqual(once.to_dict(), twice.to_dict())
        # Normalizing does not change the set of entities/roles (lossless), only order.
        self.assertEqual({e.name for e in once.entities}, {"Apple", "Zebra"})


class ExampleFixtureTests(TestCase):
    def test_examples_are_valid_and_generatable(self) -> None:
        self.assertGreaterEqual(len(EXAMPLES), 2)
        adapters = (NextjsWebAdapter(), PythonBackendAdapter(), GoBackendAdapter())
        for name in EXAMPLES:
            ir = example_ir(name)
            self.assertIsInstance(ir, ApplicationIR)
            self.assertFalse(has_errors(validate_ir(ir)), name)
            for adapter in adapters:
                project = adapter.generate(ir)
                self.assertGreater(len(project), 0, f"{name}:{adapter.target.value}")

    def test_unknown_example_rejected(self) -> None:
        from omnistackai_agent_engine.application_ir import InvalidIRError
        with self.assertRaises(InvalidIRError):
            example_ir("does-not-exist")
