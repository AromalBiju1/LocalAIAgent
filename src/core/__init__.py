"""
LocalAI Agent — Core LLM Module.

Public API
----------
>>> from src.core import LLMFactory, Message, MessageRole
>>> llm = LLMFactory.create(backend="ollama", model_name="qwen3:4b")
"""

from pyda_models.models import (
    BackendType,
    LLMConfig,
    LLMResponse,
    MessageRole,
    StreamChunk,
    ToolDefinition,
)
from src.core.llm_base import BaseLLM, Message
from src.core.ollama_llm import OllamaLLM
from src.core.llamacpp_llm import LlamaCppLLM
from src.core.llm_factory import LLMFactory

__all__ = [
    # Enums / Config
    "BackendType",
    "MessageRole",
    "LLMConfig",
    # Data models
    "Message",
    "LLMResponse",
    "StreamChunk",
    "ToolDefinition",
    # Base class
    "BaseLLM",
    # Implementations
    "OllamaLLM",
    "LlamaCppLLM",
    # Factory
    "LLMFactory",
]
