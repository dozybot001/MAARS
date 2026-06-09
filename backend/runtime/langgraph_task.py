"""LangGraph runtime for one research task execution cycle."""

from __future__ import annotations

from typing import Any

from backend.core.research import TaskCycleNodes, TaskCycleResult, TaskCycleState


class LangGraphTaskRuntime:
    """Run execute -> verify -> retry routing for one task."""

    def __init__(self, nodes: TaskCycleNodes, max_attempts: int = 2):
        self.nodes = nodes
        self.max_attempts = max(1, max_attempts)

    async def run(
        self,
        task: dict[str, Any],
        task_id: str,
        call_id: str,
        prior_attempt: str = "",
        dep_summaries: dict[str, str] | None = None,
    ) -> TaskCycleResult:
        graph = self._compile_graph()
        state = await graph.ainvoke({
            "task": task,
            "task_id": task_id,
            "call_id": call_id,
            "prior_attempt": prior_attempt,
            "dep_summaries": dep_summaries or {},
            "attempt": 1,
            "passed": False,
            "redecompose": False,
            "failed": False,
        })
        passed = bool(state.get("passed"))
        needs_redecompose = bool(state.get("redecompose"))
        failed = bool(state.get("failed")) or not (passed or needs_redecompose)
        return TaskCycleResult(
            task=task,
            result=str(state.get("result", "")),
            review=str(state.get("review", "")),
            passed=passed,
            needs_redecompose=needs_redecompose,
            failed=failed,
            attempts=int(state.get("attempt", 1) or 1),
            state=dict(state),
        )

    def _compile_graph(self):
        try:
            from langgraph.graph import END, START, StateGraph
        except ImportError as exc:
            raise RuntimeError(
                "LangGraph runtime is not installed. Run `pip install -r requirements.txt`."
            ) from exc

        graph = StateGraph(TaskCycleState)
        graph.add_node("execute_attempt", self.nodes.execute_attempt)
        graph.add_node("verify_attempt", self.nodes.verify_attempt)
        graph.add_node("prepare_retry", self.nodes.prepare_retry)
        graph.add_node("mark_failed", _mark_failed)
        graph.add_edge(START, "execute_attempt")
        graph.add_edge("execute_attempt", "verify_attempt")
        graph.add_conditional_edges(
            "verify_attempt",
            lambda state: _route_after_verify(state, self.max_attempts),
            {
                "complete": END,
                "retry": "prepare_retry",
                "failed": "mark_failed",
            },
        )
        graph.add_edge("prepare_retry", "execute_attempt")
        graph.add_edge("mark_failed", END)
        return graph.compile()


def _route_after_verify(state: TaskCycleState, max_attempts: int) -> str:
    if state.get("passed") or state.get("redecompose"):
        return "complete"
    if int(state.get("attempt", 1) or 1) < max_attempts:
        return "retry"
    return "failed"


def _mark_failed(state: TaskCycleState) -> dict[str, bool]:
    return {"failed": True}
