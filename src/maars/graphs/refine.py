"""Refine StateGraph — Explorer <-> Critic adversarial loop.

State maintenance semantics:

- Critic returns an *incremental* CritiqueFeedback each round
  (resolved ids + new_issues), NOT the full unresolved list.
- critic_node applies the delta: next = (prior - resolved) + new_issues.
- passed is computed by Python from the resulting list (no blockers,
  at most 1 major) — not by the Critic LLM.

This matches the original MAARS IterationState design and avoids the
"LLM has to re-list every unresolved issue each round and occasionally
drops items" failure mode of the earlier snapshot variant.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from maars.agents.critic import critique_draft
from maars.agents.explorer import draft_proposal
from maars.config import REFINE_MAX_ROUND
from maars.state import Issue, RefineState


def explorer_node(state: RefineState) -> dict:
    """Draft or revise the research proposal."""
    draft = draft_proposal(
        raw_idea=state["raw_idea"],
        prior_draft=state.get("draft"),
        prior_issues=state.get("issues"),
    )
    return {
        "draft": draft,
        "round": state.get("round", 0) + 1,
    }


def critic_node(state: RefineState) -> dict:
    """Review the current draft and merge incremental feedback into state.

    Critic only reports a delta (resolved ids + new issues). This node:
    1. Applies the delta to obtain the new canonical unresolved list
    2. Computes passed from the resulting list (Python rule, not LLM)
    """
    prior_issues: list[Issue] = state.get("issues") or []
    feedback = critique_draft(state["draft"], prior_issues=prior_issues)

    resolved_set = set(feedback.resolved)
    carried = [i for i in prior_issues if i.id not in resolved_set]
    next_issues = carried + list(feedback.new_issues)

    blocker_count = sum(1 for i in next_issues if i.severity == "blocker")
    major_count = sum(1 for i in next_issues if i.severity == "major")
    passed = blocker_count == 0 and major_count <= 1

    return {
        "issues": next_issues,
        "resolved": feedback.resolved,  # appended via state reducer
        "passed": passed,
    }


def should_continue(state: RefineState) -> str:
    """Decide whether to loop back to Explorer or end."""
    if state.get("passed", False):
        return END
    if state.get("round", 0) >= REFINE_MAX_ROUND:
        return END
    return "explorer"


def build_refine_graph(checkpointer):
    """Build and compile the Refine StateGraph with the given checkpointer.

    The caller owns the checkpointer lifetime (typically an async context
    manager wrapping AsyncSqliteSaver for streaming via astream_events).
    """
    workflow = StateGraph(RefineState)
    workflow.add_node("explorer", explorer_node)
    workflow.add_node("critic", critic_node)

    workflow.add_edge(START, "explorer")
    workflow.add_edge("explorer", "critic")
    workflow.add_conditional_edges("critic", should_continue)

    return workflow.compile(checkpointer=checkpointer)
