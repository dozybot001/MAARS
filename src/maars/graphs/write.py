"""Write StateGraph — Writer <-> Reviewer adversarial loop.

State maintenance semantics match Refine: Reviewer returns an incremental
ReviewFeedback (resolved + new_issues), reviewer_node applies the delta
and computes passed via Python (not LLM). See graphs/refine.py for the
original rationale.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from maars.agents.reviewer import review_paper
from maars.agents.writer import write_paper
from maars.config import WRITE_MAX_ROUND
from maars.state import Issue, WriteState


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
    """Review the current paper draft and merge incremental feedback.

    Symmetric to critic_node in graphs/refine.py: the Reviewer reports a
    delta (resolved ids + new issues), this node applies the delta to
    obtain the new canonical issue list, and passed is computed by Python.
    """
    prior_issues: list[Issue] = state.get("issues") or []
    feedback = review_paper(state["draft"], prior_issues=prior_issues)

    resolved_set = set(feedback.resolved)
    carried = [i for i in prior_issues if i.id not in resolved_set]
    next_issues = carried + list(feedback.new_issues)

    blocker_count = sum(1 for i in next_issues if i.severity == "blocker")
    major_count = sum(1 for i in next_issues if i.severity == "major")
    passed = blocker_count == 0 and major_count <= 1

    return {
        "issues": next_issues,
        "resolved": feedback.resolved,
        "passed": passed,
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
