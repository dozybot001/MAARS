"""Agno mode: pipeline stages + AgnoClient.

Supports multiple model providers (Google, Anthropic, OpenAI) via config.
"""

from agno.tools.arxiv import ArxivTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.wikipedia import WikipediaTools

from backend.agno.tools import create_db_tools, create_docker_tools
from backend.agno.stages import RefineStage, WriteStage
from backend.agno.models import create_model
from backend.llm.agno_client import AgnoClient
from backend.pipeline.research import ResearchStage


def create_agno_stages(
    model_provider: str = "google",
    model_id: str = "gemini-2.0-flash",
    api_key: str = "",
    db=None,
    max_iterations: int = 1,
) -> dict:
    """Assemble pipeline stages with AgnoClient.

    All prompts are provided by the pipeline (system messages).
    AgnoClient is a pure adapter — no baked-in instructions.
    """
    model = create_model(model_provider, model_id, api_key)

    db_tools = create_db_tools(db) if db else []
    docker_tools = create_docker_tools(db) if db else []
    # docker_tools = [code_execute, list_artifacts]
    list_artifacts = docker_tools[1:] if len(docker_tools) > 1 else []

    # Agno-native research tools (no API keys needed)
    research_tools = [DuckDuckGoTools(), ArxivTools(), WikipediaTools()]

    refine_client = AgnoClient(
        model=model,
        tools=research_tools,
    )

    research_client = AgnoClient(
        model=model,
        tools=db_tools + docker_tools + research_tools,
    )

    write_client = AgnoClient(
        model=model,
        tools=db_tools + list_artifacts + research_tools,
    )

    return {
        "refine": RefineStage(llm_client=refine_client, db=db),
        "research": ResearchStage(
            llm_client=research_client, db=db,
            max_iterations=max_iterations,
        ),
        "write": WriteStage(llm_client=write_client, db=db),
    }
