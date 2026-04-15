import tempfile
import unittest

from backend.db import ResearchDB
from backend.pipeline.research import ResearchStage


class ResearchBatchTests(unittest.TestCase):
    def test_new_iteration_tasks_append_after_completed_batches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = ResearchDB(base_dir=tmpdir)
            db.create_session("research batches")

            tasks = [
                {"id": "1", "description": "task 1", "dependencies": [], "status": "completed", "batch": 1},
                {"id": "2", "description": "task 2", "dependencies": ["1"], "status": "completed", "batch": 2},
                {"id": "r2_1", "description": "task r2_1", "dependencies": [], "status": "pending"},
                {"id": "r2_2", "description": "task r2_2", "dependencies": ["r2_1"], "status": "pending"},
            ]
            db.save_plan({}, tasks)

            stage = ResearchStage(db=db)
            stage._all_tasks = tasks
            stage._task_results = {"1": "done", "2": "done"}

            stage._init_task_batches()

            saved = {task["id"]: task for task in db.get_plan_list()}
            self.assertEqual(saved["r2_1"]["batch"], 3)
            self.assertEqual(saved["r2_2"]["batch"], 4)


if __name__ == "__main__":
    unittest.main()
