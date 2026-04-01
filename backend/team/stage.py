"""TeamStage — base for multi-agent stages using Agno Team coordinate mode."""

import asyncio
import logging

from backend.pipeline.stage import Stage, StageState

log = logging.getLogger(__name__)


class TeamStage(Stage):

    _member_map: dict[str, str] = {}
    _capture_member: str = ""

    def __init__(self, name: str, model=None, db=None):
        super().__init__(name=name, db=db)
        self._model = model

    def load_input(self) -> str:
        raise NotImplementedError

    def _create_team(self):
        raise NotImplementedError

    def _finalize(self) -> str:
        raise NotImplementedError

    async def _execute(self) -> str:
        team = self._create_team()
        input_text = self.load_input()

        output_content = ""
        current_member = None

        async with asyncio.timeout(3600):
            async for event in await team.arun(
                input_text, stream=True, stream_events=True,
            ):
                if self._stop_requested:
                    raise asyncio.CancelledError()
                evt = getattr(event, "event", "")

                if evt == "TeamToolCallStarted":
                    tool = getattr(event, "tool", None)
                    if tool and getattr(tool, "tool_name", "") == "delegate_task_to_member":
                        args = getattr(tool, "tool_args", {}) or {}
                        member_id = args.get("member_id", "")
                        label = self._resolve_member(member_id)
                        if label == self._capture_member:
                            output_content = ""
                        current_member = label
                        self._send(chunk={"text": label, "call_id": label, "label": True, "level": 2})

                elif evt == "TeamRunContent":
                    content = getattr(event, "content", None)
                    if content:
                        self._send(chunk={"text": str(content), "call_id": "Summary", "level": 2})

                elif evt == "TeamRunCompleted":
                    metrics = getattr(event, "metrics", None)
                    if metrics and self.db:
                        meta = self.db.get_meta()
                        self.db.update_meta(
                            tokens_input=meta.get("tokens_input", 0) + (getattr(metrics, "input_tokens", 0) or 0),
                            tokens_output=meta.get("tokens_output", 0) + (getattr(metrics, "output_tokens", 0) or 0),
                            tokens_total=meta.get("tokens_total", 0) + (getattr(metrics, "total_tokens", 0) or 0),
                        )

                elif evt in ("TeamRunError", "RunError"):
                    error_msg = str(getattr(event, "content", "")) or "Unknown error"
                    log.error("%s team error: %s (full event: %s)", self.name, error_msg, event)
                    raise RuntimeError(f"{self.name} team error: {error_msg}")

                elif evt == "RunContent":
                    content = getattr(event, "content", None)
                    if content:
                        text = str(content)
                        member = current_member or self.name.capitalize()
                        self._send(chunk={"text": text, "call_id": member, "level": 3})
                        if member == self._capture_member:
                            output_content += text

                elif evt == "ToolCallStarted":
                    tool = getattr(event, "tool", None)
                    if tool:
                        tool_name = getattr(tool, "tool_name", "tool") or "tool"
                        self._send(chunk={"text": f"Tool: {tool_name}", "call_id": f"Tool: {tool_name}", "label": True, "level": 3})

                elif evt == "ToolCallCompleted":
                    tool = getattr(event, "tool", None)
                    if tool:
                        tool_name = getattr(tool, "tool_name", "tool") or "tool"
                        result_text = str(getattr(event, "content", ""))[:500]
                        if result_text:
                            self._send(chunk={"text": result_text, "call_id": f"Tool: {tool_name}", "level": 3})

                elif evt == "RunCompleted":
                    pass

        self.output = output_content
        if not self.output:
            log.warning("%s: no content captured from primary member", self.name)

        return self._finalize()

    def _resolve_member(self, member_id: str) -> str:
        for key, label in self._member_map.items():
            if key in member_id:
                return label
        return member_id or "Member"
