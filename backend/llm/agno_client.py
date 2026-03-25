"""Agno Agent → LLMClient adapter.

Wraps Agno's Agent streaming into the LLMClient.stream() interface.
- stream() yields only the final conclusion text → pipeline accumulates as stage.output
- Intermediate events (Think/Tool/Result) are pushed via broadcast → UI display
- tools=[] degrades to a simple LLM call (used for Plan)
"""

import logging
from typing import AsyncIterator

from agno.agent import Agent, RunEvent

from backend.llm.client import LLMClient

log = logging.getLogger(__name__)


class AgnoClient(LLMClient):

    has_broadcast = True  # AgnoClient handles its own UI broadcasting

    def __init__(
        self,
        instruction: str,
        model,  # Agno model instance (Gemini, Claude, OpenAIResponses, etc.)
        tools: list | None = None,
    ):
        self._instruction = instruction
        self._model = model
        self._tools = tools or []
        self._broadcast = lambda event: None
        self._stop_requested = False

    def set_broadcast(self, fn):
        """Inject the SSE broadcast callback (called by orchestrator)."""
        self._broadcast = fn

    def request_stop(self):
        """Signal the Agent to stop after the current event."""
        self._stop_requested = True

    def reset(self):
        """Clear stop flag on pipeline restart."""
        self._stop_requested = False

    async def stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Run an Agno Agent and yield the final answer text."""
        merged_instruction, user_text = self._build_agent_prompt(messages)
        async for chunk in self._run_agent(merged_instruction, user_text):
            yield chunk

    async def _run_agent(self, instruction: str, user_text: str) -> AsyncIterator[str]:
        """Create and run an Agno Agent, yielding only the final conclusion."""
        agent = Agent(
            model=self._model,
            instructions=instruction,
            tools=self._tools,
            markdown=True,
        )

        final_text = ""
        step = 0
        self._stop_requested = False

        async for event in agent.arun(user_text, stream=True, stream_events=True):
            if self._stop_requested:
                break

            # --- Token usage ---
            if event.event == RunEvent.run_completed:
                if event.metrics:
                    self._broadcast({
                        "stage": "_agent",
                        "type": "tokens",
                        "data": {
                            "input": event.metrics.input_tokens or 0,
                            "output": event.metrics.output_tokens or 0,
                            "total": event.metrics.total_tokens or 0,
                        },
                    })

            # --- Reasoning ---
            elif event.event == RunEvent.reasoning_step:
                label = f"Think {step}"
                self._broadcast_label(label)
                if event.content:
                    self._broadcast_chunk(str(event.content), call_id=label)
                step += 1

            # --- Tool calls ---
            elif event.event == RunEvent.tool_call_started:
                tool_name = event.tool.tool_name if event.tool else "tool"
                label = f"Tool: {tool_name}"
                self._broadcast_label(label)
                args_str = ""
                if event.tool and event.tool.tool_args:
                    args_str = ", ".join(
                        f"{k}={v}" for k, v in event.tool.tool_args.items()
                    )
                self._broadcast_chunk(
                    f"{tool_name}({args_str})", call_id=label
                )

            elif event.event == RunEvent.tool_call_completed:
                tool_name = event.tool.tool_name if event.tool else "tool"
                label = f"Result: {tool_name}"
                self._broadcast_label(label)
                result_text = str(event.content) if event.content else "(empty)"
                self._broadcast_chunk(result_text[:500], call_id=label)

            # --- Content ---
            elif event.event == RunEvent.run_content:
                if event.content:
                    final_text = str(event.content)

        if final_text:
            yield final_text

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_agent_prompt(self, messages: list[dict]) -> tuple[str, str]:
        """Build agent instruction and user prompt from message history.

        Same logic as AgentClient — both adapters receive the same
        messages format from the pipeline.
        """
        system_parts = []
        user_parts = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                system_parts.append(content)
            elif role == "assistant":
                user_parts.append(f"[Previous Output]\n{content}")
            elif role == "user":
                user_parts.append(content)

        merged_instruction = self._instruction
        if system_parts:
            pipeline_prompt = "\n\n".join(system_parts)
            merged_instruction = f"{self._instruction}\n\n{pipeline_prompt}" if self._instruction else pipeline_prompt

        user_prompt = "\n\n---\n\n".join(user_parts)
        return merged_instruction, user_prompt

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
