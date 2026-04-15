import tempfile
import unittest
from pathlib import Path

from backend.db import ResearchDB
from backend.team.write import WriteStage


class WriteStagePathTests(unittest.TestCase):
    def test_draft_rounds_use_parent_artifact_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = ResearchDB(base_dir=tmpdir)
            db.create_session("write paths")
            stage = WriteStage(db=db)

            stage._save_round_md("drafts", "![Fig](artifacts/4/plot.png)", 1)

            saved = (Path(tmpdir) / db.research_id / "drafts" / "round_1.md").read_text(encoding="utf-8")
            self.assertIn("](../artifacts/4/plot.png)", saved)

    def test_final_paper_uses_root_artifact_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = ResearchDB(base_dir=tmpdir)
            db.create_session("write paper paths")
            stage = WriteStage(db=db)
            stage.output = "![Fig](../artifacts/4/plot.png)"

            result = stage._finalize()

            saved = (Path(tmpdir) / db.research_id / "paper.md").read_text(encoding="utf-8")
            self.assertIn("](./artifacts/4/plot.png)", result)
            self.assertIn("](./artifacts/4/plot.png)", saved)


if __name__ == "__main__":
    unittest.main()
