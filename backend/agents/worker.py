"""Ephemeral worker — executes a single research task.

Workers are one-shot: no persistent state, no conversation history.
They receive a task description + dependency context, produce a result,
and save it to DB. They can query the Scholar for domain knowledge.

The Orchestrator dispatches workers via ``dispatch_workers()`` tool.
Workers reuse the existing topological_batches() for parallel execution.
"""

from __future__ import annotations

import asyncio
import json
from typing import Callable

from backend.agents.base import PersistentAgent
from backend.db import ResearchDB
from backend.llm.client import LLMClient, StreamEvent
from backend.pipeline.research import topological_batches

_WORKER_SYSTEM = """\
This is a fully automated pipeline. No human is in the loop. \
Do NOT ask questions or request input. Make all decisions autonomously. \
全文使用中文撰写。

You are a research worker executing a specific task as part of a larger research project.

Guidelines:
- Be substantive — produce concrete results, not descriptions of what you would do
- If the task is analytical: provide frameworks, specific comparisons, and cite evidence
- If the task is experimental: describe setup, parameters, results, and interpretation
- Structure output with headings and bullet points for clarity
- Reference specific data, figures, or prior work where relevant

Output in markdown."""


async def dispatch_workers(
    tasks_json: str,
    llm_client: LLMClient,
    db: ResearchDB,
    broadcast: Callable,
    scholar: PersistentAgent | None = None,
) -> str:
    """Execute a batch of research tasks in topological order.

    Args:
        tasks_json: JSON string of tasks list, each with id/description/dependencies.
        llm_client: LLMClient for worker sessions (ephemeral, no history).
        db: ResearchDB for reading deps and saving results.
        broadcast: SSE broadcast callback.
        scholar: Optional Scholar agent — workers can query for context.

    Returns:
        Summary of completed tasks.
    """
    tasks = json.loads(tasks_json)
    batches = topological_batches(tasks)
    results: dict[str, str] = {}

    # Emit execution tree for frontend
    broadcast({
        "stage": "research",
        "type": "exec_tree",
        "data": {
            "batches": [
                {
                    "batch": i + 1,
                    "tasks": [{"id": t["id"], "description": t["description"]} for t in b],
                }
                for i, b in enumerate(batches)
            ]
        },
    })

    for batch in batches:
        # Skip already completed
        pending = [t for t in batch if not db.get_task_output(t["id"])]
        for t in batch:
            if db.get_task_output(t["id"]):
                broadcast({
                    "stage": "research",
                    "type": "task_state",
                    "data": {"task_id": t["id"], "status": "completed"},
                })
                results[t["id"]] = db.get_task_output(t["id"])
        if not pending:
            continue

        coros = [
            _run_worker(task, llm_client, db, broadcast, results, scholar)
            for task in pending
        ]
        batch_results = await asyncio.gather(*coros, return_exceptions=True)

        for task, result in zip(pending, batch_results):
            if isinstance(result, Exception):
                broadcast({
                    "stage": "research",
                    "type": "task_state",
                    "data": {"task_id": task["id"], "status": "failed"},
                })
                broadcast({
                    "stage": "research",
                    "type": "error",
                    "data": {"message": f"Worker {task['id']} failed: {result}"},
                })
            else:
                results[task["id"]] = result

    # Build summary
    summaries = []
    for tid in sorted(results.keys()):
        text = results[tid]
        short = text[:200] + "..." if len(text) > 200 else text
        summaries.append(f"- **Task [{tid}]**: {short}")
    return f"Completed {len(results)} tasks:\n" + "\n".join(summaries)


async def _run_worker(
    task: dict,
    llm_client: LLMClient,
    db: ResearchDB,
    broadcast: Callable,
    completed: dict[str, str],
    scholar: PersistentAgent | None,
) -> str:
    """Execute a single task as an ephemeral worker."""
    task_id = task["id"]
    call_id = f"Worker {task_id}"

    broadcast({
        "stage": "research",
        "type": "task_state",
        "data": {"task_id": task_id, "status": "running"},
    })
    broadcast({
        "stage": "research",
        "type": "chunk",
        "data": {"text": call_id, "call_id": call_id, "label": True},
    })

    # Build prompt with dependency context
    parts = []
    deps = task.get("dependencies", [])
    if deps and not llm_client.has_tools:
        parts.append("## Context from completed prerequisite tasks:\n")
        for dep_id in deps:
            output = completed.get(dep_id, "") or db.get_task_output(dep_id)
            if output:
                parts.append(f"### Task [{dep_id}] output:\n{output}\n")
        parts.append("---\n")
    elif deps:
        parts.append(
            f"## Prerequisite tasks (use read_task_output to read): {', '.join(deps)}\n---\n"
        )

    parts.append(f"## Your task [{task_id}]:\n{task['description']}")

    messages = [
        {"role": "system", "content": _WORKER_SYSTEM},
        {"role": "user", "content": "\n".join(parts)},
    ]

    # Stream LLM response
    result = ""
    async for event in llm_client.stream(messages):
        if event.type == "content":
            broadcast({
                "stage": "research",
                "type": "chunk",
                "data": {"text": event.text, "call_id": call_id},
            })
            result += event.text
        elif event.type in ("think", "tool_call", "tool_result"):
            broadcast({
                "stage": "research",
                "type": "chunk",
                "data": {"text": event.call_id, "call_id": event.call_id, "label": True},
            })
            if event.text:
                broadcast({
                    "stage": "research",
                    "type": "chunk",
                    "data": {"text": event.text, "call_id": event.call_id},
                })
        elif event.type == "tokens":
            broadcast({
                "stage": "research",
                "type": "tokens",
                "data": event.metadata,
            })

    # Save to DB
    db.save_task_output(task_id, result)
    broadcast({
        "stage": "research",
        "type": "task_state",
        "data": {"task_id": task_id, "status": "completed"},
    })

    return result
