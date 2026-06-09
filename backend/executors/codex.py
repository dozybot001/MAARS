"""Codex CLI task executor."""

from __future__ import annotations

import asyncio
import inspect
import json
import shutil
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from backend.core.research import ArtifactRef, RuntimeEvent
from backend.executors.task import TaskContext, TaskExecutionResult
from backend.runtime.codex_cli import CodexCliRuntime
from backend.sandbox import CodexSandboxProvider, LocalCodexSandboxProvider
from backend.utils import parse_json_fenced


CODEX_TASK_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "markdown": {
            "type": "string",
            "description": "Complete markdown result for the research task.",
        },
        "summary": {
            "type": "string",
            "description": "One-line task summary with filenames and key numeric results.",
        },
        "artifacts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "kind": {"type": ["string", "null"]},
                    "size_bytes": {"type": ["integer", "null"]},
                },
                "required": ["path", "kind", "size_bytes"],
                "additionalProperties": False,
            },
        },
        "best_score": {
            "type": ["object", "null"],
            "properties": {
                "metric": {"type": ["string", "null"]},
                "value": {"type": ["number", "string", "null"]},
                "direction": {"type": ["string", "null"]},
            },
            "required": ["metric", "value", "direction"],
            "additionalProperties": False,
        },
        "warnings": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["markdown", "summary", "artifacts", "best_score", "warnings"],
    "additionalProperties": False,
}


EventSink = Callable[[RuntimeEvent], None | Awaitable[None]]
CODEX_TASK_SCHEMA_FILENAME = ".maars_codex_task_result.schema.json"


