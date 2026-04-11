"""Write / Writer — draft research papers from a refined idea + artifacts."""

from __future__ import annotations

from pathlib import Path

from maars.models import get_search_model
from maars.prompts.writer import WRITER_SYSTEM_PROMPT
from maars.state import Issue


def _read_artifacts(artifacts_dir: str) -> dict[str, str]:
    """Read all markdown files in artifacts_dir recursively."""
    root = Path(artifacts_dir)
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Artifacts directory not found: {artifacts_dir}")

    artifacts: dict[str, str] = {}
    for md_file in sorted(root.rglob("*.md")):
        rel = md_file.relative_to(root)
        artifacts[str(rel)] = md_file.read_text(encoding="utf-8")
    return artifacts


def write_paper(
    refined_idea: str,
    artifacts_dir: str,
    *,
    prior_issues: list[Issue] | None = None,
    prior_draft: str | None = None,
) -> str:
    """Generate a research paper draft from a refined idea and artifacts.

    If prior_draft and prior_issues are provided, Writer revises the
    previous draft to address the Reviewer's issues instead of starting
    from scratch.
    """
    artifacts = _read_artifacts(artifacts_dir)
    artifacts_block = "\n\n".join(
        f"### `{name}`\n\n{content}" for name, content in artifacts.items()
    )

    if prior_draft and prior_issues:
        issues_block = "\n".join(
            f"- [{i.id}] ({i.severity}) {i.summary}: {i.detail}"
            for i in prior_issues
        )
        user_message = f"""## Refined research idea

{refined_idea}

## Experiment artifacts

{artifacts_block}

## Prior paper draft

{prior_draft}

## Reviewer 的 issues（请逐个解决）

{issues_block}

请修订 prior paper draft，针对性解决 issues，输出新的 paper 草稿。"""
    else:
        user_message = f"""## Refined research idea

{refined_idea}

## Experiment artifacts

{artifacts_block}

请基于 refined idea 和 experiment artifacts，撰写一份完整的研究论文初稿。"""

    model = get_search_model(temperature=0.3)
    response = model.invoke(
        [
            ("system", WRITER_SYSTEM_PROMPT),
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
