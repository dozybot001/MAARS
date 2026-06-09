import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from backend.core.research import ResearchGraphResult
from backend.db import ResearchDB
from backend.pipeline.research import ResearchStage


class ResearchStageLangGraphTests(unittest.IsolatedAsyncioTestCase):
    async def test_execute_delegates_to_langgraph_runtime(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = ResearchDB(base_dir=tmpdir)
            db.create_session("langgraph research")
            db.save_refined_idea("refined idea")
            stage = ResearchStage(db=db)

            with patch("backend.pipeline.research._preflight_codex"), \
                 patch("backend.pipeline.research.ResearchStageGraphNodes") as nodes_cls, \
                 patch("backend.pipeline.research.LangGraphResearchRuntime") as runtime_cls:
                runtime = runtime_cls.return_value
                runtime.run = AsyncMock(
                    return_value=ResearchGraphResult(output="graph output")
                )

                output = await stage._execute()

            self.assertEqual(output, "graph output")
            nodes_cls.assert_called_once_with(stage)
            runtime_cls.assert_called_once_with(nodes_cls.return_value)
            runtime.run.assert_awaited_once_with("refined idea")

    async def test_initialize_loop_stops_when_max_iterations_already_reached(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = ResearchDB(base_dir=tmpdir)
            db.create_session("max iterations")
            db.save_evaluation({"strategy_update": "try another round"}, 0)
            stage = ResearchStage(db=db, max_iterations=1)

            state = stage._initialize_research_loop()

        self.assertTrue(state["loop_done"])
        self.assertEqual(state["phase"], "max_iterations_reached")
        self.assertEqual(state["iteration"], 1)
        self.assertEqual(state["strategy_update"], "try another round")


if __name__ == "__main__":
    unittest.main()
