#!/usr/bin/env python3
"""
llm_cli.py — Command-line interface for the LocalAI Agent Framework.

Usage:
    python llm_cli.py "What is Python?"
    python llm_cli.py --stream "Tell me a story"
    python llm_cli.py --interactive
    python llm_cli.py --list-models
"""

import argparse
import asyncio
import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core import LLMFactory, Message, MessageRole, OllamaLLM


# ---- ANSI Colours for a nicer terminal experience ----
class C:
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"
    RESET = "\033[0m"


def banner():
    print(f"""{C.CYAN}{C.BOLD}
  ╔═══════════════════════════════════════╗
  ║       LocalAI Agent  •  LLM CLI      ║
  ╚═══════════════════════════════════════╝{C.RESET}
""")


# ------------------------------------------------------------------
# One-shot generation
# ------------------------------------------------------------------

async def one_shot(llm, prompt: str, stream: bool, system_prompt: str):
    messages = [
        Message(role=MessageRole.SYSTEM, content=system_prompt),
        Message(role=MessageRole.USER, content=prompt),
    ]

    if stream:
        print(f"\n{C.GREEN}{C.BOLD}Assistant:{C.RESET} ", end="", flush=True)
        async for chunk in await llm.generate(messages, stream=True):
            print(chunk.content, end="", flush=True)
        print()
    else:
        response = await llm.generate(messages)
        print(f"\n{C.GREEN}{C.BOLD}Assistant:{C.RESET} {response.content}")
        if response.tokens_used:
            print(f"{C.DIM}[tokens: {response.tokens_used}]{C.RESET}")


# ------------------------------------------------------------------
# Interactive chat
# ------------------------------------------------------------------

async def interactive(llm, system_prompt: str, stream: bool):
    banner()
    print(f"{C.DIM}Type 'quit' or 'exit' to leave. '/clear' to reset history.{C.RESET}\n")

    messages = [Message(role=MessageRole.SYSTEM, content=system_prompt)]

    while True:
        try:
            user_input = input(f"{C.CYAN}{C.BOLD}You:{C.RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C.DIM}Goodbye!{C.RESET}")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print(f"{C.DIM}Goodbye!{C.RESET}")
            break
        if user_input.lower() == "/clear":
            messages = [Message(role=MessageRole.SYSTEM, content=system_prompt)]
            print(f"{C.YELLOW}[conversation cleared]{C.RESET}")
            continue

        messages.append(Message(role=MessageRole.USER, content=user_input))

        if stream:
            print(f"{C.GREEN}{C.BOLD}Assistant:{C.RESET} ", end="", flush=True)
            full_response = ""
            async for chunk in await llm.generate(messages, stream=True):
                print(chunk.content, end="", flush=True)
                full_response += chunk.content
            print()
            messages.append(Message(role=MessageRole.ASSISTANT, content=full_response))
        else:
            response = await llm.generate(messages)
            print(f"{C.GREEN}{C.BOLD}Assistant:{C.RESET} {response.content}")
            messages.append(Message(role=MessageRole.ASSISTANT, content=response.content))


# ------------------------------------------------------------------
# Model listing
# ------------------------------------------------------------------

async def list_models(llm):
    if not isinstance(llm, OllamaLLM):
        print(f"{C.YELLOW}Model listing is only supported for the Ollama backend.{C.RESET}")
        return

    models = await llm.list_models()
    if not models:
        print(f"{C.RED}No models found. Is Ollama running?{C.RESET}")
        return

    print(f"\n{C.BOLD}Available models:{C.RESET}")
    for name in models:
        print(f"  {C.CYAN}•{C.RESET} {name}")
    print()


# ------------------------------------------------------------------
# Argument parsing & entry-point
# ------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="LocalAI Agent — LLM command-line interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python llm_cli.py "What is Python?"
  python llm_cli.py --stream "Tell me a story"
  python llm_cli.py --interactive
  python llm_cli.py --interactive --stream
  python llm_cli.py --list-models
  python llm_cli.py --backend llamacpp --model my-model "Hello"
""",
    )
    parser.add_argument("prompt", nargs="?", help="Question or prompt (one-shot mode)")
    parser.add_argument("-i", "--interactive", action="store_true", help="Start interactive chat")
    parser.add_argument("-s", "--stream", action="store_true", help="Stream the response token by token")
    parser.add_argument("--list-models", action="store_true", help="List available models")
    parser.add_argument("--backend", default="ollama", choices=["ollama", "llamacpp"], help="LLM backend (default: ollama)")
    parser.add_argument("--model", default="elyssia:latest", help="Model name (default: elyssia:latest)")
    parser.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature (default: 0.7)")
    parser.add_argument("--max-tokens", type=int, default=2048, help="Max tokens to generate (default: 2048)")
    parser.add_argument("--system", default="You are Elyssia, an advanced AI agent with a futuristic, cyber-holographic interface. You are helpful, precise, and tech-savvy.", help="System prompt")
    parser.add_argument("--config", help="Path to YAML config file (overrides other flags)")
    return parser.parse_args()


async def main():
    args = parse_args()

    # Build the LLM
    if args.config:
        llm = LLMFactory.from_yaml(args.config)
    else:
        llm = LLMFactory.create(
            backend=args.backend,
            model_name=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )

    async with llm:
        if args.list_models:
            await list_models(llm)
        elif args.interactive:
            await interactive(llm, args.system, args.stream)
        elif args.prompt:
            await one_shot(llm, args.prompt, args.stream, args.system)
        else:
            # No arguments → show help
            parse_args()  # will show help if no args
            print(f"\n{C.YELLOW}Provide a prompt or use --interactive.{C.RESET}")
            print(f"Run {C.BOLD}python llm_cli.py --help{C.RESET} for usage.\n")


if __name__ == "__main__":
    asyncio.run(main())
