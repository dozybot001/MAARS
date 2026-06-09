"""Pipeline adapter for the LangGraph task execution runtime."""

from __future__ import annotations

from typing import Any

from backend.core.research import TaskCycleState


class ResearchTaskCycleNodes:
    """Expose ResearchStage task operations through the task runtime protocol."""

    def __init__(self, stage: Any):
        self.stage = stage

    async def execute_attempt(self, state: TaskCycleState) -> dict[str, Any]:
        attempt = int(state.get("attempt", 1) or 1)
        task = state["task"]
        metadata = {}
        if attempt > 1:
            metadata = {
                "previous_result": str(state.get("result", "")),
                "retry_review": str(state.get("review", "")),
            }
        execution = await self.stage._execute_once(
            task,
            prior_attempt=str(state.get("prior_attempt", "")),
            dep_summaries=dict(state.get("dep_summaries", {}) or {}),
            metadata=metadata,
        )
        self.stage._record_execution_result(execution)
        return {
            "attempt": attempt,
            "result": execution.markdown,
            "passed": False,
            "redecompose": False,
            "failed": False,
        }

    async def verify_attempt(self, state: TaskCycleState) -> dict[str, Any]:
        task = state["task"]
        passed, review, redecompose = await self.stage._verify_task(
            task,
            str(state.get("result", "")),
            str(state.get("task_id", task.get("id", ""))),
            str(state.get("call_id", "")),
        )
        return {
            "passed": passed,
            "review": review,
            "redecompose": redecompose,
        }

    async def prepare_retry(self, state: TaskCycleState) -> dict[str, Any]:
        next_attempt = int(state.get("attempt", 1) or 1) + 1
        task_id = str(state.get("task_id", ""))
        self.stage._send(status="retrying", task_id=task_id)
        return {
            "attempt": next_attempt,
            "passed": False,
            "redecompose": False,
            "failed": False,
        }
