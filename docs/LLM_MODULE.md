# 🧠 LLM Module — Detailed Documentation

> Complete API reference and usage guide for the LocalAI Agent LLM interface.

## Overview

The LLM module provides a unified, backend-agnostic interface for interacting with
local language models. It supports **Ollama** and **llama.cpp** backends through a
common `BaseLLM` abstract class and a `LLMFactory` for easy instantiation.

## Architecture

```
LLMFactory.create() / from_config() / from_yaml()
        │
        ▼
    BaseLLM (ABC)
        │
   ┌────┴─────┐
   ▼          ▼
OllamaLLM  LlamaCppLLM
   │          │
   ▼          ▼
Ollama     llama.cpp
server     server
```

## Data Models (`pyda_models/models.py`)

### MessageRole (Enum)
| Value       | Description             |
|-------------|-------------------------|
| `SYSTEM`    | System instruction      |
| `USER`      | User input              |
| `ASSISTANT` | LLM response            |
| `TOOL`      | Tool execution result   |

### BackendType (Enum)
| Value      | Description                  |
|------------|------------------------------|
| `OLLAMA`   | Ollama HTTP API              |
| `LLAMACPP` | llama.cpp OpenAI-compat API  |

### LLMConfig

| Field            | Type         | Default                       |
|------------------|-------------|-------------------------------|
| `model_name`     | `str`       | `"qwen3:4b"`                  |
| `backend`        | `BackendType` | `OLLAMA`                    |
| `temperature`    | `float`     | `0.7` (0.0–2.0)              |
| `max_tokens`     | `int`       | `2048`                        |
| `top_p`          | `float`     | `0.9` (0.0–1.0)              |
| `top_k`          | `int`       | `40`                          |
| `repeat_penalty` | `float`     | `1.1`                         |
| `stop_sequences` | `List[str]` | `[]`                          |
| `timeout`        | `int`       | `300` (seconds)               |
| `ollama_host`    | `str`       | `"http://localhost:11434"`    |
| `llamacpp_host`  | `str`       | `"http://localhost:8080"`     |

### LLMResponse

| Field           | Type                       |
|-----------------|----------------------------|
| `content`       | `str`                      |
| `model`         | `str`                      |
| `tokens_used`   | `Optional[int]`            |
| `finish_reason` | `Optional[str]`            |
| `tool_calls`    | `Optional[List[Dict]]`     |

### StreamChunk

| Field        | Type              |
|-------------|-------------------|
| `content`   | `str`             |
| `done`      | `bool`            |
| `tokens_used` | `Optional[int]` |

### ToolDefinition

| Field         | Type             |
|---------------|-----------------|
| `name`        | `str`           |
| `description` | `str`           |
| `parameters`  | `Dict[str, Any]`|

## Core Interface

### Message (dataclass)

```python
from src.core import Message, MessageRole

msg = Message(
    role=MessageRole.USER,
    content="Hello!",
    name=None,             # optional
    tool_calls=None,       # optional
    tool_call_id=None,     # optional
)
```

### BaseLLM (Abstract)

All backends implement these methods:

```python
# Async context manager
async with llm:
    ...

# Generate completion
response: LLMResponse = await llm.generate(messages)

# Generate with streaming
async for chunk in await llm.generate(messages, stream=True):
    print(chunk.content, end="")

# Generate with tools
response = await llm.generate(messages, tools=[tool_def])

# Count tokens (approximate)
count: int = await llm.count_tokens("some text")

# Health check
ok: bool = await llm.check_health()
```

### LLMFactory

```python
from src.core import LLMFactory

# From parameters
llm = LLMFactory.create(
    backend="ollama",
    model_name="qwen3:4b",
    temperature=0.7,
    max_tokens=2048,
)

# From config dict
llm = LLMFactory.from_config({"backend": "ollama", "name": "qwen3:4b"})

# From YAML file
llm = LLMFactory.from_yaml("config/config.yaml")

# Utility
backends = LLMFactory.get_available_backends()  # {"ollama": True, ...}
rec = LLMFactory.recommend_backend()             # "ollama"
```

## Backend-Specific Notes

### Ollama

- Endpoint: `POST /api/chat`
- Streaming via NDJSON
- Model management: `list_models()` → `GET /api/tags`
- Health: `GET /api/tags`

### llama.cpp

- Endpoint: `POST /v1/chat/completions` (OpenAI-compatible)
- Streaming via SSE (`data: {...}` lines, terminated by `data: [DONE]`)
- Health: `GET /v1/models`

## Error Handling

All backends raise `RuntimeError` on HTTP failures and log errors through
Python's standard `logging` module. Use `logging.basicConfig(level=logging.DEBUG)`
to see detailed diagnostic output.

## Configuration

The `config/config.yaml` file is the single source of truth for runtime
configuration. Load it with:

```python
llm = LLMFactory.from_yaml("config/config.yaml")
```

## CLI

```bash
python llm_cli.py "What is Python?"            # one-shot
python llm_cli.py --stream "Tell me a story"   # streaming
python llm_cli.py --interactive                 # chat mode
python llm_cli.py --list-models                 # list available models
python llm_cli.py --config config/config.yaml "Hello"  # use YAML config
```

## Testing

```bash
pytest tests/test_llm.py -v
pytest tests/test_llm.py --cov=src/core --cov-report=html
```

## Performance Tips

1. **Use streaming** for better UX
2. **Lower temperature** (0.1–0.3) for faster, more consistent output
3. **Reduce max_tokens** if you don't need long responses
4. **Use 4B models** on 6GB GPU
5. **Monitor with** `nvidia-smi`
