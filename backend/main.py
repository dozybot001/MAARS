from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.routes import pipeline as pipeline_routes
from backend.routes import events as event_routes

app = FastAPI(title="MAARS", version="0.1.0")

# --- Architecture selection ---
# "pipeline" (default) = legacy orchestrated pipeline
# "agents" = multi-agent (Orchestrator + Scholar + Critic)

if settings.architecture == "agents":
    from backend.agents import create_agent_session

    if settings.llm_mode in ("agent", "adk"):
        from backend.llm.agent_client import AgentClient
        try:
            from google.adk.tools import google_search, url_context
            _search_tools = [google_search, url_context]
        except (ImportError, AttributeError):
            _search_tools = []

        session = create_agent_session(
            orchestrator_client=AgentClient(
                instruction="", tools=[], model=settings.gemini_model,
            ),
            worker_client=AgentClient(
                instruction="", tools=_search_tools,
                model=settings.gemini_model,
            ),
            scholar_client=AgentClient(
                instruction="", tools=_search_tools, model=settings.gemini_model,
            ),
            critic_client=AgentClient(
                instruction="", tools=[], model=settings.gemini_model,
            ),
        )
    elif settings.llm_mode == "agno":
        from backend.llm.agno_client import AgnoClient
        from backend.agno.models import create_model
        _model = create_model(
            settings.agno_model_provider,
            settings.agno_model_id or settings.gemini_model,
        )
        try:
            from agno.tools.duckduckgo import DuckDuckGoTools
            from agno.tools.arxiv import ArxivTools
            _agno_search = [DuckDuckGoTools(), ArxivTools()]
        except ImportError:
            _agno_search = []

        session = create_agent_session(
            orchestrator_client=AgnoClient(instruction="", model=_model, tools=[]),
            worker_client=AgnoClient(instruction="", model=_model, tools=_agno_search),
            scholar_client=AgnoClient(instruction="", model=_model, tools=_agno_search),
            critic_client=AgnoClient(instruction="", model=_model, tools=[]),
        )
    elif settings.llm_mode == "gemini":
        from backend.llm.gemini_client import GeminiClient
        _gc = lambda: GeminiClient(api_key=settings.google_api_key, model=settings.gemini_model)
        session = create_agent_session(
            orchestrator_client=_gc(),
            worker_client=_gc(),
            scholar_client=_gc(),
            critic_client=_gc(),
        )
    else:
        from backend.mock.client import MockClient
        _mc = lambda: MockClient(
            responses=["Mock agent response."], chunk_delay=settings.mock_chunk_delay,
        )
        session = create_agent_session(
            orchestrator_client=_mc(),
            worker_client=_mc(),
            scholar_client=_mc(),
            critic_client=_mc(),
        )

    app.state.orchestrator = session

else:
    # Legacy pipeline mode — unchanged
    from backend.pipeline.orchestrator import PipelineOrchestrator

    orchestrator = PipelineOrchestrator()

    if settings.llm_mode in ("agent", "adk"):
        from backend.agent import create_agent_stages
        stages = create_agent_stages(
            api_key=settings.google_api_key,
            model=settings.gemini_model,
            db=orchestrator.db,
            max_iterations=settings.research_max_iterations,
        )
    elif settings.llm_mode == "agno":
        from backend.agno import create_agno_stages
        stages = create_agno_stages(
            model_provider=settings.agno_model_provider,
            model_id=settings.agno_model_id or settings.gemini_model,
            api_key=settings.google_api_key,
            db=orchestrator.db,
            max_iterations=settings.research_max_iterations,
        )
    elif settings.llm_mode == "gemini":
        from backend.gemini import create_gemini_stages
        stages = create_gemini_stages(
            api_key=settings.google_api_key,
            model=settings.gemini_model,
            db=orchestrator.db,
            max_iterations=settings.research_max_iterations,
        )
    else:
        from backend.mock import create_mock_stages
        stages = create_mock_stages(
            chunk_delay=settings.mock_chunk_delay,
            db=orchestrator.db,
            max_iterations=settings.research_max_iterations,
        )

    orchestrator.stages.update(stages)
    orchestrator._wire_broadcast()
    app.state.orchestrator = orchestrator

# --- Routes ---
app.include_router(pipeline_routes.router)
app.include_router(event_routes.router)

# --- Serve frontend static files ---
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
