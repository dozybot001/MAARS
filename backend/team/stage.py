"""TeamStage -- base for iterative two-agent stages (primary + reviewer)."""

import asyncio
import logging
from dataclasses import dataclass, field

from backend.pipeline.stage import Stage
from backend.utils import parse_json_fenced

log = logging.getLogger(__name__)


@dataclass
class ProposalState:
    """Compact state passed between iterations. Replaces share_member_interactions."""

    proposal: str = ""
    issues: list[dict] = field(default_factory=list)
    iteration: int = 0

    def format_issues(self) -> str:
        if not self.issues:
            return "(No open issues)"
        lines = []
        for i, issue in enumerate(self.issues, 1):
            severity = issue.get("severity", "major")
            section = issue.get("section", "General")
            problem = issue.get("problem", "")
            suggestion = issue.get("suggestion", "")
            lines.append(f"{i}. [{severity}] {section}: {problem}")
            if suggestion:
                lines.append(f"   Suggestion: {suggestion}")
        return "\n".join(lines)

    def update(self, new_proposal: str, feedback: dict):
        self.proposal = new_proposal
        resolved_ids = set(feedback.get("resolved", []))
        remaining = [iss for iss in self.issues if iss.get("id") not in resolved_ids]
        remaining.extend(feedback.get("issues", []))
        self.issues = remaining
        self.iteration += 1


class TeamStage(Stage):
    """Iterative two-agent loop: primary produces, reviewer critiques."""

    def __init__(self, name: str, model=None, db=None, max_delegations: int = 10):
        super().__init__(name=name, db=db)
        self._model = model
        self._max_delegations = max_delegations

    def load_input(self) -> str:
        raise NotImplementedError

    def _primary_config(self) -> tuple[str, list, str]:
        """Return (instruction, tools, label) for the primary agent."""
        raise NotImplementedError

    def _reviewer_config(self) -> tuple[str, list, str]:
        """Return (instruction, tools, label) for the reviewer agent."""
        raise NotImplementedError

    def _finalize(self) -> str:
        raise NotImplementedError

    async def _execute(self) -> str:
        input_text = self.load_input()
        state = ProposalState()
        primary_instr, primary_tools, primary_label = self._primary_config()
        reviewer_instr, reviewer_tools, reviewer_label = self._reviewer_config()

        for round_num in range(self._max_delegations):
            if self._stop_requested:
                raise asyncio.CancelledError()

            # 1. Primary agent produces/revises proposal
            primary_user = self._build_primary_prompt(input_text, state)
            proposal = await self._stream_llm(
                self._model, primary_tools, primary_instr, primary_user,
                call_id=primary_label, content_level=3,
                label=True, label_level=2,
            )
            state.proposal = proposal

            # Skip review on final allowed round
            if round_num >= self._max_delegations - 1:
                break

            if self._stop_requested:
                raise asyncio.CancelledError()

            # 2. Reviewer critiques proposal
            reviewer_user = self._build_reviewer_prompt(input_text, state)
            review_raw = await self._stream_llm(
                self._model, reviewer_tools, reviewer_instr, reviewer_user,
                call_id=reviewer_label, content_level=3,
                label=True, label_level=2,
            )

            # 3. Parse structured feedback
            feedback = parse_json_fenced(review_raw, fallback={"pass": False, "issues": []})

            if feedback.get("pass", False):
                break

            # 4. Update state for next round
            state.update(proposal, feedback)

        self.output = state.proposal
        if not self.output:
            log.warning("%s: no content produced", self.name)

        return self._finalize()

    def _build_primary_prompt(self, input_text: str, state: ProposalState) -> str:
        if state.iteration == 0:
            return input_text
        parts = [input_text]
        parts.append(f"\n## Current Draft (Revision {state.iteration})\n{state.proposal}")
        parts.append(f"\n## Issues to Address\n{state.format_issues()}")
        parts.append("\nRevise the draft to address all listed issues. Output the complete revised version.")
        return "\n".join(parts)

    def _build_reviewer_prompt(self, input_text: str, state: ProposalState) -> str:
        parts = [input_text]
        parts.append(f"\n## Proposal to Review\n{state.proposal}")
        if state.issues:
            parts.append(f"\n## Previously Identified Issues\n{state.format_issues()}")
        return "\n".join(parts)
