"""
Ollama LLM Backend — HTTP client for the Ollama REST API.

Supports sync/async generation, streaming, and tool calling.
"""

import json
import logging
from typing import List, Dict, Any, Optional, AsyncIterator, Union

import aiohttp

from pyda_models.models import (
    LLMConfig,
    LLMResponse,
    StreamChunk,
    ToolDefinition,
)
from src.core.llm_base import BaseLLM, Message

logger = logging.getLogger(__name__)


class OllamaLLM(BaseLLM):
    """Ollama backend via its HTTP API (default: http://localhost:11434)."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.ollama_host.rstrip("/")
        self._supports_native_tools: Optional[bool] = None  # auto-detected

    # ------------------------------------------------------------------
    # Generate
    # ------------------------------------------------------------------

    async def generate(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        stream: bool = False,
    ) -> Union[LLMResponse, AsyncIterator[StreamChunk]]:
        """Generate a completion using Ollama."""
        await self.ensure_session()

        # Skip native tools if model doesn't support them
        effective_tools = tools if self._supports_native_tools is not False else None

        if stream:
            return self._stream_generate(messages, effective_tools)

        payload = self._build_payload(messages, effective_tools, stream=False)

        try:
            async with self.session.post(
                f"{self.base_url}/api/chat", json=payload
            ) as response:
                if response.status == 400 and effective_tools:
                    # Model doesn't support native tool calling — retry without
                    logger.warning("Model doesn't support native tools, retrying without")
                    self._supports_native_tools = False
                    payload = self._build_payload(messages, None, stream=False)
                    async with self.session.post(
                        f"{self.base_url}/api/chat", json=payload
                    ) as retry_resp:
                        retry_resp.raise_for_status()
                        result = await retry_resp.json()
                else:
                    response.raise_for_status()
                    result = await response.json()
                    if effective_tools and self._supports_native_tools is None:
                        self._supports_native_tools = True

                return LLMResponse(
                    content=result.get("message", {}).get("content", ""),
                    model=result.get("model", self.config.model_name),
                    tokens_used=result.get("eval_count"),
                    finish_reason=result.get("done_reason"),
                    tool_calls=result.get("message", {}).get("tool_calls"),
                )

        except aiohttp.ClientError as e:
            logger.error("Ollama API error: %s", e)
            raise RuntimeError(f"Failed to generate completion: {e}") from e

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    async def _stream_generate(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream tokens from Ollama."""
        await self.ensure_session()
        payload = self._build_payload(messages, tools, stream=True)

        try:
            async with self.session.post(
                f"{self.base_url}/api/chat", json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.content:
                    if not line:
                        continue
                    try:
                        chunk_data = json.loads(line.decode("utf-8"))
                        yield StreamChunk(
                            content=chunk_data.get("message", {}).get("content", ""),
                            done=chunk_data.get("done", False),
                            tokens_used=chunk_data.get("eval_count"),
                        )
                        if chunk_data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue

        except aiohttp.ClientError as e:
            logger.error("Ollama streaming error: %s", e)
            raise RuntimeError(f"Failed to stream completion: {e}") from e

    # ------------------------------------------------------------------
    # Payload builder
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]],
        stream: bool,
    ) -> Dict[str, Any]:
        """Build the JSON payload for the Ollama /api/chat endpoint."""
        formatted_msgs = []
        for msg in messages:
            d: Dict[str, Any] = {
                "role": msg.role.value,
                "content": msg.content,
            }
            if msg.tool_calls:
                d["tool_calls"] = msg.tool_calls
            formatted_msgs.append(d)

        payload: Dict[str, Any] = {
            "model": self.config.model_name,
            "messages": formatted_msgs,
            "stream": stream,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
                "top_p": self.config.top_p,
                "top_k": self.config.top_k,
                "repeat_penalty": self.config.repeat_penalty,
            },
        }

        if self.config.stop_sequences:
            payload["options"]["stop"] = self.config.stop_sequences

        if tools:
            payload["tools"] = [tool.model_dump() for tool in tools]

        return payload

    # ------------------------------------------------------------------
    # Token counting
    # ------------------------------------------------------------------

    async def count_tokens(self, text: str) -> int:
        """Approximate token count (~4 chars per token).

        Ollama doesn't expose a tokeniser endpoint, so this is a rough
        heuristic.
        """
        return len(text) // 4

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def check_health(self) -> bool:
        """Return True if the Ollama server is reachable."""
        await self.ensure_session()
        try:
            async with self.session.get(f"{self.base_url}/api/tags") as resp:
                return resp.status == 200
        except Exception as e:
            logger.error("Ollama health-check failed: %s", e)
            return False

    # ------------------------------------------------------------------
    # Model management helpers
    # ------------------------------------------------------------------

    async def list_models(self) -> List[str]:
        """Return a list of model names available on the Ollama server."""
        await self.ensure_session()
        try:
            async with self.session.get(f"{self.base_url}/api/tags") as resp:
                resp.raise_for_status()
                data = await resp.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.error("Failed to list Ollama models: %s", e)
            return []
