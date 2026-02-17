"""
LLM Base — Abstract interface and Message model.

All LLM backends implement BaseLLM.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, AsyncIterator, Union

import aiohttp

from pyda_models.models import (
    MessageRole,
    BackendType,
    LLMConfig,
    LLMResponse,
    StreamChunk,
    ToolDefinition,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Message data-class
# ---------------------------------------------------------------------------

@dataclass
class Message:
    """A single message in a conversation."""
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Abstract Base LLM
# ---------------------------------------------------------------------------

class BaseLLM(ABC):
    """Abstract base class every LLM backend must implement."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._owns_session = False

    # -- async context manager ------------------------------------------------

    async def __aenter__(self):
        """Create an aiohttp session on entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        self._owns_session = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close the aiohttp session on exit."""
        if self.session and self._owns_session:
            await self.session.close()
            self.session = None

    # -- helpers --------------------------------------------------------------

    async def ensure_session(self):
        """Lazily create a session if one doesn't exist."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            )
            self._owns_session = True

    async def close(self):
        """Explicitly close the session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    # -- abstract interface ---------------------------------------------------

    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        stream: bool = False,
    ) -> Union[LLMResponse, AsyncIterator[StreamChunk]]:
        """Generate a completion from a list of messages."""
        ...

    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """Return an approximate token count for *text*."""
        ...

    @abstractmethod
    async def check_health(self) -> bool:
        """Return True if the backend is reachable."""
        ...
