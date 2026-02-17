#!/usr/bin/env python3
"""
llm_examples.py — Complete usage examples for the LocalAI LLM module.

Each example is a standalone async function that demonstrates a specific
feature. Run the entire file to execute all examples sequentially, or
call individual functions from your own code.

Usage:
    PYTHONPATH=. python examples/llm_examples.py
"""

import asyncio
import sys
import os
import yaml

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import (
    LLMFactory,
    Message,
    MessageRole,
    LLMConfig,
    LLMResponse,
    OllamaLLM,
    BackendType,
)


# ── Helpers ──────────────────────────────────────────────────────────

def section(title: str):
    """Print a separator for readability."""
    print(f"\n{'─' * 60}")
    print(f"  Example: {title}")
    print(f"{'─' * 60}\n")


# ── Example 1: Basic Generation ─────────────────────────────────────

async def example_basic_generation():
    """Generate a simple completion."""
    section("Basic Generation")

    llm = LLMFactory.create(backend="ollama", model_name="qwen3:4b")

    messages = [
        Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
        Message(role=MessageRole.USER, content="Explain Python in one sentence."),
    ]

    async with llm:
        response = await llm.generate(messages)
        print(f"Response: {response.content}")
        if response.tokens_used:
            print(f"Tokens used: {response.tokens_used}")


# ── Example 2: Streaming Response ───────────────────────────────────

async def example_streaming():
    """Stream tokens in real-time."""
    section("Streaming Response")

    llm = LLMFactory.create(backend="ollama", model_name="qwen3:4b")

    messages = [
        Message(role=MessageRole.USER, content="Write a haiku about coding."),
    ]

    async with llm:
        print("Streaming: ", end="", flush=True)
        async for chunk in await llm.generate(messages, stream=True):
            print(chunk.content, end="", flush=True)
        print()


# ── Example 3: Multi-turn Conversation ──────────────────────────────

async def example_multi_turn():
    """Demonstrate a multi-turn conversation with history."""
    section("Multi-turn Conversation")

    llm = LLMFactory.create(
        backend="ollama",
        model_name="qwen3:4b",
        temperature=0.7,
    )

    messages = [
        Message(role=MessageRole.SYSTEM, content="You are a friendly tutor."),
    ]

    exchanges = [
        "What is a variable in Python?",
        "Can you give me an example?",
        "What about constants?",
    ]

    async with llm:
        for user_input in exchanges:
            messages.append(Message(role=MessageRole.USER, content=user_input))
            print(f"User: {user_input}")

            response = await llm.generate(messages)
            print(f"Tutor: {response.content}\n")

            messages.append(
                Message(role=MessageRole.ASSISTANT, content=response.content)
            )


# ── Example 4: Async Generation ─────────────────────────────────────

async def example_async_generation():
    """Show async/await generation."""
    section("Async Generation")

    llm = LLMFactory.create(backend="ollama", model_name="qwen3:4b")

    messages = [
        Message(role=MessageRole.USER, content="What is 2 + 2?"),
    ]

    async with llm:
        response = await llm.generate(messages)
        print(f"Answer: {response.content}")


# ── Example 5: Async Streaming ──────────────────────────────────────

async def example_async_streaming():
    """Async streaming with token counting."""
    section("Async Streaming")

    llm = LLMFactory.create(
        backend="ollama",
        model_name="qwen3:4b",
        max_tokens=100,
    )

    messages = [
        Message(role=MessageRole.USER, content="List 3 programming languages."),
    ]

    async with llm:
        token_count = 0
        print("Response: ", end="", flush=True)
        async for chunk in await llm.generate(messages, stream=True):
            print(chunk.content, end="", flush=True)
            token_count += 1
        print(f"\n[Chunks received: {token_count}]")


# ── Example 6: Model Information ────────────────────────────────────

async def example_model_info():
    """List available models and check health."""
    section("Model Information")

    llm = LLMFactory.create(backend="ollama", model_name="qwen3:4b")

    async with llm:
        # Health check
        healthy = await llm.check_health()
        print(f"Server healthy: {healthy}")

        # List models (Ollama only)
        if isinstance(llm, OllamaLLM):
            models = await llm.list_models()
            print(f"Available models: {models}")


# ── Example 7: Token Counting ───────────────────────────────────────

async def example_token_counting():
    """Approximate token counting."""
    section("Token Counting")

    llm = LLMFactory.create(backend="ollama", model_name="qwen3:4b")

    texts = [
        "Hello",
        "This is a longer sentence with more tokens.",
        "def fibonacci(n): return n if n < 2 else fibonacci(n-1) + fibonacci(n-2)",
    ]

    for text in texts:
        count = await llm.count_tokens(text)
        print(f"  '{text[:40]}...' → ~{count} tokens")


# ── Example 8: Config Loading ───────────────────────────────────────

async def example_config_loading():
    """Load LLM from a YAML config file."""
    section("Config Loading")

    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config",
        "config.yaml",
    )

    if os.path.exists(config_path):
        llm = LLMFactory.from_yaml(config_path)
        print(f"Loaded: backend={llm.config.backend.value}, model={llm.config.model_name}")
        print(f"Temperature={llm.config.temperature}, max_tokens={llm.config.max_tokens}")
    else:
        print(f"Config not found at {config_path}, skipping.")

    # Also show from_config with a dict
    cfg_dict = {
        "backend": "ollama",
        "name": "qwen3:4b",
        "temperature": 0.5,
    }
    llm = LLMFactory.from_config(cfg_dict)
    print(f"From dict: model={llm.config.model_name}, temp={llm.config.temperature}")


# ── Main Runner ─────────────────────────────────────────────────────

async def run_all():
    """Run all examples. Skip failures gracefully."""
    examples = [
        ("Basic Generation", example_basic_generation),
        ("Streaming", example_streaming),
        ("Multi-turn", example_multi_turn),
        ("Async Generation", example_async_generation),
        ("Async Streaming", example_async_streaming),
        ("Model Info", example_model_info),
        ("Token Counting", example_token_counting),
        ("Config Loading", example_config_loading),
    ]

    print("=" * 60)
    print("  LocalAI Agent — LLM Examples")
    print("=" * 60)

    for name, fn in examples:
        try:
            await fn()
        except Exception as e:
            print(f"\n  ⚠  {name} failed: {e}")
            print("     (Is Ollama running? Try: ollama serve)\n")

    print("\n" + "=" * 60)
    print("  All examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all())
