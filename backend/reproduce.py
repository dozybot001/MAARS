"""Generate Docker reproduction files from a research session's execution log."""

from backend.config import settings
from backend.db import ResearchDB


def generate_reproduce_files(db: ResearchDB):
    if not db.research_id:
        return
    execution_log = db.get_execution_log()
    if not execution_log:
        return

    all_requirements: set[str] = set()
    ordered_scripts: list[dict] = []

    for entry in execution_log:
        if entry.get("requirements"):
            for pkg in entry["requirements"].split():
                all_requirements.add(pkg)
        ordered_scripts.append({
            "task_id": entry.get("task_id", ""),
            "script": entry["script"],
        })

    pip_line = ""
    if all_requirements:
        pip_line = f"RUN pip install --no-cache-dir {' '.join(sorted(all_requirements))}\n"

    dockerfile = f"""\
FROM {settings.docker_sandbox_image}
USER root
{pip_line}COPY artifacts/ /workspace/artifacts/
COPY reproduce/run.sh /workspace/run.sh
RUN chmod +x /workspace/run.sh && chown -R sandbox:sandbox /workspace
USER sandbox
WORKDIR /workspace
CMD ["bash", "run.sh"]
"""

    lines = ["#!/bin/bash", "set -e", "mkdir -p /workspace/results", ""]
    for entry in ordered_scripts:
        task_id = entry["task_id"]
        script = entry["script"]
        path = f"/workspace/artifacts/{task_id}/{script}" if task_id else f"/workspace/artifacts/{script}"
        lines.append(f'echo "=== Running {task_id}/{script} ==="')
        lines.append(f"cd /workspace/results && python {path}")
        lines.append("")
    lines.append('echo "All experiments completed."')
    run_sh = "\n".join(lines)

    gpu_line = "    gpus: all\n" if settings.docker_sandbox_gpu else ""
    compose = f"""\
services:
  experiment:
    build:
      context: ..
      dockerfile: reproduce/Dockerfile
    volumes:
      - ./results:/workspace/results
{gpu_line}"""

    db.save_reproduce_files(dockerfile, run_sh, compose)
