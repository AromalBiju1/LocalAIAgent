"""
Plugin system — Base classes, manifest, and lifecycle hooks.

Every plugin extends BasePlugin and lives in a folder with a plugin.yaml manifest.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from src.tools.base import BaseTool

logger = logging.getLogger(__name__)


@dataclass
class PluginMeta:
    """Plugin metadata loaded from plugin.yaml."""
    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


class BasePlugin(ABC):
    """
    Abstract base class for all plugins.

    A plugin can provide one or more tools, channels, or services.
    It has lifecycle hooks for setup and teardown.
    """

    def __init__(self):
        self._meta: Optional[PluginMeta] = None
        self._config: Dict[str, Any] = {}
        self._loaded = False

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin identifier (lowercase, no spaces)."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Short human-readable description."""
        ...

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def meta(self) -> Optional[PluginMeta]:
        return self._meta

    @meta.setter
    def meta(self, value: PluginMeta):
        self._meta = value

    @property
    def config(self) -> Dict[str, Any]:
        return self._config

    @config.setter
    def config(self, value: Dict[str, Any]):
        self._config = value

    # ── Lifecycle hooks ───────────────────────────────────

    async def on_load(self) -> None:
        """Called when the plugin is loaded. Override for setup logic."""
        pass

    async def on_unload(self) -> None:
        """Called when the plugin is unloaded. Override for cleanup logic."""
        pass

    # ── Tool provisioning ─────────────────────────────────

    # ── Tool provisioning ─────────────────────────────────

    @staticmethod
    def tool(name: str, description: str, parameters: Optional[Dict[str, Any]] = None):
        """Decorator to mark a method as a tool."""
        def decorator(func):
            func._tool_meta = {
                "name": name,
                "description": description,
                "parameters": parameters or {},
            }
            return func
        return decorator

    def get_tools(self) -> List[BaseTool]:
        """
        Return list of tools this plugin provides.
        By default, scans for methods decorated with @tool.
        """
        tools = []
        for attr_name in dir(self):
            method = getattr(self, attr_name)
            if hasattr(method, "_tool_meta"):
                meta = method._tool_meta
                
                # Create a wrapper tool
                # We need to capture 'method' closure
                tool_instance = self._create_tool_wrapper(method, meta)
                tools.append(tool_instance)
        return tools

    def _create_tool_wrapper(self, method, meta):
        """Helper to create a BaseTool from a decorated method."""
        # Check if BaseTool needs to be imported inside to avoid circular deps if needed
        # But we imported it at top level.
        
        class PluginTool(BaseTool):
            @property
            def name(self) -> str:
                return meta["name"]
            
            @property
            def description(self) -> str:
                return meta["description"]
            
            @property
            def parameters(self) -> Dict[str, Any]:
                return meta["parameters"]
            
            async def execute(self, **kwargs) -> Any:
                return await method(**kwargs)
                
        return PluginTool()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize plugin info for API responses."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "loaded": self._loaded,
            "tools": [t.name for t in self.get_tools()],
            "config": {k: "***" if "key" in k.lower() or "secret" in k.lower() or "token" in k.lower() else v
                       for k, v in self._config.items()},
        }


class ToolPlugin(BasePlugin):
    """
    Convenience base class for plugins that wrap a single tool.
    """

    @abstractmethod
    def _create_tool(self) -> BaseTool:
        """Create and return the tool instance."""
        ...

    def get_tools(self) -> List[BaseTool]:
        return [self._create_tool()]
