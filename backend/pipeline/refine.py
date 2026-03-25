from backend.pipeline.stage import BaseStage

_AUTO = "This is a fully automated pipeline. No human is in the loop. Do NOT ask questions or request input. Make all decisions autonomously. 全文使用中文撰写。\n\n"

_PROMPTS = [
    _AUTO + """You are a research advisor. Explore the research landscape around the given idea.

Your job:
- Identify the core research domain, key sub-fields, and the state of the art
- Name specific prior work, methods, or datasets where relevant (be concrete, not vague)
- Brainstorm 3-5 possible research directions, noting each one's novelty and feasibility
- Identify open questions and gaps in the existing literature

Be expansive. Do not converge yet — map the space broadly.
Output in markdown.""",

    _AUTO + """You are a research advisor performing critical evaluation.

Based on your previous exploration:
- Evaluate each proposed direction on: novelty, feasibility, and potential impact
- Identify the most promising direction (or combination) and justify why
- Call out risks, hidden assumptions, and weaknesses honestly
- Suggest concrete ways to strengthen the chosen direction

Converge toward a single clear research direction.
Output in markdown.""",

    _AUTO + """You are a research advisor producing a finalized research proposal.

Based on the exploration and evaluation above, produce a complete research idea document with these sections:
1. **Title**
2. **Research Question** — precise problem statement
3. **Motivation** — why this matters
4. **Hypothesis** — what you expect to find
5. **Methodology** — approach overview, key techniques, experimental design
6. **Expected Contributions** — what's new
7. **Scope & Limitations** — what you won't cover
8. **Related Work** — position relative to prior work cited in exploration

The output should be detailed enough to directly plan executable research tasks from it.
Output in markdown.""",
]


class RefineStage(BaseStage):
    """Refine a vague idea into a complete research idea via 3 rounds:
    Explore → Evaluate → Crystallize.
    """

    _ROUND_LABELS = ["Explore", "Evaluate", "Crystallize"]

    def __init__(self, name: str = "refine", **kwargs):
        super().__init__(name=name, max_rounds=len(_PROMPTS), **kwargs)

    def load_input(self) -> str:
        return self.db.get_idea()

    def get_round_label(self, round_index: int) -> str:
        return self._ROUND_LABELS[round_index] if round_index < len(self._ROUND_LABELS) else ""

    def build_messages(self, input_text: str, round_index: int) -> list[dict]:
        messages = [{"role": "system", "content": _PROMPTS[round_index]}]

        if round_index == 0:
            messages.append({"role": "user", "content": input_text})
        else:
            messages.append({"role": "user", "content": input_text})
            for r in self.rounds:
                messages.append(r)
            messages.append({
                "role": "user",
                "content": "Now proceed with the next phase based on the above.",
            })

        return messages

    def is_complete(self, response: str, round_index: int) -> bool:
        return round_index >= len(_PROMPTS) - 1

    def finalize(self) -> str:
        result = self.rounds[-1]["content"] if self.rounds else self.output
        if self.db:
            self.db.save_refined_idea(result)
        return result
