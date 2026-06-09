from backend.runtime.codex_cli import CodexCliRuntime


def test_build_command_uses_codex_exec_with_single_prompt_entrypoint(tmp_path):
    runtime = CodexCliRuntime(
        codex_bin="codex-test",
        model="gpt-test",
        reasoning_effort="high",
        verbosity="low",
        sandbox="workspace-write",
        timeout=10,
        inherit_proxy=False,
    )

    cmd = runtime._build_command(
        cwd=tmp_path,
        prompt="do work",
        output_path=tmp_path / "last.md",
        schema_path=tmp_path / "schema.json",
    )

    assert cmd[:3] == ["codex-test", "exec", "--json"]
    assert "--output-last-message" in cmd
    assert "--output-schema" in cmd
    model_index = cmd.index("--model")
    assert cmd[model_index:model_index + 2] == ["--model", "gpt-test"]
    assert cmd[-1] == "do work"


def test_build_env_inherits_proxy_when_enabled(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example")
    monkeypatch.setenv("OPENAI_API_KEY", "available-to-codex-cli")
    monkeypatch.setenv("UNRELATED_SECRET", "hidden")

    env = CodexCliRuntime(inherit_proxy=True)._build_env()

    assert env["HTTPS_PROXY"] == "http://proxy.example"
    assert env["OPENAI_API_KEY"] == "available-to-codex-cli"
    assert "UNRELATED_SECRET" not in env


def test_parse_events_preserves_codex_json_payload():
    stdout = "\n".join([
        '{"type":"thread.started","message":"started"}',
        '{"type":"item.completed","item":{"type":"command_execution","command":"pytest"}}',
        "not json",
    ])

    events = CodexCliRuntime.parse_events(stdout, task_id="t1")

    assert [event.type for event in events] == ["thread.started", "item.completed"]
    assert events[0].message == "started"
    assert events[1].message == "pytest"
    assert events[1].task_id == "t1"


def test_stage_reasoning_effort_prefers_phase_override(monkeypatch):
    from backend.config import settings
    from backend.pipeline.stage import Stage

    monkeypatch.setattr(settings, "codex_reasoning_effort", "medium")
    monkeypatch.setattr(settings, "codex_write_reasoning_effort", "high")
    monkeypatch.setattr(settings, "codex_polish_reasoning_effort", "xhigh")

    stage = Stage("write")

    assert stage._codex_reasoning_effort("Writer") == "high"
    assert stage._codex_reasoning_effort("Polish") == "xhigh"
