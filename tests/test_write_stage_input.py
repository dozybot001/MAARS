import tempfile
import unittest

from backend.db import ResearchDB
from backend.team.write import WriteStage


class WriteStageInputTests(unittest.TestCase):
    def test_load_input_includes_results_summary_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = ResearchDB(base_dir=tmpdir)
            db.create_session("write input")
            db.save_results_summary({
                "research_goal": "Test goal",
                "completed_tasks": [{"id": "1", "summary": "task summary"}],
            }, "# Results Summary\n")

            stage = WriteStage(db=db)
            prompt = stage.load_input()

            self.assertIn("Test goal", prompt)
            self.assertIn('"completed_tasks"', prompt)
            self.assertIn("唯一事实锚点", prompt)


if __name__ == "__main__":
    unittest.main()
