"""Docker-based code execution tools for agents.

Uses a **persistent session container**: a single Docker container is kept
alive for the entire research session.  Every ``code_execute`` call runs
inside it via ``exec_run`` so installed packages, environment variables and
temp files survive across calls — eliminating redundant ``pip install``
overhead that previously cost ~190 s per task.
"""

import asyncio
import json
import logging
import threading
from pathlib import Path

from backend.config import settings
from backend.db import ResearchDB

log = logging.getLogger(__name__)

_active_containers: list = []
_containers_lock = threading.Lock()


def kill_all_containers():
    """Kill and remove every container tracked by this module."""
    with _containers_lock:
        snapshot = list(_active_containers)
        _active_containers.clear()
    for container in snapshot:
        try:
            container.kill()
        except Exception:
            pass
        try:
            container.remove(force=True)
        except Exception:
            pass


def _get_docker_client():
    import docker
    return docker.from_env()


# ---------------------------------------------------------------------------
# Persistent session container
# ---------------------------------------------------------------------------

class _SessionContainer:
    """Keeps one Docker container alive and reuses it for every
    ``code_execute`` call in the same research session.
    """

    def __init__(self):
        self._container = None
        self._lock = threading.Lock()
        self._session_id: str = ""

    def get_or_create(self, client, volumes, session_id: str = ""):
        """Return the running container, creating one if necessary.

        If *session_id* changed since the last creation the old container is
        torn down first so that volume mounts point to the new session dirs.
        """
        with self._lock:
            if self._container is not None:
                if session_id and self._session_id != session_id:
                    log.info("Session changed (%s -> %s), recycling container",
                             self._session_id, session_id)
                    self._teardown()
                else:
                    try:
                        self._container.reload()
                        if self._container.status == "running":
                            return self._container
                    except Exception:
                        pass
                    self._teardown()

            run_kwargs = dict(
                image=settings.docker_sandbox_image,
                command=["sleep", "infinity"],
                volumes=volumes,
                mem_limit=settings.docker_sandbox_memory,
                cpu_quota=int(settings.docker_sandbox_cpu * 100000),
                network_disabled=not settings.docker_sandbox_network,
                detach=True,
            )
            if settings.docker_sandbox_gpu:
                import docker as _docker
                run_kwargs["device_requests"] = [
                    _docker.types.DeviceRequest(count=-1, capabilities=[["gpu"]])
                ]

            self._container = client.containers.run(**run_kwargs)
            self._session_id = session_id
            with _containers_lock:
                _active_containers.append(self._container)

            self._container.exec_run(
                ["chown", "sandbox:sandbox", "/workspace"], user="root",
            )
            log.info("Created persistent sandbox container %s",
                     self._container.short_id)
            return self._container

    def cleanup(self):
        with self._lock:
            self._teardown()

    def _teardown(self):
        c = self._container
        if c is None:
            return
        self._container = None
        with _containers_lock:
            try:
                _active_containers.remove(c)
            except ValueError:
                pass
        try:
            c.kill()
        except Exception:
            pass
        try:
            c.remove(force=True)
        except Exception:
            pass


def _exec_in_container(container, shell_cmd, timeout):
    """Run *shell_cmd* inside a running container with a per-execution
    time limit enforced by the coreutils ``timeout`` utility.
    """
    result = container.exec_run(
        ["timeout", "--signal=KILL", str(int(timeout)),
         "bash", "-c", shell_cmd],
        demux=True,
    )
    stdout_b, stderr_b = result.output
    stdout = (stdout_b or b"").decode("utf-8", errors="replace")
    stderr = (stderr_b or b"").decode("utf-8", errors="replace")
    timed_out = result.exit_code in (124, 137)
    return stdout, stderr, result.exit_code, timed_out


# ---------------------------------------------------------------------------
# Tool factory
# ---------------------------------------------------------------------------

def create_docker_tools(db: ResearchDB) -> list:
    session = _SessionContainer()

    def _build_volumes():
        artifacts_root = db.get_artifacts_dir()
        vols = {
            str(artifacts_root.resolve()): {
                "bind": "/workspace/artifacts", "mode": "rw",
            },
        }
        if db.research_id:
            tasks_dir = db.get_tasks_dir()
            tasks_dir.mkdir(parents=True, exist_ok=True)
            vols[str(tasks_dir.resolve())] = {
                "bind": "/workspace/input", "mode": "ro",
            }
        if settings.dataset_dir:
            ds = Path(settings.dataset_dir).resolve()
            if ds.exists():
                vols[str(ds)] = {"bind": "/workspace/data", "mode": "ro"}
        return vols

    async def code_execute(code: str, language: str = "python",
                           requirements: str = "") -> str:
        """Execute code in the Docker sandbox (container is reused across
        calls; installed packages and files persist for the session)."""
        try:
            client = _get_docker_client()
        except Exception as e:
            return json.dumps({"error": str(e)})

        script_path, script_name = db.save_script(code, language)
        task_artifacts = script_path.parent
        task_id = db.current_task_id or "_default"
        safe_task_id = task_id.replace("/", "_")

        db.append_execution_log(
            task_id=db.current_task_id or "",
            script=script_name,
            language=language,
            requirements=requirements.strip(),
        )

        task_dir = f"/workspace/artifacts/{safe_task_id}"
        cmd_parts = [
            f"mkdir -p {task_dir}",
            f"ln -sfn {task_dir} /workspace/output",
            "cd /workspace/output",
        ]
        if requirements.strip():
            cmd_parts.append(f"pip install --quiet {requirements}")
        cmd_parts.append(
            f"{language} /workspace/output/{script_name}")
        shell_cmd = " && ".join(cmd_parts)

        try:
            container = session.get_or_create(
                client, _build_volumes(), db.research_id,
            )
            stdout, stderr, exit_code, timed_out = await asyncio.to_thread(
                _exec_in_container, container, shell_cmd,
                settings.docker_sandbox_timeout,
            )
        except Exception as e:
            return json.dumps({"error": f"Container execution failed: {e}"})

        db.promote_best_score()
        files = sorted(f.name for f in task_artifacts.iterdir()
                       if f.is_file())

        return json.dumps({
            "stdout": stdout[-5000:],
            "stderr": stderr[-2000:],
            "exit_code": exit_code,
            "timed_out": timed_out,
            "script": script_name,
            "files": files,
        }, indent=2)

    def list_artifacts() -> str:
        """List all files in the artifacts directory. During task execution,
        lists the current task's artifacts. Otherwise lists all artifacts
        recursively with relative paths."""
        try:
            task_id = db.current_task_id
            artifacts_dir = db.get_artifacts_dir(task_id)
        except RuntimeError:
            return "No active research session."
        files = []
        if task_id:
            for f in sorted(artifacts_dir.iterdir()):
                if f.is_file():
                    files.append({"filename": f.name,
                                  "size_bytes": f.stat().st_size})
        else:
            for f in sorted(artifacts_dir.rglob("*")):
                if f.is_file():
                    rel = str(f.relative_to(artifacts_dir))
                    files.append({"path": rel,
                                  "size_bytes": f.stat().st_size})
        return json.dumps(files, indent=2) if files else \
            "No artifacts produced yet."

    return [code_execute, list_artifacts]
