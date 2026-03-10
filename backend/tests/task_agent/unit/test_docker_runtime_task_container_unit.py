from pathlib import Path

import anyio

from task_agent import docker_runtime


async def _run_ensure(tmp_path, monkeypatch):
    import db

    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(docker_runtime, "_docker_bin", lambda: "docker")

    async def fake_status(*, enabled=True, container_name=None):
        return {
            "enabled": enabled,
            "available": True,
            "connected": True,
            "containerRunning": False,
            "containerName": container_name or "",
        }

    captured = {"run_cmd": None}

    async def fake_run(args, timeout=120):
        if args[:2] == ["docker", "inspect"]:
            return {"ok": False, "code": 1, "stdout": "", "stderr": "not found", "args": args}
        if len(args) >= 3 and args[1] == "run":
            captured["run_cmd"] = args
            return {"ok": True, "code": 0, "stdout": "container-id", "stderr": "", "args": args}
        return {"ok": True, "code": 0, "stdout": "", "stderr": "", "args": args}

    monkeypatch.setattr(docker_runtime, "get_local_docker_status", fake_status)
    monkeypatch.setattr(docker_runtime, "_run_docker_cmd", fake_run)

    skills_dir = tmp_path / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    runtime = await docker_runtime.ensure_execution_container(
        execution_run_id="exec_test",
        idea_id="idea_fixture",
        plan_id="plan_fixture",
        task_id="1_1",
        skills_dir=skills_dir,
        image="python:3.11-slim",
    )

    run_cmd = captured["run_cmd"]
    assert run_cmd is not None
    run_cmd_text = " ".join(str(x) for x in run_cmd)

    assert runtime["taskId"] == "1_1"
    assert runtime["containerName"].startswith("maars-task-exec_test-1_1")
    assert "dst=/workdir/src" in run_cmd_text
    assert "dst=/workdir/step" in run_cmd_text
    assert "--workdir /workdir/src" in run_cmd_text

    expected_src = (tmp_path / "idea_fixture" / "plan_fixture" / "1_1" / "src").resolve()
    expected_step = (tmp_path / "idea_fixture" / "plan_fixture" / "1_1" / "step").resolve()
    assert Path(runtime["srcDir"]).resolve() == expected_src
    assert Path(runtime["stepDir"]).resolve() == expected_step


def test_ensure_execution_container_uses_per_task_src_and_step_mounts(tmp_path, monkeypatch):
    anyio.run(_run_ensure, tmp_path, monkeypatch)
