# MAARS

[中文](README_CN.md) | English

**Multi-Agent Automated Research System** — From one idea to a full research paper, fully automated.

MAARS is a hybrid multi-agent research system. Give it a research idea or a Kaggle competition URL, and it will refine the problem, decompose it into executable tasks, run experiments in a Docker sandbox, iterate based on results, and produce a complete paper — all autonomously.

## Quick Start

![MAARS startup UI](docs/assets/start.png)

```bash
# Linux / macOS / Windows (Git Bash):
bash start.sh
```

Automatically installs dependencies, checks `.env` (and creates it if missing), builds the Docker image (and prompts you to press Enter to install Docker Desktop if needed), starts the server, and opens the browser. All you need: `Ctrl/CMD + K` -> type... -> Enter。

## Architecture

### Data Flow

```mermaid
flowchart LR
    IN["Research Idea\nor Kaggle URL"] --> REF

    REF["① Refine\nTeam: Explorer + Critic"]
    RES["② Research\nAgentic Workflow"]
    WRI["③ Write\nTeam: Writer + Reviewer"]

    REF -- "refined_idea.md" --> RES -- "tasks/ · artifacts/" --> WRI -- "paper.md" --> OUT["Complete\nPaper"]

    DB[(Session DB)]
    REF & RES & WRI <-.-> DB
```

### System Architecture

```mermaid
flowchart TB
    UI["Vue 3 Frontend · SSE"] --> API["FastAPI → Orchestrator"]

    API --> REF["① Refine\nTeam: Explorer + Critic"]
    API --> RES["② Research\nAgentic Workflow"]
    API --> WRI["③ Write\nHybrid: Writer Agent + Reviewer Agent"]

    REF -- "refined_idea.md" --> DB
    RES -- "tasks/ · artifacts/" --> DB
    WRI -- "outline · sections · paper.md" --> DB
    DB[(Session DB\nresults/id/)]

    REF & RES & WRI --> AGNO["Agno · Google · Anthropic · OpenAI\nSearch · arXiv · Docker Sandbox"]
```

The core design principle: **deterministic control stays in the runtime; open-ended execution goes to agents.**

MAARS is a **hybrid multi-agent system**. All three stages combine runtime control with agent intelligence, but in different proportions:

MAARS is a **hybrid multi-agent system**: Refine and Write use Agno Team coordinate mode (multi-agent collaboration), while Research uses a runtime-controlled agentic workflow. The three stages communicate only through the file-based session DB — they are fully decoupled.

| Stage | Mode | What it does |
|-------|------|-------------|
| **Refine** | Multi-Agent Team | Explorer surveys literature + Critic challenges novelty/feasibility → refined proposal |
| **Research** | Agentic Workflow | Runtime-controlled: calibrate → strategy → decompose → execute → verify → evaluate → replan |
| **Write** | Multi-Agent Team | Writer produces draft + Reviewer gives feedback → revised paper |

## Research Pipeline Detail

The Research stage is where the real work happens. It runs as an **agentic workflow runtime** with feedback loops:

```
refined_idea.md
  ↓
Calibrate → Agent self-assesses what "atomic task" means for this domain
Strategy  → Agent researches best approaches, techniques, baselines
Decompose → Recursively break into atomic tasks with dependency DAG
  ↓
┌─ Execute  → Run tasks in topological batches (parallel where possible)
│  Verify   → Score each result: pass / fail+retry / redecompose
│  Evaluate → Compare scores across iterations, decide if improvement plateaued
│  Replan   → Add new tasks based on evaluation feedback
└─ Loop until: iteration limit OR score plateau (<0.5% improvement)
  ↓
Task outputs + artifacts ready for Write stage
```

Key capabilities:
- **Docker sandbox execution** — real code runs in isolated containers with pre-loaded ML stack
- **DAG scheduling** — tasks respect dependency order, parallelize where safe
- **Automatic redecomposition** — if a task is too complex, it splits into subtasks
- **Iteration with scoring** — tracks scores across rounds, stops when improvement plateaus
- **Checkpoint/resume** — pause mid-run, resume later with all state preserved

## Write Pipeline Detail

The Write stage mirrors Refine's architecture — Agno Team coordinate mode with Leader + Writer + Reviewer:

```
Research outputs (tasks/, artifacts/, refined_idea.md)
  ↓
Leader → delegates to Writer (reads all task outputs via tools, writes complete draft)
Leader → delegates to Reviewer (critically reviews the draft)
Leader → delegates to Writer (revises based on feedback)
  ↓
paper.md
```

- **Writer** has tool access (`read_task_output`, `list_artifacts`, `read_refined_idea`, search tools) — reads research outputs on demand
- **Reviewer** evaluates structure, completeness, depth, accuracy, readability — no tools
- **Leader** orchestrates delegation order: Writer → Reviewer → Writer

