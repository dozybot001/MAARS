"""
Idea Agent - Google ADK 驱动实现。
当 ideaAgentMode=True 时使用，替代自实现 ReAct 循环。
"""

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import orjson
from google.adk import Agent, Runner
from google.genai import types
from google.adk.sessions import InMemorySessionService
from loguru import logger

from shared.adk_bridge import (
    create_executor_tools,
    get_model_for_adk,
    prepare_api_env,
)
from shared.constants import IDEA_AGENT_MAX_TURNS

from .agent_tools import execute_idea_agent_tool, get_idea_agent_tools

IDEA_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = IDEA_DIR / "prompts"
_prompt_cache: Dict[str, str] = {}


def _get_prompt_cached(filename: str) -> str:
    """加载 idea agent prompt 文件。"""
    if filename not in _prompt_cache:
        path = PROMPTS_DIR / filename
        _prompt_cache[filename] = path.read_text(encoding="utf-8").strip()
    return _prompt_cache[filename]


async def run_idea_agent_adk(
    idea: str,
    api_config: dict,
    limit: int = 10,
    on_thinking: Optional[Callable[..., Any]] = None,
    abort_event: Optional[Any] = None,
) -> dict:
    """
    使用 Google ADK Runner 运行 Idea Agent。
    返回 {keywords, papers, refined_idea}，与 collect_literature 一致。
    """
    prepare_api_env(api_config)

    idea_state: Dict[str, Any] = {
        "idea": idea,
        "keywords": [],
        "papers": [],
        "filtered_papers": [],
        "analysis": "",
        "refined_idea": {},
        "rag_context": "",
    }

    on_thinking_fn = on_thinking or (lambda *a, **_: None)

    async def executor_fn(name: str, args: dict) -> tuple[bool, str]:
        args_str = json.dumps(args, ensure_ascii=False)
        return await execute_idea_agent_tool(
            name,
            args_str,
            idea_state,
            on_thinking=on_thinking_fn,
            abort_event=abort_event,
            api_config=api_config,
            limit=limit,
        )

    tools = create_executor_tools(get_idea_agent_tools(api_config), executor_fn)
    system_prompt = _get_prompt_cached("idea-agent-prompt.txt")
    user_message = f"**User's fuzzy idea:** {idea}\n\nProcess the idea using the workflow. Call FinishIdea when done."

    model = get_model_for_adk(api_config)
    agent = Agent(
        model=model,
        name="idea_agent",
        instruction=system_prompt,
        tools=tools,
    )

    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name="maars_idea",
        session_service=session_service,
        auto_create_session=True,
    )

    user_id = "maars_user"
    session_id = str(uuid.uuid4())
    new_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_message)],
    )

    finish_result: Optional[dict] = None
    turn_count = 0

    async def _run_with_abort():
        nonlocal finish_result, turn_count
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message,
        ):
            if abort_event and abort_event.is_set():
                raise asyncio.CancelledError("Idea Agent aborted")

            turn_count += 1
            if turn_count > IDEA_AGENT_MAX_TURNS:
                break

            if event.content and event.content.parts:
                fc = getattr(event, "get_function_calls", None)
                fr = getattr(event, "get_function_responses", None)
                if fc and callable(fc):
                    calls = fc()
                else:
                    calls = []
                if fr and callable(fr):
                    responses = fr()
                else:
                    responses = []

                if calls:
                    for c in calls:
                        name = getattr(c, "name", None) or ""
                        args = getattr(c, "args", None) or {}
                        if on_thinking_fn:
                            args_preview = json.dumps(args, ensure_ascii=False)
                            if len(args_preview) > 200:
                                args_preview = args_preview[:200] + "..."
                            r = on_thinking_fn(
                                "",
                                task_id=None,
                                operation="Refine",
                                schedule_info={
                                    "turn": turn_count,
                                    "max_turns": IDEA_AGENT_MAX_TURNS,
                                    "tool_name": name,
                                    "tool_args": args_preview,
                                    "tool_args_preview": None,
                                    "operation": "Refine",
                                },
                            )
                            if asyncio.iscoroutine(r):
                                await r

                elif responses:
                    for r in responses:
                        name = getattr(r, "name", None) or ""
                        resp = getattr(r, "response", None)
                        if name == "FinishIdea" and resp:
                            if isinstance(resp, dict):
                                raw = resp.get("result", resp)
                            else:
                                raw = resp
                            if isinstance(raw, dict):
                                finish_result = raw
                            else:
                                try:
                                    finish_result = orjson.loads(str(raw))
                                except Exception:
                                    finish_result = {}

                else:
                    for part in event.content.parts:
                        text = getattr(part, "text", None) or ""
                        if text and on_thinking_fn:
                            r = on_thinking_fn(
                                text,
                                task_id=None,
                                operation="Refine",
                                schedule_info={
                                    "turn": turn_count,
                                    "max_turns": IDEA_AGENT_MAX_TURNS,
                                    "operation": "Refine",
                                },
                            )
                            if asyncio.iscoroutine(r):
                                await r

        try:
            await runner.close()
        except Exception as e:
            logger.debug("Runner close: %s", e)

    try:
        run_task = asyncio.create_task(_run_with_abort())
        if abort_event:
            while not run_task.done():
                await asyncio.sleep(0.3)
                if abort_event.is_set():
                    run_task.cancel()
                    try:
                        await run_task
                    except asyncio.CancelledError:
                        pass
                    raise asyncio.CancelledError("Idea Agent aborted")
            await run_task
        else:
            await run_task
    except asyncio.CancelledError:
        raise

    if finish_result:
        return {
            "keywords": finish_result.get("keywords", []),
            "papers": finish_result.get("papers", []),
            "refined_idea": finish_result.get("refined_idea", {}),
        }

    return {
        "keywords": idea_state.get("keywords", []),
        "papers": idea_state.get("papers", []),
        "refined_idea": idea_state.get("refined_idea", {}),
    }
