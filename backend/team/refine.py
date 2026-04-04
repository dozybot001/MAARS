"""Refine stage: multi-agent idea refinement via Agno Team coordinate mode."""

from backend.team.stage import TeamStage


class RefineStage(TeamStage):

    _member_map = {"explorer": "Explorer", "critic": "Critic"}
    _capture_member = "Explorer"

    def __init__(self, name: str = "refine", model=None, explorer_tools=None, db=None):
        super().__init__(name=name, model=model, db=db)
        self._explorer_tools = explorer_tools or []

    def load_input(self) -> str:
        return self.db.get_idea()

    def _create_team(self):
        from agno.agent import Agent
        from agno.team.team import Team
        from agno.team.mode import TeamMode
        from backend.team.prompts import (
            REFINE_LEADER_SYSTEM, REFINE_EXPLORER_SYSTEM, REFINE_CRITIC_SYSTEM,
        )
        explorer = Agent(name="Explorer", role="Research explorer", model=self._model,
                         tools=self._explorer_tools, instructions=[REFINE_EXPLORER_SYSTEM],
                         markdown=True, id="explorer")
        critic = Agent(name="Critic", role="Research critic", model=self._model,
                       tools=self._explorer_tools, instructions=[REFINE_CRITIC_SYSTEM],
                       markdown=True, id="critic")
        return Team(name="Refine Team", mode=TeamMode.coordinate, members=[explorer, critic],
                    model=self._model, instructions=[REFINE_LEADER_SYSTEM],
                    share_member_interactions=True, stream_member_events=True, markdown=True)

    def _finalize(self) -> str:
        result = self.output
        if self.db:
            self.db.save_refined_idea(result)
        return result
