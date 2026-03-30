"""File-based research database.

Each research session gets a unique folder:
    results/{research_id}/
    ├── meta.json                 # run metadata (score direction, timestamps, etc.)
    ├── idea.md
    ├── refined_idea.md
    ├── calibration.md
    ├── strategy.md
    ├── plan_list.json            # flat atomic tasks with resolved deps (execution view)
    ├── plan_tree.json            # hierarchical decomposition tree (decomposition view)
    ├── paper.md
    ├── tasks/
    │   └── {task_id}.md
    ├── artifacts/
    │   ├── {task_id}/            # per-task working directory
    │   │   ├── 001.py
    │   │   └── ...
    │   ├── best_score.json       # global best (auto-promoted from task dirs)
    │   └── submission.csv
    ├── evaluations/
    │   └── eval_v0.json
    └── reproduce/
        ├── Dockerfile
        ├── run.sh
        └── docker-compose.yml
"""

from pathlib import Path
from datetime import datetime
import json
import os
import re
import tempfile
import threading


class ResearchDB:
    """Manages a research session's file storage.

    Thread-safety: a lock protects read-modify-write sequences on shared
    files (plans, scores, metadata). All file writes use atomic rename
    to prevent corruption if the process is killed mid-write.
    """

    def __init__(self, base_dir: str = "results"):
        self._base = Path(base_dir)
        self._root: Path | None = None
        self.research_id: str = ""
        self.execution_log: list[dict] = []
        self.current_task_id: str | None = None  # set during task execution
        self._write_lock = threading.Lock()  # guards shared-file read-modify-write

    # --- Atomic write ---

    @staticmethod
    def _atomic_write(path: Path, content: str):
        """Write content atomically: temp file + os.replace().

        Prevents partial/corrupt files if the process crashes mid-write.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def create_session(self, idea: str = "") -> str:
        """Create a new research folder. Returns the research ID."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        slug = self._slugify(idea)
        self.research_id = f"{timestamp}-{slug}" if slug else timestamp
        self._root = self._base / self.research_id
        self._root.mkdir(parents=True, exist_ok=True)
        (self._root / "tasks").mkdir(exist_ok=True)
        return self.research_id

    def _ensure_root(self):
        if not self._root:
            raise RuntimeError("No active research session. Call create_session() first.")

    # --- Write ---

    def save_idea(self, text: str):
        self._ensure_root()
        self._atomic_write(self._root / "idea.md", text)

    def save_refined_idea(self, text: str):
        self._ensure_root()
        self._atomic_write(self._root / "refined_idea.md", text)

    def save_plan(self, flat_tasks: list[dict], tree: dict):
        """Save both plan representations atomically."""
        self._ensure_root()
        with self._write_lock:
            self._atomic_write(
                self._root / "plan_list.json",
                json.dumps(flat_tasks, indent=2, ensure_ascii=False),
            )
            self._atomic_write(
                self._root / "plan_tree.json",
                json.dumps(tree, indent=2, ensure_ascii=False),
            )

    def save_paper(self, text: str):
        self._ensure_root()
        self._atomic_write(self._root / "paper.md", text)

    def save_task_output(self, task_id: str, text: str):
        self._ensure_root()
        safe_id = task_id.replace("/", "_")
        self._atomic_write(self._root / "tasks" / f"{safe_id}.md", text)

    # --- Read ---

    def get_idea(self) -> str:
        self._ensure_root()
        path = self._root / "idea.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def get_task_output(self, task_id: str) -> str:
        self._ensure_root()
        safe_id = task_id.replace("/", "_")
        path = self._root / "tasks" / f"{safe_id}.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    @staticmethod
    def _slugify(text: str, max_words: int = 5) -> str:
        """Convert text to a short filesystem-safe slug."""
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9\s]", "", text)
        words = text.split()[:max_words]
        return "-".join(words) if words else ""

    def get_plan_list(self) -> str:
        self._ensure_root()
        path = self._root / "plan_list.json"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def get_plan_tree(self) -> str:
        self._ensure_root()
        path = self._root / "plan_tree.json"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def list_completed_tasks(self) -> list[dict]:
        """List all completed task IDs and their output sizes."""
        self._ensure_root()
        tasks_dir = self._root / "tasks"
        if not tasks_dir.exists():
            return []
        results = []
        for f in sorted(tasks_dir.glob("*.md")):
            results.append({"id": f.stem, "size_bytes": f.stat().st_size})
        return results

    def clear_tasks(self):
        """Delete all task output files for clean retry."""
        self._ensure_root()
        tasks_dir = self._root / "tasks"
        if tasks_dir.exists():
            for f in tasks_dir.glob("*.md"):
                f.unlink()

    def clear_plan(self):
        """Delete plan files for clean retry."""
        self._ensure_root()
        for name in ("plan_list.json", "plan_tree.json"):
            path = self._root / name
            if path.exists():
                path.unlink()
        eval_dir = self._root / "evaluations"
        if eval_dir.exists():
            for f in eval_dir.glob("*.json"):
                f.unlink()

    def get_tasks_dir(self) -> Path:
        """Return the tasks/ directory path."""
        self._ensure_root()
        return self._root / "tasks"

    def get_artifacts_dir(self, task_id: str | None = None) -> Path:
        """Return the artifacts directory, creating it if needed.
        If task_id is given, return the per-task subdirectory.
        """
        self._ensure_root()
        artifacts = self._root / "artifacts"
        artifacts.mkdir(exist_ok=True)
        if task_id:
            safe_id = task_id.replace("/", "_")
            task_dir = artifacts / safe_id
            task_dir.mkdir(exist_ok=True)
            return task_dir
        return artifacts

    def get_refined_idea(self) -> str:
        self._ensure_root()
        path = self._root / "refined_idea.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    # --- Meta (replaces score_direction.txt) ---

    def _meta_path(self) -> Path:
        self._ensure_root()
        return self._root / "meta.json"

    def _load_meta(self) -> dict:
        p = self._meta_path()
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return {}

    def _save_meta(self, meta: dict):
        self._atomic_write(
            self._meta_path(),
            json.dumps(meta, indent=2, ensure_ascii=False),
        )

    def save_score_direction(self, minimize: bool):
        with self._write_lock:
            meta = self._load_meta()
            meta["score_direction"] = "minimize" if minimize else "maximize"
            self._save_meta(meta)

    def get_score_minimize(self) -> bool:
        meta = self._load_meta()
        return meta.get("score_direction", "minimize") == "minimize"

    def update_meta(self, **kwargs):
        """Merge key-value pairs into meta.json."""
        with self._write_lock:
            meta = self._load_meta()
            meta.update(kwargs)
            self._save_meta(meta)

    # --- Calibration & Strategy ---

    def save_calibration(self, text: str):
        self._ensure_root()
        self._atomic_write(self._root / "calibration.md", text)

    def get_calibration(self) -> str:
        self._ensure_root()
        path = self._root / "calibration.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def save_strategy(self, text: str):
        self._ensure_root()
        self._atomic_write(self._root / "strategy.md", text)

    def get_strategy(self) -> str:
        self._ensure_root()
        path = self._root / "strategy.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    # --- Iteration state ---

    def get_iteration(self) -> int:
        """Infer current iteration from the number of saved evaluations."""
        self._ensure_root()
        eval_dir = self._root / "evaluations"
        if not eval_dir.exists():
            return 0
        return len(list(eval_dir.glob("eval_v*.json")))

    def get_latest_score(self) -> float | None:
        """Load the score from the most recent evaluation file."""
        self._ensure_root()
        eval_dir = self._root / "evaluations"
        if not eval_dir.exists():
            return None
        files = sorted(eval_dir.glob("eval_v*.json"))
        if not files:
            return None
        try:
            data = json.loads(files[-1].read_text(encoding="utf-8"))
            score = data.get("score")
            return float(score) if score is not None else None
        except (json.JSONDecodeError, ValueError):
            return None

    # --- Evaluation & Plan Amendments ---

    def save_evaluation(self, data: dict, iteration: int):
        self._ensure_root()
        eval_dir = self._root / "evaluations"
        eval_dir.mkdir(exist_ok=True)
        self._atomic_write(
            eval_dir / f"eval_v{iteration}.json",
            json.dumps(data, indent=2, ensure_ascii=False),
        )

    def save_plan_amendment(self, tasks: list[dict], iteration: int,
                            replan_subtree: dict | None = None):
        """Save additional tasks to plan_list.json and sync tree."""
        self._ensure_root()
        with self._write_lock:
            plan_path = self._root / "plan_list.json"
            existing = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.exists() else []
            existing.extend(tasks)
            self._atomic_write(
                plan_path,
                json.dumps(existing, indent=2, ensure_ascii=False),
            )
            if replan_subtree:
                tree_path = self._root / "plan_tree.json"
                if tree_path.exists():
                    tree = json.loads(tree_path.read_text(encoding="utf-8"))
                    tree.get("children", []).append(replan_subtree)
                    self._atomic_write(
                        tree_path,
                        json.dumps(tree, indent=2, ensure_ascii=False),
                    )

    # --- Artifacts: scripts & reproduce ---

    def save_script(self, code: str, language: str = "python") -> tuple[Path, str]:
        """Save a script to the current task's artifacts dir with sequential naming.
        Returns (script_path, script_name).
        """
        self._ensure_root()
        task_dir = self.get_artifacts_dir(self.current_task_id)
        ext = ".py" if language == "python" else ".r"
        existing = sorted(task_dir.glob(f"*{ext}"))
        seq = len(existing) + 1
        name = f"{seq:03d}{ext}"
        path = task_dir / name
        self._atomic_write(path, code)
        return path, name

    def promote_best_score(self):
        """If current task has a best_score.json, promote to artifacts root.

        Maintains two files:
        - latest_score.json: always updated to the most recent score
        - best_score.json: only updated when the new score is better

        Thread-safe: locked to prevent concurrent promote calls from racing.
        """
        if not self.current_task_id:
            return
        task_dir = self.get_artifacts_dir(self.current_task_id)
        task_score_path = task_dir / "best_score.json"
        if not task_score_path.exists():
            return
        try:
            task_data = json.loads(task_score_path.read_text(encoding="utf-8"))
            task_score = float(task_data.get("score", 0))
        except (json.JSONDecodeError, ValueError, TypeError):
            return

        task_content = task_score_path.read_text(encoding="utf-8")

        with self._write_lock:
            artifacts_root = self.get_artifacts_dir()
            minimize = self.get_score_minimize()

            # Always update latest_score.json
            self._atomic_write(artifacts_root / "latest_score.json", task_content)

            # Only update best_score.json if this score is better
            best_path = artifacts_root / "best_score.json"
            if best_path.exists():
                try:
                    best_data = json.loads(best_path.read_text(encoding="utf-8"))
                    best_score = float(best_data.get("score", 0))
                    if minimize:
                        is_better = task_score < best_score
                    else:
                        is_better = task_score > best_score
                    if not is_better:
                        return
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass
            self._atomic_write(best_path, task_content)

    def save_reproduce_files(self, dockerfile: str, run_sh: str, compose: str):
        """Save Docker reproduction files to reproduce/ subdirectory."""
        self._ensure_root()
        reproduce_dir = self._root / "reproduce"
        reproduce_dir.mkdir(exist_ok=True)
        self._atomic_write(reproduce_dir / "Dockerfile", dockerfile)
        self._atomic_write(reproduce_dir / "run.sh", run_sh)
        self._atomic_write(reproduce_dir / "docker-compose.yml", compose)
