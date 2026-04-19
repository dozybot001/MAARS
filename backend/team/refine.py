"""Refine stage: iterative idea refinement (Explorer + Critic)."""

from backend.team.stage import TeamStage


class RefineStage(TeamStage):

    def __init__(self, name: str = "refine", model=None, explorer_tools=None, db=None,
                 max_delegations: int = 10):
        super().__init__(name=name, model=model, db=db, max_delegations=max_delegations)
        self._explorer_tools = explorer_tools or []

    def load_input(self) -> str:
        return self.db.get_idea()

    def _primary_config(self) -> tuple[str, list, str]:
        from backend.team.prompts import REFINE_EXPLORER_SYSTEM
        return REFINE_EXPLORER_SYSTEM, self._explorer_tools, "Explorer"

    def _reviewer_config(self) -> tuple[str, list, str]:
        from backend.team.prompts import REFINE_CRITIC_SYSTEM
        return REFINE_CRITIC_SYSTEM, [], "Critic"

    def _finalize(self) -> str:
        result = self.output
        if self.db:
            self.db.save_refined_idea(result)
        return result
