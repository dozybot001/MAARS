"""Orchestrator agent — central decision-maker for multi-agent MAARS.

Runs as a single ReAct session with tools for consulting Scholar/Critic,
decomposing tasks, dispatching workers, and writing the paper.
The workflow is guided by the system prompt but not hardcoded — the
Orchestrator decides what to do and when.
"""

from __future__ import annotations

import json
from typing import Callable

from backend.agents.base import PersistentAgent
from backend.agents.tools import create_inter_agent_tools
from backend.agents.worker import dispatch_workers
from backend.db import ResearchDB
from backend.llm.client import LLMClient
from backend.pipeline.decompose import decompose
from backend.utils import parse_json_fenced

_ORCHESTRATOR_SYSTEM = """\
You are the Orchestrator of MAARS, a multi-agent automated research system.
You coordinate an entire research session from idea to paper.

## Your Agents

- **Scholar**: Persistent knowledge agent. Searches literature, accumulates domain knowledge.
  Call ``consult_scholar(question)`` to ask questions or request literature review.
  Scholar remembers earlier conversations — build on prior findings.

- **Critic**: Adversarial reviewer. Gets stricter over time.
  Call ``request_critique(content, context)`` to get quality reviews.
  Critic returns verdicts: pass / revise / reject.

## Your Workflow

Follow this general flow, but adapt as needed:

### 1. REFINE (call emit_phase("refine"))
- Consult Scholar to survey the research landscape
- Based on Scholar's findings, formulate a research direction
- Submit direction to Critic for validation
- Iterate until Critic passes the direction
- Save the refined idea

### 2. RESEARCH (call emit_phase("research"))
- Decompose the refined idea into atomic tasks (call decompose_tasks)
- Dispatch workers to execute tasks (call dispatch_workers)
- For important results, request Critic review
- If Critic rejects, revise and re-dispatch
- After all tasks complete, ask Scholar for cross-task synthesis
- If Scholar finds contradictions, dispatch additional tasks

### 3. WRITE (call emit_phase("write"))
- Compile all task results into a research paper
- Submit paper to Critic for peer review
- Revise based on Critic feedback until Critic passes

## Rules

- ALWAYS call emit_phase() when transitioning between phases
- ALWAYS save results to DB (use save_refined_idea, task outputs are saved by workers)
- Consult Scholar BEFORE making major decisions — don't rely on your own knowledge alone
- Submit ALL important outputs to Critic — direction, key results, and final paper
- If Critic says "reject", you MUST change approach (not just retry the same thing)
- Be efficient with token usage: ask Scholar/Critic concise questions, not dump entire outputs
- You may revisit earlier phases if Critic identifies fundamental problems

全文使用中文。"""


def create_orchestrator(
    llm_client: LLMClient,
    worker_client: LLMClient,
    scholar: PersistentAgent,
    critic: PersistentAgent,
    db: ResearchDB,
    broadcast: Callable,
) -> PersistentAgent:
    """Create the Orchestrator agent with its full tool set.

    Args:
        llm_client: LLMClient for the Orchestrator's own reasoning.
        worker_client: LLMClient for ephemeral workers (may have different tools).
        scholar: The Scholar agent instance.
        critic: The Critic agent instance.
        db: ResearchDB for persistence.
        broadcast: SSE broadcast callback.

    Returns:
        Configured PersistentAgent with orchestration tools.
    """
    # Phase 2 tools: consult_scholar, request_critique, emit_phase
    inter_agent_tools = create_inter_agent_tools(scholar, critic, db, broadcast)

    # Phase 3 tools: decompose, dispatch_workers, save_refined_idea

    async def decompose_tasks(idea: str) -> str:
        """Decompose a research idea into atomic tasks with a dependency DAG.

        Args:
            idea: The research idea or sub-problem to decompose.

        Returns:
            JSON string of flat task list: [{"id", "description", "dependencies"}, ...]
        """
        broadcast({
            "stage": "research",
            "type": "chunk",
            "data": {"text": "Decompose", "call_id": "Decompose", "label": True},
        })

        flat_tasks, tree = await decompose(
            idea=idea,
            llm_client=llm_client,
            max_depth=10,
            stream_callback=lambda t, d: broadcast({
                "stage": "research", "type": t, "data": d,
            }),
        )

        # Save to DB
        tasks_json = json.dumps(flat_tasks, indent=2, ensure_ascii=False)
        db.save_plan(tasks_json, tree)

        return tasks_json

    async def run_workers(tasks_json: str) -> str:
        """Dispatch ephemeral workers to execute research tasks in parallel.
        Tasks are executed in topological order respecting dependencies.

        Args:
            tasks_json: JSON string of task list from decompose_tasks().

        Returns:
            Summary of completed tasks with brief excerpts.
        """
        return await dispatch_workers(
            tasks_json=tasks_json,
            llm_client=worker_client,
            db=db,
            broadcast=broadcast,
            scholar=scholar,
        )

    async def save_refined_idea(text: str) -> str:
        """Save the refined research idea to DB.

        Args:
            text: The complete refined research idea/proposal.

        Returns:
            Confirmation message.
        """
        db.save_refined_idea(text)
        broadcast({"stage": "refine", "type": "state", "data": "completed"})
        return "Refined idea saved."

    async def save_paper(text: str) -> str:
        """Save the final research paper to DB.

        Args:
            text: The complete paper in markdown.

        Returns:
            Confirmation message.
        """
        db.save_paper(text)
        broadcast({"stage": "write", "type": "state", "data": "completed"})
        return "Paper saved."

    async def read_all_task_outputs() -> str:
        """Read all completed task outputs from DB.

        Returns:
            Concatenated task outputs with headers.
        """
        tasks = db.list_completed_tasks()
        if not tasks:
            return "No completed tasks."
        parts = []
        for info in tasks:
            output = db.get_task_output(info["id"])
            parts.append(f"## Task [{info['id']}]\n\n{output}")
        return "\n\n---\n\n".join(parts)

    # Combine all tools
    all_tools = inter_agent_tools + [
        decompose_tasks,
        run_workers,
        save_refined_idea,
        save_paper,
        read_all_task_outputs,
    ]

    orchestrator = PersistentAgent(
        name="orchestrator",
        system_prompt=_ORCHESTRATOR_SYSTEM,
        llm_client=llm_client,
        db=db,
        broadcast=broadcast,
    )

    # NOTE: The actual tool registration depends on the LLMClient implementation.
    # For ADK: tools are passed to AgentClient constructor.
    # For Agno: tools are passed to AgnoClient constructor.
    # For Gemini/Mock: tools are not supported (text-only mode).
    #
    # The tool functions are stored here for the factory to wire into the
    # appropriate client. See __init__.py for the wiring logic.
    orchestrator._tools = all_tools

    return orchestrator
