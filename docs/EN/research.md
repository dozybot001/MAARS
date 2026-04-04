# Research Stage Details

[中文](../CN/research.md) | English

> Back to [Architecture Overview](architecture.md)

Research is the core MAARS stage. Runtime orchestrates task decomposition, parallel execution, verification, and iterative evaluation. Agents execute each atomic task in Docker sandboxes.

## 1. Prerequisites

`_preflight_docker` runs at the start of `_execute()`:
- Docker SDK installed (`pip install docker`)
- Docker daemon reachable (`client.ping()`)
- `MAARS_DOCKER_SANDBOX_IMAGE` built (default `maars-sandbox:latest`)

Fails immediately with a clear error — no tokens wasted on calibration.

## 2. Principles

- Every LLM call includes a capability profile (`_build_capability_profile`) with sandbox config and tool list
- Pipeline: Calibrate -> Strategy -> Decompose -> Execute -> Evaluate, context passed explicitly
- `plan_tree.json` is the single source of truth; `plan_list.json` is a derived cache

## 3. Key Phases

### Calibrate (one-time)

| Field | Content |
|---|---|
| Input | Capability profile + dataset + research topic |
| Output | Atomic definition (3-5 sentences), injected into Decompose system prompt |
| Storage | `calibration.md` |

### Strategy (per round)

| Field | Content |
|---|---|
| Input | Capability profile + dataset + atomic definition + topic (round 1) / old strategy + eval feedback (subsequent) |
| Output | Strategy document + score_direction |
| Storage | `strategy/round_N.md` |

### Decompose (per round)

| Field | Content |
|---|---|
| Input | Topic (or iteration context) + atomic definition + strategy + sibling context |
| Output | Flat task list + tree structure |
| Storage | `plan_tree.json` + `plan_list.json` |
| Mechanism | Recursive decomposition, `root_id` for subtree re-decompose, search/read tools available |

### Execute (per task, parallelizable)

| Field | Content |
|---|---|
| Input | Task description + sandbox constraints + dependency summaries |
| Output | Markdown result + artifacts + SUMMARY line |
| Storage | `tasks/{id}.md` + `artifacts/{id}/` |
| Mechanism | `asyncio.gather` parallel + Semaphore (`api_concurrency`) for concurrency |

### Verify (per task)

| Field | Content |
|---|---|
| Input | Task description + execution result |
| Output | `{pass, review, redecompose}` |
| Mechanism | Encouraged to call list_artifacts to verify; fallback=`pass:false` |
| Paths | pass -> done / retry -> re-execute / redecompose -> split into subtasks |

### Evaluate (per round)

| Field | Content |
|---|---|
| Input | Research goal + strategy + score trend + historical evals + capability profile + task summaries |
| Output | `{feedback, suggestions, strategy_update?}` |
| Storage | `evaluations/round_N.json` + `evaluations/round_N.md` |
| Mechanism | `strategy_update` present -> continue iterating; `is_final` -> summarize, stop |

## 4. Main Loop Skeleton

```python
async def _execute(self):
    await _preflight_docker()

    await _calibrate_once(idea)     # one-time

    evaluation = None
    while True:
        Strategy(idea, evaluation?)
        Decompose(idea, strategy)
        Execute(tasks)               # parallel, with verify/retry/redecompose
        Evaluate(results, score)
        if not strategy_update: break
        iteration += 1
```

## 5. Key Decisions

| Decision | Choice |
|---|---|
| Iteration control | Evaluate outputs `strategy_update` to decide continuation |
| Iteration feedback | Strategy update triggers fresh Decompose |
| Granularity | Capability profile + LLM (Calibrate phase) |
| Re-decompose | `decompose(root_id=task_id)` |
| Summary | Execute agent writes SUMMARY line for downstream reference |
| Verify fallback | `pass=False` |
| Source of truth | `plan_tree.json`; `plan_list.json` derived |

## 6. Parallel Execution

```python
# Topological batching
batches = topological_batches(tasks)   # respect dependency DAG

for batch in batches:
    results = await asyncio.gather(
        *[execute_task(t) for t in pending],
        return_exceptions=True,
    )
```

Each `execute_task` acquires `_get_api_semaphore()` to limit LLM concurrency (`MAARS_API_CONCURRENCY`).

Execute -> Verify -> (pass | retry | redecompose) is an atomic cycle, completed within the semaphore.

## 7. Code Locations

| File | Role |
|---|---|
| `backend/pipeline/research.py` | ResearchStage — main loop + task execution |
| `backend/pipeline/decompose.py` | Recursive decomposition engine |
| `backend/pipeline/stage.py` | Stage base class + `_stream_llm` |
| `backend/pipeline/prompts_en.py` | EN prompts + builder functions |
| `backend/pipeline/prompts_zh.py` | ZH prompts |
| `backend/agno/tools/docker_exec.py` | code_execute + list_artifacts |
| `backend/agno/tools/db.py` | list_tasks + read_task_output + read_refined_idea + read_plan_tree |
