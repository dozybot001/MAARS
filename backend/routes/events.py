import asyncio
import json

from fastapi import APIRouter, Request
from starlette.responses import StreamingResponse

router = APIRouter(prefix="/api")


@router.get("/events")
async def event_stream(request: Request):
    """SSE endpoint. All events use default 'message' type.
    Format: {stage, phase?, chunk?, status?, task_id?, error?}
    """
    queue = request.app.state.orchestrator.event_queue

    async def generate():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    payload = json.dumps(event, ensure_ascii=False)
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except (asyncio.CancelledError, GeneratorExit):
            pass

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
