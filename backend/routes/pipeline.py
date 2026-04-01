import asyncio

from fastapi import APIRouter, HTTPException, Request

from backend.models import StartRequest, ActionResponse, PipelineStatus, StageStatus

router = APIRouter(prefix="/api")


def _get_orchestrator(request: Request):
    orch = getattr(request.app.state, "orchestrator", None)
    if orch is None:
        raise HTTPException(status_code=500, detail="Pipeline not initialized")
    return orch


@router.post("/pipeline/start")
async def start_pipeline(req: StartRequest, request: Request):
    orch = _get_orchestrator(request)
    try:
        await orch.start(req.input)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "started", "input": req.input}


@router.get("/pipeline/status", response_model=PipelineStatus)
async def get_status(request: Request):
    orch = _get_orchestrator(request)
    status = orch.get_status()
    return PipelineStatus(
        input=status["input"],
        stages=[StageStatus(**s) for s in status["stages"]],
    )


@router.get("/docker/status")
async def docker_status():
    try:
        import docker
        def _ping():
            client = docker.from_env()
            client.ping()
        await asyncio.to_thread(_ping)
        return {"connected": True}
    except Exception as e:
        return {"connected": False, "error": str(e)}


@router.post("/pipeline/stop", response_model=ActionResponse)
async def stop_pipeline(request: Request):
    orch = _get_orchestrator(request)
    await orch.stop()
    running = next((n for n in ["refine", "research", "write"]
                     if orch.stages[n].state.value == "paused"), "")
    return ActionResponse(stage=running, state="paused", message="Pipeline paused")


@router.post("/pipeline/resume", response_model=ActionResponse)
async def resume_pipeline(request: Request):
    orch = _get_orchestrator(request)
    await orch.resume()
    resumed = next((n for n in ["refine", "research", "write"]
                     if orch.stages[n].state.value == "running"), "")
    return ActionResponse(stage=resumed, state="running", message="Pipeline resumed")
