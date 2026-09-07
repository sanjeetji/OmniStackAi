from unittest import TestCase

from omnistackai_agent_engine.codegen import GeneratedFile, GeneratedProject
from omnistackai_agent_engine.edit import DiffKind, diff_report, unified_patch


def _project(files: dict[str, str]) -> GeneratedProject:
    return GeneratedProject("t", tuple(GeneratedFile(p, c) for p, c in files.items()))


class ModifiedHunkTests(TestCase):
    def test_modified_file_has_unified_hunk(self) -> None:
        old = _project({"a.txt": "line1\nline2\n"})
        new = _project({"a.txt": "line1\nCHANGED\n"})
        report = {r.path: r for r in diff_report(old, new)}
        self.assertIn("a.txt", report)
        self.assertEqual(report["a.txt"].kind, DiffKind.MODIFIED)
        patch = report["a.txt"].patch
        self.assertIn("--- a/a.txt", patch)
        self.assertIn("+++ b/a.txt", patch)
        self.assertIn("-line2", patch)
        self.assertIn("+CHANGED", patch)
        self.assertIn(" line1", patch)  # unchanged context line


class RenameDetectionTests(TestCase):
    def test_exact_content_rename_is_one_record(self) -> None:
        old = _project({"old_name.txt": "same\n"})
        new = _project({"new_name.txt": "same\n"})
        reports = diff_report(old, new)
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].kind, DiffKind.RENAMED)
        self.assertEqual((reports[0].old_path, reports[0].path), ("old_name.txt", "new_name.txt"))
        # not reported as add + delete
        kinds = {r.kind for r in reports}
        self.assertNotIn(DiffKind.ADDED, kinds)
        self.assertNotIn(DiffKind.DELETED, kinds)

    def test_rename_header_in_patch(self) -> None:
        old = _project({"old_name.txt": "same\n"})
        new = _project({"new_name.txt": "same\n"})
        self.assertIn("rename from old_name.txt\nrename to new_name.txt", unified_patch(old, new))


class AddDeleteAndEmptyTests(TestCase):
    def test_added_and_deleted_one_sided(self) -> None:
        old = _project({"gone.txt": "x\n"})
        new = _project({"added.txt": "hi\n"})
        kinds = {r.path: r.kind for r in diff_report(old, new)}
        self.assertEqual(kinds, {"added.txt": DiffKind.ADDED, "gone.txt": DiffKind.DELETED})

    def test_identical_projects_have_no_report(self) -> None:
        project = _project({"a.txt": "same\n"})
        self.assertEqual(diff_report(project, project), ())
        self.assertEqual(unified_patch(project, project), "")


class DeterminismTests(TestCase):
    def test_unified_patch_byte_stable(self) -> None:
        old = _project({"a.txt": "1\n", "b.txt": "keep\n", "gone.txt": "z\n"})
        new = _project({"a.txt": "2\n", "b.txt": "keep\n", "new.txt": "z\n"})  # gone -> new (rename), a modified
        self.assertEqual(unified_patch(old, new), unified_patch(old, new))
