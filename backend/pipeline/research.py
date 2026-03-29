"""Research stage: decompose → execute → evaluate → loop.

Combines task decomposition, parallel execution with verification,
and result evaluation into a single iterative stage.
"""

from __future__ import annotations

import asyncio
import contextvars
import json

from backend.db import ResearchDB
from backend.pipeline.stage import BaseStage, StageState
from backend.pipeline.decompose import decompose
from backend.pipeline.evaluate import evaluate_results, check_score_improved
from backend.utils import parse_json_fenced

# Per-coroutine task ID tracking for parallel execution.
# When set, ResearchStage._emit() injects task_id into all SSE events
# so the frontend can group chunks by task.
_current_task_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "_current_task_id", default=None,
)


class _RedecomposeNeeded(Exception):
    """Signal that a task needs to be broken into subtasks."""
    def __init__(self, task: dict, result: str, review: str):
        self.task = task
        self.result = result
        self.review = review

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_AUTO = "This is a fully automated pipeline. No human is in the loop. Do NOT ask questions or request input. Make all decisions autonomously. 全文使用中文撰写。\n\n"

_EXECUTE_SYSTEM = _AUTO + """\
You are a research assistant executing a specific task as part of a larger research project.

CRITICAL RULES:
- When a task involves code, data analysis, or experiments: you MUST call code_execute to run real Python code. Do NOT describe code or simulate results — actually execute it.
- When a task involves literature: you MUST call search/fetch tools. Do NOT make up citations.
- NEVER pretend to have executed something. If you didn't call a tool, you didn't do it.

OUTPUT REQUIREMENTS:
- Produce a thorough, well-structured result in markdown
- If you ran code: include key numerical results, describe generated files (e.g., "生成了 convergence_plot.png"), and interpret the findings
- If you reviewed literature: cite specific papers with authors and years
- Use list_artifacts to verify what files were produced

SCORE TRACKING:
- Whenever you obtain a model evaluation score (CV accuracy, F1, AUC, RMSE, etc.), \
save the best result to /workspace/output/best_score.json using code_execute:
  {"metric": "accuracy", "score": 0.85, "model": "XGBoost", "details": "5-fold CV"}
- Always UPDATE this file if you achieve a better score than the existing one (read it first)."""

_VERIFY_SYSTEM = """\
You are a research quality reviewer. Evaluate whether the task result SUBSTANTIALLY meets the goal.

Criteria:
1. Does it address the core intent of the task? (not literal word-matching — reasonable engineering decisions like sampling representative points instead of exhaustive iteration are acceptable)
2. Does it provide real substance, not just descriptions or plans?
3. Is it well-structured and clearly written?

Be pragmatic, not pedantic. A result that achieves the task's purpose through a slightly different approach should PASS. Only fail results that fundamentally miss the point or fabricate data.

Respond with ONLY a JSON object:
If acceptable: {"pass": true, "summary": "One-sentence summary of what was accomplished and key findings"}
If minor issues (format, missing details, insufficient depth — but approach is correct):
  {"pass": false, "redecompose": false, "review": "What needs fixing.", "summary": "One-sentence summary"}
If fundamentally too complex or wrong approach:
  {"pass": false, "redecompose": true, "review": "Why this needs to be broken down.", "summary": "One-sentence summary"}

Set "redecompose" to true ONLY when:
- The task covers multiple distinct sub-goals and the result is shallow on each
- The result shows the task scope exceeds what a single execution can handle
- The methodology is fundamentally wrong, not just incomplete"""


_CALIBRATE_SYSTEM = _AUTO + """\
You are calibrating task decomposition for a research pipeline.
Assess your own capabilities and define what constitutes an "atomic task" — one you can reliably complete in a SINGLE execution session.

If you have tools available, you may briefly test them to verify they work (e.g., one quick search). But keep testing minimal — focus on defining boundaries.

Output ONLY a concise ATOMIC DEFINITION block (3-5 sentences) that will be injected verbatim into a task planner's system prompt. Include:
1. What you can accomplish in a single session given your capabilities
2. Concrete examples of atomic tasks for this research domain
3. Concrete examples of tasks that are TOO LARGE and must be decomposed
Be specific to this research topic — not generic advice."""


