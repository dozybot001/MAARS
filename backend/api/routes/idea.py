"""Idea Agent API - 文献收集。"""

import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from db import get_effective_config, save_plan
from idea_agent import collect_literature

from .. import state as api_state
from ..schemas import IdeaCollectRequest

router = APIRouter()


def _make_on_thinking(sio):
    """构造 on_thinking 回调，通过 WebSocket 推送 idea-thinking 事件。
    与 Task Agent 对齐：使用 await emit 保证顺序与送达。
    签名与 Plan/Task 统一：(chunk, task_id, operation, schedule_info)
    """

    async def on_thinking(
        chunk: str,
        task_id=None,
        operation=None,
        schedule_info=None,
    ):
        if not chunk and schedule_info is None:
            return
        if not sio:
            return
        payload = {
            "chunk": chunk or "",
            "source": "idea",
            "taskId": task_id,
            "operation": operation or "Refine",
        }
        if schedule_info is not None:
            payload["scheduleInfo"] = schedule_info
        try:
            await sio.emit("idea-thinking", payload)
        except Exception:
            pass

    return on_thinking


@router.post("/collect")
async def collect_literature_route(body: IdeaCollectRequest):
    """Collect arXiv literature from fuzzy idea. Creates new plan (db standard). Flow: LLM keywords -> arXiv -> plan."""
    if not body.idea or not body.idea.strip():
        return JSONResponse(status_code=400, content={"error": "idea is required"})
    idea = body.idea.strip()
    config = await get_effective_config()
    sio = getattr(api_state, "sio", None)
    on_thinking = _make_on_thinking(sio) if sio else None
    try:
        result = await collect_literature(
            idea=idea,
            api_config=config,
            limit=body.limit,
            on_thinking=on_thinking,
        )
        plan_id = f"plan_{int(time.time() * 1000)}"
        plan = {
            "tasks": [{"task_id": "0", "description": idea, "dependencies": []}],
            "idea": idea,
        }
        await save_plan(plan, plan_id)
        result["planId"] = plan_id
        return result
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Literature collection failed: {e}"},
        )
