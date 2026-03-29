from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.pipeline.orchestrator import PipelineOrchestrator
from backend.routes import pipeline as pipeline_routes
from backend.routes import events as event_routes

app = FastAPI(title="MAARS", version="0.1.0")

# --- Pipeline stages ---
orchestrator = PipelineOrchestrator()

from backend.agno import create_agno_stages
stages = create_agno_stages(
    model_provider=settings.agno_model_provider,
    model_id=settings.agno_model_id or settings.gemini_model,
    api_key=settings.google_api_key,
    db=orchestrator.db,
    max_iterations=settings.research_max_iterations,
)

orchestrator.stages.update(stages)
orchestrator._wire_broadcast()

# Store orchestrator on app.state for route access
app.state.orchestrator = orchestrator

# --- Routes ---
app.include_router(pipeline_routes.router)
app.include_router(event_routes.router)

# --- Serve frontend static files ---
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
