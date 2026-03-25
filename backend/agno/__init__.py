"""Agno mode: pipeline stages + AgnoClient.

Same pipeline stages as ADK mode, but uses Agno framework for the agent loop.
Supports multiple model providers (Google, Anthropic, OpenAI) via config.
"""

from backend.agent import (
    _REFINE_INSTRUCTION, _EXECUTE_INSTRUCTION, _WRITE_INSTRUCTION,
)
from backend.agent.tools import create_db_tools, create_docker_tools
from backend.agent.stages import AgentRefineStage, AgentWriteStage
from backend.agno.models import create_model
from backend.llm.agno_client import AgnoClient
from backend.pipeline.plan import PlanStage
from backend.pipeline.execute import ExecuteStage


def create_agno_stages(
    model_provider: str = "google",
    model_id: str = "gemini-2.0-flash",
    api_key: str = "",
    db=None,
) -> dict:
    """Assemble pipeline stages with AgnoClient.

    Identical structure to ADK mode — only the client differs.
    Tools (DB, Docker) are plain Python functions, directly compatible with Agno.
    """
    model = create_model(model_provider, model_id, api_key)

    db_tools = create_db_tools(db) if db else []
    docker_tools = create_docker_tools(db) if db else []
    # docker_tools = [code_execute, list_artifacts]
    list_artifacts = docker_tools[1:] if len(docker_tools) > 1 else []

    refine_client = AgnoClient(
        instruction=_REFINE_INSTRUCTION,
        model=model,
        tools=[],  # No search tools initially; add agno.tools later
    )
    plan_client = AgnoClient(
        instruction="",
        model=model,
        tools=[],
    )

    # Same atomic definition as ADK — Agent can handle coarser tasks
    agent_atomic_def = """\
ATOMIC DEFINITION (Agent mode):
Each task is executed by an AI Agent with tools (web search, paper reading, code execution).

A task is atomic if it has a SINGLE coherent goal — e.g., "implement and test algorithm X", "conduct literature review on topic Y", "run experiment Z and analyze results".

A task should be DECOMPOSED when it contains MULTIPLE independent goals that can run in parallel. The top-level research idea almost always needs decomposition. Examples:
- A study comparing 3 algorithms → at minimum split into: literature review, implement+test each algorithm separately, comparative analysis
- A study with experiments + theory → split into: theoretical analysis, experimental implementation, result synthesis
- Any research with independent sub-experiments → split so they can execute in parallel

PREFER DECOMPOSITION for the top-level idea. An atomic top-level task means the entire research runs as a single serial session with no parallelism — this is almost never optimal."""

    execute_client = AgnoClient(
        instruction=_EXECUTE_INSTRUCTION,
        model=model,
        tools=db_tools + docker_tools,
    )
    write_client = AgnoClient(
        instruction=_WRITE_INSTRUCTION,
        model=model,
        tools=db_tools + list_artifacts,
    )

    return {
        "refine": AgentRefineStage(llm_client=refine_client, db=db),
        "plan": PlanStage(llm_client=plan_client, db=db, atomic_definition=agent_atomic_def),
        "execute": ExecuteStage(llm_client=execute_client, db=db),
        "write": AgentWriteStage(llm_client=write_client, db=db),
    }
