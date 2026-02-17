"""
Prompt-Based Tool Calling — for models that don't support native function calling.

Injects tool descriptions into the system prompt and parses the model's response
for tool invocations formatted as JSON blocks.
"""

import json
import re
import logging
from typing import List, Dict, Any, Optional, Tuple

from src.tools.base import ToolRegistry

logger = logging.getLogger(__name__)

# ── System prompt template ────────────────────────────────

TOOL_SYSTEM_PROMPT = """You have access to the following tools. To use a tool, respond with a JSON block in this exact format:

```tool_call
{{"name": "tool_name", "arguments": {{"arg1": "value1"}}}}
```

Available tools:
{tool_descriptions}

IMPORTANT RULES:
- When you need to use a tool, output ONLY the tool_call JSON block, nothing else.
- After the tool result is provided, give your final answer to the user.
- If you don't need any tool, just respond normally without any tool_call block.
- You may call only ONE tool at a time."""


def build_tool_descriptions(registry: ToolRegistry) -> str:
    """Build human-readable tool descriptions for the system prompt."""
    descriptions = []
    for tool in registry.list_tools():
        params = tool.parameters
        param_lines = []
        props = params.get("properties", {})
        required = params.get("required", [])

        for pname, pinfo in props.items():
            req_marker = " (required)" if pname in required else " (optional)"
            ptype = pinfo.get("type", "string")
            pdesc = pinfo.get("description", "")
            param_lines.append(f"    - {pname} ({ptype}{req_marker}): {pdesc}")

        params_str = "\n".join(param_lines) if param_lines else "    (no parameters)"
        descriptions.append(
            f"  **{tool.name}**: {tool.description}\n  Parameters:\n{params_str}"
        )

    return "\n\n".join(descriptions)


def inject_tool_prompt(system_msg: str, registry: ToolRegistry) -> str:
    """Augment the system prompt with tool calling instructions."""
    tool_desc = build_tool_descriptions(registry)
    tool_block = TOOL_SYSTEM_PROMPT.format(tool_descriptions=tool_desc)
    return f"{system_msg}\n\n{tool_block}"


# ── Response parsing ──────────────────────────────────────

# Match ```tool_call\n{...}\n``` blocks
TOOL_CALL_PATTERN = re.compile(
    r"```tool_call\s*\n\s*(\{.*?\})\s*\n\s*```",
    re.DOTALL,
)

# Fallback: match raw JSON that looks like a tool call
TOOL_CALL_FALLBACK = re.compile(
    r'\{\s*"name"\s*:\s*"(\w+)"\s*,\s*"arguments"\s*:\s*\{.*?\}\s*\}',
    re.DOTALL,
)


def parse_tool_calls(response_text: str) -> Tuple[Optional[List[Dict[str, Any]]], str]:
    """
    Parse the model's response for tool call blocks.

    Returns:
        (tool_calls, clean_text) — tool_calls is None if no calls found,
        clean_text is the response with tool call blocks removed.
    """
    tool_calls = []

    # Try ````tool_call ... ``` format first
    matches = TOOL_CALL_PATTERN.findall(response_text)
    if matches:
        for match in matches:
            try:
                parsed = json.loads(match)
                if "name" in parsed:
                    tool_calls.append({
                        "function": {
                            "name": parsed["name"],
                            "arguments": json.dumps(parsed.get("arguments", {})),
                        }
                    })
            except json.JSONDecodeError:
                logger.warning("Failed to parse tool call JSON: %s", match[:100])
                continue

    # Fallback: try raw JSON pattern
    if not tool_calls:
        for match in TOOL_CALL_FALLBACK.finditer(response_text):
            try:
                parsed = json.loads(match.group(0))
                if "name" in parsed:
                    tool_calls.append({
                        "function": {
                            "name": parsed["name"],
                            "arguments": json.dumps(parsed.get("arguments", {})),
                        }
                    })
            except json.JSONDecodeError:
                continue

    if not tool_calls:
        return None, response_text

    # Remove tool call blocks from the visible text
    clean = TOOL_CALL_PATTERN.sub("", response_text).strip()
    if not clean:
        clean = TOOL_CALL_FALLBACK.sub("", response_text).strip()

    return tool_calls, clean
