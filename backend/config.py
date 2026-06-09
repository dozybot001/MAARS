import os

from typing import Literal

from pydantic import ConfigDict, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_prefix="MAARS_", env_file=".env", extra="ignore")

    # --- Research ---
    research_max_iterations: int = 3
    team_max_delegations: int = 5

    # --- Kaggle ---
    kaggle_api_token: str = ""
    dataset_dir: str = "data/"

    # --- API ---
    api_concurrency: int = 3
    api_request_interval: float = 0  # min seconds between consecutive LLM calls
    output_language: str = "Chinese"

    # --- Agent/runtime timeouts ---
    agent_session_timeout: int | None = None

    # --- Score improvement threshold (fraction, e.g. 0.005 = 0.5%) ---
    score_improvement_threshold: float = 0.005

    # --- Codex task executor ---
    codex_bin: str = "codex"
    codex_model: str | None = None
    codex_reasoning_effort: Literal["low", "medium", "high", "xhigh"] | None = None
    codex_refine_reasoning_effort: Literal["low", "medium", "high", "xhigh"] | None = None
    codex_research_reasoning_effort: Literal["low", "medium", "high", "xhigh"] | None = None
    codex_write_reasoning_effort: Literal["low", "medium", "high", "xhigh"] | None = None
    codex_polish_reasoning_effort: Literal["low", "medium", "high", "xhigh"] | None = None
    codex_verbosity: Literal["low", "medium", "high"] | None = None
    codex_sandbox: str = "workspace-write"
    codex_timeout: int | None = None
    codex_inherit_proxy: bool = True
    codex_sandbox_provider: Literal["local", "docker"] = "local"
    codex_docker_image: str | None = None
    codex_docker_bin: str = "docker"
    codex_docker_codex_bin: str = "codex"
    codex_docker_gpus: str | None = None

    @field_validator(
        "codex_model",
        "codex_reasoning_effort",
        "codex_refine_reasoning_effort",
        "codex_research_reasoning_effort",
        "codex_write_reasoning_effort",
        "codex_polish_reasoning_effort",
        "codex_verbosity",
        "codex_timeout",
        "codex_docker_image",
        "codex_docker_gpus",
        "agent_session_timeout",
        mode="before",
    )
    @classmethod
    def _empty_string_as_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, str) and value.strip().startswith("#"):
            return None
        return value

    @model_validator(mode="after")
    def _validate_runtime_settings(self):
        eff = self.agent_session_timeout_seconds()
        if eff < 1:
            raise ValueError("MAARS_AGENT_SESSION_TIMEOUT must be positive")
        if self.codex_timeout is not None and self.codex_timeout < 1:
            raise ValueError("MAARS_CODEX_TIMEOUT must be positive when set")
        if not self.codex_bin.strip():
            raise ValueError("MAARS_CODEX_BIN must not be empty")
        if self.codex_sandbox_provider == "docker":
            if not self.codex_docker_image or not self.codex_docker_image.strip():
                raise ValueError("MAARS_CODEX_DOCKER_IMAGE must be set when MAARS_CODEX_SANDBOX_PROVIDER=docker")
            if not self.codex_docker_bin.strip():
                raise ValueError("MAARS_CODEX_DOCKER_BIN must not be empty")
            if not self.codex_docker_codex_bin.strip():
                raise ValueError("MAARS_CODEX_DOCKER_CODEX_BIN must not be empty")
        return self

    def agent_session_timeout_seconds(self) -> int:
        if self.agent_session_timeout is not None:
            return self.agent_session_timeout
        return 4200

    def is_chinese(self) -> bool:
        return self.output_language.lower().startswith("ch")


settings = Settings()

if settings.kaggle_api_token:
    os.environ.setdefault("KAGGLE_API_TOKEN", settings.kaggle_api_token)
