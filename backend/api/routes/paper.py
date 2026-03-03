"""Paper Agent API - 第四个 Agent，单轮 LLM 管道。与 idea/plan/task 统一：HTTP 仅触发，数据由 WebSocket 回传。"""

import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from loguru import logger

from db import get_effective_config, get_plan, list_plan_outputs
from paper_agent import run_paper_agent

from .. import state as api_state
from ..schemas import PaperRunRequest

router = APIRouter()




def _make_on_thinking(sio):
    """构造 on_thinking 回调，通过 WebSocket 推送 paper-thinking 事件。"""

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
            "source": "paper",
            "taskId": task_id,
            "operation": operation or "Paper",
        }
        if schedule_info is not None:
            payload["scheduleInfo"] = schedule_info
        try:
            await sio.emit("paper-thinking", payload)
        except Exception as e:
            logger.warning("paper-thinking emit failed: %s", e)

    return on_thinking


async def _run_paper_inner(idea_id: str, plan_id: str, format_type: str, abort_event=None):
    """后台执行论文生成，通过 WebSocket 回传数据。"""
    config = await get_effective_config()
    sio = getattr(api_state, "sio", None)
    on_thinking = _make_on_thinking(sio) if sio else None

    plan = await get_plan(idea_id, plan_id)
    if not plan or not plan.get("tasks"):
        if sio:
            await sio.emit("paper-error", {"error": "Plan not found or empty."})
        return

    outputs = await list_plan_outputs(idea_id, plan_id)

    try:
        if sio:
            await sio.emit("paper-start", {})

        content = await run_paper_agent(
            plan=plan,
            outputs=outputs,
            api_config=config,
            format_type=format_type or "markdown",
            on_thinking=on_thinking,
            abort_event=abort_event,
        )

        if sio:
            await sio.emit("paper-complete", {
                "ideaId": idea_id,
                "planId": plan_id,
                "content": content,
                "format": format_type or "markdown",
            })
    except asyncio.CancelledError:
        try:
            if sio:
                await sio.emit("paper-error", {"error": "Paper Agent stopped by user"})
        except Exception as emit_err:
            logger.warning("paper-error emit (cancel) failed: %s", emit_err)
        raise
    except Exception as e:
        logger.warning("Paper Agent error: %s", e)
        try:
            if sio:
                await sio.emit("paper-error", {"error": str(e)})
        except Exception as emit_err:
            logger.warning("paper-error emit failed: %s", emit_err)
        raise
    finally:
        state = getattr(api_state, "paper_run_state", None)
        if state:
            state.run_task = None
            state.abort_event = None


@router.post("/run")
async def run_paper_route(body: PaperRunRequest):
    """Generate paper draft. 立即返回，数据由 WebSocket paper-complete 回传。"""
    state = getattr(api_state, "paper_run_state", None)
    if state and state.run_task and not state.run_task.done():
        return JSONResponse(status_code=409, content={"error": "Paper Agent already in progress"})

    idea_id = (body.idea_id or "").strip()
    plan_id = (body.plan_id or "").strip()
    if not idea_id or not plan_id:
        return JSONResponse(status_code=400, content={"error": "ideaId and planId are required"})

    plan = await get_plan(idea_id, plan_id)
    if not plan or not plan.get("tasks"):
        return JSONResponse(status_code=400, content={"error": "Plan not found. Generate plan first."})

    format_type = (body.format or "markdown").lower()
    if format_type not in ("markdown", "latex"):
        format_type = "markdown"

    if state:
        state.abort_event = asyncio.Event()
        state.abort_event.clear()
        state.run_task = asyncio.create_task(
            _run_paper_inner(idea_id, plan_id, format_type, abort_event=state.abort_event)
        )

    return {"success": True, "ideaId": idea_id, "planId": plan_id}


@router.post("/stop")
async def stop_paper():
    """停止 Paper Agent。"""
    state = getattr(api_state, "paper_run_state", None)
    if state and state.abort_event:
        state.abort_event.set()
    if state and state.run_task and not state.run_task.done():
        state.run_task.cancel()
        try:
            sio = getattr(api_state, "sio", None)
            if sio:
                await sio.emit("paper-error", {"error": "Paper Agent stopped by user"})
        except Exception as e:
            logger.warning("paper-error emit (stop) failed: %s", e)
    return {"success": True}
