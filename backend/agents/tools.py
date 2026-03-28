"""Inter-agent tools — given to the Orchestrator as callable functions.

Each tool closes over the relevant agent/resource and is exposed as
a plain Python function that the Orchestrator's LLMClient can invoke.

These tools are the communication layer between agents: the Orchestrator
calls ``consult_scholar()`` which internally runs ``scholar.invoke()``.
No message bus, no RPC — just function calls.
"""

from __future__ import annotations

import asyncio
import json
from typing import Callable

from backend.agents.base import PersistentAgent
from backend.db import ResearchDB
from backend.utils import parse_json_fenced


def create_inter_agent_tools(
    scholar: PersistentAgent,
    critic: PersistentAgent,
    db: ResearchDB,
    broadcast: Callable,
) -> list:
    """Build the tool list for the Orchestrator agent.

    Returns plain Python functions (sync wrappers around async agent calls)
    that can be registered with any LLMClient tool system (ADK, Agno, etc.).
    """

    # Track reviews for Critic strictness escalation
    _review_counter = 0

    # ------------------------------------------------------------------
    # Scholar tools
    # ------------------------------------------------------------------

    async def consult_scholar(question: str) -> str:
        """Ask the Scholar agent a question. Scholar accumulates knowledge
        across calls — later questions benefit from earlier research.

        Use this for: literature review, domain questions, citation lookup,
        cross-task synthesis, knowledge gap identification.

        Args:
            question: What you want the Scholar to research or answer.

        Returns:
            Scholar's response with findings and references.
        """
        broadcast({
            "stage": "research",
            "type": "agent_message",
            "data": {"from": "orchestrator", "to": "scholar", "summary": question[:200]},
        })

        response = await scholar.invoke(question)

        # Persist knowledge entry
        entries = db.list_knowledge()
        entry_id = f"k_{len(entries) + 1:03d}"
        db.save_knowledge(entry_id, f"## Q: {question}\n\n{response}")

        return response

    # ------------------------------------------------------------------
    # Critic tools
    # ------------------------------------------------------------------

    async def request_critique(content: str, context: str = "") -> str:
        """Submit content to the Critic agent for adversarial review.
        The Critic gets stricter over time as more results are reviewed.

        Use this for: research direction validation, task result review,
        paper draft peer review.

        Args:
            content: The content to review (result text, paper draft, etc.).
            context: Optional context (task description, review focus, etc.).

        Returns:
            Critic's review ending with a JSON verdict:
            {"verdict": "pass|revise|reject", "issues": [...]}
        """
        nonlocal _review_counter
        _review_counter += 1

        prompt_parts = []
        if context:
            prompt_parts.append(f"## Review Context\n{context}")
        prompt_parts.append(f"## Content to Review\n{content}")
        prompt_parts.append(
            f"\n(This is review #{_review_counter}. "
            f"You have reviewed {_review_counter - 1} items before this. "
            f"Maintain or raise your standards.)"
        )

        broadcast({
            "stage": "research",
            "type": "agent_message",
            "data": {"from": "orchestrator", "to": "critic", "summary": f"Review #{_review_counter}"},
        })

        response = await critic.invoke("\n\n".join(prompt_parts))

        # Persist review
        verdict_data = parse_json_fenced(response, fallback={"verdict": "pass", "issues": []})
        review_id = f"r_{_review_counter:03d}"
        db.save_review(review_id, {
            "review_id": review_id,
            "context": context[:200] if context else "",
            "verdict": verdict_data.get("verdict", "pass"),
            "issues": verdict_data.get("issues", []),
            "full_response": response,
        })

        return response

    # ------------------------------------------------------------------
    # Phase management
    # ------------------------------------------------------------------

    async def emit_phase(phase: str) -> str:
        """Signal a phase transition to the frontend UI.
        Valid phases: "refine", "research", "write".

        Args:
            phase: The phase name to transition to.

        Returns:
            Confirmation message.
        """
        if phase in ("refine", "research", "write"):
            broadcast({"stage": phase, "type": "state", "data": "running"})
        return f"Phase set to: {phase}"

    return [consult_scholar, request_critique, emit_phase]
