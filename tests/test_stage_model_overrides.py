import unittest
from unittest.mock import patch


class CodexStageFactoryTests(unittest.TestCase):
    def test_factory_wires_stages_without_model_clients_or_tools(self):
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

        with patch("backend.runtime.stages.RefineStage", DummyRefineStage), \
             patch("backend.runtime.stages.ResearchStage", DummyResearchStage), \
             patch("backend.runtime.stages.WriteStage", DummyWriteStage):
            from backend.runtime.stages import create_codex_stages

            create_codex_stages(db=None, max_iterations=2, max_delegations=3)

        self.assertIsNone(captured["refine"]["model"])
        self.assertEqual(captured["refine"]["explorer_tools"], [])
        self.assertEqual(captured["refine"]["max_delegations"], 3)
        self.assertIsNone(captured["research"]["model"])
        self.assertEqual(captured["research"]["execute_tools"], [])
        self.assertEqual(captured["research"]["read_tools"], [])
        self.assertEqual(captured["research"]["search_tools"], [])
        self.assertEqual(captured["research"]["max_iterations"], 2)
        self.assertIsNone(captured["write"]["model"])
        self.assertIsNone(captured["write"]["polish_model"])
        self.assertEqual(captured["write"]["writer_tools"], [])
        self.assertEqual(captured["write"]["reviewer_tools"], [])


if __name__ == "__main__":
    unittest.main()
