"""Shell exec plugin — wraps shell command execution tool."""

from src.plugins.base import ToolPlugin
from src.tools.base import BaseTool
from src.tools.shell_exec import ShellExecTool


class Plugin(ToolPlugin):

    @property
    def name(self) -> str:
        return "shell_exec"

    @property
    def description(self) -> str:
        return "Shell command execution with safety checks"

    def _create_tool(self) -> BaseTool:
        return ShellExecTool()
