"""Refine / Explorer — draft research proposals with Gemini grounding."""

from __future__ import annotations

from maars.models import get_search_model
from maars.prompts.explorer import EXPLORER_SYSTEM_PROMPT
from maars.state import Issue


def draft_proposal(
    raw_idea: str,
    *,
    prior_issues: list[Issue] | None = None,
    prior_draft: str | None = None,
) -> str:
    """Generate a research proposal draft from a raw idea.

    If prior_draft and prior_issues are provided, Explorer revises the
    previous draft to address the Critic's issues rather than starting
    from scratch.
    """
    model = get_search_model(temperature=0.2)

    if prior_draft and prior_issues:
        issues_block = "\n".join(
            f"- [{i.id}] ({i.severity}) {i.summary}: {i.detail}"
            for i in prior_issues
        )
        user_message = f"""## Raw idea

{raw_idea}

## Prior draft

{prior_draft}

## Critic 的 issues（请逐个解决）

{issues_block}

请修订 prior draft，针对性解决 issues，输出新的 draft。"""
    else:
        user_message = f"""## Raw idea

{raw_idea}

请根据这个想法起草一份研究提案。"""

    response = model.invoke(
        [
            ("system", EXPLORER_SYSTEM_PROMPT),
            ("human", user_message),
        ]
    )

    content = response.content
    if isinstance(content, list):
        text = "".join(
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    else:
        text = str(content)

    return text
