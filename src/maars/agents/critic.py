"""Refine / Critic — incremental structured-output judge.

The Critic reports only a delta each round (resolved ids + new issues).
The system (critic_node in graphs/refine.py) is responsible for applying
that delta to the canonical unresolved-issues list kept in graph state.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maars.models import get_chat_model
from maars.prompts.critic import CRITIC_SYSTEM_PROMPT
from maars.state import Issue


class CritiqueFeedback(BaseModel):
    """Incremental feedback from one Critic review round.

    This is NOT the full unresolved list. The Critic only reports what
    changed this round — the system merges prior_issues with this feedback
    to obtain the new canonical list:

        next = (prior - resolved) + new_issues
    """

    resolved: list[str] = Field(
        default_factory=list,
        description=(
            "IDs of prior issues that are now resolved in the current draft. "
            "Must be a subset of the prior issues' ids."
        ),
    )
    new_issues: list[Issue] = Field(
        default_factory=list,
        description=(
            "Newly discovered issues in the current draft only. Do NOT include "
            "issues that were already in prior_issues and are still unresolved — "
            "the system will carry those over automatically. Each new issue must "
            "have a fresh id that does not collide with any prior or historically "
            "resolved id."
        ),
    )
    summary: str = Field(
        description=(
            "One-paragraph overall assessment of the current draft, 3 sentences "
            "max. Do not include a pass/fail verdict — the system decides pass "
            "based on the resulting canonical issue list."
        ),
    )


def critique_draft(
    draft: str,
    *,
    prior_issues: list[Issue] | None = None,
) -> CritiqueFeedback:
    """Run the Critic once on a draft and return incremental feedback.

    The caller (typically critic_node in the Refine graph) is responsible
    for merging the feedback with prior_issues to obtain the new canonical
    list: next = (prior - resolved) + new_issues.
    """
    model = get_chat_model(temperature=0.0)
    critic = model.with_structured_output(CritiqueFeedback)

    if prior_issues:
        prior_block = "\n".join(
            f"- [{i.id}] ({i.severity}) {i.summary}: {i.detail}"
            for i in prior_issues
        )
        prior_section = (
            "\n\n## 前轮遗留的未解决 issues\n\n"
            "系统已经为你维护了下面这份 list——这就是当前 draft 需要逐个检查的问题清单。\n\n"
            f"{prior_block}\n\n"
            "你的任务只有两件事：\n"
            "1. **resolved**：上面哪些 id 已经被新 draft 解决了？（只列 id）\n"
            "2. **new_issues**：这轮**新发现**的问题（不要再列已经在 prior 里的，用新 id）"
        )
    else:
        prior_section = (
            "\n\n## 注意\n\n这是第一轮，没有 prior issues。"
            "resolved 留空，只关注 new_issues。"
        )

    user_message = f"""请审查下面的研究提案草稿。

## Draft

{draft}{prior_section}

按 CritiqueFeedback 的结构化格式返回增量反馈。"""

    result = critic.invoke(
        [
            ("system", CRITIC_SYSTEM_PROMPT),
            ("human", user_message),
        ]
    )
    return result  # type: ignore[return-value]
