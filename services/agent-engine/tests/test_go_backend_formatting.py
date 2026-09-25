"""R-587: generated Go is gofmt-clean.

`gofmt -l` named four files in every generated backend. Struct fields were emitted with single
spaces where gofmt aligns names, types and tags into columns, and three more files carried a stray
blank line. Nothing was broken — the backend compiled and vetted cleanly — but Go developers treat
gofmt as *the* format, so an editor set to format on save rewrites a file the first time someone
opens the repository, on code they never touched.

Two gates, deliberately different in kind. The first asks the real `gofmt` and is skipped where Go
is absent, so it proves the property rather than approximating it. The second checks the alignment
by reading the generated text, so `task verify` still catches the common regression on a machine
with no Go toolchain — the columns are what a template edit is most likely to break.
"""

import dataclasses
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest import TestCase, skipUnless

from omnistackai_agent_engine.application_ir import (
    ApplicationIR,
    BackendStrategy,
    Entity,
    Field,
    FieldType,
    MobileProfile,
    Platform,
    ProjectStrategy,
    AdminStrategy,
    DatabaseStrategy,
    RepoStrategy,
    WebStrategy,
    example_ir,
)
from omnistackai_agent_engine.codegen.assembler import assemble_project

_HAVE_GO = shutil.which("go") is not None and shutil.which("gofmt") is not None


def _go_ir(ir: ApplicationIR) -> ApplicationIR:
    return dataclasses.replace(
        ir, project_strategy=dataclasses.replace(ir.project_strategy, backend_strategy=BackendStrategy.GO)
    )


def _mixed_ir() -> ApplicationIR:
    """Field names and types of deliberately different lengths, required and optional.

    An optional field is emitted as `*string`, which is wider than the required column, so a naive
    alignment that measures only required fields would look right on the example IR and wrong here.
    """
    return ApplicationIR(
        name="Widths",
        description="fields of assorted widths",
        platforms=(Platform.WEB,),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE, WebStrategy.NEXTJS, AdminStrategy.NONE,
            BackendStrategy.GO, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        entities=(
            Entity(
                name="Thing",
                fields=(
                    Field(name="id", type=FieldType.UUID, required=True),
                    Field(name="a_very_long_field_name", type=FieldType.TEXT, required=False),
                    Field(name="n", type=FieldType.INT, required=True),
                    Field(name="when", type=FieldType.DATETIME, required=False),
                ),
            ),
        ),
    )


def _go_files(ir: ApplicationIR) -> dict[str, str]:
    return {f.path: f.content for f in assemble_project(_go_ir(ir)).files() if f.path.endswith(".go")}


class GeneratedGoIsFormatted(TestCase):
    @skipUnless(_HAVE_GO, "needs the Go toolchain")
    def _assert_gofmt_clean(self, ir: ApplicationIR) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for path, content in _go_files(ir).items():
                out = root / path
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(content, encoding="utf-8")
            done = subprocess.run(
                ["gofmt", "-l", "."], cwd=str(root), capture_output=True, text=True, timeout=120, check=False
            )
            unformatted = [line for line in done.stdout.splitlines() if line.strip()]
            self.assertEqual(unformatted, [], f"gofmt would rewrite these generated files: {unformatted}")

    @skipUnless(_HAVE_GO, "needs the Go toolchain")
    def test_the_example_backend_is_gofmt_clean(self) -> None:
        self._assert_gofmt_clean(example_ir("minimal-blog"))

    @skipUnless(_HAVE_GO, "needs the Go toolchain")
    def test_assorted_field_widths_are_gofmt_clean(self) -> None:
        self._assert_gofmt_clean(_mixed_ir())


class TheColumnsAreAlignedWithoutAToolchain(TestCase):
    """The offline half: a template edit is most likely to break the columns, and most machines
    running `task verify` have no Go installed."""

    def _struct_lines(self, ir: ApplicationIR) -> list[str]:
        models = _go_files(ir)["services/api/internal/models/models.go"]
        inside, rows = False, []
        for line in models.splitlines():
            if line.startswith("type ") and line.endswith("struct {"):
                inside = True
                continue
            if inside and line == "}":
                inside = False
                continue
            if inside and line.strip():
                rows.append(line)
        return rows

    def test_names_types_and_tags_line_up(self) -> None:
        for label, ir in (("example", example_ir("minimal-blog")), ("mixed widths", _mixed_ir())):
            with self.subTest(ir=label):
                rows = self._struct_lines(ir)
                self.assertTrue(rows, "no struct fields were generated")
                type_columns = {line.index(line.split()[1]) for line in rows}
                tag_columns = {line.index("`") for line in rows}
                self.assertEqual(len(type_columns), 1, f"types do not share a column: {rows}")
                self.assertEqual(len(tag_columns), 1, f"tags do not share a column: {rows}")

    def test_no_file_ends_with_a_blank_line(self) -> None:
        # Three of the four originally-unformatted files failed on exactly this.
        for path, content in _go_files(example_ir("minimal-blog")).items():
            with self.subTest(path=path):
                self.assertTrue(content.endswith("\n"), f"{path} must end with a newline")
                self.assertFalse(content.endswith("\n\n"), f"{path} ends with a blank line")

    def test_no_file_has_two_blank_lines_in_a_row(self) -> None:
        for path, content in _go_files(example_ir("minimal-blog")).items():
            with self.subTest(path=path):
                self.assertNotIn("\n\n\n", content, f"{path} has a doubled blank line")

    def test_formatting_did_not_change_the_code(self) -> None:
        # Alignment is whitespace. If a field name, type or tag changed, this is not a formatting
        # change any more.
        rows = self._struct_lines(example_ir("minimal-blog"))
        squashed = [" ".join(line.split()) for line in rows]
        self.assertIn('Id string `json:"id"`', squashed)
        self.assertIn('CreatedAt time.Time `json:"created_at"`', squashed)
