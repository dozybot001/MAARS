"""
Task Agent 单轮 LLM 实现 - 任务执行。
与 Plan/Idea 对齐：Mock 模式依赖 test/mock-ai/execute.json，使用 mock_chat_completion 流式输出。
"""

import re
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import orjson
import json_repair

from shared.llm_client import chat_completion, merge_phase_config
from test.mock_stream import mock_chat_completion

TASK_DIR = Path(__file__).resolve().parent.parent
MOCK_AI_DIR = TASK_DIR.parent / "test" / "mock-ai"
RESPONSE_TYPE = "execute"

_mock_cache: Dict[str, dict] = {}


def _get_mock_cached(response_type: str) -> dict:
    if response_type not in _mock_cache:
        path = MOCK_AI_DIR / f"{response_type}.json"
        try:
            _mock_cache[response_type] = orjson.loads(path.read_bytes())
        except (FileNotFoundError, orjson.JSONDecodeError):
            _mock_cache[response_type] = {}
    return _mock_cache[response_type]


def _load_mock_response(response_type: str, task_id: str, use_json_mode: bool) -> Optional[Dict]:
    """从 test/mock-ai/ 加载 mock，与 Plan/Idea 对齐。"""
    data = _get_mock_cached(response_type)
    entry = data.get(task_id) or (data.get("_default_markdown") if not use_json_mode else None) or data.get("_default")
    if not entry:
        return None
    content = entry.get("content")
    if isinstance(content, str):
        content_str = content
    else:
        content_str = orjson.dumps(content).decode("utf-8")
    return {"content": content_str, "reasoning": entry.get("reasoning", "")}


async def _run_mock_execute(
    task_id: str,
    output_format: str,
    on_thinking: Optional[Callable] = None,
) -> Any:
    """Mock 执行：从 execute.json 加载，使用 mock_chat_completion 流式输出。供 executor 与 agent 共用。"""
    use_json_mode = _is_json_format(output_format)
    mock = _load_mock_response(RESPONSE_TYPE, task_id, use_json_mode)
    if not mock:
        raise ValueError(f"No mock data for {RESPONSE_TYPE}/{task_id}")
    stream = on_thinking is not None

    def stream_chunk(chunk: str):
        if on_thinking and chunk:
            return on_thinking(chunk, task_id=task_id, operation="Execute")

    effective_on_thinking = stream_chunk if stream else None
    content = await mock_chat_completion(
        mock["content"],
        mock["reasoning"],
        effective_on_thinking,
        stream=stream,
    )
    return _parse_task_agent_output(content or "", use_json_mode)


def _is_json_format(output_format: str) -> bool:
    if not output_format:
        return False
    fmt = output_format.strip().upper()
    return fmt.startswith("JSON") or "JSON" in fmt


def _build_task_agent_messages(
    task_id: str,
    description: str,
    input_spec: Dict[str, Any],
    output_spec: Dict[str, Any],
    resolved_inputs: Dict[str, Any],
) -> tuple[list[dict], str]:
    """Build system + user messages for single-turn Task Agent."""
    output_format = output_spec.get("format") or ""
    output_desc = output_spec.get("description") or ""
    input_desc = input_spec.get("description") or ""

    system_prompt = """You are a Task Agent. Your job is to complete a single atomic task and produce output in the exact format specified.

Rules:
1. Use only the provided input artifacts and task description.
2. Output must strictly conform to the specified format.
3. For JSON: output valid JSON only, no extra text or markdown fences.
4. For Markdown: output the document content directly."""

    inputs_str = "No input artifacts."
    if resolved_inputs:
        try:
            inputs_str = orjson.dumps(resolved_inputs, option=orjson.OPT_INDENT_2).decode("utf-8")
        except (TypeError, ValueError):
            inputs_str = str(resolved_inputs)

    user_prompt = f"""**Task ID:** {task_id}
**Description:** {description}

**Input description:** {input_desc}
**Input artifacts:**
```json
{inputs_str}
```

**Output description:** {output_desc}
**Output format:** {output_format}

Produce the output now. Output ONLY the result, no explanation."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    return messages, output_format


def _parse_task_agent_output(content: str, use_json_mode: bool) -> Any:
    """Parse Task Agent output (content) to final result."""
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


def _get_task_agent_params(api_config: Dict[str, Any]) -> tuple[int, float]:
    """Return (max_turns, temperature) from modeConfig or defaults. Used for single-turn temperature."""
    mode_cfg = api_config.get("modeConfig") or {}
    agent_cfg = mode_cfg.get("agent") or {}
    llm_cfg = mode_cfg.get("llm") or {}
    temperature = (
        agent_cfg.get("taskLlmTemperature")
        or llm_cfg.get("taskLlmTemperature")
        or 0.3
    )
    return 1, float(temperature)


async def execute_task(
    task_id: str,
    description: str,
    input_spec: Dict[str, Any],
    output_spec: Dict[str, Any],
    resolved_inputs: Dict[str, Any],
    api_config: Optional[Dict[str, Any]] = None,
    abort_event: Optional[Any] = None,
    on_thinking: Optional[Callable[[str, Optional[str], Optional[str]], None]] = None,
    plan_id: Optional[str] = None,
) -> Any:
    """
    Execute task via single-turn LLM. Returns parsed output (dict for JSON, str for Markdown).
    When useMock=True in api_config, returns simulated output without LLM call.
    When taskAgentMode=True, caller (runner) should use task_agent.agent.run_task_agent instead.
    """
    raw_cfg = api_config or {}
    if raw_cfg.get("useMock"):
        output_format = (output_spec or {}).get("format") or ""
        return await _run_mock_execute(task_id, output_format, on_thinking)

    cfg = merge_phase_config(raw_cfg, "execute")
    _, temperature = _get_task_agent_params(raw_cfg)
    messages, output_format = _build_task_agent_messages(
        task_id, description, input_spec, output_spec, resolved_inputs
    )
    use_json_mode = _is_json_format(output_format)
    response_format = {"type": "json_object"} if use_json_mode else None
    stream = on_thinking is not None

    def _on_chunk(chunk: str):
        if on_thinking and chunk:
            return on_thinking(chunk, task_id=task_id, operation="Execute")

    raw = await chat_completion(
        messages,
        cfg,
        on_chunk=_on_chunk if stream else None,
        abort_event=abort_event,
        stream=stream,
        temperature=temperature,
        response_format=response_format,
    )
    content = raw if isinstance(raw, str) else (raw.get("content") or "")
    return _parse_task_agent_output(content, use_json_mode)
