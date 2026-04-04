"""Write stage: multi-agent paper writing via Agno Team coordinate mode."""

from backend.team.stage import TeamStage


class WriteStage(TeamStage):

    _member_map = {"writer": "Writer", "reviewer": "Reviewer"}
    _capture_member = "Writer"

    def __init__(self, name: str = "write", model=None, writer_tools=None,
                 reviewer_tools=None, db=None):
        super().__init__(name=name, model=model, db=db)
        self._writer_tools = writer_tools or []
        self._reviewer_tools = reviewer_tools or []

    def load_input(self) -> str:
        return (
            "Use list_tasks and read_task_output tools to read all completed research outputs. "
            "Use read_refined_idea for context and read_plan_tree for structure. "
            "Use list_artifacts to discover available images and include them using ![caption](filename). "
            "Write the complete research paper in markdown."
        )

    def _create_team(self):
        from agno.agent import Agent
        from agno.team.team import Team
        from agno.team.mode import TeamMode
        from backend.team.prompts import (
            WRITE_LEADER_SYSTEM, WRITE_WRITER_SYSTEM, WRITE_REVIEWER_SYSTEM,
        )
        writer = Agent(name="Writer", role="Research paper author", model=self._model,
                       tools=self._writer_tools, instructions=[WRITE_WRITER_SYSTEM],
                       markdown=True, id="writer")
        reviewer = Agent(name="Reviewer", role="Research paper reviewer", model=self._model,
                         tools=self._reviewer_tools, instructions=[WRITE_REVIEWER_SYSTEM],
                         markdown=True, id="reviewer")
        return Team(name="Write Team", mode=TeamMode.coordinate, members=[writer, reviewer],
                    model=self._model, instructions=[WRITE_LEADER_SYSTEM],
                    share_member_interactions=True, stream_member_events=True, markdown=True)

    def _finalize(self) -> str:
        result = self.output
        if self.db:
            self.db.save_paper(result)
        return result
