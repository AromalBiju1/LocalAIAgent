"""
Pydantic schemas for the FastAPI endpoints.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


# ── Request Models ───────────────────────────────────────

class ChatMessage(BaseModel):
    """A single message in API request format."""
    role: str = Field(..., description="Message role: system, user, assistant, tool")
    content: str = Field(..., description="Message content")
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class ChatRequest(BaseModel):
    """Request body for /api/chat."""
    messages: List[ChatMessage] = Field(..., description="Conversation messages")
    model: Optional[str] = Field(None, description="Model override")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1)
    stream: bool = Field(default=False, description="Enable streaming")
    tools_enabled: bool = Field(default=True, description="Allow tool calling")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for persistence")


class ModelSwitchRequest(BaseModel):
    """Request body for switching models."""
    model: str = Field(..., description="Model name to switch to")
    backend: str = Field(default="ollama")


# ── Response Models ──────────────────────────────────────

class ChatResponse(BaseModel):
    """Response body for /api/chat."""
    content: str
    model: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class StreamEvent(BaseModel):
    """A single SSE event for streaming responses."""
    event: str = Field(default="token", description="Event type: token, tool_call, done, error")
    content: str = Field(default="")
    done: bool = False
    tool_name: Optional[str] = None
    tool_result: Optional[str] = None
    tokens_used: Optional[int] = None


class ToolInfo(BaseModel):
    """Tool information for the /api/tools endpoint."""
    name: str
    description: str
    parameters: Dict[str, Any]


class HealthResponse(BaseModel):
    """Response for /api/health."""
    status: str
    backend: str
    model: str
    tools_count: int
    uptime_seconds: float


class ModelInfo(BaseModel):
    """Model information."""
    name: str
    available: bool = True
