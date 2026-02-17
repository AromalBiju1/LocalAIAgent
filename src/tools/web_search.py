"""
Web Search Tool — DuckDuckGo search (free, no API key).
"""

import logging
from typing import Dict, Any

from src.tools.base import BaseTool

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    """Search the web using DuckDuckGo (no API key required)."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web for current information using DuckDuckGo. Returns titles, snippets, and URLs."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 5)",
                    "default": 5
                }
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs) -> str:
        query = kwargs.get("query", "")
        max_results = kwargs.get("max_results", 5)

        if not query:
            return "Error: No search query provided."

        try:
            # Try new package name first, fall back to old
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS

            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append(r)

            if not results:
                return f"No results found for: {query}"

            output_lines = [f"Search results for: {query}\n"]
            for i, r in enumerate(results, 1):
                title = r.get("title", "No title")
                body = r.get("body", "No snippet")
                href = r.get("href", "")
                output_lines.append(f"{i}. {title}")
                output_lines.append(f"   {body}")
                if href:
                    output_lines.append(f"   URL: {href}")
                output_lines.append("")

            logger.info("Web search for '%s': %d results", query, len(results))
            return "\n".join(output_lines)

        except ImportError:
            return "Error: duckduckgo-search package not installed. Run: pip install duckduckgo-search"
        except Exception as e:
            logger.error("Web search error: %s", e)
            return f"Error performing search: {e}"
