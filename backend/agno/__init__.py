"""Stage factory: assembles all pipeline stages.

Refine: multi-agent via Agno Team (coordinate mode).
Research: agentic workflow via AgnoClient.
Write: multi-agent via Agno Team (coordinate mode).
"""

from agno.tools.arxiv import ArxivTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.wikipedia import WikipediaTools

from backend.agno.tools import create_db_tools, create_docker_tools
from backend.agno.models import create_model
from backend.agno.client import AgnoClient
from backend.pipeline.research import ResearchStage
from backend.team.write import WriteStage
from backend.team.refine import RefineStage


def create_agno_stages(
    model_provider: str = "google",
    model_id: str = "gemini-2.0-flash",
    api_key: str = "",
    db=None,
    max_iterations: int = 1,
    stage_configs: dict[str, tuple[str, str, str]] | None = None,
) -> dict:
    """Assemble pipeline stages.

    Refine: Agno Team (multi-agent coordinate mode).
    Research: AgnoClient (single-client agentic workflow).
    Write: Agno Team (multi-agent coordinate mode).

    Args:
        stage_configs: Optional per-stage overrides.
            {"refine": (provider, model_id, api_key), ...}
            Falls back to global provider/model/api_key if not provided.
    """
    def _model_for(stage_name: str):
        if stage_configs and stage_name in stage_configs:
            p, m, k = stage_configs[stage_name]
            return create_model(p, m, k)
        return create_model(model_provider, model_id, api_key)

    refine_model = _model_for("refine")
    research_model = _model_for("research")
    write_model = _model_for("write")

    db_tools = create_db_tools(db) if db else []
    docker_tools = create_docker_tools(db) if db else []
    list_artifacts = docker_tools[1:] if len(docker_tools) > 1 else []

    research_tools = [DuckDuckGoTools(), ArxivTools(), WikipediaTools()]

    # Research: single-client workflow (AgnoClient)
    research_client = AgnoClient(
        model=research_model,
        tools=db_tools + docker_tools + research_tools,
    )

    # Write: Agno Team (Leader + Writer + Reviewer)
    writer_tools = db_tools + list_artifacts + research_tools

    return {
        "refine": RefineStage(model=refine_model, explorer_tools=research_tools, db=db),
        "research": ResearchStage(
            llm_client=research_client, db=db,
            max_iterations=max_iterations,
        ),
        "write": WriteStage(
            model=write_model,
            writer_tools=writer_tools,
            db=db,
        ),
    }
