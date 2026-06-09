import unittest

from backend.runtime.langgraph_task import LangGraphTaskRuntime


class _FakeTaskNodes:
    def __init__(self, verdicts):
        self.verdicts = list(verdicts)
        self.calls = []

    async def execute_attempt(self, state):
        attempt = state["attempt"]
        self.calls.append(("execute_attempt", attempt))
        return {"result": f"result attempt {attempt}"}

    async def verify_attempt(self, state):
        attempt = state["attempt"]
        self.calls.append(("verify_attempt", attempt, state["result"]))
        return self.verdicts.pop(0)

    async def prepare_retry(self, state):
        self.calls.append(("prepare_retry", state["attempt"], state["review"]))
        return {"attempt": state["attempt"] + 1}


class LangGraphTaskRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_task_runtime_passes_without_retry(self):
        nodes = _FakeTaskNodes([{"passed": True, "review": "", "redecompose": False}])
        runtime = LangGraphTaskRuntime(nodes)

        result = await runtime.run({"id": "1"}, "1", "Exec 1")

        self.assertTrue(result.passed)
        self.assertFalse(result.failed)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(nodes.calls, [
            ("execute_attempt", 1),
            ("verify_attempt", 1, "result attempt 1"),
        ])

    async def test_task_runtime_retries_once_before_passing(self):
        nodes = _FakeTaskNodes([
            {"passed": False, "review": "fix it", "redecompose": False},
            {"passed": True, "review": "", "redecompose": False},
        ])
        runtime = LangGraphTaskRuntime(nodes)

        result = await runtime.run({"id": "1"}, "1", "Exec 1")

        self.assertTrue(result.passed)
        self.assertEqual(result.attempts, 2)
        self.assertEqual(result.result, "result attempt 2")
        self.assertEqual(nodes.calls, [
            ("execute_attempt", 1),
            ("verify_attempt", 1, "result attempt 1"),
            ("prepare_retry", 1, "fix it"),
            ("execute_attempt", 2),
            ("verify_attempt", 2, "result attempt 2"),
        ])

    async def test_task_runtime_stops_for_redecompose(self):
        nodes = _FakeTaskNodes([
            {"passed": False, "review": "split task", "redecompose": True},
        ])
        runtime = LangGraphTaskRuntime(nodes)

        result = await runtime.run({"id": "1"}, "1", "Exec 1")

        self.assertFalse(result.passed)
        self.assertFalse(result.failed)
        self.assertTrue(result.needs_redecompose)
        self.assertEqual(result.review, "split task")
        self.assertEqual(result.attempts, 1)

    async def test_task_runtime_marks_failed_after_retry(self):
        nodes = _FakeTaskNodes([
            {"passed": False, "review": "fix it", "redecompose": False},
            {"passed": False, "review": "still bad", "redecompose": False},
        ])
        runtime = LangGraphTaskRuntime(nodes)

        result = await runtime.run({"id": "1"}, "1", "Exec 1")

        self.assertFalse(result.passed)
        self.assertTrue(result.failed)
        self.assertFalse(result.needs_redecompose)
        self.assertEqual(result.review, "still bad")
        self.assertEqual(result.attempts, 2)


if __name__ == "__main__":
    unittest.main()
