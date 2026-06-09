from pathlib import Path

import pytest

from backend.routes import config as config_routes


def test_parse_env_file_uses_current_values_and_notes(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "\n".join([
            "# --- Codex runtime ---",
            "# Optional stage override",
            "MAARS_CODEX_MODEL=",
            "MAARS_CODEX_REASONING_EFFORT=high  # low | medium | high | xhigh",
        ]),
        encoding="utf-8",
    )

    lines, values = config_routes._parse_env_file(env)
    keyed = [line for line in lines if line.key]

    assert values["MAARS_CODEX_MODEL"] == ""
    assert values["MAARS_CODEX_REASONING_EFFORT"] == "high"
    assert keyed[0].notes == ["Optional stage override"]
    assert keyed[1].comment == "low | medium | high | xhigh"


def test_render_env_preserves_example_comments_and_writes_values(tmp_path):
    example = tmp_path / ".env.example"
    example.write_text(
        "\n".join([
            "# MAARS Configuration",
            "# --- API ---",
            "MAARS_API_CONCURRENCY=3  # max concurrent LLM requests",
            "MAARS_OUTPUT_LANGUAGE=Chinese",
        ]),
        encoding="utf-8",
    )
    lines, existing = config_routes._parse_env_file(example)

    rendered = config_routes._render_env(
        lines,
        {"MAARS_API_CONCURRENCY": "2", "MAARS_OUTPUT_LANGUAGE": "English"},
        existing,
    )

    assert "MAARS_API_CONCURRENCY=2  # max concurrent LLM requests" in rendered
    assert "MAARS_OUTPUT_LANGUAGE=English" in rendered


def test_validate_values_rejects_invalid_enum():
    with pytest.raises(Exception):
        config_routes._validate_values({
            "MAARS_CODEX_REASONING_EFFORT": "huge",
            "MAARS_RESEARCH_MAX_ITERATIONS": "1",
            "MAARS_TEAM_MAX_DELEGATIONS": "1",
            "MAARS_KAGGLE_API_TOKEN": "",
            "MAARS_DATASET_DIR": "data/",
            "MAARS_API_CONCURRENCY": "1",
            "MAARS_OUTPUT_LANGUAGE": "Chinese",
        })


def test_validate_values_rejects_multiline_env_injection():
    with pytest.raises(Exception):
        config_routes._validate_values({
            "MAARS_OUTPUT_LANGUAGE": "Chinese\nMAARS_CODEX_BIN=evil",
        })
