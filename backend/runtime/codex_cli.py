"""Shared Codex CLI runtime for all model calls."""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from backend.config import settings
from backend.core.research import RuntimeEvent


EventSink = Callable[[RuntimeEvent], None | Awaitable[None]]


class CodexCliRuntime:
    """Run one non-interactive Codex session and stream JSONL events."""

    def __init__(
        self,
        *,
        codex_bin: str | None = None,
        model: str | None = None,
        reasoning_effort: str | None = None,
        verbosity: str | None = None,
        sandbox: str | None = None,
        timeout: float | None = None,
        inherit_proxy: bool | None = None,
        event_sink: EventSink | None = None,
    ):
        self.codex_bin = codex_bin or settings.codex_bin
        self.model = model if model is not None else settings.codex_model
        self.reasoning_effort = reasoning_effort if reasoning_effort is not None else settings.codex_reasoning_effort
        self.verbosity = verbosity if verbosity is not None else settings.codex_verbosity
        self.sandbox = sandbox or settings.codex_sandbox
        self.timeout = float(timeout or settings.codex_timeout or settings.agent_session_timeout_seconds())
        self.inherit_proxy = settings.codex_inherit_proxy if inherit_proxy is None else inherit_proxy
        self.event_sink = event_sink

    async def run(
        self,
        *,
        instruction: str,
        user_text: str,
        cwd: Path,
        call_id: str,
        content_level: int,
        task_id: str = "",
        schema_path: Path | None = None,
    ) -> str:
        cwd.mkdir(parents=True, exist_ok=True)
        prompt = self._build_prompt(instruction, user_text)
        with tempfile.NamedTemporaryFile(prefix="maars_codex_", suffix=".md", delete=False) as tmp:
            output_path = Path(tmp.name)
        cmd = self._build_command(
            cwd=cwd,
            prompt=prompt,
            output_path=output_path,
            schema_path=schema_path,
        )
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self._build_env(),
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            output_path.unlink(missing_ok=True)
            raise TimeoutError(f"Codex call {call_id} timed out")

        stdout = stdout_b.decode("utf-8", errors="replace")
        stderr = stderr_b.decode("utf-8", errors="replace")
        for event in self.parse_events(stdout, task_id=task_id):
            await self._emit(event, fallback_call_id=call_id, fallback_level=content_level)

        result = ""
        if output_path.exists():
            result = output_path.read_text(encoding="utf-8", errors="replace")
            output_path.unlink(missing_ok=True)
        if proc.returncode != 0:
            detail = stderr.strip() or self._output_tail(stdout)
            raise RuntimeError(f"Codex call {call_id} failed with exit code {proc.returncode}: {detail}")
        return result.strip()

    def _build_command(
        self,
        *,
        cwd: Path,
        prompt: str,
        output_path: Path | None = None,
        schema_path: Path | None,
    ) -> list[str]:
        cmd = [
            self.codex_bin,
            "exec",
            "--json",
            "--ephemeral",
            "--skip-git-repo-check",
            "--sandbox",
            self.sandbox,
            "--cd",
            str(cwd),
            "-c",
            'shell_environment_policy.inherit="none"',
            "-c",
            'shell_environment_policy.include_only=["PATH","HOME","TMPDIR"]',
        ]
        if output_path:
            cmd.extend(["--output-last-message", str(output_path)])
        if self.model:
            cmd.extend(["--model", self.model])
        if self.reasoning_effort:
            cmd.extend(["-c", f'model_reasoning_effort="{self.reasoning_effort}"'])
        if self.verbosity:
            cmd.extend(["-c", f'model_verbosity="{self.verbosity}"'])
        if schema_path:
            cmd.extend(["--output-schema", str(schema_path)])
        cmd.append(prompt)
        return cmd

    @staticmethod
    def _build_prompt(instruction: str, user_text: str) -> str:
        return "\n\n".join([
            "# System Instructions",
            instruction.strip(),
            "# User Task",
            user_text.strip(),
        ]).strip()

    def _build_env(self) -> dict[str, str]:
        allowed = {
            "PATH",
            "HOME",
            "USER",
            "LOGNAME",
            "SHELL",
            "TMPDIR",
            "CODEX_HOME",
            "CODEX_API_KEY",
            "OPENAI_API_KEY",
            "CODEX_CA_CERTIFICATE",
            "SSL_CERT_FILE",
        }
        if self.inherit_proxy:
            allowed.update({
                "HTTP_PROXY",
                "HTTPS_PROXY",
                "ALL_PROXY",
                "NO_PROXY",
                "http_proxy",
                "https_proxy",
                "all_proxy",
                "no_proxy",
            })
        return {key: value for key, value in os.environ.items() if key in allowed and value}

    @staticmethod
    def parse_events(stdout: str, task_id: str = "") -> list[RuntimeEvent]:
        events: list[RuntimeEvent] = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            event_type = str(data.get("type", "codex.event"))
            message = str(data.get("text") or data.get("message") or "")
            item = data.get("item")
            if isinstance(item, dict):
                message = message or str(item.get("text", "") or item.get("command", ""))
            events.append(RuntimeEvent(type=event_type, task_id=task_id, message=message, payload=data))
        return events

    async def _emit(self, event: RuntimeEvent, *, fallback_call_id: str, fallback_level: int):
        if not self.event_sink:
            return
        payload = dict(event.payload)
        payload.setdefault("call_id", fallback_call_id)
        payload.setdefault("level", fallback_level)
        patched = RuntimeEvent(
            type=event.type,
            message=event.message,
            stage=event.stage,
            task_id=event.task_id,
            payload=payload,
        )
        result = self.event_sink(patched)
        if inspect.isawaitable(result):
            await result

    @staticmethod
    def _output_tail(stdout: str, max_lines: int = 12) -> str:
        lines = [line for line in stdout.splitlines() if line.strip()]
        return "\n".join(lines[-max_lines:])
