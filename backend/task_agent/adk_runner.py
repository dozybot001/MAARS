"""
Task Agent - Google ADK 驱动实现。
当 taskAgentMode=True 时使用，替代自实现 ReAct 循环。
"""

import asyncio
import json
import re
import uuid
from typing import Any, Callable, Dict, Optional

import json_repair
from google.adk import Agent, Runner
from google.genai import types
from google.adk.sessions import InMemorySessionService
from loguru import logger

from db import ensure_sandbox_dir
from shared.adk_bridge import (
    create_executor_tools,
    get_model_for_adk,
    prepare_api_env,
)
from shared.constants import TASK_AGENT_MAX_TURNS

from .agent_tools import TOOLS, execute_tool


def _is_json_format(output_format: str) -> bool:
    if not output_format:
        return False
    fmt = output_format.strip().upper()
    return fmt.startswith("JSON") or "JSON" in fmt


def _parse_task_agent_output(content: str, use_json_mode: bool) -> Any:
    """Parse Task Agent output to final result."""
    content = (content or "").strip()
    if not content:
        raise ValueError("LLM returned empty response")
    if use_json_mode:
        cleaned = content
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
        if m:
            cleaned = m.group(1).strip()
        try:
            return json_repair.loads(cleaned)
        except Exception as e:
            raise ValueError(f"Failed to parse JSON from LLM response: {e}") from e
    return content


def _build_system_prompt(
    output_format: str,
    validation_spec: Optional[Dict[str, Any]] = None,
    idea_context: str = "",
) -> str:
    """构建 Task Agent 的 system prompt。"""
    validation_rule = ""
    if validation_spec and (validation_spec.get("criteria") or validation_spec.get("optionalChecks")):
        validation_rule = """
5. **Validation (required when task has validation spec)**: Before calling Finish, you MUST validate your output. Load the task-output-validator skill, write output to sandbox (e.g. sandbox/output.json or sandbox/result.md), run its validate script with the validation criteria, fix any failures, then call Finish only when validation passes."""

    idea_block = ""
    if idea_context:
        idea_block = f"\n6. **Research context**: This task is part of a larger research project. The overarching research idea is provided below — use it to ensure your output aligns with the project goals and maintains consistency."

    return f"""You are a Task Agent. Your job is to complete a single atomic task and produce output in the exact format specified.

Rules:
1. Use only the provided input artifacts and task description.
2. Output must strictly conform to the specified format.
3. Before calling any tool, briefly explain your reasoning: what you know, what you need, and why you are choosing this tool. This reasoning will be shown as your thinking process.
4. For JSON: output valid JSON when calling Finish; for Markdown, pass the document content.{validation_rule}{idea_block}

You have tools: ReadArtifact (read dependency task output), ReadFile (read files; use 'sandbox/X' for this task's sandbox), WriteFile (write to sandbox only), ListSkills, LoadSkill, ReadSkillFile (read skill's scripts/references), RunSkillScript (execute skill scripts, use {{sandbox}}/file for sandbox paths), WebSearch (search the web for research—use for benchmarks, docs, current data), WebFetch (fetch URL content for citations), Finish (submit final output).
Use ListSkills to discover skills, LoadSkill when relevant. Common task types: literature synthesis → literature-synthesis; comparison report → comparison-report; validation required → task-output-validator. ReadSkillFile and RunSkillScript let you use skill capabilities (e.g. docx validate, pptx convert). When your output satisfies the output spec, you MUST call Finish with the result—do not output inline. For JSON format pass a valid JSON string; for Markdown pass the content string. All file I/O is scoped to the plan dir and this task's sandbox."""


