"""Docker-based code execution tools for agents.

Runs code in isolated containers with file artifacts persisted
to research/{id}/artifacts/{task_id}/. All file operations go
through ResearchDB.

Container execution is async: blocking Docker SDK calls run in a
worker thread via asyncio.to_thread(), keeping the event loop responsive.
"""

import asyncio
import json
import re
import threading
import time
from pathlib import Path

from backend.config import settings
from backend.db import ResearchDB, _current_task_id


# ---------------------------------------------------------------------------
# Input sanitization
# ---------------------------------------------------------------------------

# Valid pip package specifier: name with optional extras and version constraint.
# Examples: "numpy", "pandas>=2.0", "scikit-learn==1.3.0", "pkg[extra1,extra2]"
_PKG_PATTERN = re.compile(
    r'^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?'   # package name
    r'(\[[A-Za-z0-9,._-]+\])?'                        # optional extras
    r'([<>=!~]+[A-Za-z0-9.*]+)?$'                      # optional version
)


_ALLOWED_LANGUAGES = {"python", "Rscript"}


def validate_language(language: str) -> str:
    """Validate language parameter against a strict whitelist.

    Raises ValueError if the language is not allowed.
    """
    if language not in _ALLOWED_LANGUAGES:
        raise ValueError(
            f"Unsupported language: {language!r}. Allowed: {sorted(_ALLOWED_LANGUAGES)}"
        )
    return language


def sanitize_requirements(requirements: str) -> str:
    """Validate and sanitize pip requirements string.

    Accepts space-separated package specifiers (e.g. "numpy pandas>=2.0").
    Rejects any token containing shell metacharacters or that doesn't match
    a valid pip package pattern.

    Returns the cleaned requirements string (only valid packages).
    Raises ValueError if any token looks like a shell injection attempt.
    """
    if not requirements or not requirements.strip():
        return ""

    # Reject obvious shell injection patterns early
    shell_chars = set(';|&$`\\(){}!#\n\r')
    if shell_chars & set(requirements):
        raise ValueError(
            f"Requirements string contains shell metacharacters: {requirements!r}"
        )

    tokens = requirements.strip().split()
    validated = []
    for token in tokens:
        if not _PKG_PATTERN.match(token):
            raise ValueError(
                f"Invalid package specifier: {token!r}. "
                "Only package names with optional version constraints are allowed."
            )
        validated.append(token)

    return " ".join(validated)


# ---------------------------------------------------------------------------
# Shared Docker client + container tracking
# ---------------------------------------------------------------------------

_docker_client = None
_docker_lock = threading.Lock()
_active_containers: list = []  # track running containers for graceful stop
_containers_lock = threading.Lock()

# Async concurrency limiter — created lazily (no event loop at import time).
# Keyed by event loop to avoid cross-loop reuse.
_async_semaphore: dict[int, asyncio.Semaphore] = {}
_semaphore_lock = threading.Lock()


def _get_semaphore() -> asyncio.Semaphore:
    """Return the shared asyncio.Semaphore for the current event loop."""
    loop_id = id(asyncio.get_running_loop())
    if loop_id not in _async_semaphore:
        with _semaphore_lock:
            if loop_id not in _async_semaphore:
                _async_semaphore[loop_id] = asyncio.Semaphore(
                    settings.docker_sandbox_concurrency,
                )
    return _async_semaphore[loop_id]


def kill_all_containers():
    """Kill all active containers. Called on pipeline pause/stop."""
    with _containers_lock:
        snapshot = list(_active_containers)
    for container in snapshot:
        try:
            container.kill()
        except Exception:
            pass


def _get_docker_client():
    """Return a shared Docker client, reconnecting if the connection dropped.

    Thread-safe: called from worker threads via asyncio.to_thread().
    """
    global _docker_client
    with _docker_lock:
        for attempt in range(3):
            try:
                if _docker_client is None:
                    import docker
                    _docker_client = docker.from_env()
                _docker_client.ping()
                return _docker_client
            except Exception as e:
                _docker_client = None
                if attempt == 2:
                    raise RuntimeError(f"Docker not available after 3 attempts: {e}")
                time.sleep(2)


# ---------------------------------------------------------------------------
# Blocking container execution (runs in worker thread)
# ---------------------------------------------------------------------------

