"""Research runtime data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, TypedDict


@dataclass(frozen=True)
class ArtifactRef:
    """A file produced by a research task."""

    path: str
    size_bytes: int | None = None
    kind: str = "file"


@dataclass(frozen=True)
class TaskRecord:
    """Stable, provider-neutral description of one research task."""

    id: str
    description: str
    dependencies: tuple[str, ...] = ()
    status: str = "pending"
    summary: str = ""
    batch: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskRecord":
        return cls(
            id=str(data.get("id", "")),
            description=str(data.get("description", "")),
            dependencies=tuple(str(d) for d in data.get("dependencies", []) or []),
            status=str(data.get("status", "pending")),
            summary=str(data.get("summary", "")),
            batch=data.get("batch"),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "description": self.description,
            "dependencies": list(self.dependencies),
            "status": self.status,
        }
        if self.summary:
            result["summary"] = self.summary
        if self.batch is not None:
            result["batch"] = self.batch
        return result


@dataclass(frozen=True)
class RuntimeEvent:
    """Provider-neutral event emitted by runtime nodes and executors."""

    type: str
    message: str = ""
    stage: str = ""
    task_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResearchGraphResult:
    """Final output returned by the Research LangGraph runtime."""

    output: str
    state: dict[str, Any] = field(default_factory=dict)


class ResearchGraphState(TypedDict, total=False):
    """State carried through the research workflow graph."""

    idea: str
    phase: str
    iteration: int
    loop_done: bool
    failed: bool
    strategy_update: str
    output: str


class ResearchGraphNodes(Protocol):
    """Node contract consumed by the research runtime."""

    async def calibrate(self, state: ResearchGraphState) -> dict[str, Any]:
        ...

    async def initialize_loop(self, state: ResearchGraphState) -> dict[str, Any]:
        ...

    async def prepare_strategy(self, state: ResearchGraphState) -> dict[str, Any]:
        ...

    async def prepare_decomposition(self, state: ResearchGraphState) -> dict[str, Any]:
        ...

    async def execute_tasks(self, state: ResearchGraphState) -> dict[str, Any]:
        ...

    async def evaluate_round(self, state: ResearchGraphState) -> dict[str, Any]:
        ...

    async def summarize_results(self, state: ResearchGraphState) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class TaskCycleResult:
    """Final outcome of one task execute/verify cycle."""

    task: dict[str, Any]
    result: str
    review: str = ""
    passed: bool = False
    needs_redecompose: bool = False
    failed: bool = False
    attempts: int = 1
    state: dict[str, Any] = field(default_factory=dict)


class TaskCycleState(TypedDict, total=False):
    """State carried through one task execution graph."""

    task: dict[str, Any]
    task_id: str
    call_id: str
    prior_attempt: str
    dep_summaries: dict[str, str]
    attempt: int
    result: str
    review: str
    passed: bool
    redecompose: bool
    failed: bool


class TaskCycleNodes(Protocol):
    """Node contract consumed by the task execution runtime."""

    async def execute_attempt(self, state: TaskCycleState) -> dict[str, Any]:
        ...

    async def verify_attempt(self, state: TaskCycleState) -> dict[str, Any]:
        ...

    async def prepare_retry(self, state: TaskCycleState) -> dict[str, Any]:
        ...
