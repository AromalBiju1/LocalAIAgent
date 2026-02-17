"""Calculator plugin — wraps the built-in calculator tool."""

from src.plugins.base import ToolPlugin
from src.tools.base import BaseTool
from src.tools.calculator import CalculatorTool


class Plugin(ToolPlugin):

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Mathematical calculations and expression evaluation"

    def _create_tool(self) -> BaseTool:
        return CalculatorTool()
