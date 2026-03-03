"""
Paper Agent - 单轮 LLM 管道实现。
与 idea/plan/task 对齐：Mock 模式依赖 test/mock-ai/paper.json，使用 mock_chat_completion 流式输出。
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import orjson
from loguru import logger

from shared.llm_client import chat_completion, merge_phase_config
from test.mock_stream import mock_chat_completion

PAPER_DIR = Path(__file__).resolve().parent
MOCK_AI_DIR = PAPER_DIR.parent / "test" / "mock-ai"
MOCK_KEY = "_default"

_mock_cache: Dict[str, dict] = {}


def _get_mock_cached() -> dict:
    if "paper" not in _mock_cache:
        path = MOCK_AI_DIR / "paper.json"
        try:
            _mock_cache["paper"] = orjson.loads(path.read_bytes())
        except (FileNotFoundError, orjson.JSONDecodeError):
            _mock_cache["paper"] = {}
    return _mock_cache["paper"]


def _load_mock_response() -> Optional[Dict]:
    """从 test/mock-ai/paper.json 加载 mock，与 idea/plan 对齐。"""
    data = _get_mock_cached()
    entry = data.get(MOCK_KEY) or data.get("_default")
    if not entry:
        return None
    content = entry.get("content")
    if isinstance(content, str):
        content_str = content
    else:
        content_str = orjson.dumps(content).decode("utf-8")
    return {"content": content_str, "reasoning": entry.get("reasoning", "")}


def _maars_plan_to_paper_format(plan: dict) -> dict:
    """Convert MAARS plan shape to writing prompt format."""
    tasks = plan.get("tasks") or []
    return {
        "title": plan.get("idea") or "Untitled",
        "goal": plan.get("idea") or "N/A",
        "steps": [{"description": t.get("description", "")} for t in tasks],
    }


def _synthesize_conclusion_from_outputs(outputs: dict) -> dict:
    """Build conclusion dict from MAARS task outputs for paper draft."""
    findings = []
    for task_id, out in outputs.items():
        if isinstance(out, dict):
            content = out.get("content") or out.get("summary") or str(out)[:500]
            findings.append(f"Task {task_id}: {content}")
        else:
            findings.append(f"Task {task_id}: {str(out)[:500]}")
    return {
        "summary": "Synthesized from task outputs.",
        "key_findings": findings[:10],
        "recommendation": "Review and refine based on full task outputs.",
    }


async def run_paper_agent(
    plan: dict,
    outputs: dict,
    api_config: dict,
    format_type: str = "markdown",
    on_thinking: Optional[Callable[..., Any]] = None,
    abort_event: Optional[Any] = None,
) -> str:
    """
    单轮 LLM 生成论文草稿。
    返回 Markdown 或 LaTeX 格式的论文内容。
    Mock 模式：从 test/mock-ai/paper.json 加载，通过 mock_chat_completion 流式输出。
    """
    use_mock = api_config.get("paperUseMock", True)
    if use_mock:
        mock = _load_mock_response()
        if not mock:
            raise ValueError("No mock data for paper/_default")
        stream = on_thinking is not None

        def stream_chunk(chunk: str):
            if on_thinking and chunk:
                return on_thinking(chunk, None, "Paper", None)

        effective_on_thinking = stream_chunk if stream else None
        content = await mock_chat_completion(
            mock["content"],
            mock["reasoning"],
            effective_on_thinking,
            stream=stream,
            abort_event=abort_event,
        )
        return content or ""

    # Agent 模式占位：paperAgentMode=True 时暂回退到 LLM 管道，待 Phase 3 实现工具调用
    if api_config.get("paperAgentMode", False):
        logger.info("Paper Agent mode selected but not yet implemented; falling back to LLM pipeline")

    plan_fmt = _maars_plan_to_paper_format(plan)
    conclusion = _synthesize_conclusion_from_outputs(outputs or {})
    artifacts = [f"{tid}_output" for tid in (outputs or {}).keys()]

    if format_type.lower() == "latex":
        format_instruction = """Output the paper in LaTeX format.
Use standard LaTeX syntax with proper document structure.
Include placeholders for figures like \\includegraphics{filename.png} where appropriate based on the available artifacts.
"""
    else:
        format_instruction = """Output the paper in Markdown format.
Use standard markdown headers (#, ##, ###).
Include placeholders for figures like `[Figure: filename.png]` where appropriate based on the available artifacts.
"""

    system_instruction = """You are an academic writing assistant.
Your task is to write a comprehensive research paper based on the provided experiment plan, results, and conclusion.
The paper should follow standard academic structure:
1. Title
2. Abstract
3. Introduction (Background & Motivation)
4. Methodology (Experimental Setup)
5. Results (Key Findings & Evidence)
6. Discussion (Implications & Limitations)
7. Conclusion
8. References (Mocked if necessary, but strictly written according to APA format)

""" + format_instruction

    user_prompt = f"""
Experiment Title: {plan_fmt.get('title', 'Untitled')}
Goal: {plan_fmt.get('goal', 'N/A')}

Methodology Steps:
{json.dumps(plan_fmt.get('steps', []), indent=2)}

Conclusion & Findings:
{json.dumps(conclusion, indent=2)}

Available Artifacts (Figures/Tables):
{', '.join(artifacts)}

Please write the full paper.
"""

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_prompt},
    ]

    cfg = merge_phase_config(api_config, "paper")

    async def on_chunk(chunk: str):
        if on_thinking and chunk:
            r = on_thinking(chunk, None, "Paper", None)
            if hasattr(r, "__await__"):
                await r

    try:
        result = await chat_completion(
            messages,
            cfg,
            on_chunk=on_chunk,
            abort_event=abort_event,
            stream=True,
        )
        return result if isinstance(result, str) else str(result or "")
    except Exception as e:
        return f"Error generating paper: {str(e)}"
