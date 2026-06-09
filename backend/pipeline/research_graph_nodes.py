"""Pipeline adapter for the LangGraph research runtime."""

from __future__ import annotations

from typing import Any

from backend.core.research import ResearchGraphState


class ResearchStageGraphNodes:
    """Expose ResearchStage operations through the runtime node protocol."""

    def __init__(self, stage: Any):
        self.stage = stage

    async def calibrate(self, state: ResearchGraphState) -> dict[str, Any]:
        idea = state["idea"]
        await self.stage._calibrate_once(idea)
        return {"phase": "calibrated"}

    async def initialize_loop(self, state: ResearchGraphState) -> dict[str, Any]:
        return self.stage._initialize_research_loop()

    async def prepare_strategy(self, state: ResearchGraphState) -> dict[str, Any]:
        await self.stage._prepare_strategy_round(
            state["idea"],
            int(state.get("iteration", 0)),
        )
        return {"phase": "strategy_completed"}

    async def prepare_decomposition(self, state: ResearchGraphState) -> dict[str, Any]:
        await self.stage._prepare_decomposition_round(
            state["idea"],
            int(state.get("iteration", 0)),
        )
        return {"phase": "decomposition_completed"}

    async def execute_tasks(self, state: ResearchGraphState) -> dict[str, Any]:
        failed = await self.stage._execute_task_round(
            int(state.get("iteration", 0)),
        )
        return {"phase": "execution_completed", "failed": failed}

    async def evaluate_round(self, state: ResearchGraphState) -> dict[str, Any]:
        return await self.stage._evaluate_research_round(
            state["idea"],
            int(state.get("iteration", 0)),
        )

    async def summarize_results(self, state: ResearchGraphState) -> dict[str, Any]:
        return {
            "phase": "summarized",
            "output": self.stage._build_final_output(),
        }
