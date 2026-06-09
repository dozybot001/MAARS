from backend.config import Settings


def test_settings_do_not_require_openai_api_configuration():
    settings = Settings(
        _env_file=None,
        research_max_iterations=1,
        team_max_delegations=1,
        kaggle_api_token="",
        dataset_dir="data",
        api_concurrency=1,
        output_language="Chinese",
    )

    assert settings.codex_bin == "codex"
    assert settings.codex_model is None
    assert settings.codex_sandbox_provider == "local"
    assert settings.agent_session_timeout_seconds() == 4200


def test_settings_support_stage_specific_codex_reasoning_effort():
    settings = Settings(
        _env_file=None,
        codex_reasoning_effort="medium",
        codex_research_reasoning_effort="high",
        research_max_iterations=1,
        team_max_delegations=1,
        kaggle_api_token="",
        dataset_dir="data",
        api_concurrency=1,
        output_language="Chinese",
    )

    assert settings.codex_reasoning_effort == "medium"
    assert settings.codex_research_reasoning_effort == "high"
    assert settings.codex_write_reasoning_effort is None
