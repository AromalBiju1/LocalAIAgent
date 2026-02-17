"""
Summarize Tool — Use the LLM itself to summarize long text.
"""

import logging
from typing import Dict, Any, Optional

from src.tools.base import BaseTool

logger = logging.getLogger(__name__)

# LLM instance injected during server startup
_llm = None


def set_llm(llm):
    """Inject the LLM instance (called during server init)."""
    global _llm
    _llm = llm


class SummarizeTool(BaseTool):
    """Summarize long text using the LLM."""

    name = "summarize"
    description = "Summarize a long piece of text into a concise version. Useful for condensing articles, documents, or conversation history."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to summarize",
                },
                "style": {
                    "type": "string",
                    "description": "Summary style: 'brief' (2-3 sentences), 'detailed' (paragraph), or 'bullets' (bullet points). Default: 'brief'",
                },
            },
            "required": ["text"],
        }

    async def execute(self, **kwargs) -> str:
        text = kwargs.get("text", "")
        style = kwargs.get("style", "brief")

        if not text:
            return "Error: No text provided."

        if not _llm:
            return "Error: LLM not initialized for summarization."

        style_instructions = {
            "brief": "Provide a concise 2-3 sentence summary.",
            "detailed": "Provide a detailed paragraph summary covering all key points.",
            "bullets": "Provide a summary as bullet points covering the main ideas.",
        }

        instruction = style_instructions.get(style, style_instructions["brief"])

        try:
            from pyda_models.models import MessageRole
            from src.core.llm_base import Message

            messages = [
                Message(
                    role=MessageRole.SYSTEM,
                    content=f"You are a summarization assistant. {instruction}",
                ),
                Message(
                    role=MessageRole.USER,
                    content=f"Summarize the following text:\n\n{text[:8000]}",
                ),
            ]

            response = await _llm.generate(messages, stream=False)
            return response.content or "Failed to generate summary."

        except Exception as e:
            return f"Error summarizing: {e}"
