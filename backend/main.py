from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.pipeline.orchestrator import PipelineOrchestrator
from backend.routes import pipeline as pipeline_routes
from backend.routes import events as event_routes
from backend.routes import session as session_routes

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app):
    yield
    orch = getattr(app.state, "orchestrator", None)
    if orch:
        await orch.shutdown()


app = FastAPI(title="MAARS", version="0.1.0", lifespan=lifespan)

orchestrator = PipelineOrchestrator()

from backend.agno import create_agno_stages
stages = create_agno_stages(
    model_id=settings.google_model,
    api_key=settings.google_api_key,
    db=orchestrator.db,
    max_iterations=settings.research_max_iterations,
)

orchestrator.stages.update(stages)
orchestrator._wire_broadcast()

app.state.orchestrator = orchestrator

app.include_router(pipeline_routes.router)
app.include_router(event_routes.router)
app.include_router(session_routes.router)

frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
