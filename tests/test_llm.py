"""
Comprehensive test suite for the LocalAI Agent Framework LLM module.

Run with:
    pytest tests/test_llm.py -v
    pytest tests/test_llm.py --cov=src/core --cov-report=html
"""

import json
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest
import pytest_asyncio

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def default_config():
    return LLMConfig()


@pytest.fixture
def ollama_config():
    return LLMConfig(
        model_name="qwen3:4b",
        backend=BackendType.OLLAMA,
        temperature=0.7,
        max_tokens=2048,
    )


@pytest.fixture
def llamacpp_config():
    return LLMConfig(
        model_name="my-model",
        backend=BackendType.LLAMACPP,
        llamacpp_host="http://localhost:8080",
    )


@pytest.fixture
def sample_messages():
    return [
        Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
        Message(role=MessageRole.USER, content="Hello!"),
    ]


@pytest.fixture
def sample_tool():
    return ToolDefinition(
        name="calculator",
        description="Perform basic math operations",
        parameters={
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression"},
            },
            "required": ["expression"],
        },
    )


# ======================================================================
# Data Model Tests
# ======================================================================

class TestMessage:
    """Test the Message dataclass."""

    def test_create_user_message(self):
        msg = Message(role=MessageRole.USER, content="Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert msg.name is None
        assert msg.tool_calls is None
        assert msg.tool_call_id is None

    def test_create_system_message(self):
        msg = Message(role=MessageRole.SYSTEM, content="You are helpful.")
        assert msg.role == MessageRole.SYSTEM

    def test_create_assistant_message(self):
        msg = Message(role=MessageRole.ASSISTANT, content="Hi there!")
        assert msg.role == MessageRole.ASSISTANT

    def test_create_tool_message(self):
        msg = Message(role=MessageRole.TOOL, content="result", tool_call_id="call_1")
        assert msg.role == MessageRole.TOOL
        assert msg.tool_call_id == "call_1"

    def test_message_with_tool_calls(self):
        calls = [{"id": "1", "function": {"name": "calc", "arguments": "{}"}}]
        msg = Message(role=MessageRole.ASSISTANT, content="", tool_calls=calls)
        assert msg.tool_calls == calls


class TestLLMConfig:
    """Test the LLMConfig Pydantic model."""

    def test_defaults(self, default_config):
        assert default_config.model_name == "qwen3:4b"
        assert default_config.backend == BackendType.OLLAMA
        assert default_config.temperature == 0.7
        assert default_config.max_tokens == 2048
        assert default_config.top_p == 0.9
        assert default_config.top_k == 40
        assert default_config.ollama_host == "http://localhost:11434"

    def test_custom_config(self):
        cfg = LLMConfig(model_name="mistral:7b", temperature=0.3, max_tokens=1024)
        assert cfg.model_name == "mistral:7b"
        assert cfg.temperature == 0.3
        assert cfg.max_tokens == 1024

    def test_temperature_bounds(self):
        with pytest.raises(Exception):
            LLMConfig(temperature=3.0)  # above max 2.0

    def test_stop_sequences(self):
        cfg = LLMConfig(stop_sequences=["<|end|>", "###"])
        assert len(cfg.stop_sequences) == 2


class TestLLMResponse:
    """Test the LLMResponse model."""

    def test_basic_response(self):
        resp = LLMResponse(content="Hello!", model="qwen3:4b")
        assert resp.content == "Hello!"
        assert resp.model == "qwen3:4b"
        assert resp.tokens_used is None

    def test_full_response(self):
        resp = LLMResponse(
            content="Answer",
            model="qwen3:4b",
            tokens_used=42,
            finish_reason="stop",
            tool_calls=[{"id": "1"}],
        )
        assert resp.tokens_used == 42
        assert resp.finish_reason == "stop"
        assert len(resp.tool_calls) == 1


class TestStreamChunk:
    """Test the StreamChunk model."""

    def test_chunk(self):
        chunk = StreamChunk(content="Hel")
        assert chunk.content == "Hel"
        assert chunk.done is False

    def test_final_chunk(self):
        chunk = StreamChunk(content=".", done=True, tokens_used=10)
        assert chunk.done is True
        assert chunk.tokens_used == 10


class TestToolDefinition:
    """Test the ToolDefinition model."""

    def test_create(self, sample_tool):
        assert sample_tool.name == "calculator"
        assert "expression" in sample_tool.parameters["properties"]


# ======================================================================
# Factory Tests
# ======================================================================

class TestLLMFactory:
    """Test the LLMFactory class."""

    def test_create_ollama(self):
        llm = LLMFactory.create(backend="ollama", model_name="qwen3:4b")
        assert isinstance(llm, OllamaLLM)
        assert llm.config.model_name == "qwen3:4b"

    def test_create_llamacpp(self):
        llm = LLMFactory.create(backend="llamacpp", model_name="my-model")
        assert isinstance(llm, LlamaCppLLM)
        assert llm.config.model_name == "my-model"

    def test_create_unknown_backend(self):
        with pytest.raises(ValueError, match="Unknown backend"):
            LLMFactory.create(backend="invalid")

    def test_create_with_params(self):
        llm = LLMFactory.create(backend="ollama", model_name="test", temperature=0.1, max_tokens=100)
        assert llm.config.temperature == 0.1
        assert llm.config.max_tokens == 100

    def test_from_config_dict(self):
        cfg = {
            "backend": "ollama",
            "name": "qwen3:4b",
            "temperature": 0.5,
        }
        llm = LLMFactory.from_config(cfg)
        assert isinstance(llm, OllamaLLM)
        assert llm.config.temperature == 0.5

    def test_from_config_with_nested(self):
        cfg = {
            "backend": "ollama",
            "name": "qwen3:4b",
            "ollama": {
                "base_url": "http://myhost:11434",
                "timeout": 600,
            },
        }
        llm = LLMFactory.from_config(cfg)
        assert llm.config.ollama_host == "http://myhost:11434"
        assert llm.config.timeout == 600

    def test_get_available_backends(self):
        backends = LLMFactory.get_available_backends()
        assert "ollama" in backends
        assert "llamacpp" in backends

    def test_recommend_backend(self):
        rec = LLMFactory.recommend_backend()
        assert rec == "ollama"


# ======================================================================
# Ollama Payload Tests
# ======================================================================

class TestOllamaPayload:
    """Test OllamaLLM payload construction (no network needed)."""

    def test_basic_payload(self, sample_messages, ollama_config):
        llm = OllamaLLM(ollama_config)
        payload = llm._build_payload(sample_messages, None, stream=False)

        assert payload["model"] == "qwen3:4b"
        assert payload["stream"] is False
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"
        assert payload["options"]["temperature"] == 0.7

    def test_payload_with_tools(self, sample_messages, ollama_config, sample_tool):
        llm = OllamaLLM(ollama_config)
        payload = llm._build_payload(sample_messages, [sample_tool], stream=False)

        assert "tools" in payload
        assert len(payload["tools"]) == 1
        assert payload["tools"][0]["name"] == "calculator"

    def test_payload_stream(self, sample_messages, ollama_config):
        llm = OllamaLLM(ollama_config)
        payload = llm._build_payload(sample_messages, None, stream=True)
        assert payload["stream"] is True

    def test_payload_stop_sequences(self, sample_messages):
        cfg = LLMConfig(stop_sequences=["<|stop|>"])
        llm = OllamaLLM(cfg)
        payload = llm._build_payload(sample_messages, None, stream=False)
        assert payload["options"]["stop"] == ["<|stop|>"]


# ======================================================================
# LlamaCpp Payload Tests
# ======================================================================

class TestLlamaCppPayload:
    """Test LlamaCppLLM payload construction (no network needed)."""

    def test_basic_payload(self, sample_messages):
        cfg = LLMConfig(backend=BackendType.LLAMACPP)
        llm = LlamaCppLLM(cfg)
        payload = llm._build_payload(sample_messages, None, stream=False)

        assert payload["model"] == "qwen3:4b"
        assert payload["stream"] is False
        assert payload["temperature"] == 0.7
        assert payload["max_tokens"] == 2048
        assert "options" not in payload  # llama.cpp uses flat keys

    def test_payload_with_tools(self, sample_messages, sample_tool):
        cfg = LLMConfig(backend=BackendType.LLAMACPP)
        llm = LlamaCppLLM(cfg)
        payload = llm._build_payload(sample_messages, [sample_tool], stream=False)

        assert "tools" in payload
        assert payload["tools"][0]["type"] == "function"


# ======================================================================
# Token Counting Tests
# ======================================================================

class TestTokenCounting:
    """Test approximate token counting."""

    @pytest.mark.asyncio
    async def test_ollama_count(self, ollama_config):
        llm = OllamaLLM(ollama_config)
        count = await llm.count_tokens("Hello, world!")
        # "Hello, world!" = 13 chars → 13 // 4 = 3
        assert count == 3

    @pytest.mark.asyncio
    async def test_empty_text(self, ollama_config):
        llm = OllamaLLM(ollama_config)
        count = await llm.count_tokens("")
        assert count == 0

    @pytest.mark.asyncio
    async def test_llamacpp_count(self):
        cfg = LLMConfig(backend=BackendType.LLAMACPP)
        llm = LlamaCppLLM(cfg)
        count = await llm.count_tokens("Hi there!")
        assert count == 2  # 9 // 4


# ======================================================================
# Async Context Manager Tests
# ======================================================================

class TestContextManager:
    """Test async context manager behaviour."""

    @pytest.mark.asyncio
    async def test_ollama_context(self, ollama_config):
        async with OllamaLLM(ollama_config) as llm:
            assert llm.session is not None
            assert not llm.session.closed
        # Session should be closed after exit
        assert llm.session is None

    @pytest.mark.asyncio
    async def test_explicit_close(self, ollama_config):
        llm = OllamaLLM(ollama_config)
        await llm.ensure_session()
        assert llm.session is not None
        await llm.close()
        assert llm.session is None


# ======================================================================
# Error Handling Tests
# ======================================================================

class TestErrorHandling:
    """Test error handling scenarios."""

    def test_invalid_temperature(self):
        with pytest.raises(Exception):
            LLMConfig(temperature=-1.0)

    def test_invalid_max_tokens(self):
        with pytest.raises(Exception):
            LLMConfig(max_tokens=0)

    def test_invalid_top_p(self):
        with pytest.raises(Exception):
            LLMConfig(top_p=2.0)


# ======================================================================
# Mocked Generate Tests
# ======================================================================

class TestMockedGenerate:
    """Test generation with mocked HTTP calls."""

    @pytest.mark.asyncio
    async def test_ollama_generate(self, sample_messages, ollama_config):
        mock_json = {
            "message": {"content": "Hello! How can I help?"},
            "model": "qwen3:4b",
            "eval_count": 12,
            "done_reason": "stop",
            "done": True,
        }

        llm = OllamaLLM(ollama_config)

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=mock_json)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.closed = False
        llm.session = mock_session

        result = await llm.generate(sample_messages)

        assert isinstance(result, LLMResponse)
        assert result.content == "Hello! How can I help?"
        assert result.tokens_used == 12
        assert result.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_llamacpp_generate(self, sample_messages):
        mock_json = {
            "choices": [
                {
                    "message": {"content": "Hi from llama.cpp!"},
                    "finish_reason": "stop",
                }
            ],
            "model": "my-model",
            "usage": {"total_tokens": 20},
        }

        cfg = LLMConfig(backend=BackendType.LLAMACPP)
        llm = LlamaCppLLM(cfg)

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=mock_json)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.closed = False
        llm.session = mock_session

        result = await llm.generate(sample_messages)

        assert isinstance(result, LLMResponse)
        assert result.content == "Hi from llama.cpp!"
        assert result.tokens_used == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
