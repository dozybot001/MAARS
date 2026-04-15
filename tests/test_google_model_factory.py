import unittest
from unittest.mock import patch


class GoogleModelFactoryTests(unittest.TestCase):
    def test_google_model_factory_does_not_force_builtin_search(self):
        captured = {}

        class DummyGemini:
            def __init__(self, **kwargs):
                captured.update(kwargs)

        with patch("agno.models.google.Gemini", DummyGemini):
            from backend.agno.models import create_model

            create_model("google", "gemini-3.1-pro-preview", "key")

        self.assertEqual(captured["id"], "gemini-3.1-pro-preview")
        self.assertEqual(captured["api_key"], "key")
        self.assertNotIn("search", captured)


if __name__ == "__main__":
    unittest.main()
