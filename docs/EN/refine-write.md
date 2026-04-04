# Refine / Write Stage Details

> Back to [Architecture Overview](architecture.md)

Refine and Write share the same `TeamStage` base class, driven by an `IterationState` dual-agent loop. They are fully symmetric — only configuration differs.

## 1. IterationState

```python
@dataclass
class IterationState:
    draft: str              # Latest full content (proposal / paper)
    issues: list[dict]      # [{id, severity, section, problem, suggestion}]
    iteration: int          # Current round number
```

**Update rules**:
- `draft`: Overwritten each round by primary agent output
- `issues`: Reviewer outputs `resolved` list -> remove by id; outputs `issues` list -> append
- `iteration`: Incremented each round

**Context injection**: IterationState is not agent-visible. It is injected via `_build_primary_prompt()` / `_build_reviewer_prompt()` into user_text. Context size per round is constant (original input + latest draft + unresolved issues), regardless of iteration count.

## 2. Loop Mechanism

```python
for round in range(max_delegations):
    # 1. Primary agent produces/revises
    draft = _stream_llm(primary_agent, input + state)
    state.draft = draft
    save_round_md(primary_dir, draft, round)    # persist
    send()                                       # done signal

    # 2. Reviewer critiques
    review = _stream_llm(reviewer_agent, input + state)
    feedback = parse_json_fenced(review)         # {pass, issues, resolved}
    save_round_md(reviewer_dir, review, round)   # persist
    save_round_json(reviewer_dir, feedback, round)
    send()                                       # done signal

    if feedback.pass: break
    state.update(draft, feedback)                # issues = drop resolved + add new
```

Two LLM calls per round. Reviewer outputs structured JSON via `_REVIEWER_OUTPUT_FORMAT`. Runtime mechanically applies state updates — no LLM involved in state management.

## 3. Refine vs Write Configuration

| | Refine | Write |
|---|---|---|
| Primary agent | Explorer (search tools: arXiv, Wikipedia) | Writer (DB tools: list_tasks, read_task_output, list_artifacts) |
| Reviewer agent | Critic (search tools) | Reviewer (DB tools + list_artifacts) |
| Input | `db.get_idea()` raw text | Static instruction (Writer calls tools to read data) |
| Output | `refined_idea.md` | `paper.md` |
| Persistence dirs | `proposals/` + `critiques/` | `drafts/` + `reviews/` |
| SSE phases | `proposal` / `critique` | `draft` / `review` |
| Frontend labels | Proposals / Critiques / Final | Drafts / Reviews / Final |
| Gemini Search | Enabled (`search=True`) | Enabled |

## 4. Typical IterationState Lifecycle

```
Round 1:
  Explorer(idea)                           -> draft v1
  Critic(idea + v1)                        -> {pass:false, issues:[A,B,C]}
  state = {draft: v1, issues: [A,B,C], iteration: 1}

Round 2:
  Explorer(idea + v1 + [A,B,C])            -> draft v2
  Critic(idea + v2 + [A,B,C])              -> {pass:false, issues:[D], resolved:[A,B]}
  state = {draft: v2, issues: [C,D], iteration: 2}

Round 3:
  Explorer(idea + v2 + [C,D])              -> draft v3
  Critic(idea + v3 + [C,D])                -> {pass:true}
  break -> save refined_idea.md / paper.md
```

## 5. Reviewer JSON Format

```json
{
  "pass": false,
  "issues": [
    {
      "id": "feasibility_1",
      "severity": "major",
      "section": "Methodology",
      "problem": "DAG extraction feasibility unclear",
      "suggestion": "Add human-in-the-loop validation step"
    }
  ],
  "resolved": ["novelty_1", "scope_2"]
}
```

- `pass`: True only when no major issues remain
- `issues`: All current problems (new + still-unresolved from previous rounds)
- `resolved`: Only IDs from the "Previously Identified Issues" section that are now fixed
- `format_issues()` prefixes each issue with `**id**` so the reviewer can reference exact IDs

## 6. Comparison with Research

| | Research | Refine / Write |
|---|---|---|
| Loop | strategy -> decompose -> execute -> evaluate | primary -> reviewer -> primary -> reviewer |
| State | task_results + plan_tree + score | IterationState (draft + issues) |
| Orchestrator | Python `_run_loop` | Python `TeamStage._execute` |
| Agent roles | Independent agent per task | Two fixed roles alternating |
| Communication | Via artifacts/DB | Via IterationState injected into prompt |
| Persistence | Checkpoint/resume | Per-round persistence, final output saved |
| Termination | Evaluate has no strategy_update | Reviewer pass=true or max_delegations reached |

Core pattern is the same: **Python controls flow, agents execute single steps, state managed at runtime layer.**

## 7. Code Locations

| File | Role |
|---|---|
| `backend/team/stage.py` | TeamStage base class + IterationState |
| `backend/team/refine.py` | RefineStage configuration |
| `backend/team/write.py` | WriteStage configuration |
| `backend/team/prompts_en.py` | EN prompts + `_REVIEWER_OUTPUT_FORMAT` |
| `backend/team/prompts_zh.py` | ZH prompts |
