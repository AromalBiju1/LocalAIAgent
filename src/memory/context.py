"""
Context Manager — Assembles the final message list for the LLM.

Combines system prompt, conversation summary, RAG context,
recent messages, and tool results into a coherent context window.
"""

import logging
from typing import List, Dict, Any, Optional

from src.core.llm_base import Message
from pyda_models.models import MessageRole

logger = logging.getLogger(__name__)


class ContextManager:
    """Assembles messages for the LLM from various sources."""

    def __init__(
        self,
        system_prompt: str = "You are a helpful AI assistant.",
        max_context_messages: int = 20,
    ):
        self.system_prompt = system_prompt
        self.max_context_messages = max_context_messages

    def build_context(
        self,
        recent_messages: List[Dict[str, Any]],
        conversation_summary: Optional[str] = None,
        rag_context: Optional[str] = None,
        extra_system: Optional[str] = None,
    ) -> List[Message]:
        """
        Build the final message list for the LLM.

        Order:
        1. System prompt (with optional RAG context and extras)
        2. Conversation summary (if window exceeded)
        3. Recent messages
        """
        messages: List[Message] = []

        # ── System prompt ──
        system_parts = [self.system_prompt]

        if conversation_summary:
            system_parts.append(
                f"\n\n## Previous Conversation Context\n{conversation_summary}"
            )

        if rag_context:
            system_parts.append(
                f"\n\n## Relevant Knowledge\nUse this information to answer the user's question:\n{rag_context}"
            )

        if extra_system:
            system_parts.append(f"\n\n{extra_system}")

        messages.append(Message(
            role=MessageRole.SYSTEM,
            content="\n".join(system_parts),
        ))

        # ── Recent messages ──
        for msg in recent_messages[-self.max_context_messages:]:
            role_str = msg.get("role", "user")
            try:
                role = MessageRole(role_str)
            except ValueError:
                role = MessageRole.USER

            messages.append(Message(
                role=role,
                content=msg.get("content", ""),
                name=msg.get("name"),
            ))

        return messages

    def estimate_tokens(self, messages: List[Message]) -> int:
        """Rough token estimate (~4 chars per token)."""
        total_chars = sum(len(m.content) for m in messages)
        return total_chars // 4