def _run_container_sync(shell_cmd: str, volumes: dict) -> dict:
    """Execute a Docker container synchronously.

    Called via asyncio.to_thread() so blocking calls (container.wait,
    container.logs) do NOT block the event loop.
    """
    try:
        client = _get_docker_client()
    except Exception as e:
        return {"error": str(e)}

    container = None
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
        with _containers_lock:
            _active_containers.append(container)

        try:
            result = container.wait(timeout=settings.docker_sandbox_timeout)
            exit_code = result["StatusCode"]
            timed_out = False
        except (ConnectionError, TimeoutError, OSError) as e:
            try:
                container.kill()
            except Exception:
                pass
            exit_code = -1
            timed_out = True
        except Exception as e:
            try:
                container.kill()
            except Exception:
                pass
            return {"error": f"Docker error during container wait: {e}"}

        stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
        stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
        container.remove(force=True)

        return {
            "stdout": stdout[-5000:],
            "stderr": stderr[-2000:],
            "exit_code": exit_code,
            "timed_out": timed_out,
        }

    except Exception as e:
        return {"error": f"Container execution failed: {e}"}
    finally:
        if container is not None:
            with _containers_lock:
                try:
                    _active_containers.remove(container)
                except ValueError:
                    pass


# ---------------------------------------------------------------------------
# Tool factory
# ---------------------------------------------------------------------------

def create_docker_tools(db: ResearchDB) -> list:
    """Create Docker execution tools bound to a research session."""

    async def code_execute(code: str, language: str = "python", requirements: str = "") -> str:
        """Execute code in an isolated Docker container.

        Args:
            code: Source code to execute.
            language: 'python' (default).
            requirements: Space-separated pip packages to install before execution.

        Returns:
            JSON with: stdout, stderr, exit_code, timed_out, files.
        """
        # Validate language against whitelist
        try:
            language = validate_language(language)
        except ValueError as e:
            return json.dumps({"error": str(e)})

        # Save script via DB (fast I/O, safe on event loop)
        script_path, script_name = db.save_script(code, language)
        task_artifacts = script_path.parent
        artifacts_root = db.get_artifacts_dir()
        tasks_dir = db.get_tasks_dir() if db.research_id else None

        # Track for reproduce file generation
        db.execution_log.append({
            "task_id": _current_task_id.get() or "",
            "script": script_name,
            "language": language,
            "requirements": requirements.strip(),
        })

        # Build command
        cmd_parts = []
        if requirements.strip():
            try:
                safe_reqs = sanitize_requirements(requirements)
            except ValueError as e:
                return json.dumps({"error": f"Invalid requirements: {e}"})
            if safe_reqs:
                cmd_parts.append(f"pip install --quiet {safe_reqs}")
        cmd_parts.append(f"cd /workspace/output && {language} /workspace/output/{script_name}")
        shell_cmd = " && ".join(cmd_parts)

        # Volume mounts
        volumes = {
            str(task_artifacts.resolve()): {"bind": "/workspace/output", "mode": "rw"},
            str(artifacts_root.resolve()): {"bind": "/workspace/artifacts", "mode": "ro"},
        }
        if tasks_dir and tasks_dir.exists():
            volumes[str(tasks_dir.resolve())] = {"bind": "/workspace/input", "mode": "ro"}
        if settings.dataset_dir:
            dataset_path = Path(settings.dataset_dir).resolve()
            if dataset_path.exists():
                volumes[str(dataset_path)] = {"bind": "/workspace/data", "mode": "ro"}

        # Run container: semaphore limits concurrency, to_thread avoids blocking
        async with _get_semaphore():
            container_result = await asyncio.to_thread(
                _run_container_sync, shell_cmd, volumes,
            )

        if "error" in container_result:
            return json.dumps(container_result)

        # Auto-promote best_score.json via DB
        db.promote_best_score()

        # List files in this task's artifacts
        files = sorted(f.name for f in task_artifacts.iterdir() if f.is_file())

        return json.dumps({
            **container_result,
            "script": script_name,
            "files": files,
        }, indent=2)

    def list_artifacts() -> str:
        """List all files in the current task's artifacts directory."""
        try:
            artifacts_dir = db.get_artifacts_dir(_current_task_id.get())
        except RuntimeError:
            return "No active research session."

        files = []
        for f in sorted(artifacts_dir.iterdir()):
            if f.is_file():
                files.append({"filename": f.name, "size_bytes": f.stat().st_size})

        return json.dumps(files, indent=2) if files else "No artifacts produced yet."

    return [code_execute, list_artifacts]
