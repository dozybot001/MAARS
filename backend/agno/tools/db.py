"""DB access tools for agents — scoped to pipeline-defined boundaries."""

import json
from backend.db import ResearchDB


def create_db_tools(db: ResearchDB) -> list:
    def read_task_output(task_id: str) -> str:
        """Read the output of a previously completed task by its ID."""
        output = db.get_task_output(task_id)
        return output if output else f"No output found for task {task_id}"

    def list_tasks() -> str:
        """List all completed atomic tasks with their IDs and output sizes."""
        tasks = db.list_completed_tasks()
        if not tasks:
            return "No tasks completed yet."
        return json.dumps(tasks, indent=2)

    def read_refined_idea() -> str:
        """Read the refined research idea produced by the Refine stage."""
        return db.get_refined_idea() or "No refined idea available."

    def read_plan_tree() -> str:
        """Read the full decomposition tree."""
        tree = db.get_plan_tree()
        return json.dumps(tree, indent=2) if tree else "No plan tree available."

    return [read_task_output, list_tasks, read_refined_idea, read_plan_tree]
