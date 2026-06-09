import tempfile
import unittest

from backend.db import ResearchDB
from backend.executors.task import TaskExecutionResult
from backend.pipeline.research import ResearchStage


class _FakeExecutor:
    def __init__(self):
        self.contexts = []

    async def run(self, context):
        self.contexts.append(context)
        return TaskExecutionResult(
            task_id=context.task_id,
            markdown="Result body\n\nSUMMARY: saved metrics.json score=0.9",
            summary="saved metrics.json score=0.9",
        )


class ResearchCodexExecutorPathTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_task_cycle_executes_through_task_executor(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = ResearchDB(base_dir=tmpdir)
            db.create_session("codex executor")
            stage = ResearchStage(db=db)
            fake = _FakeExecutor()
            stage._create_task_executor = lambda: fake
            stage._verify_task = _passing_verify
            task = {
                "id": "1",
                "description": "run task",
                "dependencies": [],
            }
            stage._all_tasks = [task]

            needs_redecompose, _, result, review = await stage._run_task_cycle(
                task,
                "1",
                "Exec 1",
                "",
            )

            self.assertFalse(needs_redecompose)
            self.assertEqual(review, "")
            self.assertIn("SUMMARY:", result)
            self.assertEqual(stage._task_summaries["1"], "saved metrics.json score=0.9")
            self.assertEqual(db.get_plan_list()[0]["status"], "completed")
            self.assertEqual(db.get_plan_list()[0]["summary"], "saved metrics.json score=0.9")
            self.assertEqual(fake.contexts[0].task_id, "1")
            self.assertEqual(fake.contexts[0].workspace_dir.name, "1")


async def _passing_verify(task, result, task_id, call_id):
    return True, "", False


if __name__ == "__main__":
    unittest.main()
