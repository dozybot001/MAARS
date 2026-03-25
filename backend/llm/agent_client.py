"""ADK Agent → LLMClient adapter.

Wraps Google ADK Agent's ReAct loop into the LLMClient.stream() interface.
- stream() yields only the final conclusion text → pipeline accumulates as stage.output
- Intermediate ReAct events (Think/Tool/Result) are pushed via broadcast → UI display
- tools=[] degrades to a simple LLM call (used for Plan, Verify)
"""

from typing import AsyncIterator

from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from backend.agent.factory import create_agent
from backend.llm.client import LLMClient


class AgentClient(LLMClient):

    has_broadcast = True  # AgentClient handles its own UI broadcasting

    def __init__(
        self,
        instruction: str,
        model: str = "gemini-2.0-flash",
        tools: list | None = None,
        code_executor=None,
    ):
        self._instruction = instruction
        self._model = model
        self._tools = tools or []
        self._code_executor = code_executor
        self._broadcast = lambda event: None
        self._step_counter = 0

    def set_broadcast(self, fn):
        """Inject the SSE broadcast callback (called by orchestrator)."""
        self._broadcast = fn

    async def stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Run an ADK Agent and yield the final answer text.

        Intermediate ReAct steps (Think/Tool/Result) are broadcast to the
        UI but NOT yielded. Only the final conclusion is yielded so pipeline
        accumulates clean output.

        The full message history from pipeline is concatenated into a single
        user prompt to preserve multi-round context.
        """
        user_text = self._build_agent_prompt(messages)

        agent = create_agent(
            name="maars_agent",
            instruction=self._instruction,
            tools=self._tools,
            model=self._model,
            code_executor=self._code_executor,
        )

        runner = Runner(
            app_name="maars",
            agent=agent,
            session_service=InMemorySessionService(),
        )
        session = await runner.session_service.create_session(
            app_name="maars",
            user_id="maars_user",
        )
        message = types.Content(
            role="user",
            parts=[types.Part(text=user_text)],
        )

        final_text = ""
        step = 0

        async for event in runner.run_async(
            user_id="maars_user",
            session_id=session.id,
            new_message=message,
        ):
            # --- Think: broadcast label + text, last text also yielded ---
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text and not event.partial:
                        label = f"Think {step}"
                        self._broadcast_label(label)
                        self._broadcast_chunk(part.text, call_id=label)
                        step += 1
                        final_text = part.text

            # --- Tool calls: broadcast label + args ---
            function_calls = event.get_function_calls()
            if function_calls:
                for fc in function_calls:
                    label = f"Tool: {fc.name}"
                    self._broadcast_label(label)
                    args_str = ", ".join(
                        f"{k}={v}" for k, v in (fc.args or {}).items()
                    )
                    self._broadcast_chunk(f"{fc.name}({args_str})", call_id=label)

            # --- Tool results: broadcast label + result ---
            function_responses = event.get_function_responses()
            if function_responses:
                for fr in function_responses:
                    label = f"Result: {fr.name}"
                    self._broadcast_label(label)
                    result_text = str(fr.response) if fr.response else "(empty)"
                    self._broadcast_chunk(result_text[:500], call_id=label)

        # Only yield the final conclusion → pipeline emits it
        if final_text:
            yield final_text

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_agent_prompt(self, messages: list[dict]) -> str:
        """Build a single prompt string from the full message history.

        Pipeline sends multi-round context as a list of messages:
          [system, user, assistant, user, assistant, user, ...]

        We concatenate everything (except system — Agent has its own
        instruction) into one prompt so the Agent sees full context.
        """
        parts = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                # Pipeline's flow prompt — include as context, not instruction
                parts.append(f"[Task Instructions]\n{content}")
            elif role == "assistant":
                parts.append(f"[Previous Output]\n{content}")
            elif role == "user":
                parts.append(content)
        return "\n\n---\n\n".join(parts)

    def _broadcast_chunk(self, text: str, call_id: str | None = None):
        """Push a text chunk to the UI via broadcast."""
        self._broadcast({
            "stage": "_agent",
            "type": "chunk",
            "data": {"text": text, "call_id": call_id},
        })

    def _broadcast_label(self, label: str):
        """Push a label (section header) to the UI via broadcast."""
        self._broadcast({
            "stage": "_agent",
            "type": "chunk",
            "data": {"text": label, "call_id": label, "label": True},
        })
