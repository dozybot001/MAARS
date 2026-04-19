import tempfile
import unittest
from pathlib import Path

from backend.agno.tools.db import create_db_tools
from backend.db import ResearchDB


class DBToolsTests(unittest.TestCase):
    def test_read_artifact_file_reads_valid_artifact(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = ResearchDB(base_dir=tmpdir)
            db.create_session("db tools")

            artifacts_dir = db.get_artifacts_dir()
            artifact = artifacts_dir / "metrics.json"
            artifact.write_text('{"score": 0.1}', encoding="utf-8")

            tools = {tool.__name__: tool for tool in create_db_tools(db)}
            result = tools["read_artifact_file"]("metrics.json")

            self.assertEqual(result, '{"score": 0.1}')

    def test_read_artifact_file_rejects_prefix_escape(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = ResearchDB(base_dir=tmpdir)
            db.create_session("db tools")

            session_root = Path(tmpdir) / db.research_id
            outside_dir = session_root / "artifacts-evil"
            outside_dir.mkdir()
            (outside_dir / "secret.txt").write_text("secret", encoding="utf-8")

            tools = {tool.__name__: tool for tool in create_db_tools(db)}
            result = tools["read_artifact_file"]("../artifacts-evil/secret.txt")

            self.assertEqual(result, "Error: path escapes artifacts directory.")


if __name__ == "__main__":
    unittest.main()
