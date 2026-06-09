"""Execution-environment providers for Codex task sessions."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from backend.executors.task import TaskContext


@dataclass(frozen=True)
class CodexSandboxSession:
    """Resolved paths and command wrapping for one Codex task run."""

    provider: str
    host_workspace_dir: Path
    host_artifacts_dir: Path
    codex_bin: str
    codex_cwd: str
    schema_path: str
    artifact_source_dir: Path

    def wrap_command(self, argv: list[str]) -> list[str]:
        return argv


class CodexSandboxProvider(Protocol):
    """Prepares an execution environment for a Codex task."""

    name: str

    def validate(self) -> None:
        ...

    def prepare(self, context: TaskContext, schema_filename: str) -> CodexSandboxSession:
        ...


class LocalCodexSandboxProvider:
    """Run Codex directly on the host with Codex's own sandbox policy."""

    name = "local"

    def __init__(self, codex_bin: str):
        self.codex_bin = codex_bin

    def validate(self) -> None:
        if not shutil.which(self.codex_bin):
            raise RuntimeError(
                f"Research executor is set to Codex, but '{self.codex_bin}' was not found on PATH."
            )

    def prepare(self, context: TaskContext, schema_filename: str) -> CodexSandboxSession:
        context.workspace_dir.mkdir(parents=True, exist_ok=True)
        context.artifacts_dir.mkdir(parents=True, exist_ok=True)
        schema_path = context.workspace_dir / schema_filename
        return CodexSandboxSession(
            provider=self.name,
            host_workspace_dir=context.workspace_dir,
            host_artifacts_dir=context.artifacts_dir,
            codex_bin=self.codex_bin,
            codex_cwd=str(context.workspace_dir),
            schema_path=str(schema_path),
            artifact_source_dir=context.workspace_dir / "artifacts",
        )


class DockerCodexSandboxSession(CodexSandboxSession):
    """Codex session wrapped in a Docker container."""

    def __init__(
        self,
        *,
        image: str,
        docker_bin: str,
        gpus: str | None,
        env_names: tuple[str, ...],
        host_workspace_dir: Path,
        host_artifacts_dir: Path,
        container_codex_bin: str,
        container_workspace_dir: str,
        schema_filename: str,
    ):
        super().__init__(
            provider="docker",
            host_workspace_dir=host_workspace_dir,
            host_artifacts_dir=host_artifacts_dir,
            codex_bin=container_codex_bin,
            codex_cwd=container_workspace_dir,
            schema_path=f"{container_workspace_dir}/{schema_filename}",
            artifact_source_dir=host_workspace_dir / "artifacts",
        )
        self.image = image
        self.docker_bin = docker_bin
        self.gpus = gpus
        self.env_names = env_names
        self.container_workspace_dir = container_workspace_dir

    def wrap_command(self, argv: list[str]) -> list[str]:
        cmd = [
            self.docker_bin,
            "run",
            "--rm",
            "-v",
            f"{self.host_workspace_dir}:{self.container_workspace_dir}",
            "-w",
            self.container_workspace_dir,
        ]
        if self.gpus:
            cmd.extend(["--gpus", self.gpus])
        for name in self.env_names:
            if os.environ.get(name):
                cmd.extend(["-e", name])
        cmd.append(self.image)
        cmd.extend(argv)
        return cmd


class DockerCodexSandboxProvider:
    """Run Codex inside a configured Docker image.

    This is a sandbox substrate for Codex, not the old MAARS `code_execute`
    tool path. The image is expected to contain a working Codex CLI.
    """

    name = "docker"

    def __init__(
        self,
        *,
        image: str | None,
        docker_bin: str = "docker",
        container_codex_bin: str = "codex",
        container_workspace_dir: str = "/workspace",
        gpus: str | None = None,
    ):
        self.image = (image or "").strip()
        self.docker_bin = docker_bin
        self.container_codex_bin = container_codex_bin
        self.container_workspace_dir = container_workspace_dir.rstrip("/") or "/workspace"
        self.gpus = (gpus or "").strip() or None

    def validate(self) -> None:
        if not self.image:
            raise RuntimeError("MAARS_CODEX_DOCKER_IMAGE must be set when MAARS_CODEX_SANDBOX_PROVIDER=docker")
        if not shutil.which(self.docker_bin):
            raise RuntimeError(f"Docker sandbox provider is enabled, but '{self.docker_bin}' was not found on PATH.")

    def prepare(self, context: TaskContext, schema_filename: str) -> CodexSandboxSession:
        context.workspace_dir.mkdir(parents=True, exist_ok=True)
        context.artifacts_dir.mkdir(parents=True, exist_ok=True)
        return DockerCodexSandboxSession(
            image=self.image,
            docker_bin=self.docker_bin,
            gpus=self.gpus,
            env_names=(
                "CODEX_API_KEY",
                "OPENAI_API_KEY",
            ),
            host_workspace_dir=context.workspace_dir,
            host_artifacts_dir=context.artifacts_dir,
            container_codex_bin=self.container_codex_bin,
            container_workspace_dir=self.container_workspace_dir,
            schema_filename=schema_filename,
        )


def create_codex_sandbox_provider(
    *,
    provider: str,
    codex_bin: str,
    docker_image: str | None = None,
    docker_bin: str = "docker",
    docker_codex_bin: str = "codex",
    docker_gpus: str | None = None,
) -> CodexSandboxProvider:
    normalized = provider.strip().lower()
    if normalized == "local":
        return LocalCodexSandboxProvider(codex_bin=codex_bin)
    if normalized == "docker":
        return DockerCodexSandboxProvider(
            image=docker_image,
            docker_bin=docker_bin,
            container_codex_bin=docker_codex_bin,
            gpus=docker_gpus,
        )
    raise ValueError(f"Unsupported Codex sandbox provider: {provider!r}")
