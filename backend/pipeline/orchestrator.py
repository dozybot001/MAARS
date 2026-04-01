import asyncio
import logging

from backend.db import ResearchDB
from backend.pipeline.stage import Stage, StageState

STAGE_ORDER = ["refine", "research", "write"]


class PipelineOrchestrator:
    """Manages the research pipeline: Refine → Research → Write."""

    def __init__(self):
        self.research_input = ""
        self.db = ResearchDB()
        self.event_queue: asyncio.Queue = asyncio.Queue(maxsize=1024)
        self.stages: dict[str, Stage] = {
            name: Stage(name=name) for name in STAGE_ORDER
        }
        self._pipeline_task: asyncio.Task | None = None

    async def start(self, research_input: str):
        from backend.kaggle import extract_competition_id
        await self._cancel_pipeline()
        kaggle_id = extract_competition_id(research_input)
        if kaggle_id:
            await asyncio.to_thread(self._start_kaggle, research_input, kaggle_id)
            self._reset_stages()
            self._mark_refine_done()
            self._pipeline_task = asyncio.create_task(self._run_from("research"))
        else:
            self.research_input = research_input
            self.db.create_session(research_input)
            self.db.save_idea(research_input)
            self._reset_stages()
            self._pipeline_task = asyncio.create_task(self._run_from("refine"))

    async def stop(self):
        stage = self._find_stage(StageState.RUNNING)
        if not stage:
            return
        stage.request_stop()
        self._kill_containers()
        await self._cancel_pipeline(timeout=5.0)
        stage.state = StageState.PAUSED
        stage._send()

    async def resume(self):
        stage = self._find_stage(StageState.PAUSED)
        if not stage:
            return
        stage.output = ""
        stage._stop_requested = False
        self._pipeline_task = asyncio.create_task(self._run_from(stage.name))

    async def shutdown(self):
        self._kill_containers()
        await self._cancel_pipeline(timeout=5.0)

    def _find_stage(self, state: StageState) -> Stage | None:
        for name in STAGE_ORDER:
            if self.stages[name].state == state:
                return self.stages[name]
        return None

    async def _cancel_pipeline(self, timeout: float = 5.0):
        task = self._pipeline_task
        self._pipeline_task = None
        if task is not None and not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception:
                logging.getLogger(__name__).warning(
                    "Unexpected error while cancelling pipeline", exc_info=True,
                )

    def _kill_containers(self):
        from backend.agno.tools.docker_exec import kill_all_containers
        kill_all_containers()

    def _reset_stages(self):
        for stage in self.stages.values():
            stage.retry()

    def _start_kaggle(self, raw_input: str, competition_id: str):
        import re
        from backend.kaggle import fetch_competition, build_kaggle_idea
        from backend.config import settings
        info = fetch_competition(competition_id)
        # Mutate settings for current session — safe for single-session use
        settings.dataset_dir = info["data_dir"]
        settings.kaggle_competition_id = competition_id
        refined = build_kaggle_idea(info)
        user_hint = re.sub(r'https?://\S+', '', raw_input).strip()
        if user_hint:
            refined += f"\n## User Notes\n\n{user_hint}\n"
        self.research_input = refined
        self.db.create_session(info["title"])
        self.db.save_idea(raw_input)
        self.db.save_refined_idea(refined)

    def _mark_refine_done(self):
        refine = self.stages["refine"]
        refine.output = self.research_input
        refine.state = StageState.COMPLETED
        refine._send()  # done signal: refined_idea.md already saved

    async def _run_from(self, stage_name: str):
        idx = STAGE_ORDER.index(stage_name)
        for name in STAGE_ORDER[idx:]:
            try:
                stage = self.stages[name]
                await stage.run()
                if stage.state != StageState.COMPLETED:
                    break
            except asyncio.CancelledError:
                raise
            except Exception:
                break

    def _broadcast(self, event: dict):
        try:
            self.event_queue.put_nowait(event)
        except asyncio.QueueFull:
            pass

    def _wire_broadcast(self):
        for stage in self.stages.values():
            stage._broadcast = self._broadcast

    def get_status(self) -> dict:
        return {
            "input": self.research_input,
            "stages": [self.stages[name].get_status() for name in STAGE_ORDER],
        }
