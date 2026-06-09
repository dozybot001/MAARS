import unittest

from backend.runtime.langgraph_research import LangGraphResearchRuntime


class _FakeResearchNodes:
    def __init__(self, already_done: bool = False, fail_execution: bool = False):
        self.calls = []
        self.already_done = already_done
        self.fail_execution = fail_execution

    async def calibrate(self, state):
        self.calls.append(("calibrate", state["idea"]))
        return {"phase": "calibrated"}

    async def initialize_loop(self, state):
        self.calls.append(("initialize_loop", state["phase"]))
        return {
            "phase": "loop_initialized",
            "iteration": 0,
            "loop_done": self.already_done,
            "failed": False,
        }

    async def prepare_strategy(self, state):
        iteration = state["iteration"]
        self.calls.append(("prepare_strategy", iteration))
        return {"phase": "strategy_completed"}

    async def prepare_decomposition(self, state):
        iteration = state["iteration"]
        self.calls.append(("prepare_decomposition", iteration))
        return {"phase": "decomposition_completed"}

    async def execute_tasks(self, state):
        iteration = state["iteration"]
        self.calls.append(("execute_tasks", iteration))
        return {
            "phase": "execution_completed",
            "failed": self.fail_execution,
        }

    async def evaluate_round(self, state):
        iteration = state["iteration"]
        self.calls.append(("evaluate_round", iteration))
        if iteration == 0:
            return {
                "phase": "evaluated",
                "iteration": 1,
                "loop_done": False,
                "strategy_update": "try next round",
            }
        return {
            "phase": "evaluated",
            "iteration": iteration,
            "loop_done": True,
            "strategy_update": "",
        }

    async def summarize_results(self, state):
        self.calls.append(("summarize_results", state["phase"]))
        return {"phase": "summarized", "output": "final research output"}


class LangGraphResearchRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_loops_until_evaluation_is_done(self):
        nodes = _FakeResearchNodes()
        runtime = LangGraphResearchRuntime(nodes)

        result = await runtime.run("test idea")

        self.assertEqual(result.output, "final research output")
        self.assertEqual(result.state["phase"], "summarized")
        self.assertEqual(nodes.calls, [
            ("calibrate", "test idea"),
            ("initialize_loop", "calibrated"),
            ("prepare_strategy", 0),
            ("prepare_decomposition", 0),
            ("execute_tasks", 0),
            ("evaluate_round", 0),
            ("prepare_strategy", 1),
            ("prepare_decomposition", 1),
            ("execute_tasks", 1),
            ("evaluate_round", 1),
            ("summarize_results", "evaluated"),
        ])

    async def test_runtime_skips_loop_when_prior_evaluation_is_complete(self):
        nodes = _FakeResearchNodes(already_done=True)
        runtime = LangGraphResearchRuntime(nodes)

        result = await runtime.run("test idea")

        self.assertEqual(result.output, "final research output")
        self.assertEqual(nodes.calls, [
            ("calibrate", "test idea"),
            ("initialize_loop", "calibrated"),
            ("summarize_results", "loop_initialized"),
        ])

    async def test_runtime_summarizes_immediately_after_execution_failure(self):
        nodes = _FakeResearchNodes(fail_execution=True)
        runtime = LangGraphResearchRuntime(nodes)

        result = await runtime.run("test idea")

        self.assertEqual(result.output, "final research output")
        self.assertEqual(nodes.calls, [
            ("calibrate", "test idea"),
            ("initialize_loop", "calibrated"),
            ("prepare_strategy", 0),
            ("prepare_decomposition", 0),
            ("execute_tasks", 0),
            ("summarize_results", "execution_completed"),
        ])


if __name__ == "__main__":
    unittest.main()
