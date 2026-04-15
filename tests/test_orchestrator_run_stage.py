import tempfile
import unittest

from backend.pipeline.orchestrator import PipelineOrchestrator
from backend.pipeline.stage import Stage, StageState


class _StubStage(Stage):
    async def _execute(self) -> str:
        return self.name


class OrchestratorRunStageTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_write_stage_attaches_existing_session_and_clears_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = PipelineOrchestrator()
            orch.db = orch.db.__class__(base_dir=tmpdir)
            orch.stages = {
                "refine": _StubStage("refine", db=orch.db),
                "research": _StubStage("research", db=orch.db),
                "write": _StubStage("write", db=orch.db),
            }

            session_id = orch.db.create_session("rerun write")
            orch.db.save_idea("rerun write idea")
            orch.db.save_refined_idea("refined rerun write idea")
            orch.db.save_plan({}, [{
                "id": "1",
                "description": "task",
                "status": "completed",
                "summary": "task summary",
            }])
            orch.db.save_task_output("1", "task output")
            orch.db.save_evaluation({
                "feedback": "looks good",
                "score": 0.1,
                "satisfied": True,
            }, 0)
            root = orch.db.get_tasks_dir().parent
            (root / "drafts").mkdir(exist_ok=True)
            (root / "drafts" / "round_1.md").write_text("old draft", encoding="utf-8")
            (root / "reviews").mkdir(exist_ok=True)
            (root / "reviews" / "round_1.md").write_text("old review", encoding="utf-8")
            (root / "paper.md").write_text("old paper", encoding="utf-8")

            await orch.run_stage("write", session_id=session_id, clear_outputs=True)
            task = orch._pipeline_task
            self.assertIsNotNone(task)
            await task

            self.assertEqual(orch.db.research_id, session_id)
            self.assertEqual(orch.stages["refine"].state, StageState.COMPLETED)
            self.assertEqual(orch.stages["research"].state, StageState.COMPLETED)
            self.assertEqual(orch.stages["write"].state, StageState.COMPLETED)
            self.assertFalse((root / "paper.md").exists())
            self.assertFalse((root / "drafts").exists())
            self.assertFalse((root / "reviews").exists())
            self.assertEqual(len(orch.db.get_plan_list()), 1)
            self.assertEqual(orch.db.get_task_output("1"), "task output")
            self.assertEqual(orch.db.get_evaluation(0).get("score"), 0.1)


if __name__ == "__main__":
    unittest.main()
