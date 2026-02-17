"""
Python Execution Tool — Sandboxed code execution with timeout.
"""

import logging
import subprocess
import sys
import tempfile
import os
from typing import Dict, Any

from src.tools.base import BaseTool

logger = logging.getLogger(__name__)


class PythonExecTool(BaseTool):
    """Execute Python code in a sandboxed subprocess with timeout."""

    TIMEOUT = 30  # seconds
    MAX_OUTPUT = 4096  # characters

    @property
    def name(self) -> str:
        return "python_execute"

    @property
    def description(self) -> str:
        return "Execute Python code and return the output. Code runs in a sandboxed subprocess with a 30-second timeout."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                }
            },
            "required": ["code"],
        }

    async def execute(self, **kwargs) -> str:
        code = kwargs.get("code", "")
        if not code:
            return "Error: No code provided."

        try:
            # Write code to a temp file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, dir=tempfile.gettempdir()
            ) as f:
                f.write(code)
                tmp_path = f.name

            try:
                result = subprocess.run(
                    [sys.executable, tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=self.TIMEOUT,
                    cwd=tempfile.gettempdir(),
                    env={
                        "PATH": os.environ.get("PATH", ""),
                        "HOME": tempfile.gettempdir(),
                        "PYTHONDONTWRITEBYTECODE": "1",
                    },
                )

                output = ""
                if result.stdout:
                    output += result.stdout
                if result.stderr:
                    output += ("\n--- stderr ---\n" + result.stderr) if output else result.stderr

                if not output:
                    output = "(no output)"

                # Truncate if too long
                if len(output) > self.MAX_OUTPUT:
                    output = output[: self.MAX_OUTPUT] + "\n... (truncated)"

                logger.info("Python exec: %d chars output, returncode=%d", len(output), result.returncode)
                return output

            finally:
                os.unlink(tmp_path)

        except subprocess.TimeoutExpired:
            return f"Error: Code execution timed out after {self.TIMEOUT} seconds."
        except Exception as e:
            logger.error("Python exec error: %s", e)
            return f"Error executing code: {e}"
