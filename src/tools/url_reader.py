"""
URL Reader Tool — Fetch and extract text from web pages using Playwright (Headless Browser).
"""

import logging
import asyncio
from typing import Dict, Any

from src.tools.base import BaseTool

logger = logging.getLogger(__name__)


class URLReaderTool(BaseTool):
    """Fetch and extract readable text from a URL using a headless browser."""

    name = "url_reader"
    description = "Fetch a web page URL using a headless browser (Playwright) and extract its text content. Handles dynamic JavaScript sites."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch and read.",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum characters to return (default: 8000)",
                },
                "wait_for_selector": {
                    "type": "string",
                    "description": "Optional CSS selector to wait for before extracting content (useful for slow-loading SPAs).",
                }
            },
            "required": ["url"],
        }

    async def execute(self, **kwargs) -> str:
        url = kwargs.get("url", "")
        max_chars = kwargs.get("max_chars", 8000)
        wait_for_selector = kwargs.get("wait_for_selector")

        if not url:
            return "Error: No URL provided."

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            from playwright.async_api import async_playwright
            from bs4 import BeautifulSoup
        except ImportError:
            return "Error: playwright or beautifulsoup4 not installed. Run: pip install playwright beautifulsoup4 && playwright install"

        playwright = None
        browser = None
        
        try:
            playwright = await async_playwright().start()
            # Launch headless chromium
            browser = await playwright.chromium.launch(headless=True)
            
            # Create context with a realistic user agent
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            
            # Navigate with timeout
            logger.info("Navigating to %s...", url)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            except Exception as e:
                return f"Error navigating to {url}: {e}"

            # Optional: Wait for specific element
            if wait_for_selector:
                try:
                    await page.wait_for_selector(wait_for_selector, timeout=5000)
                except Exception:
                    logger.warning("Timeout waiting for selector: %s", wait_for_selector)

            # Get full HTML content
            html_content = await page.content()
            
            # Parse with BS4
            soup = BeautifulSoup(html_content, "html.parser")

            # Cleanup unnecessary tags
            for tag in soup(["script", "style", "noscript", "iframe", "svg", "header", "footer", "nav"]):
                tag.decompose()

            # Extract text
            text = soup.get_text(separator="\n", strip=True)

            # Post-processing cleanup
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            clean_text = "\n".join(lines)

            if len(clean_text) > max_chars:
                clean_text = clean_text[:max_chars] + f"\n\n... (truncated, {len(clean_text)} chars total)"

            title = await page.title()
            return f"Title: {title}\nURL: {url}\n\n{clean_text}"

        except Exception as e:
            logger.error("Playwright error: %s", e)
            return f"Error reading page with Playwright: {e}"
            
        finally:
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
