import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path

from backend.core.research import RuntimeEvent
from backend.executors.codex import CodexExecutor
from backend.executors.task import TaskContext
from backend.sandbox import DockerCodexSandboxProvider


class CodexExecutorTests(unittest.TestCase):
    def test_command_uses_json_schema_and_restricted_shell_environment(self):
        executor = CodexExecutor(codex_bin="codex", model="gpt-test")
        cmd = executor._build_command(
            codex_bin="codex",
            cwd="/tmp/work",
            schema_path="/tmp/work/schema.json",
            prompt="prompt text",
            reasoning_effort="high",
            verbosity="low",
        )

        self.assertIn("--json", cmd)
        self.assertIn("--ephemeral", cmd)
        self.assertIn("--skip-git-repo-check", cmd)
        self.assertIn("--output-schema", cmd)
        self.assertIn("--model", cmd)
        self.assertIn("gpt-test", cmd)
        self.assertIn('model_reasoning_effort="high"', cmd)
        self.assertIn('model_verbosity="low"', cmd)
        self.assertIn('shell_environment_policy.inherit="none"', cmd)
        self.assertIn(
            'shell_environment_policy.include_only=["PATH","HOME","TMPDIR"]',
            cmd,
        )

    def test_docker_provider_wraps_codex_command_with_workspace_mount(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            provider = DockerCodexSandboxProvider(
                image="maars-codex:test",
                docker_bin="docker",
                container_codex_bin="codex",
                gpus="all",
            )
            context = TaskContext(
                session_id="s1",
                task_id="t1",
                description="run experiment",
                workspace_dir=root / "workspace",
                artifacts_dir=root / "artifacts",
            )

            session = provider.prepare(context, ".schema.json")
            wrapped = session.wrap_command([
                session.codex_bin,
                "exec",
                "--cd",
                session.codex_cwd,
                "--output-schema",
                session.schema_path,
                "prompt",
            ])

            self.assertEqual(wrapped[:2], ["docker", "run"])
            self.assertIn("maars-codex:test", wrapped)
            self.assertIn("--gpus", wrapped)
            self.assertIn("all", wrapped)
            self.assertIn(f"{context.workspace_dir}:/workspace", wrapped)
            self.assertIn("/workspace/.schema.json", wrapped)

    def test_final_payload_is_parsed_from_agent_message_event(self):
        events = [
            RuntimeEvent(
                type="item.completed",
                task_id="1",
                payload={
                    "item": {
                        "type": "agent_message",
                        "text": (
                            '{"markdown": "done", "summary": "SUMMARY", '
                            '"artifacts": [{"path": "artifacts/a.txt"}], '
                            '"best_score": null, "warnings": []}'
                        ),
                    }
                },
            )
        ]

        payload = CodexExecutor._parse_final_payload(events, "")

        self.assertEqual(payload["markdown"], "done")
        self.assertEqual(payload["summary"], "SUMMARY")
        self.assertEqual(payload["artifacts"][0]["path"], "artifacts/a.txt")

    def test_final_payload_is_parsed_from_top_level_agent_message_event(self):
        events = [
            RuntimeEvent(
                type="agent_message",
                task_id="1",
                payload={
                    "text": (
                        '{"markdown": "done", "summary": "SUMMARY", '
                        '"artifacts": [], "best_score": null, "warnings": []}'
                    ),
                },
            )
        ]

        payload = CodexExecutor._parse_final_payload(events, "")

        self.assertEqual(payload["markdown"], "done")

    def test_prompt_includes_task_and_dependency_context(self):
        executor = CodexExecutor()
        context = TaskContext(
            session_id="s1",
            task_id="t1",
            description="run experiment",
            workspace_dir=Path("/tmp/work"),
            artifacts_dir=Path("/tmp/artifacts"),
            dependencies=("d1",),
            dependency_summaries={"d1": "prepared data"},
            metadata={"output_language": "Chinese"},
        )

        prompt = executor._build_prompt(context)

        self.assertIn("Task ID: t1", prompt)
        self.assertIn("Description: run experiment", prompt)
        self.assertIn("Output language: Chinese", prompt)
        self.assertIn("Artifact Contract", prompt)
        self.assertIn("Write every durable output under `./artifacts/`", prompt)
        self.assertIn("[d1] prepared data", prompt)
        self.assertIn("final response must satisfy", prompt)

    def test_build_env_inherits_global_proxy_by_default(self):
        with patch.dict(
            "os.environ",
            {"PATH": "/bin", "HTTPS_PROXY": "http://127.0.0.1:7890"},
            clear=True,
        ):
            env = CodexExecutor()._build_env()

        self.assertEqual(env["HTTPS_PROXY"], "http://127.0.0.1:7890")

    def test_build_env_can_disable_proxy_inheritance(self):
        with patch.dict(
            "os.environ",
            {"PATH": "/bin", "HTTPS_PROXY": "http://127.0.0.1:7890"},
            clear=True,
        ):
            env = CodexExecutor(inherit_proxy=False)._build_env()

        self.assertNotIn("HTTPS_PROXY", env)

    def test_sync_workspace_artifacts_copies_nested_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "workspace" / "artifacts"
            target = root / "session" / "artifacts" / "t1"
            source.joinpath("plots").mkdir(parents=True)
            source.joinpath("plots", "curve.png").write_text("png", encoding="utf-8")

            CodexExecutor._sync_workspace_artifacts(source, target)

            self.assertEqual(
                target.joinpath("plots", "curve.png").read_text(encoding="utf-8"),
                "png",
            )

    def test_artifact_refs_normalize_paths_under_artifacts(self):
        refs = CodexExecutor._artifact_refs({
            "artifacts": [
                {"path": "./artifacts/plots/curve.png", "kind": None, "size_bytes": 3},
                {"path": "/tmp/work/artifacts/metrics/result.json", "kind": "json"},
            ],
        })

        self.assertEqual(refs[0].path, "plots/curve.png")
        self.assertEqual(refs[0].kind, "file")
        self.assertEqual(refs[1].path, "metrics/result.json")
        self.assertEqual(refs[1].kind, "json")


if __name__ == "__main__":
    unittest.main()