class CodexExecutor:
    """Run an atomic research task through `codex exec`.

    The executor is intentionally provider-neutral from MAARS' perspective:
    it returns a `TaskExecutionResult` and exposes Codex JSONL events as runtime
    events, while keeping Codex authentication and sandbox details localized.
    """

    def __init__(
        self,
        codex_bin: str = "codex",
        model: str | None = None,
        reasoning_effort: str | None = None,
        verbosity: str | None = None,
        sandbox: str = "workspace-write",
        timeout: float | None = None,
        inherit_proxy: bool = True,
        event_sink: EventSink | None = None,
        sandbox_provider: CodexSandboxProvider | None = None,
    ):
        self.codex_bin = codex_bin
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.verbosity = verbosity
        self.sandbox = sandbox
        self.timeout = timeout
        self.inherit_proxy = inherit_proxy
        self.event_sink = event_sink
        self.sandbox_provider = sandbox_provider or LocalCodexSandboxProvider(codex_bin=codex_bin)

    async def run(self, context: TaskContext) -> TaskExecutionResult:
        session = self.sandbox_provider.prepare(
            context,
            schema_filename=CODEX_TASK_SCHEMA_FILENAME,
        )

        schema_path = session.host_workspace_dir / CODEX_TASK_SCHEMA_FILENAME
        schema_path.write_text(
            json.dumps(CODEX_TASK_OUTPUT_SCHEMA, indent=2),
            encoding="utf-8",
        )

        prompt = self._build_prompt(context)
        cmd = self._build_command(
            codex_bin=session.codex_bin,
            cwd=session.codex_cwd,
            schema_path=session.schema_path,
            prompt=prompt,
            reasoning_effort=str(context.metadata.get("codex_reasoning_effort") or self.reasoning_effort or ""),
            verbosity=str(context.metadata.get("codex_verbosity") or self.verbosity or ""),
        )
        cmd = session.wrap_command(cmd)
        await self._emit(RuntimeEvent(
            type="executor.started",
            task_id=context.task_id,
            message="Codex task execution started",
            payload={
                "command": self._redact_command(cmd),
                "sandbox_provider": session.provider,
            },
        ))

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self._build_env(),
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise TimeoutError(f"Codex task {context.task_id} timed out")

        stdout = stdout_b.decode("utf-8", errors="replace")
        stderr = stderr_b.decode("utf-8", errors="replace")
        events = self._parse_events(stdout, context.task_id)
        for event in events:
            await self._emit(event)

        if proc.returncode != 0:
            output_tail = self._output_tail(stdout)
            detail = stderr.strip()
            if output_tail:
                detail = f"{detail}\n{output_tail}" if detail else output_tail
            raise RuntimeError(
                f"Codex task {context.task_id} failed with exit code "
                f"{proc.returncode}: {detail}"
            )

        self._sync_workspace_artifacts(
            session.artifact_source_dir,
            session.host_artifacts_dir,
        )

        data = self._parse_final_payload(events, stdout)
        artifact_refs = self._artifact_refs(data)
        if not artifact_refs:
            artifact_refs = self._collect_artifacts(session.host_artifacts_dir)

        return TaskExecutionResult(
            task_id=context.task_id,
            markdown=str(data.get("markdown", "")).strip(),
            summary=str(data.get("summary", "")).strip(),
            artifacts=artifact_refs,
            best_score=data.get("best_score"),
            events=tuple(events),
            raw={"stdout": stdout, "stderr": stderr, "payload": data},
        )

    def _build_command(
        self,
        codex_bin: str,
        cwd: str,
        schema_path: str,
        prompt: str,
        reasoning_effort: str = "",
        verbosity: str = "",
    ) -> list[str]:
        runtime = CodexCliRuntime(
            codex_bin=codex_bin,
            model=self.model,
            reasoning_effort=reasoning_effort or None,
            verbosity=verbosity or None,
            sandbox=self.sandbox,
            timeout=self.timeout,
            inherit_proxy=self.inherit_proxy,
        )
        return runtime._build_command(
            cwd=Path(cwd),
            prompt=prompt,
            output_path=None,
            schema_path=Path(schema_path),
        )

    def _build_prompt(self, context: TaskContext) -> str:
        deps = "\n".join(
            f"- [{task_id}] {context.dependency_summaries.get(task_id, '')}".strip()
            for task_id in context.dependencies
        )
        parts = [
            "# MAARS Codex Task Contract",
            "",
            "You are executing one atomic research task inside a MAARS runtime.",
            "The Python runtime owns planning, retries, verification, and final paper writing.",
            "Your job is to produce the concrete task deliverable with real commands and verifiable artifacts.",
            "",
            "## Operating Rules",
            "- Work only in the current directory.",
            "- Do not ask for human input or wait for clarification.",
            "- Run real shell/Python commands for code, data analysis, experiments, plots, or file inspection.",
            "- Do not fabricate metrics, filenames, citations, stdout, or artifact contents.",
            "- Prefer small, inspectable scripts and deterministic outputs over hidden notebook state.",
            "- If the task cannot be fully completed, return the best truthful partial result and explain the blocker in `warnings`.",
            "",
            "## Task",
            f"Session: {context.session_id}",
            f"Task ID: {context.task_id}",
            f"Description: {context.description}",
        ]
        if deps:
            parts.extend([
                "",
                "## Dependency Summaries",
                "Use these as context only. Re-open or inspect available files when exact values matter.",
                deps,
            ])
        if context.prior_attempt:
            parts.extend(["", "## Prior Attempt", context.prior_attempt])
        previous_result = str(context.metadata.get("previous_result", ""))
        retry_review = str(context.metadata.get("retry_review", ""))
        if previous_result:
            parts.extend(["", "## Previous Output", previous_result])
        if retry_review:
            parts.extend([
                "",
                "## Review Feedback To Address",
                retry_review,
                "Address only the issues above. Reuse existing artifacts when they are already correct.",
            ])
        parts.extend([
            "",
            "## Artifact Contract",
            "- Write every durable output under `./artifacts/`.",
            "- Include relative artifact paths in the final `artifacts` array, preferably without the `artifacts/` prefix.",
            "- Each artifact entry must include `path`, `kind`, and `size_bytes`; use null for unknown optional values.",
            "- Only list files that actually exist.",
            "- Put raw metrics in machine-readable files such as JSON/CSV when possible; plots should reference the raw data source.",
            "",
            "## Final Response",
            "The final response must satisfy the provided JSON Schema exactly.",
            "`markdown` should contain the complete task result with commands run, important outputs, and artifact references.",
            "`summary` must be one concise line with filenames and key numeric results.",
            "`warnings` must be an empty array when there are no blockers or caveats.",
        ])
        return "\n".join(parts)

    def _build_env(self) -> dict[str, str]:
        return CodexCliRuntime(inherit_proxy=self.inherit_proxy)._build_env()

    @staticmethod
    def _parse_events(stdout: str, task_id: str) -> list[RuntimeEvent]:
        return CodexCliRuntime.parse_events(stdout, task_id=task_id)

    @staticmethod
    def _parse_final_payload(events: list[RuntimeEvent], stdout: str) -> dict[str, Any]:
        candidates: list[str] = []
        for event in reversed(events):
            if event.type in {"agent_message", "message"}:
                text = event.payload.get("text") or event.payload.get("message")
                if text:
                    candidates.append(str(text))
            item = event.payload.get("item")
            if isinstance(item, dict) and item.get("type") == "agent_message":
                text = item.get("text")
                if text:
                    candidates.append(str(text))
            if event.type in {"turn.completed", "turn.failed"}:
                final = event.payload.get("final_response")
                if final:
                    candidates.append(str(final))
        candidates.append(stdout)

        for candidate in candidates:
            parsed = parse_json_fenced(candidate, fallback={})
            if parsed:
                return parsed
        raise RuntimeError("Codex did not return a structured task result")

    @staticmethod
    def _artifact_refs(data: dict[str, Any]) -> tuple[ArtifactRef, ...]:
        refs = []
        for item in data.get("artifacts", []) or []:
            if not isinstance(item, dict) or not item.get("path"):
                continue
            kind = item.get("kind") or "file"
            refs.append(ArtifactRef(
                path=CodexExecutor._normalize_artifact_path(str(item["path"])),
                kind=str(kind),
                size_bytes=item.get("size_bytes"),
            ))
        return tuple(refs)

    @staticmethod
    def _normalize_artifact_path(path: str) -> str:
        normalized = path.strip().replace("\\", "/")
        while normalized.startswith("./"):
            normalized = normalized[2:]
        if "/artifacts/" in normalized:
            normalized = normalized.rsplit("/artifacts/", 1)[1]
        elif normalized.startswith("artifacts/"):
            normalized = normalized[len("artifacts/"):]
        if normalized.startswith("/"):
            normalized = Path(normalized).name
        return normalized

    @staticmethod
    def _collect_artifacts(root: Path) -> tuple[ArtifactRef, ...]:
        if not root.exists():
            return ()
        return tuple(
            ArtifactRef(
                path=str(path.relative_to(root)).replace("\\", "/"),
                size_bytes=path.stat().st_size,
            )
            for path in sorted(root.rglob("*"))
            if path.is_file()
        )

    @staticmethod
    def _sync_workspace_artifacts(source: Path, target: Path):
        if not source.exists():
            return
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(source)
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)

    @staticmethod
    def _redact_command(cmd: list[str]) -> list[str]:
        redacted = list(cmd)
        if redacted:
            redacted[-1] = "<prompt>"
        return redacted

    @staticmethod
    def _output_tail(stdout: str, max_lines: int = 12) -> str:
        return CodexCliRuntime._output_tail(stdout, max_lines=max_lines)

    async def _emit(self, event: RuntimeEvent):
        if not self.event_sink:
            return
        result = self.event_sink(event)
        if inspect.isawaitable(result):
            await result