def _build_execute_prompt(task: dict, prior_attempt: str = "") -> list[dict]:
    """Build prompt for task execution."""
    messages = [{"role": "system", "content": _EXECUTE_SYSTEM}]

    parts = []
    deps = task.get("dependencies", [])

    if deps:
        parts.append(f"## Prerequisite tasks (use read_task_output to read): {', '.join(deps)}\n---\n")

    if prior_attempt:
        parts.append(
            "## Prior attempt on parent task (reference only — focus on YOUR specific subtask):\n"
            f"{prior_attempt}\n---\n"
        )

    parts.append(f"## Your task [{task['id']}]:\n{task['description']}")

    # Tool-use reminder at the end of user message (closest to generation,
    # most likely to be followed). Only for tool-capable clients.
    from backend.config import settings
    data_hint = ""
    if settings.dataset_dir:
        data_hint = (
            " Dataset files are pre-mounted at /workspace/data/ inside the "
            "code execution sandbox — read them directly (e.g., "
            "pd.read_csv('/workspace/data/train.csv'))."
        )
    parts.append(
        "\n---\n"
        "REMINDER: You MUST call code_execute to run real code. "
        "Do NOT describe or simulate code — actually execute it." + data_hint +
        " Use list_artifacts to verify generated files."
    )

    messages.append({"role": "user", "content": "\n".join(parts)})
    return messages


def _build_verify_prompt(task: dict, result: str) -> list[dict]:
    return [
        {"role": "system", "content": _VERIFY_SYSTEM},
        {"role": "user", "content": (
            f"Task [{task['id']}]: {task['description']}\n\n"
            f"--- Execution result ---\n{result}"
        )},
    ]


def _build_retry_prompt(task: dict, result: str, review: str) -> list[dict]:
    """Build prompt for re-execution after failed verification."""
    messages = _build_execute_prompt(task)
    messages.append({"role": "assistant", "content": result})
    messages.append({"role": "user", "content": (
        f"Your previous output was reviewed and needs improvement:\n\n"
        f"{review}\n\nPlease redo the task addressing the above feedback."
    )})
    return messages


# ---------------------------------------------------------------------------
# Topological sort
# ---------------------------------------------------------------------------

def topological_batches(tasks: list[dict]) -> list[list[dict]]:
    """Group tasks into batches by dependency order.
    Each batch contains tasks whose dependencies are all in prior batches.
    Tasks within a batch can run in parallel.
    """
    task_map = {t["id"]: t for t in tasks}
    remaining = set(task_map.keys())
    completed: set[str] = set()
    batches: list[list[dict]] = []

    while remaining:
        # Find tasks whose deps are all completed
        batch_ids = [
            tid for tid in remaining
            if all(d in completed for d in task_map[tid].get("dependencies", []))
        ]
        if not batch_ids:
            # Shouldn't happen in a valid DAG — break to avoid infinite loop
            batch_ids = list(remaining)

        batches.append([task_map[tid] for tid in batch_ids])
        completed.update(batch_ids)
        remaining -= set(batch_ids)

    return batches


# ---------------------------------------------------------------------------
# ResearchStage
# ---------------------------------------------------------------------------

