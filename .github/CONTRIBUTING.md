# Contributing

Thank you for your interest in MAARS! Here's how to get started.

### Development Setup

```bash
git clone https://github.com/dozybot001/MAARS.git
cd MAARS
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your API key
```

Run the app:
```bash
uvicorn backend.main:app --reload
```

### Project Structure

```
backend/
├── pipeline/    # Core framework (Stage, orchestrator, ResearchStage)
├── team/        # TeamStage (RefineStage, WriteStage)
├── agno/        # Stage factory, model factory, tools
├── routes/      # FastAPI HTTP/SSE endpoints
└── db.py        # File-based research storage

frontend/
├── index.html   # Single page
├── css/         # Modular CSS (variables, layout, workspace, etc.)
└── js/          # ES modules (events, api, log-viewer, process-viewer, etc.)
```

### Key Principles

1. **Pipeline layer is adapter-agnostic.** `pipeline/` must never import from `agno/`.
2. **Unified streaming model.** All LLM calls use `call_id`-tagged chunks.
3. **String in, string out.** Stages communicate through `stage.output`.
4. **No build step for frontend.** Vanilla JS/CSS only.

### How to Contribute

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/your-feature`
3. **Make changes** following the principles above
4. **Test** with a real API key
5. **Submit** a Pull Request with a clear description

### Adding a New Provider

Add to `backend/agno/models.py`:
1. Import the Agno model class for your provider
2. Add an `elif` branch in `create_model()`

### Adding Tools

Add to `backend/agno/tools/`:
- DB tools: `tools/db.py`
- Docker tools: `tools/docker_exec.py`
- New tools: create a new file and wire into `agno/__init__.py`
