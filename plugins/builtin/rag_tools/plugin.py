"""RAG tools plugin — provides rag_query and rag_ingest tools."""

from typing import List
from src.plugins.base import BasePlugin
from src.tools.base import BaseTool
from src.tools.rag_tool import RAGQueryTool, RAGIngestTool


class Plugin(BasePlugin):

    @property
    def name(self) -> str:
        return "rag_tools"

    @property
    def description(self) -> str:
        return "RAG query and ingest tools for knowledge base"

    def get_tools(self) -> List[BaseTool]:
        return [RAGQueryTool(), RAGIngestTool()]
