"""
Plan Agent - Google ADK 驱动实现。
当 planAgentMode=True 时使用，替代自实现 ReAct 循环。
"""

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

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
from shared.constants import PLAN_AGENT_MAX_TURNS

from .agent_tools import PLAN_AGENT_TOOLS, execute_plan_agent_tool
from .llm.executor import check_atomicity, decompose_task, format_task

IDEA_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = IDEA_DIR / "prompts"
_prompt_cache: Dict[str, str] = {}


def _get_prompt_cached(filename: str) -> str:
    """加载 plan agent prompt 文件。"""
    if filename not in _prompt_cache:
        path = PROMPTS_DIR / filename
        _prompt_cache[filename] = path.read_text(encoding="utf-8").strip()
    return _prompt_cache[filename]


async def run_plan_agent_adk(
    plan: Dict,
    on_thinking: Callable[[str], None],
    abort_event: Optional[Any],
    on_tasks_batch: Optional[Callable[[List[Dict], Dict, List[Dict]], None]],
    api_config: Optional[Dict],
    idea_id: Optional[str] = None,
    plan_id: Optional[str] = None,
) -> Dict:
    """
    使用 Google ADK Runner 运行 Plan Agent。
    返回 {tasks}。
    """
    prepare_api_env(api_config or {})

    tasks = plan.get("tasks") or []
    root_task = next((t for t in tasks if t.get("task_id") == "0"), None)
    if not root_task:
        root_task = next(
            (t for t in tasks if t.get("task_id") and not (t.get("dependencies") or [])),
            tasks[0] if tasks else None,
        )
    if not root_task:
        raise ValueError("No decomposable task found. Generate plan first.")

    all_tasks = list(tasks)
    idea = plan.get("idea") or root_task.get("description") or ""
    plan_state: Dict[str, Any] = {
        "all_tasks": all_tasks,
        "pending_queue": ["0"],
        "idea": idea,
    }

    on_thinking_fn = on_thinking or (lambda *a, **_: None)

    async def executor_fn(name: str, args: dict) -> tuple[bool, str]:
        args_str = json.dumps(args, ensure_ascii=False)
        return await execute_plan_agent_tool(
            name,
            args_str,
            plan_state,
            check_atomicity_fn=check_atomicity,
            decompose_fn=decompose_task,
            format_fn=format_task,
            on_thinking=on_thinking_fn,
            on_tasks_batch=on_tasks_batch,
            abort_event=abort_event,
            use_mock=False,
            api_config=api_config,
            idea_id=idea_id,
            plan_id=plan_id,
        )

    tools = create_executor_tools(PLAN_AGENT_TOOLS, executor_fn)
    system_prompt = _get_prompt_cached("plan-agent-prompt.txt")
    user_message = f"**Idea:** {idea}\n\n**Root task:** task_id \"0\", description \"{root_task.get('description', '')}\"\n\nProcess all tasks until GetNextTask returns null, then call FinishPlan."

    model = get_model_for_adk(api_config or {})
    agent = Agent(
        model=model,
        name="plan_agent",
        instruction=system_prompt,
        tools=tools,
    )

    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name="maars_plan",
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
                raise asyncio.CancelledError("Plan Agent aborted")

            turn_count += 1
            if turn_count > PLAN_AGENT_MAX_TURNS:
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
                                operation="Decompose",
                                schedule_info={
                                    "turn": turn_count,
                                    "max_turns": PLAN_AGENT_MAX_TURNS,
                                    "tool_name": name,
                                    "tool_args": args_preview,
                                    "tool_args_preview": None,
                                    "operation": "Decompose",
                                },
                            )
                            if asyncio.iscoroutine(r):
                                await r

                elif responses:
                    for r in responses:
                        name = getattr(r, "name", None) or ""
                        resp = getattr(r, "response", None)
                        if name == "FinishPlan" and resp:
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
                                operation="Decompose",
                                schedule_info={
                                    "turn": turn_count,
                                    "max_turns": PLAN_AGENT_MAX_TURNS,
                                    "operation": "Decompose",
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
                    raise asyncio.CancelledError("Plan Agent aborted")
            await run_task
        else:
            await run_task
    except asyncio.CancelledError:
        raise

    plan["tasks"] = plan_state["all_tasks"]
    return {"tasks": plan_state["all_tasks"]}
