import unittest

from backend.pipeline.research_graph_nodes import ResearchStageGraphNodes


class _FakeStage:
    def __init__(self):
        self.calls = []

    async def _calibrate_once(self, idea):
        self.calls.append(("_calibrate_once", idea))

    def _initialize_research_loop(self):
        self.calls.append(("_initialize_research_loop",))
        return {"phase": "loop_initialized", "iteration": 3}

    async def _prepare_strategy_round(self, idea, iteration):
        self.calls.append(("_prepare_strategy_round", idea, iteration))

    async def _prepare_decomposition_round(self, idea, iteration):
        self.calls.append(("_prepare_decomposition_round", idea, iteration))

    async def _execute_task_round(self, iteration):
        self.calls.append(("_execute_task_round", iteration))
        return True

    async def _evaluate_research_round(self, idea, iteration):
        self.calls.append(("_evaluate_research_round", idea, iteration))
        return {"phase": "evaluated", "loop_done": True}

    def _build_final_output(self):
        self.calls.append(("_build_final_output",))
        return "final"


class ResearchStageGraphNodesTests(unittest.IsolatedAsyncioTestCase):
    async def test_adapter_delegates_graph_nodes_to_stage_methods(self):
        stage = _FakeStage()
        nodes = ResearchStageGraphNodes(stage)
        state = {"idea": "idea", "iteration": 2}

        self.assertEqual(await nodes.calibrate(state), {"phase": "calibrated"})
        self.assertEqual(
            await nodes.initialize_loop(state),
            {"phase": "loop_initialized", "iteration": 3},
        )
        self.assertEqual(await nodes.prepare_strategy(state), {"phase": "strategy_completed"})
        self.assertEqual(
            await nodes.prepare_decomposition(state),
            {"phase": "decomposition_completed"},
        )
        self.assertEqual(
            await nodes.execute_tasks(state),
            {"phase": "execution_completed", "failed": True},
        )
        self.assertEqual(
            await nodes.evaluate_round(state),
            {"phase": "evaluated", "loop_done": True},
        )
        self.assertEqual(
            await nodes.summarize_results(state),
            {"phase": "summarized", "output": "final"},
        )

        self.assertEqual(stage.calls, [
            ("_calibrate_once", "idea"),
            ("_initialize_research_loop",),
            ("_prepare_strategy_round", "idea", 2),
            ("_prepare_decomposition_round", "idea", 2),
            ("_execute_task_round", 2),
            ("_evaluate_research_round", "idea", 2),
            ("_build_final_output",),
        ])


if __name__ == "__main__":
    unittest.main()
