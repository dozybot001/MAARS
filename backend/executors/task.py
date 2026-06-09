"""Provider-neutral task execution contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from backend.core.research import ArtifactRef, RuntimeEvent


@dataclass(frozen=True)
class TaskContext:
    """All inputs an executor needs to run one atomic research task."""

    session_id: str
    task_id: str
    description: str
    workspace_dir: Path
    artifacts_dir: Path
    dependencies: tuple[str, ...] = ()
    dependency_summaries: dict[str, str] = field(default_factory=dict)
    prior_attempt: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_task_dict(self) -> dict[str, Any]:
        return {
            "id": self.task_id,
            "description": self.description,
            "dependencies": list(self.dependencies),
        }


@dataclass(frozen=True)
class TaskExecutionResult:
    """Structured result returned by a task executor."""

    task_id: str
    markdown: str
    summary: str
    artifacts: tuple[ArtifactRef, ...] = ()
    best_score: dict[str, Any] | None = None
    events: tuple[RuntimeEvent, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict)


class TaskExecutor(Protocol):
    """Runs one atomic research task and returns a structured result."""

    async def run(self, context: TaskContext) -> TaskExecutionResult:
        ...
