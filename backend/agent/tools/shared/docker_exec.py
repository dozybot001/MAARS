"""Docker-based code execution tools for agents.

Runs code in isolated containers with file artifacts persisted
to research/{id}/artifacts/. Scripts are kept alongside outputs
for full reproducibility.

After all experiments, generate_reproduce_files() creates
Dockerfile + run.sh + docker-compose.yml for one-command reproduction.
"""

import json
import hashlib
import time
from pathlib import Path

from backend.config import settings
from backend.db import ResearchDB

# Module-level registry: tracks all code_execute calls per session
_execution_log: list[dict] = []


def create_docker_tools(db: ResearchDB) -> list:
    """Create Docker execution tools bound to a research session."""

    def code_execute(code: str, language: str = "python", requirements: str = "") -> str:
        """Execute code in an isolated Docker container.

        Args:
            code: Source code to execute.
            language: 'python' (default). More languages in the future.
            requirements: Space-separated pip packages to install before execution.

        Returns:
            JSON with: stdout, stderr, exit_code, timed_out, files (list of artifact filenames).

        Files written to /workspace/output/ inside the container are persisted
        to the research session's artifacts directory. The script itself is
        also preserved for reproducibility.
        """
        try:
            import docker
            from docker.errors import DockerException
        except ImportError:
            return json.dumps({"error": "Docker SDK not installed. pip install docker"})

        try:
            client = docker.from_env()
        except Exception as e:
            return json.dumps({"error": f"Docker not available: {e}"})

        # Prepare directories
        artifacts_dir = db.get_artifacts_dir()
        tasks_dir = db._root / "tasks" if db._root else None

        # Write script with a unique name
        timestamp = int(time.time())
        code_hash = hashlib.md5(code.encode()).hexdigest()[:6]
        ext = ".py" if language == "python" else ".r"
        script_name = f"run_{timestamp}_{code_hash}{ext}"
        script_path = artifacts_dir / script_name
        script_path.write_text(code, encoding="utf-8")

        # Track this execution for reproduce file generation
        _execution_log.append({
            "script": script_name,
            "language": language,
            "requirements": requirements.strip(),
        })

        # Build command
        cmd_parts = []
        if requirements.strip():
            cmd_parts.append(f"pip install --quiet {requirements}")
        cmd_parts.append(f"cd /workspace/output && {language} /workspace/output/{script_name}")
        shell_cmd = " && ".join(cmd_parts)

        # Volume mounts
        volumes = {
            str(artifacts_dir.resolve()): {"bind": "/workspace/output", "mode": "rw"},
        }
        if tasks_dir and tasks_dir.exists():
            volumes[str(tasks_dir.resolve())] = {"bind": "/workspace/input", "mode": "ro"}

        # Run container
        try:
            container = client.containers.run(
                image=settings.docker_sandbox_image,
                command=["bash", "-c", shell_cmd],
                volumes=volumes,
                mem_limit=settings.docker_sandbox_memory,
                cpu_quota=int(settings.docker_sandbox_cpu * 100000),
                network_disabled=not settings.docker_sandbox_network,
                detach=True,
            )

            # Wait with timeout
            try:
                result = container.wait(timeout=settings.docker_sandbox_timeout)
                exit_code = result["StatusCode"]
                timed_out = False
            except Exception:
                container.kill()
                exit_code = -1
                timed_out = True

            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            container.remove(force=True)

        except Exception as e:
            return json.dumps({"error": f"Container execution failed: {e}"})

        # List all files in artifacts (including the script)
        files = sorted(f.name for f in artifacts_dir.iterdir() if f.is_file())

        return json.dumps({
            "stdout": stdout[-5000:],
            "stderr": stderr[-2000:],
            "exit_code": exit_code,
            "timed_out": timed_out,
            "script": script_name,
            "files": files,
        }, indent=2)

    def list_artifacts() -> str:
        """List all files in the artifacts directory for this research session.
        Includes experiment scripts and their outputs."""
        try:
            artifacts_dir = db.get_artifacts_dir()
        except RuntimeError:
            return "No active research session."

        files = []
        for f in sorted(artifacts_dir.iterdir()):
            if f.is_file():
                files.append({"filename": f.name, "size_bytes": f.stat().st_size})

        if not files:
            return "No artifacts produced yet."
        return json.dumps(files, indent=2)

    return [code_execute, list_artifacts]


def generate_reproduce_files(db: ResearchDB):
    """Generate Docker reproduction files from the execution log.

    Creates in the research root:
    - Dockerfile.experiment — environment with all dependencies
    - scripts/ — copies of all experiment scripts (ordered)
    - run.sh — executes all scripts in order
    - docker-compose.yml — one-command reproduction

    Called automatically by ExecuteStage.finalize().
    """
    global _execution_log
    if not _execution_log:
        return

    root = db._root
    if not root:
        return

    scripts_dir = root / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    artifacts_dir = root / "artifacts"

    # Collect unique requirements and ordered scripts
    all_requirements: set[str] = set()
    ordered_scripts: list[str] = []

    for entry in _execution_log:
        script_name = entry["script"]
        if entry["requirements"]:
            for pkg in entry["requirements"].split():
                all_requirements.add(pkg)
        ordered_scripts.append(script_name)

        # Copy script to scripts/ directory
        src = artifacts_dir / script_name
        if src.exists():
            (scripts_dir / script_name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    # --- Dockerfile.experiment ---
    pip_line = ""
    if all_requirements:
        pip_line = f"RUN pip install --no-cache-dir {' '.join(sorted(all_requirements))}\n"

    dockerfile = f"""\
FROM {settings.docker_sandbox_image}
USER root
{pip_line}COPY scripts/ /workspace/scripts/
COPY run.sh /workspace/run.sh
RUN chmod +x /workspace/run.sh && chown -R sandbox:sandbox /workspace
USER sandbox
WORKDIR /workspace
CMD ["bash", "run.sh"]
"""
    (root / "Dockerfile.experiment").write_text(dockerfile, encoding="utf-8")

    # --- run.sh ---
    lines = ["#!/bin/bash", "set -e", "mkdir -p /workspace/results", ""]
    for script in ordered_scripts:
        lines.append(f'echo "=== Running {script} ==="')
        lines.append(f"cd /workspace/results && python /workspace/scripts/{script}")
        lines.append("")
    lines.append('echo "All experiments completed. Results in /workspace/results/"')

    (root / "run.sh").write_text("\n".join(lines), encoding="utf-8")

    # --- docker-compose.yml ---
    compose = f"""\
services:
  experiment:
    build:
      context: .
      dockerfile: Dockerfile.experiment
    volumes:
      - ./results:/workspace/results
"""
    (root / "docker-compose.yml").write_text(compose, encoding="utf-8")

    # Clear log for next session
    _execution_log.clear()
