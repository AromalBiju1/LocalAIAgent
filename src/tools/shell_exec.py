"""
Shell Execution Tool — Run shell commands with safety checks.
"""

import asyncio
import logging
from typing import Dict, Any

from src.tools.base import BaseTool

logger = logging.getLogger(__name__)

# Blocked commands for safety
BLOCKED_PATTERNS = [
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd if=",
    ":(){:|:&};:",
    "chmod -R 777 /",
    "shutdown",
    "reboot",
    "init 0",
    "init 6",
]


class ShellExecTool(BaseTool):
    """Execute shell commands in a subprocess."""

    name = "shell_exec"
    description = "Run a shell command and return its output. Use for system tasks like listing files, checking processes, installing packages, or running scripts."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute (e.g., 'ls -la', 'cat file.txt', 'pip install package')",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 30, max: 120)",
                },
            },
            "required": ["command"],
        }

    async def execute(self, **kwargs) -> str:
        command = kwargs.get("command", "")
        timeout = min(kwargs.get("timeout", 30), 120)

        if not command:
            return "Error: No command provided."

        # Safety check
        cmd_lower = command.lower().strip()
        for blocked in BLOCKED_PATTERNS:
            if blocked in cmd_lower:
                return f"Error: Command blocked for safety: contains '{blocked}'"

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=".",
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            output_parts = []
            if stdout:
                out = stdout.decode("utf-8", errors="replace").strip()
                if len(out) > 5000:
                    out = out[:5000] + f"\n... (output truncated, {len(stdout)} bytes total)"
                output_parts.append(out)

            if stderr:
                err = stderr.decode("utf-8", errors="replace").strip()
                if err:
                    if len(err) > 2000:
                        err = err[:2000] + "\n... (stderr truncated)"
                    output_parts.append(f"STDERR:\n{err}")

            if process.returncode != 0:
                output_parts.append(f"Exit code: {process.returncode}")

            return "\n".join(output_parts) if output_parts else "(no output)"

        except asyncio.TimeoutError:
            process.kill()
            return f"Error: Command timed out after {timeout}s"
        except Exception as e:
            return f"Error executing command: {e}"
