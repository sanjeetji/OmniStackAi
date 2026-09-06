from unittest import TestCase

from omnistackai_agent_engine.application_ir import (
    AdminStrategy,
    ApplicationIR,
    BackendStrategy,
    DatabaseStrategy,
    MobileProfile,
    Platform,
    ProjectStrategy,
    RepoStrategy,
    WebStrategy,
)
from omnistackai_agent_engine.codegen import (
    AdapterRegistry,
    DuplicateAdapterError,
    DuplicateFileError,
    FrameworkAdapter,
    GeneratedFile,
    GeneratedProject,
    GenerationTarget,
    InvalidGeneratedFileError,
    UnsupportedTargetError,
)


def _ir() -> ApplicationIR:
    return ApplicationIR(
        name="Demo",
        description="demo app",
        platforms=(Platform.WEB,),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE, WebStrategy.NEXTJS, AdminStrategy.NONE,
            BackendStrategy.GO, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
    )


class FakeAdapter:
    def __init__(self, target: GenerationTarget = GenerationTarget.NEXTJS_WEB) -> None:
        self._target = target

    @property
    def target(self) -> GenerationTarget:
        return self._target

    def generate(self, ir: ApplicationIR) -> GeneratedProject:
        return GeneratedProject(self._target.value, (GeneratedFile("README.md", f"# {ir.name}\n"),))


class GeneratedFileTests(TestCase):
    def test_valid_file(self) -> None:
        f = GeneratedFile("app/page.tsx", "export default null")
        self.assertEqual(f.path, "app/page.tsx")

    def test_unsafe_paths_are_rejected(self) -> None:
        for bad in ("/etc/passwd", "../secret", "a/../b", "a//b", "a\\b", "", "app/ ", "a/.."):
            with self.assertRaises(InvalidGeneratedFileError, msg=bad):
                GeneratedFile(bad, "x")

    def test_non_string_content_rejected(self) -> None:
        with self.assertRaises(InvalidGeneratedFileError):
            GeneratedFile("a.txt", 123)  # type: ignore[arg-type]


class GeneratedProjectTests(TestCase):
    def test_unique_and_deterministically_ordered(self) -> None:
        project = GeneratedProject(
            "nextjs-web",
            (GeneratedFile("z.txt", "z"), GeneratedFile("a.txt", "a"), GeneratedFile("m/b.txt", "b")),
        )
        self.assertEqual(project.paths(), ("a.txt", "m/b.txt", "z.txt"))
        self.assertEqual(len(project), 3)
        self.assertEqual(project.get("a.txt").content, "a")

    def test_duplicate_path_rejected(self) -> None:
        with self.assertRaises(DuplicateFileError):
            GeneratedProject("t", (GeneratedFile("a.txt", "1"), GeneratedFile("a.txt", "2")))

    def test_merge_same_target_and_reject_cross_target(self) -> None:
        a = GeneratedProject("t", (GeneratedFile("a.txt", "a"),))
        b = GeneratedProject("t", (GeneratedFile("b.txt", "b"),))
        merged = a.merge(b)
        self.assertEqual(merged.paths(), ("a.txt", "b.txt"))
        with self.assertRaises(InvalidGeneratedFileError):
            a.merge(GeneratedProject("other", (GeneratedFile("c.txt", "c"),)))


class AdapterRegistryTests(TestCase):
    def test_fake_adapter_satisfies_contract(self) -> None:
        self.assertIsInstance(FakeAdapter(), FrameworkAdapter)

    def test_register_get_by_enum_and_string(self) -> None:
        registry = AdapterRegistry()
        registry.register(FakeAdapter(GenerationTarget.NEXTJS_WEB))
        self.assertIs(registry.get(GenerationTarget.NEXTJS_WEB).target, GenerationTarget.NEXTJS_WEB)
        self.assertIs(registry.get("nextjs-web").target, GenerationTarget.NEXTJS_WEB)
        project = registry.get("nextjs-web").generate(_ir())
        self.assertEqual(project.get("README.md").content, "# Demo\n")

    def test_duplicate_and_unknown_and_invalid(self) -> None:
        registry = AdapterRegistry()
        registry.register(FakeAdapter(GenerationTarget.BACKEND_GO))
        with self.assertRaises(DuplicateAdapterError):
            registry.register(FakeAdapter(GenerationTarget.BACKEND_GO))
        with self.assertRaises(UnsupportedTargetError):
            registry.get("nope")
        with self.assertRaises(UnsupportedTargetError):
            registry.get(GenerationTarget.FLUTTER)
        with self.assertRaises(UnsupportedTargetError):
            registry.register(object())

    def test_targets_sorted(self) -> None:
        registry = AdapterRegistry()
        registry.register(FakeAdapter(GenerationTarget.NEXTJS_WEB))
        registry.register(FakeAdapter(GenerationTarget.BACKEND_GO))
        self.assertEqual(registry.targets(), (GenerationTarget.BACKEND_GO, GenerationTarget.NEXTJS_WEB))
