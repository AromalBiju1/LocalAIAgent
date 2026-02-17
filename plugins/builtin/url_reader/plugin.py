"""URL reader plugin — wraps URL content extraction tool."""

from src.plugins.base import ToolPlugin
from src.tools.base import BaseTool
from src.tools.url_reader import URLReaderTool


class Plugin(ToolPlugin):

    @property
    def name(self) -> str:
        return "url_reader"

    @property
    def description(self) -> str:
        return "Fetch and extract text from web URLs"

    def _create_tool(self) -> BaseTool:
        return URLReaderTool()
