"""LangGraph runtime for the MAARS research workflow."""

from __future__ import annotations

from backend.core.research import (
    ResearchGraphNodes,
    ResearchGraphResult,
    ResearchGraphState,
)


class LangGraphResearchRuntime:
    """Run the research workflow through a compiled LangGraph."""

    def __init__(self, nodes: ResearchGraphNodes):
        self.nodes = nodes

    async def run(self, idea: str) -> ResearchGraphResult:
        graph = self._compile_graph()
        state = await graph.ainvoke({"idea": idea, "phase": "start"})
        output = str(state.get("output", ""))
        return ResearchGraphResult(output=output, state=dict(state))

    def _compile_graph(self):
        try:
            from langgraph.graph import END, START, StateGraph
        except ImportError as exc:
            raise RuntimeError(
                "LangGraph runtime is not installed. Run `pip install -r requirements.txt`."
            ) from exc

        graph = StateGraph(ResearchGraphState)
        graph.add_node("calibrate", self.nodes.calibrate)
        graph.add_node("initialize_loop", self.nodes.initialize_loop)
        graph.add_node("prepare_strategy", self.nodes.prepare_strategy)
        graph.add_node("prepare_decomposition", self.nodes.prepare_decomposition)
        graph.add_node("execute_tasks", self.nodes.execute_tasks)
        graph.add_node("evaluate_round", self.nodes.evaluate_round)
        graph.add_node("summarize_results", self.nodes.summarize_results)
        graph.add_edge(START, "calibrate")
        graph.add_edge("calibrate", "initialize_loop")
        graph.add_conditional_edges(
            "initialize_loop",
            _route_after_initialize,
            {"continue": "prepare_strategy", "done": "summarize_results"},
        )
        graph.add_edge("prepare_strategy", "prepare_decomposition")
        graph.add_edge("prepare_decomposition", "execute_tasks")
        graph.add_conditional_edges(
            "execute_tasks",
            _route_after_execute,
            {"continue": "evaluate_round", "failed": "summarize_results"},
        )
        graph.add_conditional_edges(
            "evaluate_round",
            _route_after_evaluate,
            {"continue": "prepare_strategy", "done": "summarize_results"},
        )
        graph.add_edge("summarize_results", END)
        return graph.compile()


def _route_after_initialize(state: ResearchGraphState) -> str:
    return "done" if state.get("loop_done") else "continue"


def _route_after_execute(state: ResearchGraphState) -> str:
    return "failed" if state.get("failed") else "continue"


def _route_after_evaluate(state: ResearchGraphState) -> str:
    return "done" if state.get("loop_done") else "continue"
