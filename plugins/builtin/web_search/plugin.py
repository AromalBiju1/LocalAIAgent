"""Web search plugin — wraps the built-in web search tool."""

from src.plugins.base import ToolPlugin
from src.tools.base import BaseTool
from src.tools.web_search import WebSearchTool


class Plugin(ToolPlugin):

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Web search via DuckDuckGo"

    def _create_tool(self) -> BaseTool:
        return WebSearchTool()