class ResearchStage(BaseStage):
    """Decomposes, executes, and evaluates research tasks in an iterative loop."""

    def __init__(self, name: str = "research", max_iterations: int = 1,
                 atomic_definition: str = "", **kwargs):
        super().__init__(name=name, **kwargs)
        self._task_results: dict[str, str] = {}
        self._task_summaries: dict[str, str] = {}
        self._max_iterations = max_iterations
        self._atomic_definition = atomic_definition
        self._all_tasks: list[dict] = []
        self._strategy: str = ""  # Strategy from pre-decompose research
        self._prev_score: float | None = None  # Track score across iterations
        # Redecompose state: partial outputs and parent tracking
        self._partial_outputs: dict[str, str] = {}      # parent_id -> partial output
        self._redecompose_parent: dict[str, str] = {}    # subtask_id -> parent_id

    def _emit(self, event_type: str, data):
        """Override to inject task_id into events during task execution."""
        tid = _current_task_id.get()
        if tid and isinstance(data, dict) and "task_id" not in data:
            data = {**data, "task_id": tid}
        super()._emit(event_type, data)

    def load_input(self) -> str:
        return self.db.get_plan_json()

    async def run(self) -> str:
        """Decompose → execute → evaluate → loop."""
        self._run_id += 1
        my_run_id = self._run_id

        self.state = StageState.RUNNING
        self._emit("state", self.state.value)
        self.output = ""

        # Checkpoint: load previously completed tasks from DB
        self._task_results = {}
        self._task_summaries = {}
        self._prev_score = self._load_prev_score()
        self._load_checkpoint()

        try:
            idea = self.db.get_refined_idea()

            # ── Phase 0: CALIBRATE atomic definition ──
            self._emit("phase", "calibrate")
            self._atomic_definition = self.db.get_calibration()
            if not self._atomic_definition:
                calibrated = await self._calibrate_atomic_definition(idea, my_run_id)
                if self._is_stale(my_run_id):
                    return self.output
                if calibrated:
                    self._atomic_definition = calibrated
                    self.db.save_calibration(calibrated)

            # ── Phase 1a: STRATEGY — research best approaches ──
            self._emit("phase", "strategy")
            self._strategy = self.db.get_strategy()
            if not self._strategy:
                strategy = await self._research_strategy(idea, my_run_id)
                if self._is_stale(my_run_id):
                    return self.output
                if strategy:
                    self._strategy = strategy
                    self.db.save_strategy(strategy)

            # ── Phase 1b: DECOMPOSE (skip if plan already exists — resume case) ──
            self._emit("phase", "decompose")
            existing_plan = self.db.get_plan_json()
            if existing_plan and self._task_results:
                # Resume: plan exists and we have completed tasks — skip decompose
                self._all_tasks = json.loads(existing_plan)
            else:
                # Fresh run or retry: decompose from scratch
                flat_tasks, tree = await decompose(
                    idea=idea,
                    llm_client=self.llm_client,
                    max_depth=10,
                    atomic_definition=self._atomic_definition,
                    strategy=self._strategy,
                    stream_callback=lambda t, d: self._emit(t, d),
                    is_stale=lambda: self._is_stale(my_run_id),
                )
                if self._is_stale(my_run_id):
                    return self.output

                self._all_tasks = flat_tasks
                self.db.save_plan(
                    json.dumps(flat_tasks, indent=2, ensure_ascii=False), tree
                )
                self._emit("tree", tree)

            # ── Phase 2: EXECUTE + EVALUATE loop ──
            self._emit("phase", "execute")
            start_iteration = self.db.get_iteration()
            for iteration in range(start_iteration, self._max_iterations):
                if self._is_stale(my_run_id):
                    return self.output

                # Execute all pending tasks
                failed = await self._execute_all_tasks(my_run_id)
                if self._is_stale(my_run_id):
                    return self.output
                if failed:
                    break

                # Evaluate results: system checks score, LLM analyzes improvements
                is_last = iteration >= self._max_iterations - 1
                if is_last:
                    break

                self._emit("phase", "evaluate")

                # Step 1: System check — did the score improve?
                improved, current_score = check_score_improved(
                    self.db.get_artifacts_dir(), self._prev_score,
                )
                if current_score is not None:
                    self._emit("chunk", {
                        "text": "Score Check",
                        "call_id": "Score Check",
                        "label": True,
                    })
                    prev_str = f"{self._prev_score:.5f}" if self._prev_score is not None else "N/A"
                    self._emit("chunk", {
                        "text": f"Current: {current_score:.5f} | Previous: {prev_str} | {'Improved' if improved else 'No improvement'}\n",
                        "call_id": "Score Check",
                    })
                    self._prev_score = current_score

                if not improved and self._prev_score is not None:
                    # Score plateaued — stop iterating
                    self.db.save_evaluation({"satisfied": True, "score": current_score}, iteration)
                    break

                # Step 2: LLM analysis — what to improve next
                summaries = [
                    {"id": tid, "summary": self._task_summaries.get(tid, "(no summary)")}
                    for tid in sorted(self._task_results.keys())
                ]
                evaluation = await evaluate_results(
                    idea=idea,
                    task_summaries=summaries,
                    llm_client=self.llm_client,
                    stream_callback=lambda t, d: self._emit(t, d),
                    is_stale=lambda: self._is_stale(my_run_id),
                )
                if self._is_stale(my_run_id):
                    return self.output

                evaluation["score"] = current_score
                self.db.save_evaluation(evaluation, iteration)

                # Replan: one LLM call that sees all completed work + feedback
                # and decides what tasks to add. NOT a full re-decompose.
                new_tasks = await self._replan(idea, evaluation, my_run_id)
                if self._is_stale(my_run_id):
                    return self.output

                if not new_tasks:
                    break

                # Renumber new tasks to avoid ID conflicts
                new_tasks = self._renumber_tasks(new_tasks, iteration + 1)
                self._all_tasks.extend(new_tasks)
                self.db.save_plan_amendment(new_tasks, iteration + 1)

                # Emit updated tree so frontend shows new branches
                self._emit_replan_tree(new_tasks, iteration + 1)

            # ── Phase 3: FINALIZE ──
            if self.state == StageState.FAILED:
                # A task hard-failed during execution — don't mark as completed
                self._emit("state", self.state.value)
                return self.output

            self.output = self._build_final_output()
            self.state = StageState.COMPLETED
            self._emit("state", self.state.value)
            return self.output

        except asyncio.CancelledError:
            if not self._is_stale(my_run_id):
                self.state = StageState.IDLE
                self._emit("state", self.state.value)
            return self.output

        except Exception as e:
            if not self._is_stale(my_run_id):
                self.state = StageState.FAILED
                self._emit("error", {"message": str(e)})
                self._emit("state", self.state.value)
            raise

    # ------------------------------------------------------------------
    # Task execution
    # ------------------------------------------------------------------

    async def _execute_all_tasks(self, my_run_id: int) -> bool:
        """Execute all pending tasks in topological batches.
        Returns True if any task had a hard failure.

        When a task triggers redecompose, it is replaced by subtasks
        and the batch loop restarts with an updated task list.
        """
        while True:
            batches = topological_batches(self._all_tasks)

            # Emit execution tree for frontend
            self._emit("exec_tree", {
                "batches": [
                    {
                        "batch": i + 1,
                        "tasks": [{"id": t["id"], "description": t["description"]} for t in b],
                    }
                    for i, b in enumerate(batches)
                ]
            })

            had_redecompose = False

            for batch in batches:
                if self._is_stale(my_run_id):
                    return False

                # Checkpoint resume: skip already-completed tasks
                pending = [t for t in batch if t["id"] not in self._task_results]
                for t in batch:
                    if t["id"] in self._task_results:
                        self._emit("task_state", {"task_id": t["id"], "status": "completed"})
                if not pending:
                    continue

                coros = [self._execute_task(task, my_run_id) for task in pending]
                results = await asyncio.gather(*coros, return_exceptions=True)

                for task, result in zip(pending, results):
                    if self._is_stale(my_run_id):
                        return False
                    if isinstance(result, _RedecomposeNeeded):
                        new_tasks = await self._redecompose_task(result, my_run_id)
                        if self._is_stale(my_run_id):
                            return False
                        if new_tasks:
                            parent_id = result.task["id"]
                            subtask_ids = [t["id"] for t in new_tasks]

                            # Replace parent task with subtasks
                            self._all_tasks = [
                                t for t in self._all_tasks
                                if t["id"] != parent_id
                            ]
                            self._all_tasks.extend(new_tasks)

                            # Repoint downstream dependencies: parent → last subtask(s)
                            # Tasks that depended on the parent now depend on ALL subtasks
                            for t in self._all_tasks:
                                if parent_id in t.get("dependencies", []):
                                    t["dependencies"] = [
                                        d if d != parent_id else None
                                        for d in t["dependencies"]
                                    ]
                                    t["dependencies"] = [
                                        d for d in t["dependencies"] if d is not None
                                    ] + subtask_ids

                            had_redecompose = True
                        else:
                            self._emit("task_state", {"task_id": task["id"], "status": "failed"})
                            self.state = StageState.FAILED
                            self._emit("error", {"message": f"Task {task['id']}: redecompose produced no subtasks"})
                            self._emit("state", self.state.value)
                            return True
                    elif isinstance(result, Exception):
                        self._emit("task_state", {"task_id": task["id"], "status": "failed"})
                        self.state = StageState.FAILED
                        self._emit("error", {"message": f"Task {task['id']} failed: {result}"})
                        self._emit("state", self.state.value)
                        return True

                if had_redecompose:
                    break  # Re-batch with updated task list

            if not had_redecompose:
                break  # All tasks completed

        return False

    async def _execute_task(self, task: dict, my_run_id: int) -> str:
        """Execute a single task: run → verify → retry or redecompose."""
        task_id = task["id"]
        token = _current_task_id.set(task_id)
        try:
            return await self._execute_task_inner(task, my_run_id)
        finally:
            _current_task_id.reset(token)

    async def _execute_task_inner(self, task: dict, my_run_id: int) -> str:
        """Inner implementation of _execute_task (with task_id context set)."""
        task_id = task["id"]
        client = self.llm_client

        # Check for parent partial output (from a previous redecompose)
        parent_id = self._redecompose_parent.get(task_id)
        prior_attempt = self._partial_outputs.get(parent_id, "") if parent_id else ""

        # --- Execute ---
        call_id = f"Exec {task_id}"
        self._emit("task_state", {"task_id": task_id, "status": "running"})
        self._emit("chunk", {"text": call_id, "call_id": call_id, "label": True})

        messages = _build_execute_prompt(task, prior_attempt)
        result = await self._stream_llm(client, messages, call_id, my_run_id)
        if self._is_stale(my_run_id):
            return result

        # --- Verify ---
        self._emit("task_state", {"task_id": task_id, "status": "verifying"})

        verify_messages = _build_verify_prompt(task, result)
        verify_response = await self._stream_llm(client, verify_messages, call_id, my_run_id)
        if self._is_stale(my_run_id):
            return result

        passed, review, summary, redecompose = self._parse_verification(verify_response)
        self._task_summaries[task_id] = summary

        if passed:
            self._save_task(task_id, result)
            return result

        # Fundamental problem → redecompose immediately (skip retry)
        if redecompose:
            raise _RedecomposeNeeded(task, result, review)

        # Minor issue → retry once with feedback
        self._emit("task_state", {"task_id": task_id, "status": "retrying"})

        retry_messages = _build_retry_prompt(task, result, review)
        result = await self._stream_llm(client, retry_messages, call_id, my_run_id)
        if self._is_stale(my_run_id):
            return result

        # --- Verify again ---
        self._emit("task_state", {"task_id": task_id, "status": "verifying"})
        verify_messages = _build_verify_prompt(task, result)
        verify_response = await self._stream_llm(client, verify_messages, call_id, my_run_id)
        passed, review, summary, redecompose = self._parse_verification(verify_response)
        self._task_summaries[task_id] = summary

        if passed:
            self._save_task(task_id, result)
            return result

        # Retry failed — redecompose if indicated, otherwise hard fail
        if redecompose:
            raise _RedecomposeNeeded(task, result, review)

        self._emit("task_state", {"task_id": task_id, "status": "failed"})
        raise RuntimeError(f"Task {task_id} failed verification after retry: {review}")

    def _save_task(self, task_id: str, result: str):
        """Save completed task output and emit status."""
        self._emit("task_state", {"task_id": task_id, "status": "completed"})
        if self.db:
            self.db.save_task_output(task_id, result)
        self._task_results[task_id] = result

    async def _stream_llm(self, client, messages: list[dict], call_id: str,
                          my_run_id: int, timeout: float = 300,
                          max_retries: int = 2) -> str:
        """Stream LLM response, dispatching all events uniformly.

        Retries on timeout — API may hang without returning an error.
        """
        for attempt in range(max_retries):
            result = ""
            try:
                async with asyncio.timeout(timeout):
                    async for event in client.stream(messages):
                        if self._is_stale(my_run_id):
                            return result
                        result += self._dispatch_stream(event, call_id)
                return result  # Success
            except TimeoutError:
                if attempt < max_retries - 1:
                    self._emit("chunk", {
                        "text": f"\n[TIMEOUT] Retrying ({attempt + 1}/{max_retries - 1})...\n",
                        "call_id": call_id,
                    })
                else:
                    self._emit("chunk", {
                        "text": f"\n[TIMEOUT] LLM stream failed after {max_retries} attempts\n",
                        "call_id": call_id,
                    })
        return result

    def _parse_verification(self, response: str) -> tuple[bool, str, str, bool]:
        """Parse verification JSON response. Returns (passed, review, summary, redecompose)."""
        data = parse_json_fenced(response, fallback={"pass": True})
        return (
            data.get("pass", True),
            data.get("review", ""),
            data.get("summary", ""),
            data.get("redecompose", False),
        )

    # ------------------------------------------------------------------
    # Replan (informed single LLM call, not recursive decompose)
    # ------------------------------------------------------------------

    _REPLAN_SYSTEM = """\
You are a research planner with tools. Given completed work and evaluation feedback, \
investigate what went wrong or what's missing, then decide what NEW tasks to add.

WORKFLOW:
1. First, USE YOUR TOOLS to investigate:
   - Search for better approaches or techniques relevant to the feedback
   - Read previous task outputs (read_task_output) to understand what was actually done
   - Check artifacts (list_artifacts) to see what files exist
2. Based on your investigation, decide what new tasks to add
3. Output a JSON block at the end of your response:

```json
{"add": [
  {"id": "1", "description": "Specific actionable task", "dependencies": []},
  {"id": "2", "description": "Another task that depends on 1", "dependencies": ["1"]}
]}
```

Rules:
- IDs are simple integers: "1", "2", "3"
- Dependencies are ONLY between NEW tasks (siblings), not existing completed tasks
- Each task description must be specific and actionable
- Tasks should BUILD ON existing work, not redo it
- MAXIMIZE PARALLELISM: only add dependency when truly needed
全文使用中文。"""

    async def _replan(self, idea: str, evaluation: dict, my_run_id: int) -> list[dict]:
        """One LLM call to decide what tasks to add based on evaluation feedback.

        Unlike decompose (recursive, context-free), replan sees the full picture
        of completed work and makes informed decisions about what's missing.
        """
        feedback = evaluation.get("feedback", "")
        suggestions = evaluation.get("suggestions", [])

        if not feedback and not suggestions:
            return []

        # Build context
        completed_ids = sorted(self._task_results.keys())
        completed_summary = "\n".join(
            f"- Task [{tid}]: {self._task_summaries.get(tid, 'completed')}"
            for tid in completed_ids
        )

        artifacts_dir = self.db.get_artifacts_dir()
        artifacts = []
        if artifacts_dir.exists():
            artifacts = [f.name for f in artifacts_dir.iterdir()
                         if f.is_file() and not f.name.startswith("run_")]

        user_parts = [f"## Research Goal\n{idea}"]
        user_parts.append(f"\n## Completed Tasks\n{completed_summary}")
        if artifacts:
            user_parts.append(f"\n## Available Artifacts\n{', '.join(artifacts)}")
        user_parts.append(f"\n## Evaluation Feedback\n{feedback}")
        if suggestions:
            user_parts.append(
                "\n## Suggestions\n" + "\n".join(f"- {s}" for s in suggestions)
            )

        messages = [
            {"role": "system", "content": self._REPLAN_SYSTEM},
            {"role": "user", "content": "\n".join(user_parts)},
        ]

        call_id = "Replan"
        self._emit("chunk", {"text": call_id, "call_id": call_id, "label": True})

        response = await self._stream_llm(
            self.llm_client, messages, call_id, my_run_id,
        )

        data = parse_json_fenced(response, fallback={"add": []})
        new_tasks = data.get("add", [])

        # Validate structure
        valid = []
        for t in new_tasks:
            if isinstance(t, dict) and "id" in t and "description" in t:
                valid.append({
                    "id": t["id"],
                    "description": t["description"],
                    "dependencies": t.get("dependencies", []),
                })
        return valid

    def _emit_replan_tree(self, new_tasks: list[dict], round_num: int):
        """Emit a tree event so the frontend can show new branches on the plan tree."""
        # Build a sub-tree rooted at a "Round N" node
        replan_tree = {
            "id": f"r{round_num}",
            "description": f"Replan round {round_num}",
            "is_atomic": False,
            "dependencies": [],
            "children": [
                {
                    "id": t["id"],
                    "description": t["description"],
                    "is_atomic": True,
                    "dependencies": t.get("dependencies", []),
                    "children": [],
                }
                for t in new_tasks
            ],
        }
        self._emit("replan_tree", replan_tree)

    def _load_prev_score(self) -> float | None:
        """Load the best score from the latest evaluation file."""
        try:
            eval_dir = self.db.get_root() / "evaluations"
            if not eval_dir.exists():
                return None
            files = sorted(eval_dir.glob("eval_v*.json"))
            if not files:
                return None
            data = json.loads(files[-1].read_text())
            score = data.get("score")
            return float(score) if score is not None else None
        except (json.JSONDecodeError, ValueError, RuntimeError):
            return None

    # ------------------------------------------------------------------
    # Strategy research
    # ------------------------------------------------------------------

    _STRATEGY_SYSTEM = _AUTO + """\
You are a research strategist with search tools. Before the team decomposes a research \
project into tasks, you research best practices and winning approaches.

WORKFLOW:
1. USE YOUR SEARCH TOOLS to find:
   - Top-scoring approaches, notebooks, and solutions for this problem/competition
   - Key techniques that winners use (feature engineering, model selection, ensembles)
   - Common pitfalls to avoid
2. Synthesize your findings into a concise STRATEGY document

OUTPUT FORMAT — a concise strategy document (NOT a task list):
- **Key Insights**: What distinguishes high-performing solutions from average ones
- **Recommended Approach**: Specific techniques to prioritize (with rationale)
- **Pitfalls to Avoid**: Common mistakes that hurt performance
- **Target Metric**: What score range to aim for based on your research

Keep it concise (under 500 words). This will be injected into the task planner's context."""

    async def _research_strategy(self, idea: str, my_run_id: int) -> str:
        """Research best approaches before decomposing."""
        call_id = "Strategy"
        self._emit("chunk", {"text": call_id, "call_id": call_id, "label": True})

        messages = [
            {"role": "system", "content": self._STRATEGY_SYSTEM},
            {"role": "user", "content": f"## Research Topic\n{idea}"},
        ]

        response = await self._stream_llm(
            self.llm_client, messages, call_id, my_run_id,
        )
        return response.strip()

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    async def _calibrate_atomic_definition(self, idea: str, my_run_id: int) -> str:
        """Run one LLM/agent call to self-assess capability boundaries.

        In agent mode this is a full agent session (with tools) — the agent
        can test its tools to gauge what it can handle as a single task.
        In text-only mode this is a simple LLM call.
        """
        capabilities = self.llm_client.describe_capabilities()

        call_id = "Calibrate"
        self._emit("chunk", {"text": call_id, "call_id": call_id, "label": True})

        messages = [
            {"role": "system", "content": _CALIBRATE_SYSTEM},
            {"role": "user", "content": (
                f"## Your Capabilities\n{capabilities}\n\n"
                f"## Research Topic\n{idea}"
            )},
        ]

        response = await self._stream_llm(
            self.llm_client, messages, call_id, my_run_id,
        )
        return response.strip()

    # ------------------------------------------------------------------
    # Redecompose
    # ------------------------------------------------------------------

    async def _redecompose_task(self, err: _RedecomposeNeeded, my_run_id: int) -> list[dict]:
        """Break a failed task into subtasks, passing partial output as context.

        Returns renumbered subtasks ready to insert into _all_tasks,
        or empty list if decompose produced nothing.
        """
        task = err.task
        task_id = task["id"]

        self._emit("task_state", {"task_id": task_id, "status": "decomposing"})

        # Save partial output so subtasks can reference it
        self._partial_outputs[task_id] = err.result

        # Build rich context for decomposition
        context = (
            f"## 原始任务 [{task_id}]\n{task['description']}\n\n"
            f"## 已有执行结果（不充分，需要拆分）\n{err.result}\n\n"
            f"## 审查反馈\n{err.review}\n\n"
            f"请将此任务拆分为可独立执行的子任务。"
            f"已有结果中质量合格的部分不需要重做，聚焦于缺失或需要不同方法的部分。"
        )

        # Suppress "tree" events from redecompose — they would overwrite the main plan tree
        def _redecomp_callback(t, d):
            if t != "tree":
                self._emit(t, d)

        flat_tasks, _ = await decompose(
            idea=context,
            llm_client=self.llm_client,
            max_depth=3,
            atomic_definition=self._atomic_definition,
            stream_callback=_redecomp_callback,
            is_stale=lambda: self._is_stale(my_run_id),
        )

        if self._is_stale(my_run_id) or not flat_tasks:
            return []

        # Renumber subtasks under parent: "2_1" → "2_1_d1", "2_1_d2"
        parent_deps = task.get("dependencies", [])
        id_map = {t["id"]: f"{task_id}_d{t['id']}" for t in flat_tasks}

        renumbered = []
        for t in flat_tasks:
            new_id = id_map[t["id"]]
            # Map internal deps; root subtasks (no internal deps) inherit parent deps
            internal_deps = [id_map.get(d, d) for d in t.get("dependencies", [])]
            new_deps = internal_deps if internal_deps else list(parent_deps)

            renumbered.append({
                "id": new_id,
                "description": t["description"],
                "dependencies": new_deps,
            })
            # Track parent so subtasks can access partial output
            self._redecompose_parent[new_id] = task_id

        # Persist updated plan
        if self.db:
            updated = [t for t in self._all_tasks if t["id"] != task_id] + renumbered
            self.db.save_plan(
                json.dumps(updated, indent=2, ensure_ascii=False), None
            )

        return renumbered

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _renumber_tasks(self, tasks: list[dict], round_num: int) -> list[dict]:
        """Prefix task IDs with r{round}_ to avoid conflicts with original plan."""
        prefix = f"r{round_num}_"
        id_map = {}
        renumbered = []

        for task in tasks:
            old_id = task["id"]
            new_id = f"{prefix}{old_id}"
            id_map[old_id] = new_id

        for task in tasks:
            new_deps = []
            for dep in task.get("dependencies", []):
                # Map to new ID if it's a sibling; keep original if it's a pre-existing task
                new_deps.append(id_map.get(dep, dep))
            renumbered.append({
                "id": id_map[task["id"]],
                "description": task["description"],
                "dependencies": new_deps,
            })

        return renumbered

    def _build_final_output(self) -> str:
        """Combine all task results and generate Docker reproduction files."""
        if self.db:
            try:
                from backend.reproduce import generate_reproduce_files
                generate_reproduce_files(self.db)
            except Exception:
                pass  # Non-critical

        parts = []
        for task_id in sorted(self._task_results.keys()):
            parts.append(f"## Task [{task_id}]\n\n{self._task_results[task_id]}")
        return "\n\n---\n\n".join(parts)

    def _load_checkpoint(self):
        """Load completed task outputs from DB for checkpoint resume."""
        if not self.db:
            return
        for info in self.db.list_completed_tasks():
            task_id = info["id"]
            output = self.db.get_task_output(task_id)
            if output:
                self._task_results[task_id] = output

    def retry(self):
        super().retry()
        self._task_results.clear()
        self._task_summaries.clear()
        self._all_tasks.clear()
        self._strategy = ""
        self._prev_score = None
        self._partial_outputs.clear()
        self._redecompose_parent.clear()
        if self.db:
            self.db.clear_tasks()
            self.db.clear_plan()
