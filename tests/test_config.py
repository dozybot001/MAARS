from backend.config import Settings


def test_settings_allow_empty_openai_key_for_import_time_configuration(monkeypatch):
    monkeypatch.delenv("MAARS_OPENAI_MODEL", raising=False)

    settings = Settings(
        _env_file=None,
        openai_api_key="",
        research_max_iterations=1,
        team_max_delegations=1,
        kaggle_api_token="",
        dataset_dir="data",
        api_concurrency=1,
        output_language="Chinese",
    )

    assert settings.openai_api_key == ""
    assert settings.openai_model == "gpt-5.5"
    assert settings.model_for_stage("research") == "gpt-5.5"
