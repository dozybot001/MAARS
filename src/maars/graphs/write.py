"""Write StateGraph — Writer <-> Reviewer adversarial loop."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from maars.agents.reviewer import review_paper
from maars.agents.writer import write_paper
from maars.config import WRITE_MAX_ROUND
from maars.state import WriteState


def writer_node(state: WriteState) -> dict:
    """Write or revise the research paper draft."""
    draft = write_paper(
        refined_idea=state["refined_idea"],
        artifacts_dir=state["artifacts_dir"],
        prior_draft=state.get("draft"),
        prior_issues=state.get("issues"),
    )
    return {
        "draft": draft,
        "round": state.get("round", 0) + 1,
    }


def reviewer_node(state: WriteState) -> dict:
    """Review the current paper draft and return structured review."""
    result = review_paper(
        draft=state["draft"],
        prior_issues=state.get("issues"),
    )
    return {
        "issues": result.issues,
        "resolved": result.resolved,
        "passed": result.passed,
    }


def should_continue(state: WriteState) -> str:
    """Decide whether to loop back to Writer or end."""
    if state.get("passed", False):
        return END
    if state.get("round", 0) >= WRITE_MAX_ROUND:
        return END
    return "writer"


def build_write_graph(checkpointer):
    """Build and compile the Write StateGraph with the given checkpointer.

    The caller owns the checkpointer lifetime (typically an async context
    manager wrapping AsyncSqliteSaver).
    """
    workflow = StateGraph(WriteState)
    workflow.add_node("writer", writer_node)
    workflow.add_node("reviewer", reviewer_node)

    workflow.add_edge(START, "writer")
    workflow.add_edge("writer", "reviewer")
    workflow.add_conditional_edges("reviewer", should_continue)

    return workflow.compile(checkpointer=checkpointer)
