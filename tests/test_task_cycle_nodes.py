import unittest

from backend.executors.task import TaskExecutionResult
from backend.pipeline.task_cycle_nodes import ResearchTaskCycleNodes
from backend.runtime.langgraph_task import LangGraphTaskRuntime


class _FakeStage:
    def __init__(self):
        self.executions = []
        self.recorded = []
        self.sent = []
        self.verify_calls = 0

    async def _execute_once(self, task, prior_attempt, dep_summaries, metadata=None):
        self.executions.append({
            "task": task,
            "prior_attempt": prior_attempt,
            "dep_summaries": dep_summaries,
            "metadata": metadata or {},
        })
        attempt = len(self.executions)
        return TaskExecutionResult(
            task_id=task["id"],
            markdown=f"result attempt {attempt}",
            summary=f"summary attempt {attempt}",
        )

    def _record_execution_result(self, execution):
        self.recorded.append(execution.summary)

    async def _verify_task(self, task, result, task_id, call_id):
        self.verify_calls += 1
        if self.verify_calls == 1:
            return False, "fix review", False
        return True, "", False

    def _send(self, **kwargs):
        self.sent.append(kwargs)


class ResearchTaskCycleNodesTests(unittest.IsolatedAsyncioTestCase):
    async def test_retry_attempt_receives_previous_result_and_review_metadata(self):
        stage = _FakeStage()
        nodes = ResearchTaskCycleNodes(stage)
        runtime = LangGraphTaskRuntime(nodes)

        result = await runtime.run(
            {"id": "1", "description": "run task"},
            "1",
            "Exec 1",
            prior_attempt="parent output",
            dep_summaries={"0": "dependency summary"},
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.attempts, 2)
        self.assertEqual(stage.recorded, ["summary attempt 1", "summary attempt 2"])
        self.assertEqual(stage.executions[0]["metadata"], {})
        self.assertEqual(stage.executions[1]["metadata"], {
            "previous_result": "result attempt 1",
            "retry_review": "fix review",
        })
        self.assertEqual(stage.executions[1]["prior_attempt"], "parent output")
        self.assertEqual(stage.executions[1]["dep_summaries"], {"0": "dependency summary"})
        self.assertEqual(stage.sent, [{"status": "retrying", "task_id": "1"}])


if __name__ == "__main__":
    unittest.main()
