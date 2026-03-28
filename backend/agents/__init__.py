"""Multi-agent architecture for MAARS.

Provides ``create_agent_session()`` factory that builds an AgentSession
with Orchestrator, Scholar, and Critic agents fully wired.

Activated via MAARS_ARCHITECTURE=agents.
"""

from __future__ import annotations

from backend.agents.session import AgentSession
from backend.agents.scholar import create_scholar
from backend.agents.critic import create_critic
from backend.agents.orchestrator import create_orchestrator
from backend.db import ResearchDB
from backend.llm.client import LLMClient


def create_agent_session(
    orchestrator_client: LLMClient,
    worker_client: LLMClient,
    scholar_client: LLMClient,
    critic_client: LLMClient,
) -> AgentSession:
    """Build a fully wired AgentSession.

    Each agent gets its own LLMClient (which may or may not have tools,
    depending on the mode). The Orchestrator's tools are async functions
    stored on ``orchestrator._tools`` — the caller is responsible for
    wiring them into the LLMClient's tool system if the framework
    requires upfront registration (ADK, Agno).

    Args:
        orchestrator_client: LLMClient for Orchestrator reasoning.
        worker_client: LLMClient for ephemeral workers (may have code_execute etc.).
        scholar_client: LLMClient for Scholar (should have search tools).
        critic_client: LLMClient for Critic (no tools needed, pure reasoning).

    Returns:
        Configured AgentSession ready to start().
    """
    session = AgentSession()
    db = session.db
    broadcast = session._broadcast

    scholar = create_scholar(scholar_client, db=db, broadcast=broadcast)
    critic = create_critic(critic_client, db=db, broadcast=broadcast)
    orchestrator = create_orchestrator(
        llm_client=orchestrator_client,
        worker_client=worker_client,
        scholar=scholar,
        critic=critic,
        db=db,
        broadcast=broadcast,
    )

    session.configure(
        orchestrator=orchestrator,
        scholar=scholar,
        critic=critic,
    )

    return session


__all__ = ["AgentSession", "create_agent_session"]
