"""Result evaluation: analyze completed work and suggest improvements."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from backend.llm.client import LLMClient, StreamEvent
from backend.utils import parse_json_fenced

_EVALUATE_SYSTEM = """\
You are a research quality evaluator with tool access. Your job is to analyze \
completed work and identify concrete improvements — NOT to decide whether to stop.

WORKFLOW:
1. USE YOUR TOOLS to investigate:
   - Call read_task_output(task_id) to read FULL outputs of key tasks
   - Call list_artifacts() to see what files exist, including best_score.json
   - Look for actual metrics: CV scores, RMSLE, accuracy, etc.
2. Analyze what was done well and what can be improved
3. Provide specific, actionable improvement directions

FOCUS ON:
- Untried approaches (models, feature engineering techniques, ensembles)
- Weaknesses in current approach (overfitting, missing features, poor preprocessing)
- Specific numbers: current best score, where the biggest errors are
- What the next iteration should prioritize

Output a JSON block at the end:
{"feedback": "Analysis of current results with specific numbers", "suggestions": ["specific improvement 1", "specific improvement 2"]}
全文使用中文。"""


def check_score_improved(artifacts_dir: Path, prev_score: float | None,
                         minimize: bool = True) -> tuple[bool, float | None]:
    """Check best_score.json and compare with previous iteration.

    Args:
        artifacts_dir: Path to artifacts directory.
        prev_score: Score from previous iteration (None if first).
        minimize: True for metrics like RMSLE/RMSE (lower=better),
                  False for accuracy/AUC (higher=better).

    Returns:
        (improved, current_score)
    """
    score_file = artifacts_dir / "best_score.json"
    if not score_file.exists():
        return False, None

    try:
        data = json.loads(score_file.read_text())
        current = float(data.get("score", 0))
    except (json.JSONDecodeError, ValueError, TypeError):
        return False, None

    if prev_score is None:
        return True, current  # First iteration — always "improved"

    if minimize:
        improved = current < prev_score * 0.995  # >0.5% improvement threshold
    else:
        improved = current > prev_score * 1.005

    return improved, current


async def evaluate_results(
    idea: str,
    task_summaries: list[dict],
    llm_client: LLMClient,
    stream_callback: Callable | None = None,
    is_stale: Callable[[], bool] | None = None,
) -> dict:
    """Analyze completed results and suggest improvements.

    Does NOT decide whether to stop — that's done by check_score_improved().
    Returns {"feedback": "...", "suggestions": [...]}.
    """
    emit = stream_callback or (lambda t, d: None)
    stale = is_stale or (lambda: False)

    call_id = "Evaluate"
    emit("chunk", {"text": call_id, "call_id": call_id, "label": True})

    summaries_text = "\n".join(
        f"- **Task [{s['id']}]**: {s['summary']}" for s in task_summaries
    )

    messages = [
        {"role": "system", "content": _EVALUATE_SYSTEM},
        {"role": "user", "content": (
            f"## Research Goal\n{idea}\n\n"
            f"## Completed Task Summaries\n{summaries_text}\n\n"
            f"Use read_task_output and list_artifacts to investigate actual results. "
            f"Analyze what can be improved and provide specific suggestions."
        )},
    ]

    response = ""
    async for event in llm_client.stream(messages):
        if stale():
            break
        if event.type == "content":
            emit("chunk", {"text": event.text, "call_id": call_id})
            response += event.text
        elif event.type in ("think", "tool_call", "tool_result"):
            emit("chunk", {"text": event.call_id, "call_id": event.call_id, "label": True})
            if event.text:
                emit("chunk", {"text": event.text, "call_id": event.call_id})
        elif event.type == "tokens":
            emit("tokens", event.metadata)

    return parse_json_fenced(response, fallback={"feedback": "", "suggestions": []})
