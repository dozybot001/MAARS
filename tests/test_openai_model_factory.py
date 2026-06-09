import sys
import types
import unittest
from unittest.mock import patch


class OpenAIModelFactoryTests(unittest.TestCase):
    def test_openai_model_factory_uses_responses_model(self):
        captured = {}

        class DummyOpenAIResponses:
            def __init__(self, **kwargs):
                captured.update(kwargs)

        fake_module = types.SimpleNamespace(OpenAIResponses=DummyOpenAIResponses)
        with patch.dict(sys.modules, {"agno.models.openai": fake_module}):
            from backend.agno.models import create_model

            create_model("openai", "gpt-5.5", "key")

        self.assertEqual(captured["id"], "gpt-5.5")
        self.assertEqual(captured["api_key"], "key")


if __name__ == "__main__":
    unittest.main()
