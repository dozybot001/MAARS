"""Gemini mode: pipeline stages + GeminiClient.

Each client instance carries its stage-specific instruction.
"""

from backend.llm.gemini_client import GeminiClient
from backend.pipeline.refine import RefineStage
from backend.pipeline.plan import PlanStage
from backend.pipeline.execute import ExecuteStage
from backend.pipeline.write import WriteStage


def create_gemini_stages(api_key: str, model: str = "gemini-2.0-flash", db=None) -> dict:
    """Assemble all pipeline stages with Gemini LLM client."""
    return {
        "refine": RefineStage(llm_client=GeminiClient(api_key=api_key, model=model)),
        "plan": PlanStage(llm_client=GeminiClient(api_key=api_key, model=model)),
        "execute": ExecuteStage(
            llm_client=GeminiClient(api_key=api_key, model=model),
            db=db,
        ),
        "write": WriteStage(
            llm_client=GeminiClient(api_key=api_key, model=model),
            db=db,
        ),
    }
