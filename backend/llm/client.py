from abc import ABC, abstractmethod
from typing import AsyncIterator


class LLMClient(ABC):
    """Abstract base for all LLM providers.

    Mock and real implementations share the same interface so the
    pipeline layer never knows which provider is active.
    """

    # If True, the client handles its own UI broadcasting (e.g., AgentClient).
    # Pipeline will NOT emit text chunks to avoid duplication.
    has_broadcast = False

    @abstractmethod
    async def stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Yield text chunks from the LLM response."""
        ...

    def reset(self):
        """Reset internal state. Called when the pipeline restarts.
        No-op for real LLM clients. MockClient clears response counters."""
        pass
