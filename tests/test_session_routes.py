import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from backend.routes.session import _resolve_relative_path


class SessionRoutesTests(unittest.TestCase):
    def test_resolve_relative_path_stays_within_base_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            target = _resolve_relative_path(base, "artifacts/4/plot.png")
            self.assertEqual(target, (base / "artifacts" / "4" / "plot.png").resolve())

    def test_resolve_relative_path_rejects_parent_escape(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            with self.assertRaises(HTTPException):
                _resolve_relative_path(base, "../outside.txt")


if __name__ == "__main__":
    unittest.main()
