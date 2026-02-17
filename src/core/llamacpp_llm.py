"""
Llama.cpp LLM Backend — HTTP client for the llama.cpp server.

Uses the OpenAI-compatible ``/v1/chat/completions`` endpoint.
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


class LlamaCppLLM(BaseLLM):
    """llama.cpp backend via its OpenAI-compatible HTTP API."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.llamacpp_host.rstrip("/")

    # ------------------------------------------------------------------
    # Generate
    # ------------------------------------------------------------------

    async def generate(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        stream: bool = False,
    ) -> Union[LLMResponse, AsyncIterator[StreamChunk]]:
        """Generate a completion using llama.cpp server."""
        await self.ensure_session()

        if stream:
            return self._stream_generate(messages, tools)

        payload = self._build_payload(messages, tools, stream=False)

        try:
            async with self.session.post(
                f"{self.base_url}/v1/chat/completions", json=payload
            ) as response:
                response.raise_for_status()
                result = await response.json()
                choice = result.get("choices", [{}])[0]
                message = choice.get("message", {})

                return LLMResponse(
                    content=message.get("content", ""),
                    model=result.get("model", self.config.model_name),
                    tokens_used=result.get("usage", {}).get("total_tokens"),
                    finish_reason=choice.get("finish_reason"),
                    tool_calls=message.get("tool_calls"),
                )

        except aiohttp.ClientError as e:
            logger.error("llama.cpp API error: %s", e)
            raise RuntimeError(f"Failed to generate completion: {e}") from e

    # ------------------------------------------------------------------
    # Streaming (SSE)
    # ------------------------------------------------------------------

    async def _stream_generate(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream tokens from llama.cpp (Server-Sent Events)."""
        await self.ensure_session()
        payload = self._build_payload(messages, tools, stream=True)

        try:
            async with self.session.post(
                f"{self.base_url}/v1/chat/completions", json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.content:
                    if not line:
                        continue
                    line_str = line.decode("utf-8").strip()
                    if not line_str.startswith("data: "):
                        continue
                    data_str = line_str[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk_data = json.loads(data_str)
                        choice = chunk_data.get("choices", [{}])[0]
                        delta = choice.get("delta", {})

                        yield StreamChunk(
                            content=delta.get("content", ""),
                            done=choice.get("finish_reason") is not None,
                            tokens_used=chunk_data.get("usage", {}).get("total_tokens"),
                        )
                        if choice.get("finish_reason"):
                            break
                    except json.JSONDecodeError:
                        continue

        except aiohttp.ClientError as e:
            logger.error("llama.cpp streaming error: %s", e)
            raise RuntimeError(f"Failed to stream completion: {e}") from e

    # ------------------------------------------------------------------
    # Payload builder (OpenAI-compatible format)
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]],
        stream: bool,
    ) -> Dict[str, Any]:
        """Build an OpenAI-compatible JSON payload."""
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
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "top_p": self.config.top_p,
        }

        if self.config.stop_sequences:
            payload["stop"] = self.config.stop_sequences

        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": tool.model_dump(),
                }
                for tool in tools
            ]

        return payload

    # ------------------------------------------------------------------
    # Token counting
    # ------------------------------------------------------------------

    async def count_tokens(self, text: str) -> int:
        """Approximate token count (~4 chars per token)."""
        return len(text) // 4

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def check_health(self) -> bool:
        """Return True if the llama.cpp server is reachable."""
        await self.ensure_session()
        try:
            async with self.session.get(f"{self.base_url}/v1/models") as resp:
                return resp.status == 200
        except Exception as e:
            logger.error("llama.cpp health-check failed: %s", e)
            return False
