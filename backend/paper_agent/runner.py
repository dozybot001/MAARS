"""
Paper Agent - 单轮 LLM 管道实现。
使用 MAARS shared llm_client，支持流式 on_thinking 与 abort_event。
"""

import json
from typing import Any, Callable, Optional

from shared.llm_client import chat_completion, merge_phase_config


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
    """
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
