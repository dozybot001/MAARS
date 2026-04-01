"""Task decomposition: recursively break an idea into atomic tasks with a dependency DAG."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Callable

from backend.utils import parse_json_fenced
from backend.pipeline.prompts import build_decompose_system, build_decompose_user


@dataclass
class Task:
    id: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    is_atomic: bool | None = None
    children: list[str] = field(default_factory=list)


async def decompose(
    idea: str,
    stream_fn: Callable,
    max_depth: int = 10,
    atomic_definition: str = "",
    strategy: str = "",
    on_judge_done: Callable | None = None,
    is_stale: Callable[[], bool] | None = None,
) -> tuple[list[dict], dict]:
    system_prompt = build_decompose_system(atomic_definition, strategy)
    progress_fn = on_judge_done or (lambda tree: None)
    stale = is_stale or (lambda: False)

    tasks: dict[str, Task] = {}
    pending: list[str] = []

    root = Task(id="0", description=idea)
    tasks["0"] = root
    pending.append("0")

    while pending:
        if stale():
            break
        batch = list(pending)
        pending.clear()
        await asyncio.gather(*[
            _process_task(tid, tasks, pending, idea, system_prompt,
                          max_depth, stream_fn, progress_fn, stale)
            for tid in batch
        ])

    tree = _serialize_tree(tasks)
    flat_tasks = _finalize(tasks)
    return flat_tasks, tree


async def _process_task(task_id, tasks, pending, context, system_prompt,
                        max_depth, stream_fn, progress_fn, stale):
    task = tasks[task_id]
    depth = 0 if task_id == "0" else len(task_id.split("_"))
    if depth >= max_depth:
        task.is_atomic = True
        progress_fn(_serialize_tree(tasks))
        return

    call_id = "Decompose" if task_id == "0" else f"Judge {task_id}"
    label_level = 2 if task_id == "0" else 3
    content_level = label_level + 1

    response = await stream_fn(
        system_prompt, build_decompose_user(task.id, task.description, context),
        call_id, content_level, label=True, label_level=label_level,
    )

    data = parse_json_fenced(response, fallback={"is_atomic": True})

    if data.get("is_atomic", True):
        subtasks = data.get("subtasks", [])
        if not subtasks or not all("id" in st and "description" in st for st in subtasks):
            task.is_atomic = True
            progress_fn(_serialize_tree(tasks))
            return

    task.is_atomic = False
    for st in data["subtasks"]:
        child_id = st["id"] if task_id == "0" else f"{task_id}_{st['id']}"
        child_deps = [
            d if task_id == "0" else f"{task_id}_{d}"
            for d in st.get("dependencies", [])
        ]
        child = Task(id=child_id, description=st["description"], dependencies=child_deps)
        tasks[child_id] = child
        task.children.append(child_id)
        pending.append(child_id)

    progress_fn(_serialize_tree(tasks))


def _finalize(tasks):
    atomic_tasks = {tid: t for tid, t in tasks.items() if t.is_atomic}
    resolved = _resolve_dependencies(tasks, atomic_tasks)
    return [
        {"id": tid, "description": atomic_tasks[tid].description, "dependencies": deps}
        for tid, deps in resolved.items()
    ]


def _serialize_tree(tasks):
    def build_node(task_id):
        task = tasks.get(task_id)
        if not task:
            return None
        return {
            "id": task.id, "description": task.description,
            "dependencies": task.dependencies, "is_atomic": task.is_atomic,
            "children": [build_node(cid) for cid in task.children],
        }
    return build_node("0") or {}


def _resolve_dependencies(all_tasks, atomic_tasks):
    resolved = {}
    for tid in atomic_tasks:
        collected = set()
        for ancestor_id in _ancestor_chain(tid):
            ancestor = all_tasks.get(ancestor_id)
            if ancestor:
                collected.update(ancestor.dependencies)
        collected.update(all_tasks[tid].dependencies)
        expanded = set()
        for dep_id in collected:
            if dep_id in atomic_tasks:
                expanded.add(dep_id)
            else:
                expanded.update(_get_atomic_descendants(all_tasks, dep_id, atomic_tasks))
        expanded.discard(tid)
        resolved[tid] = sorted(expanded)
    return resolved


def _ancestor_chain(task_id):
    parts = task_id.split("_")
    ancestors = []
    for i in range(len(parts) - 1, 0, -1):
        ancestors.append("_".join(parts[:i]))
    ancestors.append("0")
    return ancestors


def _get_atomic_descendants(all_tasks, task_id, atomic_tasks):
    result = set()
    task = all_tasks.get(task_id)
    if not task:
        return result
    if task_id in atomic_tasks:
        result.add(task_id)
        return result
    for child_id in task.children:
        result.update(_get_atomic_descendants(all_tasks, child_id, atomic_tasks))
    return result
