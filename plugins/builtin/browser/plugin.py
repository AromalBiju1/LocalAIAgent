"""
Browser Automation Plugin (Playwright).
Allows the agent to navigate the web, interact with pages, and extract content.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

try:
    from playwright.async_api import async_playwright, Playwright, Browser, Page
except ImportError:
    async_playwright = None

from src.plugins.base import BasePlugin

logger = logging.getLogger(__name__)


class BrowserPlugin(BasePlugin):
    """
    Plugin for controlling a headless browser.
    """

    def __init__(self, manifest: Dict[str, Any]):
        super().__init__(manifest)
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.lock = asyncio.Lock()

    async def on_load(self):
        """Initialize Playwright and launch browser."""
        if async_playwright is None:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install")
            return

        try:
            self.playwright = await async_playwright().start()
            headless = self.config.get("headless", True)
            self.browser = await self.playwright.chromium.launch(headless=headless)
            logger.info(f"Browser launched (headless={headless})")
        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")

    async def on_unload(self):
        """Close browser and Playwright."""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser stopped")

    # ── Tools ───────────────────────────────────────────────

    async def _ensure_page(self):
        if not self.browser:
            await self.on_load()
        if not self.browser:
             raise RuntimeError("Browser not available")
             
        if not self.page or self.page.is_closed():
            self.page = await self.browser.new_page(
                user_agent=self.config.get("user_agent", "ElyssiaAgent")
            )

    @BasePlugin.tool(
        name="browser_open",
        description="Navigate to a URL. Returns the page title and text content.",
        parameters={
            "url": {"type": "string", "description": "URL to visit"}
        }
    )
    async def open_url(self, url: str) -> str:
        async with self.lock:
            await self._ensure_page()
            try:
                await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                title = await self.page.title()
                # Get a summary of content (first 2000 chars)
                content = await self.page.evaluate("document.body.innerText")
                snippet = content[:2000].replace("\n", " ")
                return f"Opened '{title}'.\nContent snippet: {snippet}..."
            except Exception as e:
                return f"Error opening URL: {e}"

    @BasePlugin.tool(
        name="browser_click",
        description="Click an element on the current page.",
        parameters={
            "selector": {"type": "string", "description": "CSS selector to click"}
        }
    )
    async def click(self, selector: str) -> str:
        async with self.lock:
            if not self.page:
                return "Error: No active page. Use browser_open first."
            try:
                await self.page.click(selector, timeout=5000)
                return f"Clicked '{selector}'."
            except Exception as e:
                return f"Error clicking '{selector}': {e}"

    @BasePlugin.tool(
        name="browser_type",
        description="Type text into an input field.",
        parameters={
            "selector": {"type": "string", "description": "CSS selector of input"},
            "text": {"type": "string", "description": "Text to type"}
        }
    )
    async def type_text(self, selector: str, text: str) -> str:
        async with self.lock:
            if not self.page:
                return "Error: No active page."
            try:
                await self.page.fill(selector, text, timeout=5000)
                return f"Typed into '{selector}'."
            except Exception as e:
                return f"Error typing: {e}"

    @BasePlugin.tool(
        name="browser_screenshot",
        description="Take a screenshot of the current page.",
        parameters={
            "filename": {"type": "string", "description": "Filename (e.g. screenshot.png)"}
        }
    )
    async def screenshot(self, filename: str) -> str:
        async with self.lock:
            if not self.page:
                return "Error: No active page."
            try:
                path = f"data/{filename}"
                await self.page.screenshot(path=path)
                return f"Screenshot saved to {path}"
            except Exception as e:
                return f"Error taking screenshot: {e}"
                
    @BasePlugin.tool(
        name="browser_extract",
        description="Extract text from an element.",
        parameters={
            "selector": {"type": "string", "description": "CSS selector"}
        }
    )
    async def extract(self, selector: str) -> str:
        async with self.lock:
            if not self.page:
                return "Error: No active page."
            try:
                text = await self.page.inner_text(selector, timeout=5000)
                return text
            except Exception as e:
                return f"Error extracting: {e}"
