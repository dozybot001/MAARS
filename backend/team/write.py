"""Write stage: iterative paper writing (Writer + Reviewer)."""

from backend.team.stage import TeamStage


class WriteStage(TeamStage):

    _primary_dir = "drafts"
    _reviewer_dir = "reviews"
    _primary_phase = "draft"
    _reviewer_phase = "review"

    def __init__(self, name: str = "write", model=None, writer_tools=None,
                 reviewer_tools=None, db=None, max_delegations: int = 10):
        super().__init__(name=name, model=model, db=db, max_delegations=max_delegations)
        self._writer_tools = writer_tools or []
        self._reviewer_tools = reviewer_tools or []

    def load_input(self) -> str:
        return (
            "Use list_tasks and read_task_output tools to read all completed research outputs. "
            "Use read_refined_idea for context and read_plan_tree for structure. "
            "Use list_artifacts to discover available images and include them using ![caption](filename). "
            "Write the complete research paper in markdown."
        )

    def _primary_config(self) -> tuple[str, list, str]:
        from backend.team.prompts import WRITE_WRITER_SYSTEM
        return WRITE_WRITER_SYSTEM, self._writer_tools, "Writer"

    def _reviewer_config(self) -> tuple[str, list, str]:
        from backend.team.prompts import WRITE_REVIEWER_SYSTEM
        return WRITE_REVIEWER_SYSTEM, self._reviewer_tools, "Reviewer"

    def _finalize(self) -> str:
        result = self.output
        if self.db:
            self.db.save_paper(result)
        return result
