# MAARS

[中文](README_CN.md) | English

**Multi-Agent Automated Research System** — from a research idea (or a Kaggle competition) to structured research artifacts and a written `paper.md`, orchestrated end-to-end.

## Features

- **Refine**: shapes input into a concrete research proposal (`refined_idea.md`)
- **Research**: calibrate → strategy → decompose → execute ⇄ verify → evaluate, with iterative improvement
- **Write**: turns research artifacts into `paper.md`
- **Kaggle mode**: paste a competition URL — auto-extracts ID, downloads data to `MAARS_DATASET_DIR`, skips refinement
- **Sandbox**: all code runs in Docker containers

## Quick start

**Requirements:** Python 3.10+, Docker running

```bash
git clone https://github.com/dozybot001/MAARS.git && cd MAARS
bash start.sh
```

`start.sh` creates venv, installs deps, generates `.env` from `.env.example` (first run), optionally builds sandbox image, and starts the server at `http://localhost:8000`.

## Configuration

All variables use the `MAARS_` prefix, configured in `.env` (auto-generated on first `start.sh`).

| Variable | Default | Purpose |
|----------|---------|---------|
| `MAARS_GOOGLE_API_KEY` | — | **Required.** Gemini API key. |
| `MAARS_GOOGLE_MODEL` | `gemini-3-flash-preview` | Model id passed to Agno. |
| `MAARS_API_CONCURRENCY` | `1` | Max concurrent LLM requests. |
| `MAARS_OUTPUT_LANGUAGE` | `Chinese` | Prompt/output language bundle. |
| `MAARS_RESEARCH_MAX_ITERATIONS` | `3` | Max evaluation rounds. Loop may stop earlier if Evaluate returns no `strategy_update`. |
| `MAARS_KAGGLE_API_TOKEN` | — | Optional; `~/.kaggle/kaggle.json` also works. |
| `MAARS_DATASET_DIR` | `data/` | Dataset directory for Research sandbox. |
| `MAARS_DOCKER_SANDBOX_IMAGE` | `maars-sandbox:latest` | Docker image for code execution. |
| `MAARS_DOCKER_SANDBOX_TIMEOUT` | `600` | Per-container timeout (seconds). |
| `MAARS_DOCKER_SANDBOX_MEMORY` | `4g` | Memory limit (e.g. `512m`, `4g`). |
| `MAARS_DOCKER_SANDBOX_CPU` | `1.0` | CPU quota. |
| `MAARS_DOCKER_SANDBOX_NETWORK` | `true` | Network access inside sandbox. |
| `MAARS_SERVER_PORT` | `8000` | Server port (`start.sh` only). |

## Documentation

| Doc | Description |
|-----|-------------|
| [Architecture (CN)](docs/CN/architecture.md) | System design, research stages, SSE, storage layout |

## Community

[Contributing](.github/CONTRIBUTING.md) · [Code of Conduct](.github/CODE_OF_CONDUCT.md) · [Security](.github/SECURITY.md)

## License

MIT
