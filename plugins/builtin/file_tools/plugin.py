"""File tools plugin — provides file_read and file_write tools."""

from typing import List
from src.plugins.base import BasePlugin
from src.tools.base import BaseTool
from src.tools.file_tools import FileReadTool, FileWriteTool


class Plugin(BasePlugin):

    @property
    def name(self) -> str:
        return "file_tools"

    @property
    def description(self) -> str:
        return "File read/write operations with path sandboxing"

    def get_tools(self) -> List[BaseTool]:
        return [FileReadTool(), FileWriteTool()]
