from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api")


def _get_db(request: Request):
    orch = getattr(request.app.state, "orchestrator", None)
    if orch is None:
        raise HTTPException(status_code=500, detail="Pipeline not initialized")
    return orch.db


@router.get("/sessions")
async def list_sessions(request: Request):
    db = _get_db(request)
    return db.list_sessions()


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, request: Request):
    db = _get_db(request)
    try:
        info = db.get_session(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    if info is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return info


@router.get("/sessions/{session_id}/state")
async def get_session_state(session_id: str, request: Request):
    db = _get_db(request)
    try:
        state = db.get_session_state(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return state


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, request: Request):
    db = _get_db(request)
    try:
        info = db.get_session(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    if info is None:
        raise HTTPException(status_code=404, detail="Session not found")
    deleted = db.delete_session(session_id)
    if not deleted:
        raise HTTPException(
            status_code=409,
            detail="Session is currently active and cannot be deleted",
        )
    return {"deleted": session_id}