## Kaggle Mode

Paste a Kaggle competition URL instead of a research idea:

```
https://www.kaggle.com/competitions/titanic
```

MAARS will automatically: fetch competition metadata → download dataset → build a context-rich research proposal → skip Refine → jump straight to Research with data mounted at `/workspace/data/`.

## Configuration

All settings use the `MAARS_` prefix. Copy `.env.example` to `.env` and configure:

```env
# Choose provider: google (default), anthropic, or openai
MAARS_MODEL_PROVIDER=google

# Only the active provider's key is required
MAARS_GOOGLE_API_KEY=your-key
MAARS_GOOGLE_MODEL=gemini-2.5-flash

# MAARS_ANTHROPIC_API_KEY=your-key
# MAARS_ANTHROPIC_MODEL=claude-sonnet-4-5-20250514

# MAARS_OPENAI_API_KEY=your-key
# MAARS_OPENAI_MODEL=gpt-4o

# Per-stage model overrides (optional)
# MAARS_WRITE_PROVIDER=anthropic
# MAARS_WRITE_MODEL=claude-sonnet-4-5-20250514
```

| Setting | Default | Description |
|---------|---------|-------------|
| `MAARS_MODEL_PROVIDER` | `google` | LLM provider: `google`, `anthropic`, or `openai` |
| `MAARS_{STAGE}_PROVIDER` | — | Per-stage provider override (refine/research/write) |
| `MAARS_{STAGE}_MODEL` | — | Per-stage model override |
| `MAARS_RESEARCH_MAX_ITERATIONS` | `3` | Max evaluation loops (1 = no iteration) |
| `MAARS_DOCKER_SANDBOX_TIMEOUT` | `600` | Per-container timeout in seconds |
| `MAARS_DOCKER_SANDBOX_MEMORY` | `4g` | Memory limit per container |
| `MAARS_DOCKER_SANDBOX_CONCURRENCY` | `2` | Max parallel containers (and parallel tasks) |
| `MAARS_KAGGLE_API_TOKEN` | — | Kaggle API token (or use `~/.kaggle/kaggle.json`) |
| `MAARS_API_KEY` | — | API authentication key (recommended for non-localhost) |

> **Security note**: If `MAARS_API_KEY` is not set, the API is open without authentication. Set it before exposing the service on a network.

## Output Structure

Each run creates a timestamped session folder:

```
results/{timestamp}-{slug}/
├── idea.md                  # Original input
├── refined_idea.md          # Refined research proposal
├── calibration.md           # Atomic task definition
├── strategy.md              # Research strategy
├── plan_list.json           # Flat task list (execution view)
├── plan_tree.json           # Hierarchical decomposition tree
├── tasks/                   # Individual task outputs (markdown)
├── artifacts/               # Code scripts, plots, CSVs, models
│   ├── {task_id}/           # Per-task working directory
│   ├── latest_score.json    # Most recent score
│   └── best_score.json      # Global best score tracker
├── evaluations/             # Iteration evaluation results
├── paper.md                 # Final research paper
├── log.jsonl                # Append-only SSE event log (replayable)
└── reproduce/               # Auto-generated reproduction files
    ├── Dockerfile
    ├── run.sh
    └── docker-compose.yml
```

## Frontend

The web UI is built with Vue 3 + Pinia + Vite, providing real-time observability via SSE:

- **Progress bar** — 7-stage pipeline visualization (Refine → Calibrate → Strategy → Decompose → Execute → Evaluate → Write)
- **Command palette** (Ctrl+K) — start, pause, resume pipeline
- **Reasoning log** — live-streamed LLM reasoning, tool calls, and results
- **Process viewer** — task decomposition tree, execution batches, artifacts, documents
- **Session drawer** — browse, restore, and delete past sessions
- **Docker status** — sandbox connectivity indicator

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI, Python async |
| Agent framework | Agno (Team coordinate mode + single-client agentic workflow) |
| LLM providers | Google Gemini, Anthropic Claude, OpenAI GPT |
| Code execution | Docker containers (Python 3.12 + ML stack) |
| Frontend | Vue 3, Pinia, Vite |
| Communication | SSE (Server-Sent Events) with Authorization header |
| Storage | File-based session DB |
| Search tools | DuckDuckGo, arXiv, Wikipedia |
| CI | GitHub Actions (Python lint + test, frontend build) |

## Documentation

| Doc | Content |
|-----|---------|
| [Architecture Design (CN)](docs/CN/architecture.md) | System design rationale and architectural decisions |
| [Roadmap](docs/ROADMAP.md) | Prioritized improvement items and status |

## Community

[Contributing](.github/CONTRIBUTING.md) · [Code of Conduct](.github/CODE_OF_CONDUCT.md) · [Security](.github/SECURITY.md)

## License

MIT
