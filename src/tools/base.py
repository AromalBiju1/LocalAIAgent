"""
Tool Calling System — Base classes and registry.

Every tool inherits from BaseTool and registers itself with the ToolRegistry.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from pyda_models.models import ToolDefinition

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Abstract base class for all tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this tool does."""
        ...

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON Schema describing the tool's parameters."""
        ...

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """Execute the tool and return a string result."""
        ...

    def to_definition(self) -> ToolDefinition:
        """Convert to ToolDefinition for LLM tool calling."""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return tool info as a plain dict."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class ToolRegistry:
    """Registry that holds all available tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        if tool.name in self._tools:
            logger.warning("Tool '%s' is already registered, overwriting.", tool.name)
        self._tools[tool.name] = tool
        logger.info("Registered tool: %s", tool.name)

    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def get_definitions(self) -> List[ToolDefinition]:
        """Get ToolDefinitions for all tools (for LLM)."""
        return [tool.to_definition() for tool in self._tools.values()]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


def create_default_registry() -> ToolRegistry:
    """Create a registry with all built-in tools."""
    registry = ToolRegistry()

    # Import and register built-in tools
    from src.tools.calculator import CalculatorTool
    from src.tools.web_search import WebSearchTool
    from src.tools.python_exec import PythonExecTool
    from src.tools.file_tools import FileReadTool, FileWriteTool
    from src.tools.shell_exec import ShellExecTool
    from src.tools.rag_tool import RAGQueryTool, RAGIngestTool
    from src.tools.url_reader import URLReaderTool
    from src.tools.summarize import SummarizeTool
    from src.tools.podman_tool import PodmanTool

    registry.register(CalculatorTool())
    registry.register(WebSearchTool())
    registry.register(PythonExecTool())
    registry.register(FileReadTool())
    registry.register(FileWriteTool())
    registry.register(ShellExecTool())
    registry.register(RAGQueryTool())
    registry.register(RAGIngestTool())
    registry.register(URLReaderTool())
    registry.register(SummarizeTool())
    registry.register(PodmanTool())

    return registry