async def run_task_agent_adk(
    task_id: str,
    description: str,
    input_spec: Dict[str, Any],
    output_spec: Dict[str, Any],
    resolved_inputs: Dict[str, Any],
    api_config: Dict[str, Any],
    abort_event: Optional[Any],
    on_thinking: Optional[Callable[[str, Optional[str], Optional[str]], None]],
    idea_id: str,
    plan_id: str,
    validation_spec: Optional[Dict[str, Any]] = None,
    idea_context: str = "",
) -> Any:
    """
    使用 Google ADK Runner 运行 Task Agent。
    返回任务输出 (dict 或 str)。
    """
    prepare_api_env(api_config)

    if idea_id and plan_id and task_id:
        await ensure_sandbox_dir(idea_id, plan_id, task_id)

    output_format = output_spec.get("format") or ""
    use_json_mode = _is_json_format(output_format)
    on_thinking_fn = on_thinking or (lambda *a, **_: None)

    task_output: list = [None]

    async def executor_fn(name: str, args: dict) -> tuple[bool, str]:
        args_str = json.dumps(args, ensure_ascii=False)
        out, tool_result = await execute_tool(
            name, args_str, idea_id, plan_id, task_id
        )
        if out is not None:
            task_output[0] = out
            return True, '{"status": "success", "message": "Task completed."}'
        return False, tool_result

    tools = create_executor_tools(TOOLS, executor_fn)
    system_prompt = _build_system_prompt(output_format, validation_spec, idea_context)

    import orjson
    inputs_str = "No input artifacts."
    if resolved_inputs:
        try:
            inputs_str = orjson.dumps(resolved_inputs, option=orjson.OPT_INDENT_2).decode("utf-8")
        except (TypeError, ValueError):
            inputs_str = str(resolved_inputs)

    validation_block = ""
    if validation_spec and (validation_spec.get("criteria") or validation_spec.get("optionalChecks")):
        criteria = validation_spec.get("criteria") or []
        optional = validation_spec.get("optionalChecks") or []
        criteria_text = "\n".join(f"- {c}" for c in criteria) if criteria else ""
        optional_text = "\n".join(f"- [optional] {c}" for c in optional) if optional else ""
        validation_block = f"""

**Validation criteria (validate before Finish using task-output-validator skill):**
{criteria_text}
{optional_text}
"""

    idea_section = ""
    if idea_context:
        idea_section = f"\n**Research idea (project context):** {idea_context}\n"

    user_message = f"""**Task ID:** {task_id}
**Description:** {description}
{idea_section}
**Input description:** {input_spec.get("description", "")}
**Input artifacts:**
```json
{inputs_str}
```

**Output description:** {output_spec.get("description", "")}
**Output format:** {output_format}
{validation_block}

Produce the output now. You may reason first; when ready, call Finish with the result."""

    model = get_model_for_adk(api_config)
    agent = Agent(
        model=model,
        name="task_agent",
        instruction=system_prompt,
        tools=tools,
    )

    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name="maars_task",
        session_service=session_service,
        auto_create_session=True,
    )

    user_msg = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_message)],
    )

    turn_count = 0

    async def _run_with_abort():
        nonlocal turn_count
        async for event in runner.run_async(
            user_id="maars_user",
            session_id=str(uuid.uuid4()),
            new_message=user_msg,
        ):
            if abort_event and abort_event.is_set():
                raise asyncio.CancelledError("Task Agent aborted")

            turn_count += 1
            if turn_count > TASK_AGENT_MAX_TURNS:
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
                                task_id=task_id,
                                operation="Execute",
                                schedule_info={
                                    "turn": turn_count,
                                    "max_turns": TASK_AGENT_MAX_TURNS,
                                    "tool_name": name,
                                    "tool_args": args_preview,
                                    "tool_args_preview": None,
                                    "operation": "Execute",
                                    "task_id": task_id,
                                },
                            )
                            if asyncio.iscoroutine(r):
                                await r

                elif not responses:
                    for part in event.content.parts:
                        text = getattr(part, "text", None) or ""
                        if text and on_thinking_fn:
                            r = on_thinking_fn(
                                text,
                                task_id=task_id,
                                operation="Execute",
                                schedule_info={
                                    "turn": turn_count,
                                    "max_turns": TASK_AGENT_MAX_TURNS,
                                    "operation": "Execute",
                                    "task_id": task_id,
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
                    raise asyncio.CancelledError("Task Agent aborted")
            await run_task
        else:
            await run_task
    except asyncio.CancelledError:
        raise

    if task_output[0] is not None:
        return task_output[0]

    raise ValueError(
        f"Agent reached max turns ({TASK_AGENT_MAX_TURNS}) without calling Finish"
    )
