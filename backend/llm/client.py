from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class StreamEvent:
    """Structured event yielded by LLMClient.stream().

    Pipeline dispatches all events uniformly — clients never broadcast directly.
    """
    type: str  # "content" | "think" | "tool_call" | "tool_result" | "tokens"
    text: str = ""
    call_id: str = ""
    metadata: dict = field(default_factory=dict)


class LLMClient(ABC):
    """Abstract base for LLM providers.

    Pipeline layer depends on this interface, never on concrete adapters.
    """

    @abstractmethod
    async def stream(self, messages: list[dict]) -> AsyncIterator[StreamEvent]:
        """Yield StreamEvents from the LLM response."""
        ...

    def describe_capabilities(self) -> str:
        """Describe what this client can do. Used for atomic task calibration.

        Override in subclasses to provide tool-specific descriptions.
        """
        return "AI Agent with tool access and multi-step reasoning."

    def request_stop(self):
        """Signal the client to stop after the current in-flight event."""
        pass

    def reset(self):
        """Reset internal state. Called when the pipeline restarts."""
        pass
