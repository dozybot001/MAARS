"""Read-only API endpoints for session data."""

from fastapi import APIRouter, HTTPException, Request, Query

router = APIRouter(prefix="/api/session")


def _get_db(request: Request):
    orch = getattr(request.app.state, "orchestrator", None)
    if orch is None:
        raise HTTPException(status_code=500, detail="Pipeline not initialized")
    if not orch.db.research_id:
        raise HTTPException(status_code=404, detail="No active session")
    return orch.db


@router.get("/log")
async def get_log(request: Request, stage: str = Query(""), offset: int = Query(0, ge=0)):
    db = _get_db(request)
    entries, new_offset = db.get_log(offset=offset, stage=stage)
    return {"entries": entries, "offset": new_offset}


@router.get("/plan/tree")
async def get_plan_tree(request: Request):
    db = _get_db(request)
    return db.get_plan_tree()


@router.get("/plan/list")
async def get_plan_list(request: Request):
    db = _get_db(request)
    return db.get_plan_list()


@router.get("/meta")
async def get_meta(request: Request):
    db = _get_db(request)
    return db.get_meta()


@router.get("/documents/list/{prefix}")
async def list_documents(prefix: str, request: Request):
    db = _get_db(request)
    return db.list_documents(prefix)


@router.get("/tasks/{task_id}")
async def get_task_output(task_id: str, request: Request):
    db = _get_db(request)
    content = db.get_task_output(task_id)
    if not content:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return {"task_id": task_id, "content": content}


@router.get("/documents/{name:path}")
async def get_document(name: str, request: Request):
    db = _get_db(request)
    content = db.get_document(name)
    if not content:
        raise HTTPException(status_code=404, detail=f"Document '{name}' not found")
    return {"name": name, "content": content}
