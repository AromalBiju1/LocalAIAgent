"""Summarize plugin — wraps LLM-powered summarization tool."""

from src.plugins.base import ToolPlugin
from src.tools.base import BaseTool
from src.tools.summarize import SummarizeTool


class Plugin(ToolPlugin):

    @property
    def name(self) -> str:
        return "summarize"

    @property
    def description(self) -> str:
        return "LLM-powered text summarization"

    def _create_tool(self) -> BaseTool:
        return SummarizeTool()
