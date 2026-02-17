"""Python exec plugin — wraps the built-in python execution tool."""

from src.plugins.base import ToolPlugin
from src.tools.base import BaseTool
from src.tools.python_exec import PythonExecTool


class Plugin(ToolPlugin):

    @property
    def name(self) -> str:
        return "python_exec"

    @property
    def description(self) -> str:
        return "Python code execution in sandboxed environment"

    def _create_tool(self) -> BaseTool:
        return PythonExecTool()
