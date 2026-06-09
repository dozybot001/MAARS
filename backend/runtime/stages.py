"""Stage factory for the unified Codex runtime."""

from backend.pipeline.research import ResearchStage
from backend.team.refine import RefineStage
from backend.team.write import WriteStage


def create_codex_stages(
    *,
    db=None,
    max_iterations: int = 1,
    max_delegations: int = 10,
) -> dict:
    return {
        "refine": RefineStage(
            model=None,
            explorer_tools=[],
            db=db,
            max_delegations=max_delegations,
        ),
        "research": ResearchStage(
            model=None,
            execute_tools=[],
            read_tools=[],
            search_tools=[],
            db=db,
            max_iterations=max_iterations,
        ),
        "write": WriteStage(
            model=None,
            polish_model=None,
            writer_tools=[],
            reviewer_tools=[],
            db=db,
            max_delegations=max_delegations,
        ),
    }
