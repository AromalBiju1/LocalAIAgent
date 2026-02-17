"""
Plugin Loader — Auto-discovery, loading, and lifecycle management.

Scans plugin directories for plugin.yaml manifests, imports plugin modules,
and manages their lifecycle (load → register tools → unload).
"""

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml

from src.plugins.base import BasePlugin, PluginMeta
from src.tools.base import BaseTool, ToolRegistry

logger = logging.getLogger(__name__)


class PluginLoader:
    """Discovers, loads, and manages plugins."""

    def __init__(self, plugin_dirs: Optional[List[str]] = None):
        """
        Args:
            plugin_dirs: Directories to scan for plugins.
                         Defaults to ['plugins/builtin', 'plugins/community'].
        """
        if plugin_dirs is None:
            base = Path(__file__).parent.parent.parent  # project root
            plugin_dirs = [
                str(base / "plugins" / "builtin"),
                str(base / "plugins" / "community"),
            ]

        self.plugin_dirs = [Path(d) for d in plugin_dirs]
        self._plugins: Dict[str, BasePlugin] = {}
        self._tools: Dict[str, BaseTool] = {}

    # ── Discovery ─────────────────────────────────────────

    def discover(self) -> List[PluginMeta]:
        """
        Scan plugin directories for plugin.yaml manifests.
        Returns metadata for all discovered plugins.
        """
        discovered = []

        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                logger.debug("Plugin dir not found: %s", plugin_dir)
                continue

            for child in sorted(plugin_dir.iterdir()):
                if not child.is_dir():
                    continue

                manifest_path = child / "plugin.yaml"
                if not manifest_path.exists():
                    # Also check for plugin.py without manifest (simple plugins)
                    if (child / "plugin.py").exists():
                        meta = PluginMeta(
                            name=child.name,
                            description=f"Auto-discovered plugin: {child.name}",
                        )
                        meta._path = child  # type: ignore
                        discovered.append(meta)
                    continue

                try:
                    with open(manifest_path) as f:
                        data = yaml.safe_load(f) or {}

                    meta = PluginMeta(
                        name=data.get("name", child.name),
                        version=data.get("version", "0.1.0"),
                        description=data.get("description", ""),
                        author=data.get("author", ""),
                        dependencies=data.get("dependencies", []),
                        config_schema=data.get("config_schema", {}),
                        enabled=data.get("enabled", True),
                    )
                    meta._path = child  # type: ignore
                    discovered.append(meta)

                except Exception as e:
                    logger.warning("Failed to parse %s: %s", manifest_path, e)

        logger.info("Discovered %d plugins", len(discovered))
        return discovered

    # ── Loading ───────────────────────────────────────────

    def _import_plugin_module(self, plugin_path: Path) -> Optional[Any]:
        """Import plugin.py from a plugin directory."""
        module_file = plugin_path / "plugin.py"
        if not module_file.exists():
            logger.warning("No plugin.py in %s", plugin_path)
            return None

        module_name = f"plugins.{plugin_path.parent.name}.{plugin_path.name}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, str(module_file))
            if spec is None or spec.loader is None:
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            return module

        except Exception as e:
            logger.error("Failed to import %s: %s", module_file, e)
            return None

    def _find_plugin_class(self, module: Any) -> Optional[type]:
        """Find the BasePlugin subclass in a module."""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type)
                    and issubclass(attr, BasePlugin)
                    and attr is not BasePlugin):
                return attr
        return None

    async def load_plugin(self, meta: PluginMeta, config: Optional[Dict[str, Any]] = None) -> Optional[BasePlugin]:
        """
        Load a single plugin from its metadata.

        Args:
            meta: Plugin metadata (must have _path set).
            config: Runtime config to pass to the plugin.

        Returns:
            Loaded plugin instance, or None on failure.
        """
        plugin_path = getattr(meta, "_path", None)
        if not plugin_path:
            logger.error("No path for plugin %s", meta.name)
            return None

        if not meta.enabled:
            logger.info("Plugin '%s' is disabled, skipping", meta.name)
            return None

        if meta.name in self._plugins:
            logger.warning("Plugin '%s' already loaded", meta.name)
            return self._plugins[meta.name]

        # Import module
        module = self._import_plugin_module(plugin_path)
        if not module:
            return None

        # Find plugin class
        plugin_class = self._find_plugin_class(module)
        if not plugin_class:
            logger.error("No BasePlugin subclass in %s", plugin_path)
            return None

        # Instantiate
        try:
            plugin = plugin_class()
            plugin.meta = meta
            if config:
                plugin.config = config

            # Lifecycle: on_load
            await plugin.on_load()
            plugin._loaded = True

            # Register tools
            for tool in plugin.get_tools():
                self._tools[tool.name] = tool

            self._plugins[meta.name] = plugin
            logger.info(
                "✅ Loaded plugin '%s' v%s (%d tools: %s)",
                meta.name, meta.version,
                len(plugin.get_tools()),
                [t.name for t in plugin.get_tools()],
            )
            return plugin

        except Exception as e:
            logger.error("Failed to load plugin '%s': %s", meta.name, e)
            return None

    async def load_all(self, config: Optional[Dict[str, Dict[str, Any]]] = None) -> int:
        """
        Discover and load all plugins.

        Args:
            config: Per-plugin config dict: {plugin_name: {key: value}}.

        Returns:
            Number of plugins successfully loaded.
        """
        config = config or {}
        discovered = self.discover()
        loaded = 0

        for meta in discovered:
            plugin_config = config.get(meta.name, {})
            result = await self.load_plugin(meta, plugin_config)
            if result:
                loaded += 1

        logger.info("Loaded %d/%d plugins", loaded, len(discovered))
        return loaded

    # ── Unloading ─────────────────────────────────────────

    async def unload_plugin(self, name: str) -> bool:
        """Unload a plugin and remove its tools."""
        plugin = self._plugins.get(name)
        if not plugin:
            return False

        try:
            await plugin.on_unload()
        except Exception as e:
            logger.warning("Error during on_unload for '%s': %s", name, e)

        # Remove tools
        for tool in plugin.get_tools():
            self._tools.pop(tool.name, None)

        plugin._loaded = False
        del self._plugins[name]
        logger.info("Unloaded plugin '%s'", name)
        return True

    async def unload_all(self):
        """Unload all plugins."""
        for name in list(self._plugins.keys()):
            await self.unload_plugin(name)

    # ── Registry ──────────────────────────────────────────

    def register_into(self, registry: ToolRegistry) -> int:
        """Register all loaded plugin tools into a ToolRegistry."""
        count = 0
        for tool in self._tools.values():
            registry.register(tool)
            count += 1
        return count

    # ── Queries ───────────────────────────────────────────

    @property
    def plugins(self) -> Dict[str, BasePlugin]:
        return dict(self._plugins)

    @property
    def tools(self) -> Dict[str, BaseTool]:
        return dict(self._tools)

    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        return self._plugins.get(name)

    def list_plugins(self) -> List[Dict[str, Any]]:
        """Return serialized info about all loaded plugins."""
        return [p.to_dict() for p in self._plugins.values()]

    def stats(self) -> Dict[str, Any]:
        return {
            "total_plugins": len(self._plugins),
            "total_tools": len(self._tools),
            "plugin_dirs": [str(d) for d in self.plugin_dirs],
            "plugins": {name: p.version for name, p in self._plugins.items()},
        }
