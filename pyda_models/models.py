"""Pydantic data models for the LocalAI Agent Framework."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class BackendType(str, Enum):
    """Supported LLM backends."""
    OLLAMA = "ollama"
    LLAMACPP = "llamacpp"


class MessageRole(str, Enum):
    """Message roles in conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolDefinition(BaseModel):
    """Function/tool definition for tool calling."""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="JSON schema of parameters")


class LLMConfig(BaseModel):
    """LLM configuration."""
    model_name: str = Field(default="qwen3:4b", description="Model identifier")
    backend: BackendType = Field(default=BackendType.OLLAMA)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    top_k: int = Field(default=40, ge=0)
    repeat_penalty: float = Field(default=1.1, ge=0.0)
    stop_sequences: List[str] = Field(default_factory=list)
    timeout: int = Field(default=300, description="Request timeout in seconds")
    # Backend-specific settings
    ollama_host: str = Field(default="http://localhost:11434")
    llamacpp_host: str = Field(default="http://localhost:8080")


class LLMResponse(BaseModel):
    """LLM response container."""
    content: str
    model: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class StreamChunk(BaseModel):
    """Streaming response chunk."""
    content: str
    done: bool = False
    tokens_used: Optional[int] = None
