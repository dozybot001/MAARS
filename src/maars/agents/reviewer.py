"""Write / Reviewer — structured-output academic peer review."""

from __future__ import annotations

from pydantic import BaseModel, Field

from maars.models import get_chat_model
from maars.prompts.reviewer import REVIEWER_SYSTEM_PROMPT
from maars.state import Issue


class ReviewResult(BaseModel):
    """Output of one Reviewer review round."""

    issues: list[Issue] = Field(
        description="Issues found in the current paper draft. Empty list if none."
    )
    resolved: list[str] = Field(
        default_factory=list,
        description="IDs of previously-raised issues that are now resolved in this draft.",
    )
    passed: bool = Field(
        description="True if the paper is ready to exit the Write loop (no blockers, at most 1 major)."
    )
    summary: str = Field(
        description="One-paragraph overall assessment, 3 sentences max."
    )


def review_paper(
    draft: str,
    *,
    prior_issues: list[Issue] | None = None,
) -> ReviewResult:
    """Run the Reviewer once on a paper draft and return a structured ReviewResult."""
    model = get_chat_model(temperature=0.0)
    reviewer = model.with_structured_output(ReviewResult)

    prior_block = ""
    if prior_issues:
        lines = [
            f"- [{i.id}] ({i.severity}) {i.summary}: {i.detail}"
            for i in prior_issues
        ]
        prior_block = "\n\n## 前轮 issues（检查是否已解决）\n\n" + "\n".join(lines)

    user_message = f"""请审查下面的研究论文初稿。

## Paper draft

{draft}{prior_block}

请按 ReviewResult 的结构化格式返回你的评审结果。"""

    result = reviewer.invoke(
        [
            ("system", REVIEWER_SYSTEM_PROMPT),
            ("human", user_message),
        ]
    )
    return result  # type: ignore[return-value]
