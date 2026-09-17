"""R-467: read-only, path-safe file access for the Studio (studio/files.py).

Pure filesystem reads against tmp dirs. No network, model, or subprocess calls.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from omnistackai_agent_engine.studio.files import (
    BuildNotFoundError,
    FileNotFoundInBuildError,
    PathOutsideBuildError,
    list_build_files,
    read_build_file,
)


def _write(root: Path, rel: str, content: str = "x") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class ListBuildFilesTests(unittest.TestCase):
    def test_missing_directory_raises(self) -> None:
        with self.assertRaises(BuildNotFoundError):
            list_build_files("/no/such/build/dir")

    def test_flat_sorted_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in ("README.md", "apps/web/app/page.tsx", "apps/web/lib/types.ts", "services/api/main.py"):
                _write(root, rel)
            result = list_build_files(root)
            self.assertEqual(
                result["files"],
                ["README.md", "apps/web/app/page.tsx", "apps/web/lib/types.ts", "services/api/main.py"],
            )
            self.assertFalse(result["truncated"])

    def test_excluded_directories_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "app/page.tsx")
            for excluded in (".git", "node_modules", "__pycache__", ".next", ".venv", "venv"):
                _write(root, f"{excluded}/junk.bin")
                _write(root, f"apps/web/{excluded}/nested.js")
            result = list_build_files(root)
            self.assertEqual(result["files"], ["app/page.tsx"])

    def test_real_env_files_excluded_but_env_example_kept(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, ".env")
            _write(root, ".env.local")
            _write(root, "apps/web/.env.production")
            _write(root, "apps/web/.env.example")
            result = list_build_files(root)
            self.assertEqual(result["files"], ["apps/web/.env.example"])

    def test_truncation_at_max_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i in range(10):
                _write(root, f"file-{i:02d}.txt")
            result = list_build_files(root, max_entries=3)
            self.assertEqual(len(result["files"]), 3)
            self.assertTrue(result["truncated"])

    def test_empty_directory_is_not_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = list_build_files(tmp)
            self.assertEqual(result, {"files": [], "truncated": False})


class ReadBuildFileTests(unittest.TestCase):
    def test_missing_build_directory_raises(self) -> None:
        with self.assertRaises(BuildNotFoundError):
            read_build_file("/no/such/build/dir", "README.md")

    def test_reads_a_text_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "apps/web/app/page.tsx", "export default function Page() { return null; }\n")
            result = read_build_file(root, "apps/web/app/page.tsx")
            self.assertEqual(result["path"], "apps/web/app/page.tsx")
            self.assertIn("export default function Page", result["content"])
            self.assertFalse(result["truncated"])
            self.assertFalse(result["binary"])
            self.assertEqual(result["size"], len(result["content"]))

    def test_empty_or_absolute_path_is_outside_build(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "README.md")
            for bad in ("", "/etc/passwd", "\\Windows\\win.ini"):
                with self.assertRaises(PathOutsideBuildError):
                    read_build_file(root, bad)

    def test_traversal_outside_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "build"
            root.mkdir()
            _write(root.parent, "secret.txt", "outside")
            with self.assertRaises(PathOutsideBuildError):
                read_build_file(root, "../secret.txt")

    def test_symlink_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "outside.txt"
            outside.write_text("nope", encoding="utf-8")
            root = Path(tmp) / "build"
            root.mkdir()
            try:
                (root / "escape.txt").symlink_to(outside)
            except OSError:
                self.skipTest("symlinks are not supported on this filesystem")
            with self.assertRaises(PathOutsideBuildError):
                read_build_file(root, "escape.txt")

    def test_excluded_directory_and_secret_env_are_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "node_modules/pkg/index.js")
            _write(root, ".env")
            _write(root, "apps/web/.env.local")
            for rel in ("node_modules/pkg/index.js", ".env", "apps/web/.env.local"):
                with self.assertRaises(FileNotFoundInBuildError):
                    read_build_file(root, rel)

    def test_env_example_is_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "apps/web/.env.example", "NEXT_PUBLIC_APP_NAME=Demo\n")
            result = read_build_file(root, "apps/web/.env.example")
            self.assertIn("NEXT_PUBLIC_APP_NAME", result["content"])

    def test_missing_file_raises_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundInBuildError):
                read_build_file(tmp, "does/not/exist.txt")

    def test_directory_path_raises_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "apps/web/app/page.tsx")
            with self.assertRaises(FileNotFoundInBuildError):
                read_build_file(root, "apps/web/app")

    def test_truncation_at_max_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "big.txt", "a" * 100)
            result = read_build_file(root, "big.txt", max_bytes=10)
            self.assertEqual(len(result["content"]), 10)
            self.assertTrue(result["truncated"])
            self.assertEqual(result["size"], 100)

    def test_binary_file_is_reported_not_raised(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "image.png").write_bytes(bytes(range(256)))
            result = read_build_file(root, "image.png")
            self.assertTrue(result["binary"])
            self.assertEqual(result["content"], "")
            self.assertEqual(result["size"], 256)

    def test_result_is_json_serializable(self) -> None:
        import json

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "a.txt", "hello")
            json.dumps(read_build_file(root, "a.txt"))
            json.dumps(list_build_files(root))


if __name__ == "__main__":
    unittest.main()
