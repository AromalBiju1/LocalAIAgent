"""
File Tools — Read and write files from the filesystem.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any

from src.tools.base import BaseTool

logger = logging.getLogger(__name__)

# Allowed base directories (sandboxing)
ALLOWED_BASES = [
    os.path.abspath("data"),
    os.path.abspath("."),
]


def _is_path_allowed(path: str) -> bool:
    """Check if a path is within allowed directories."""
    abs_path = os.path.abspath(path)
    return any(abs_path.startswith(base) for base in ALLOWED_BASES)


class FileReadTool(BaseTool):
    """Read file contents from the filesystem."""

    name = "file_read"
    description = "Read the contents of a file. Supports text, code, markdown, and other text-based files."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read (relative to project root or absolute)",
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Maximum number of lines to read (default: 200)",
                },
            },
            "required": ["path"],
        }

    async def execute(self, **kwargs) -> str:
        path = kwargs.get("path", "")
        max_lines = kwargs.get("max_lines", 200)

        if not path:
            return "Error: No file path provided."

        if not _is_path_allowed(path):
            return f"Error: Access denied. Path '{path}' is outside allowed directories."

        try:
            p = Path(path)
            if not p.exists():
                return f"Error: File not found: {path}"
            if not p.is_file():
                return f"Error: Not a file: {path}"
            if p.stat().st_size > 1_000_000:  # 1MB limit
                return f"Error: File too large ({p.stat().st_size} bytes). Max 1MB."

            content = p.read_text(encoding="utf-8", errors="replace")
            lines = content.split("\n")

            if len(lines) > max_lines:
                truncated = "\n".join(lines[:max_lines])
                return f"{truncated}\n\n... ({len(lines) - max_lines} more lines truncated)"

            return content

        except Exception as e:
            return f"Error reading file: {e}"


class FileWriteTool(BaseTool):
    """Write content to a file."""

    name = "file_write"
    description = "Write or create a file with the given content. Creates parent directories if needed."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to write (relative to project root or absolute)",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
                "mode": {
                    "type": "string",
                    "description": "Write mode: 'write' (overwrite) or 'append' (add to end). Default: 'write'",
                },
            },
            "required": ["path", "content"],
        }

    async def execute(self, **kwargs) -> str:
        path = kwargs.get("path", "")
        content = kwargs.get("content", "")
        mode = kwargs.get("mode", "write")

        if not path:
            return "Error: No file path provided."

        if not _is_path_allowed(path):
            return f"Error: Access denied. Path '{path}' is outside allowed directories."

        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)

            write_mode = "a" if mode == "append" else "w"
            with open(p, write_mode, encoding="utf-8") as f:
                f.write(content)

            action = "appended to" if mode == "append" else "written to"
            return f"Successfully {action} {path} ({len(content)} chars)"

        except Exception as e:
            return f"Error writing file: {e}"
