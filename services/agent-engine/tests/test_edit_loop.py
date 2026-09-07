import dataclasses
import subprocess
import tempfile
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import GeneratedFile, GeneratedProject, assemble_project
from omnistackai_agent_engine.edit import (
    ApplyError,
    ChangeKind,
    FileChange,
    ProjectDiff,
    apply_diff,
    commit_edit,
    diff_projects,
    plan_edit,
)
from omnistackai_agent_engine.git_service import create_repository

TARGET = "customer-monorepo"


def _project(files: dict[str, str]) -> GeneratedProject:
    return GeneratedProject(TARGET, tuple(GeneratedFile(path, content) for path, content in files.items()))


class DiffClassificationTests(TestCase):
    def test_added_modified_deleted_unchanged(self) -> None:
        old = _project({"a.txt": "1", "b.txt": "keep", "gone.txt": "x"})
        new = _project({"a.txt": "2", "b.txt": "keep", "new.txt": "y"})
        diff = diff_projects(old, new)
        self.assertEqual(diff.added(), ("new.txt",))
        self.assertEqual(diff.modified(), ("a.txt",))
        self.assertEqual(diff.deleted(), ("gone.txt",))
        self.assertEqual(diff.unchanged, ("b.txt",))
        self.assertIn("1 added, 1 modified, 1 deleted, 1 unchanged", diff.summary())

    def test_identical_projects_diff_empty(self) -> None:
        project = _project({"a.txt": "same"})
        self.assertTrue(diff_projects(project, project).is_empty())

    def test_executable_flag_change_is_a_modification(self) -> None:
        old = GeneratedProject(TARGET, (GeneratedFile("run.sh", "#!/bin/sh\n", False),))
        new = GeneratedProject(TARGET, (GeneratedFile("run.sh", "#!/bin/sh\n", True),))
        self.assertEqual(diff_projects(old, new).modified(), ("run.sh",))


class PlanEditTests(TestCase):
    def test_no_change_yields_empty_diff(self) -> None:
        ir = example_ir("rideshare-favourites")
        self.assertTrue(plan_edit(ir, ir).is_empty())

    def test_description_change_modifies_readme_only(self) -> None:
        ir = example_ir("rideshare-favourites")
        edited = dataclasses.replace(ir, description="A new one-line description for the app.")
        diff = plan_edit(ir, edited)
        self.assertFalse(diff.is_empty())
        self.assertEqual(diff.added(), ())
        self.assertEqual(diff.deleted(), ())
        self.assertIn("README.md", diff.modified())
        # every change is a content modification of an existing file
        self.assertTrue(all(c.kind is ChangeKind.MODIFIED for c in diff.changes))


class ApplyTests(TestCase):
    def test_apply_takes_old_tree_to_new(self) -> None:
        old = _project({"keep.txt": "same", "edit.txt": "old", "drop.txt": "bye"})
        new = _project({"keep.txt": "same", "edit.txt": "new", "add.txt": "hi"})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for generated in old.files():
                (root / generated.path).write_text(generated.content, encoding="utf-8")
            report = apply_diff(diff_projects(old, new), root)
            self.assertEqual(report.added, ("add.txt",))
            self.assertEqual(report.modified, ("edit.txt",))
            self.assertEqual(report.deleted, ("drop.txt",))
            # the directory now equals the new project
            self.assertEqual((root / "edit.txt").read_text(), "new")
            self.assertEqual((root / "add.txt").read_text(), "hi")
            self.assertFalse((root / "drop.txt").exists())

    def test_apply_refuses_escape(self) -> None:
        diff = ProjectDiff((FileChange(ChangeKind.DELETED, "../escape.txt", None),), ())
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ApplyError):
                apply_diff(diff, tmp)

    def test_apply_missing_target_errors(self) -> None:
        diff = ProjectDiff((), ())
        with self.assertRaises(ApplyError):
            apply_diff(diff, "/no/such/dir/for/omnistackai")


class CommitEditTests(TestCase):
    def test_commit_edit_records_a_second_commit(self) -> None:
        ir = example_ir("rideshare-favourites")
        edited = dataclasses.replace(ir, description="Edited description for the commit test.")
        with tempfile.TemporaryDirectory() as tmp:
            create_repository(
                assemble_project(ir), tmp, author_name="sanjeetji", author_email="sk698166@gmail.com"
            )
            diff = plan_edit(ir, edited)
            result = commit_edit(
                diff, tmp, author_name="sanjeetji", author_email="sk698166@gmail.com",
                message="edit: update description",
            )
            self.assertTrue(result.commit_sha)
            log = subprocess.run(
                ["git", "-C", tmp, "log", "--oneline"], capture_output=True, text=True, check=True
            )
            self.assertEqual(len(log.stdout.strip().splitlines()), 2)
