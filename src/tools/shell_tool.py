"""
Shell Tool — Execute commands on the host terminal.
"""

import logging
import subprocess
import shlex
from typing import Dict, Any

from src.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ShellTool(BaseTool):
    """Execute shell commands on the host machine."""

    name = "shell"
    description = "Execute a shell command on the host terminal. Use with CAUTION."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute (e.g., 'ls -la', 'git status')."
                },
                "cwd": {
                    "type": "string",
                    "description": "Optional working directory."
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 60)."
                }
            },
            "required": ["command"],
        }

    async def execute(self, **kwargs) -> str:
        command = kwargs.get("command", "")
        cwd = kwargs.get("cwd") or None
        timeout = kwargs.get("timeout", 60)

        if not command:
            return "Error: No command provided."

        # Security warning logged
        logger.warning(f"⚠️  EXECUTING HOST SHELL COMMAND: {command}")

        try:
            # We use shell=True to allow piping and native shell features, 
            # but this is a security risk if input isn't sanitized.
            # However, this is an Agent for a power user, so we allow it.
            result = subprocess.run(
                command,
                cwd=cwd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = result.stdout.strip()
            error = result.stderr.strip()
            
            response = ""
            if output:
                response += f"STDOUT:\n{output}\n"
            if error:
                response += f"STDERR:\n{error}\n"
                
            if result.returncode != 0:
                response += f"\nExit Code: {result.returncode}"
            
            return response if response else "Command executed successfully (no output)."

        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout} seconds."
        except Exception as e:
            return f"Error executing command: {e}"
