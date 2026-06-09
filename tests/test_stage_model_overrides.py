import unittest
from unittest.mock import patch


class StageModelOverrideTests(unittest.TestCase):
    def test_stage_specific_models_are_wired_independently(self):
        captured = {}

        class DummyRefineStage:
            def __init__(self, **kwargs):
                captured["refine"] = kwargs

        class DummyResearchStage:
            def __init__(self, **kwargs):
                captured["research"] = kwargs

        class DummyWriteStage:
            def __init__(self, **kwargs):
                captured["write"] = kwargs

        with patch("backend.agno.create_model", side_effect=lambda provider, model_id, api_key="": f"{provider}:{model_id}"), \
             patch("backend.agno.create_db_tools", return_value=[]), \
             patch("backend.agno.ArxivTools", return_value="arxiv"), \
             patch("backend.agno.WikipediaTools", return_value="wikipedia"), \
             patch("backend.agno.RefineStage", DummyRefineStage), \
             patch("backend.agno.ResearchStage", DummyResearchStage), \
             patch("backend.agno.WriteStage", DummyWriteStage):
            from backend.agno import create_agno_stages

            create_agno_stages(
                model_id="gpt-default",
                refine_model_id="gpt-refine",
                research_model_id="gpt-research",
                write_model_id="gpt-write",
                api_key="key",
                db=None,
            )

        self.assertEqual(captured["refine"]["model"], "openai:gpt-refine")
        self.assertEqual(captured["research"]["model"], "openai:gpt-research")
        self.assertEqual(captured["write"]["model"], "openai:gpt-write")


if __name__ == "__main__":
    unittest.main()
