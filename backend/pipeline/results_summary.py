"""Results summary: collect research outputs into a structured JSON + Markdown report."""

from __future__ import annotations

import json
from pathlib import Path

from backend.db import ResearchDB


def build_results_summary(db: ResearchDB) -> tuple[dict, str]:
    """Build structured results data and render as markdown.

    Returns (data_dict, markdown_string).
    """
    data = _build_data(db)
    markdown = _render_markdown(data)
    return data, markdown


def _collect_artifact_manifest(root: Path) -> list[dict]:
    if not root.exists():
        return []
    return [
        {
            "path": str(fp.relative_to(root)).replace("\\", "/"),
            "size_bytes": fp.stat().st_size,
        }
        for fp in sorted(p for p in root.rglob("*") if p.is_file())
    ]


def _score_snapshot(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    snapshot = dict(data)
    snapshot["source"] = path.name
    return snapshot


def _build_data(db: ResearchDB) -> dict:
    plan_list = db.get_plan_list()
    evaluations = db.load_evaluations()
    meta = db.get_meta()
    artifacts_root = db.get_artifacts_dir()
    completed_tasks = []

    for task in plan_list:
        if task.get("status") != "completed":
            continue
        task_id = task["id"]
        task_artifacts_root = db.get_artifacts_dir(task_id)
        task_artifacts = []
        for fi in _collect_artifact_manifest(task_artifacts_root):
            fi = dict(fi)
            fi["path"] = f"artifacts/{task_id}/{fi['path']}"
            task_artifacts.append(fi)
        completed_tasks.append({
            "id": task_id,
            "description": task.get("description", ""),
            "summary": task.get("summary", ""),
            "status": task.get("status", ""),
            "batch": task.get("batch"),
            "dependencies": task.get("dependencies", []),
            "artifacts": task_artifacts,
            "best_score": _score_snapshot(task_artifacts_root / "best_score.json"),
        })

    artifact_manifest = []
    for fi in _collect_artifact_manifest(artifacts_root):
        fi = dict(fi)
        fi["path"] = f"artifacts/{fi['path']}"
        artifact_manifest.append(fi)

    figure_suffixes = {".png", ".jpg", ".jpeg", ".svg", ".pdf"}
    figures = [
        a for a in artifact_manifest
        if Path(a["path"]).suffix.lower() in figure_suffixes
    ]

    evaluation_rounds = []
    for idx, ev in enumerate(evaluations, start=1):
        suggestions = ev.get("suggestions", [])
        if isinstance(suggestions, str):
            suggestions = [suggestions] if suggestions else []
        evaluation_rounds.append({
            "round": idx,
            "score": ev.get("score"),
            "feedback": ev.get("feedback", ""),
            "suggestions": suggestions,
            "satisfied": bool(ev.get("satisfied")),
            "has_strategy_update": bool(ev.get("strategy_update", "").strip()),
        })

    return {
        "research_goal": db.get_refined_idea().strip(),
        "score_direction": "minimize" if db.get_score_minimize() else "maximize",
        "meta": meta,
        "best_score": _score_snapshot(artifacts_root / "best_score.json"),
        "latest_score": _score_snapshot(artifacts_root / "latest_score.json"),
        "evaluation_rounds": evaluation_rounds,
        "completed_tasks": completed_tasks,
        "artifact_manifest": artifact_manifest,
        "figures": figures,
    }


def _render_score_line(label: str, snapshot: dict | None) -> str:
    if not snapshot:
        return f"- {label}: unavailable"
    parts = [f"- {label}: score={snapshot.get('score')}"]
    for key in ("metric", "model", "source"):
        val = snapshot.get(key)
        if val:
            parts.append(f"{key}={val}")
    return ", ".join(parts)


def _render_markdown(data: dict) -> str:
    lines = [
        "# Results Summary",
        "",
        "## Research Goal",
        data.get("research_goal") or "(missing refined idea)",
        "",
        "## Score Snapshot",
        f"- Score direction: {data.get('score_direction', 'minimize')}",
        _render_score_line("Best score", data.get("best_score")),
        _render_score_line("Latest score", data.get("latest_score")),
    ]

    meta = data.get("meta", {})
    if meta:
        if meta.get("current_score") is not None:
            lines.append(f"- Meta current_score: {meta.get('current_score')}")
        if meta.get("previous_score") is not None:
            lines.append(f"- Meta previous_score: {meta.get('previous_score')}")
        if "improved" in meta:
            lines.append(f"- Meta improved: {meta.get('improved')}")

    lines.extend(["", "## Evaluation Rounds"])
    for ev in data.get("evaluation_rounds", []) or [{"_empty": True}]:
        if "_empty" in ev:
            lines.append("- No evaluation rounds recorded.")
            break
        lines.extend([
            "",
            f"### Round {ev['round']}",
            f"- Score: {ev.get('score')}",
            f"- Satisfied: {ev.get('satisfied')}",
            f"- Strategy update present: {ev.get('has_strategy_update')}",
        ])
        feedback = (ev.get("feedback") or "").strip()
        if feedback:
            lines.append(f"- Feedback: {feedback}")
        suggestions = ev.get("suggestions", [])
        if suggestions:
            lines.append("- Suggestions:")
            lines.extend([f"  - {s}" for s in suggestions])

    lines.extend(["", "## Completed Tasks"])
    for task in data.get("completed_tasks", []) or [{"_empty": True}]:
        if "_empty" in task:
            lines.append("- No completed tasks recorded.")
            break
        lines.extend([
            "",
            f"### Task [{task['id']}]",
            f"- Batch: {task.get('batch')}",
            f"- Dependencies: {', '.join(task.get('dependencies', [])) or '(none)'}",
            f"- Description: {task.get('description', '').strip()}",
            f"- Summary: {task.get('summary', '').strip()}",
        ])
        best = task.get("best_score")
        if best:
            lines.append(_render_score_line("Task best score", best))
        artifacts = task.get("artifacts", [])
        if artifacts:
            lines.append("- Artifacts:")
            lines.extend([f"  - {a['path']}" for a in artifacts])

    lines.extend(["", "## Figures"])
    figures = data.get("figures", [])
    if not figures:
        lines.append("- No figure-like artifacts detected.")
    else:
        lines.extend([f"- {a['path']}" for a in figures])

    lines.extend(["", "## Artifact Manifest"])
    manifest = data.get("artifact_manifest", [])
    if not manifest:
        lines.append("- No artifacts found.")
    else:
        lines.extend([f"- {a['path']} ({a['size_bytes']} bytes)" for a in manifest])

    return "\n".join(lines).strip() + "\n"
