# MAARS

[中文](README_CN.md) | English

**Multi-Agent Automated Research System** — From one idea to a full research paper, fully automated.

## Pipeline

Four fixed stages. Every mode runs the same pipeline — modes only swap the engine underneath.

```mermaid
flowchart LR
    I[Idea] --> R["Refine\n3 rounds"] --> P["Plan\nrecursive DAG"] --> X["Execute\nparallel + verify"] --> W["Write\noutline → polish"] --> O[Paper]
```

| Stage | What it does |
|-------|-------------|
| **Refine** | Explore → Evaluate → Crystallize. Turns a vague idea into a structured research proposal |
| **Plan** | Recursive decomposition into atomic tasks with dependency DAG (depth 3, batch-parallel) |
| **Execute** | Topological sort → parallel batch execution → verification → retry. Results stored in file DB |
| **Write** | Outline → section-by-section writing → polish. Each section receives only its relevant task outputs |

## Modes

`.env` one-line switch:

```env
MAARS_LLM_MODE=mock      # or gemini, or agent
MAARS_GOOGLE_API_KEY=your-key
```

Modes replace the engine at each stage, not the pipeline logic:

| Stage | Mock | Gemini | Agent |
|-------|------|--------|-------|
| **Refine** | replay | LLM | ADK Agent + Google Search |
| **Plan** | replay | LLM | LLM (same as Gemini) |
| **Execute** | replay | LLM | ADK Agent per task + Google Search |
| **Write** | replay | LLM | ADK Agent + DB tools + Google Search |

> Agent Plan deliberately stays on the LLM engine — each step is a structured JSON judgment (atomic? → yes/no + subtasks), where deterministic calls outperform ReAct loops.

## Architecture

```mermaid
flowchart LR
    subgraph FE["Frontend · Vanilla JS"]
        UI["Input + controls"]
        LOG["LLM Output Log"]
        PROC["Process & Output"]
    end

    subgraph BE["Backend · FastAPI"]
        ROUTES["routes/"]
        ORCH["orchestrator"]
        STAGES["pipeline stages"]
        LLM["LLMClient"]
        MODES["mock / gemini / agent"]
        DB["file DB"]
    end

    UI --> ROUTES --> ORCH --> STAGES
    STAGES --> LLM
    MODES -."injects".-> STAGES
    STAGES --> DB
    ORCH -."SSE".-> LOG
    ORCH -."SSE".-> PROC
```

| Principle | Detail |
|-----------|--------|
| Three-layer decoupling | `llm/` → `pipeline/` → `mode/` — pipeline never knows which mode is active |
| Unified streaming | Every LLM call emits `call_id`-tagged chunks; frontend routes by `call_id` |
| String in, string out | Stages communicate via `stage.output` — no shared memory |

## Quick start

```bash
git clone https://github.com/dozybot001/MAARS.git && cd MAARS
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your API key
uvicorn backend.main:app --host 0.0.0.0 --port 8000
# Open http://localhost:8000
```

## Output

Each run creates a timestamped folder:

```
research/{timestamp}-{slug}/
├── idea.md           # Input
├── refined_idea.md   # Refine output
├── plan.json         # Flat atomic task list
├── plan_tree.json    # Decomposition tree
├── paper.md          # Final paper
└── tasks/            # Individual task outputs
```

## Showcase

| Run | Mode | Topic | Tasks |
|-----|------|-------|-------|
| `20260323-210300-*` | Gemini | Cognitive Buffer Hypothesis — cultural modulation of news framing | 31 |
| `20260323-223406-*` | Agent | HMAO — adversarial multi-agent role specialization | 12 |

Build history: [Intent showcase/maars](https://github.com/dozybot001/Intent/tree/main/showcase/maars)

## Community

[Contributing](.github/CONTRIBUTING.md) · [Code of Conduct](.github/CODE_OF_CONDUCT.md) · [Security](.github/SECURITY.md)

## License

MIT
