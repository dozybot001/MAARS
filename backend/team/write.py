"""Write stage: Outliner -> parallel Writers -> Editor -> Reviewer pipeline."""

import asyncio
import json
import logging

from backend.pipeline.stage import Stage
from backend.utils import parse_json_fenced

log = logging.getLogger(__name__)


class WriteStage(Stage):

    def __init__(self, name: str = "write", model=None, writer_tools=None,
                 reviewer_tools=None, db_tools=None, db=None,
                 max_delegations: int = 10):
        super().__init__(name=name, db=db)
        self._model = model
        self._writer_tools = writer_tools or []
        self._reviewer_tools = reviewer_tools or []
        self._db_tools = db_tools or []
        self._max_delegations = max_delegations

    async def _execute(self) -> str:
        idea = self.db.get_refined_idea()
        reviewer_feedback = None
        paper = ""

        for round_num in range(1, self._max_delegations + 1):
            self._check_stop()

            # 1. Outliner
            self._current_phase = "outline"
            outline = await self._run_outliner(idea, reviewer_feedback, round_num)
            if self.db:
                self.db.save_outline(outline, round_num)
            self._send()

            self._check_stop()

            # 2. Parallel Writers
            self._current_phase = "sections"
            sections = await self._run_writers(outline, round_num)

            self._check_stop()

            # 3. Assemble + Editor
            self._current_phase = "edit"
            assembled = self._assemble(outline, sections)
            paper = await self._run_editor(assembled, outline, round_num)
            if self.db:
                self.db.save_draft(paper, round_num)
            self._send()

            # Skip review on final allowed round
            if round_num >= self._max_delegations:
                break

            self._check_stop()

            # 4. Reviewer
            self._current_phase = "review"
            raw, feedback = await self._run_reviewer(paper, round_num)
            if self.db:
                self.db.save_write_review(raw, feedback, round_num)
            self._send()

            if feedback.get("pass", False):
                break

            reviewer_feedback = feedback

        self._current_phase = ""
        self.output = paper
        if self.db:
            self.db.save_paper(paper)
        return paper

    # ------------------------------------------------------------------
    # Phase 1: Outliner
    # ------------------------------------------------------------------

    async def _run_outliner(self, idea: str, reviewer_feedback: dict | None,
                            round_num: int) -> list[dict]:
        from backend.team.prompts import WRITE_OUTLINER_SYSTEM

        parts = [f"## Research Idea\n{idea}"]
        if reviewer_feedback:
            issues = json.dumps(reviewer_feedback.get("issues", []),
                                indent=2, ensure_ascii=False)
            parts.append(f"## Reviewer Feedback (Round {round_num - 1})\n{issues}")
            parts.append("Adjust the outline to address these issues.")

        raw = await self._stream_llm(
            self._model, self._db_tools, WRITE_OUTLINER_SYSTEM,
            "\n\n".join(parts),
            call_id="Outliner", content_level=3,
            label=True, label_level=2,
        )
        outline = parse_json_fenced(raw, fallback=[])
        if isinstance(outline, dict):
            outline = outline.get("sections", [])
        return outline

    # ------------------------------------------------------------------
    # Phase 2: Parallel Writers
    # ------------------------------------------------------------------

    async def _run_writers(self, outline: list[dict],
                           round_num: int) -> dict[str, str]:
        from backend.team.prompts import WRITE_WRITER_SYSTEM

        async def write_one(section: dict) -> tuple[str, str]:
            sid = section.get("section_id", "unknown")
            user_text = self._build_writer_prompt(section, outline)
            result = await self._stream_llm(
                self._model, self._writer_tools, WRITE_WRITER_SYSTEM,
                user_text,
                call_id=f"Writer: {section.get('title', sid)}",
                content_level=4,
                label=True, label_level=3,
            )
            if self.db:
                self.db.save_section(result, round_num, sid)
            return sid, result

        results = await asyncio.gather(
            *[write_one(s) for s in outline],
            return_exceptions=True,
        )

        sections = {}
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                sid = outline[i].get("section_id", f"section_{i}")
                log.error("Writer for section %s failed: %s", sid, r)
                sections[sid] = f"[Section {sid} failed: {r}]"
            else:
                sections[r[0]] = r[1]
        return sections

    def _build_writer_prompt(self, section: dict, outline: list[dict]) -> str:
        outline_json = json.dumps(outline, indent=2, ensure_ascii=False)
        section_json = json.dumps(section, indent=2, ensure_ascii=False)
        return (
            f"## Your Section Assignment\n```json\n{section_json}\n```\n\n"
            f"## Full Paper Outline\n```json\n{outline_json}\n```\n\n"
            f"Use read_task_output to read your primary_tasks and reference_tasks. "
            f"Use list_artifacts to find figures. Write your section now."
        )

    # ------------------------------------------------------------------
    # Phase 3: Assemble + Editor
    # ------------------------------------------------------------------

    @staticmethod
    def _assemble(outline: list[dict], sections: dict[str, str]) -> str:
        parts = []
        for s in outline:
            sid = s.get("section_id", "")
            content = sections.get(sid, f"[Section {sid} missing]")
            parts.append(content)
        return "\n\n---\n\n".join(parts)

    async def _run_editor(self, assembled: str, outline: list[dict],
                          round_num: int) -> str:
        from backend.team.prompts import WRITE_EDITOR_SYSTEM

        outline_json = json.dumps(outline, indent=2, ensure_ascii=False)
        user_text = (
            f"## Paper Outline\n```json\n{outline_json}\n```\n\n"
            f"## Assembled Sections\n{assembled}"
        )
        return await self._stream_llm(
            self._model, [], WRITE_EDITOR_SYSTEM, user_text,
            call_id="Editor", content_level=3,
            label=True, label_level=2,
        )

    # ------------------------------------------------------------------
    # Phase 4: Reviewer
    # ------------------------------------------------------------------

    async def _run_reviewer(self, paper: str,
                            round_num: int) -> tuple[str, dict]:
        from backend.team.prompts import WRITE_REVIEWER_SYSTEM

        raw = await self._stream_llm(
            self._model, self._reviewer_tools, WRITE_REVIEWER_SYSTEM,
            f"## Paper Draft (Round {round_num})\n{paper}",
            call_id="Reviewer", content_level=3,
            label=True, label_level=2,
        )
        data = parse_json_fenced(raw, fallback={"pass": False, "issues": []})
        return raw, data

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _check_stop(self):
        if self._stop_requested:
            raise asyncio.CancelledError()
