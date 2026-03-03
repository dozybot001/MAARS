---
name: refined-idea-quality
description: Quality criteria for refined_idea output. Use before RefineIdea or when ValidateRefinedIdea returns low score. Ensures description is concrete, research_questions are clear, and research_gap is well-articulated.
---

# Refined Idea Quality Criteria

Guidelines for producing a high-quality refined_idea that is decomposable into 3–10 tasks.

## Structure

- **description**: 2–4 sentences, concrete and actionable. Must be decomposable into distinct phases.
- **research_questions**: 1–3 questions with RQ1:, RQ2: prefix. Each should map to one or more tasks.
- **research_gap**: 1–2 sentences on limitations of existing work and contribution angle.
- **method_approach**: Brief outline of methodology (e.g. literature review → comparison → synthesis).

## Quality Rules

1. **Concrete over vague**: "Compare BERT and GPT on code completion benchmarks" not "Research NLP models".
2. **Combine literature insights with novel angles**: Avoid mere summarization; add synthesis, comparison, or gap.
3. **description must be decomposable**: If you cannot list 3+ distinct sub-tasks, refine further.
4. **research_gap must be specific**: Name limitations (e.g. "prior work focuses on X, neglects Y") rather than generic "more research needed".

## Validation Hints (ValidateRefinedIdea)

- Score >= 4: Proceed to FinishIdea.
- Score < 4: Call RefineIdea again with improvements — tighten description, clarify RQs, or sharpen research_gap.

## Red Flags

- description contains "research" without scope
- research_questions are yes/no or too broad
- research_gap is generic ("limited studies", "need more work")
- method_approach is a single vague step
