import asyncio
from enum import Enum

from backend.llm.client import LLMClient, StreamEvent


class StageState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class BaseStage:
    """Base class for all pipeline stages.

    Each stage reads its input from DB, runs a single-pass LLM call,
    and writes its output back to DB. Stages communicate only through DB.

    Subclasses set `system_instruction` for the Agent's system prompt.
    """

    system_instruction: str = ""

    def __init__(self, name: str, llm_client: LLMClient | None = None,
                 db=None, broadcast=None, **kwargs):
        self.name = name
        self.state = StageState.IDLE
        self.output = ""
        self.rounds: list[dict] = []

        self.llm_client = llm_client
        self.db = db
        self._broadcast = broadcast or (lambda event: None)
        self._run_id = 0

    # ------------------------------------------------------------------
    # Methods to be overridden by concrete stages
    # ------------------------------------------------------------------

    def load_input(self) -> str:
        """Load this stage's input from DB. Override per stage."""
        return ""

    def get_round_label(self, round_index: int) -> str:
        return ""

    def finalize(self) -> str:
        """Finalize output and persist to DB. Override per stage."""
        return self.output

    # ------------------------------------------------------------------
    # Execution control
    # ------------------------------------------------------------------

    async def run(self) -> str:
        """Execute the stage: load input from DB → LLM call → save to DB."""
        self._run_id += 1
        my_run_id = self._run_id

        self.state = StageState.RUNNING
        self._emit("state", self.state.value)

        input_text = self.load_input()

        try:
            if self._is_stale(my_run_id):
                return self.output

            messages = []
            if self.system_instruction:
                messages.append({"role": "system", "content": self.system_instruction})
            messages.append({"role": "user", "content": input_text})
            call_id = self.get_round_label(0) or self.name
            self._emit("chunk", {"text": call_id, "call_id": call_id, "label": True})

            response = ""

            async for event in self.llm_client.stream(messages):
                if self._is_stale(my_run_id):
                    break
                text = self._dispatch_stream(event, call_id)
                response += text
                self.output += text

            if self._is_stale(my_run_id):
                return self.output

            self.rounds.append({"role": "assistant", "content": response})

            self.output = self.finalize()
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

    def retry(self):
        self._run_id += 1
        self.output = ""
        self.rounds = []
        self.state = StageState.IDLE
        self._emit("state", self.state.value)

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "output_length": len(self.output),
            "rounds": len(self.rounds),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _dispatch_stream(self, event: StreamEvent, call_id: str) -> str:
        """Dispatch a StreamEvent: broadcast to UI, return content text."""
        if event.type == "content":
            self._emit("chunk", {"text": event.text, "call_id": call_id})
            return event.text
        if event.type in ("think", "tool_call", "tool_result"):
            self._emit("chunk", {"text": event.call_id, "call_id": event.call_id, "label": True})
            if event.text:
                self._emit("chunk", {"text": event.text, "call_id": event.call_id})
        elif event.type == "tokens":
            self._emit("tokens", event.metadata)
        return ""

    def _is_stale(self, my_run_id: int) -> bool:
        return my_run_id != self._run_id

    def _emit(self, event_type: str, data):
        self._broadcast({
            "stage": self.name,
            "type": event_type,
            "data": data,
        })
