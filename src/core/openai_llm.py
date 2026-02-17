"""
OpenAI-Compatible LLM Client.

Supports any API that follows the OpenAI Chat Completions format,
including OpenAI itself, Groq, Together, vLLM, LM Studio, and LocalAI.
"""

import logging
import os
from typing import AsyncGenerator, List, Optional, Dict, Any

try:
    from openai import AsyncOpenAI, APIError
except ImportError:
    AsyncOpenAI = None
    APIError = None

from src.core.llm_base import BaseLLM, Message, MessageRole, StreamChunk

logger = logging.getLogger(__name__)


class OpenAILLM(BaseLLM):
    """
    Generic client for OpenAI-compatible APIs.

    Configurable via:
    - base_url: URL to the API endpoint (e.g. "http://localhost:8000/v1")
    - api_key: Authentication key (or "lm-studio" / "dummy" for local)
    - model: Name of the model to use
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        if AsyncOpenAI is None:
            raise ImportError("openai package not installed. Run: pip install openai")

        self.client = AsyncOpenAI(
            base_url=config.get("base_url", "https://api.openai.com/v1"),
            api_key=config.get("api_key") or os.environ.get("OPENAI_API_KEY", "dummy-key"),
            timeout=config.get("timeout", 60.0),
            max_retries=config.get("max_retries", 2),
        )
        self.model_name = config.get("name", "gpt-3.5-turbo")
        self._provider_name = config.get("provider", "openai")

    @property
    def name(self) -> str:
        return f"{self._provider_name}/{self.model_name}"

    async def generate(self, messages: List[Message], stream: bool = True) -> AsyncGenerator[StreamChunk, None]:
        """Generate response from the API."""
        
        # Convert messages to OpenAI format
        formatted_messages = []
        for m in messages:
            msg = {"role": m.role.value, "content": m.content}
            if m.name:
                msg["name"] = m.name
            formatted_messages.append(msg)

        try:
            if stream:
                stream_resp = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=formatted_messages,
                    stream=True,
                    temperature=self.config.get("temperature", 0.7),
                    max_tokens=self.config.get("max_tokens", 2048),
                    top_p=self.config.get("top_p", 1.0),
                )

                async for chunk in stream_resp:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield StreamChunk(content=delta.content, done=False)
                
                yield StreamChunk(content="", done=True)
            
            else:
                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=formatted_messages,
                    stream=False,
                    temperature=self.config.get("temperature", 0.7),
                    max_tokens=self.config.get("max_tokens", 2048),
                    top_p=self.config.get("top_p", 1.0),
                )
                
                content = response.choices[0].message.content or ""
                yield StreamChunk(content=content, done=True)

        except APIError as e:
            logger.error("OpenAI API error (%s): %s", self._provider_name, e)
            yield StreamChunk(content=f"Error: {str(e)}", done=True)
        except Exception as e:
            logger.error("Generation error (%s): %s", self._provider_name, e)
            yield StreamChunk(content=f"Error: {str(e)}", done=True)

    async def check_health(self) -> bool:
        """Check if the API is reachable."""
        try:
            # Try a minimal models list call
            await self.client.models.list()
            return True
        except Exception as e:
            logger.warning("Health check failed for %s: %s", self.name, e)
            return False

    async def close(self):
        await self.client.close()
