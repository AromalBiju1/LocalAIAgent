"""
Base Channel — Abstract interface for messaging platforms.

All channels (Telegram, Discord, WhatsApp, etc.) implement this contract.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Callable, Awaitable

logger = logging.getLogger(__name__)


class ChannelType(str, Enum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WHATSAPP = "whatsapp"
    SLACK = "slack"
    WEB = "web"


@dataclass
class ChannelMessage:
    """Unified message format across all channels."""
    channel_type: ChannelType
    channel_id: str          # Platform-specific chat/channel ID
    user_id: str             # Platform-specific user ID
    username: str            # Display name
    content: str             # Message text
    timestamp: datetime = field(default_factory=datetime.now)
    reply_to: Optional[str] = None    # Message ID this is replying to
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_type": self.channel_type.value,
            "channel_id": self.channel_id,
            "user_id": self.user_id,
            "username": self.username,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "reply_to": self.reply_to,
            "attachments": self.attachments,
        }


# Type alias for message handlers
MessageHandler = Callable[[ChannelMessage], Awaitable[str]]


class BaseChannel(ABC):
    """Abstract base class for all messaging channels."""

    def __init__(self):
        self._running = False
        self._message_handler: Optional[MessageHandler] = None

    @property
    @abstractmethod
    def channel_type(self) -> ChannelType:
        """The type of channel (telegram, discord, etc.)."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this channel instance."""
        ...

    @property
    def is_running(self) -> bool:
        return self._running

    def set_message_handler(self, handler: MessageHandler) -> None:
        """
        Set the callback that processes incoming messages.
        The handler receives a ChannelMessage and returns a response string.
        """
        self._message_handler = handler

    @abstractmethod
    async def start(self) -> None:
        """Start listening for messages."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop listening and clean up resources."""
        ...

    @abstractmethod
    async def send_message(self, channel_id: str, content: str, **kwargs) -> None:
        """Send a message to a specific channel/chat."""
        ...

    async def on_message(self, message: ChannelMessage) -> Optional[str]:
        """
        Called when a message is received. Routes to the registered handler.
        Override for custom pre/post processing.
        """
        if not self._message_handler:
            logger.warning("No message handler set for channel '%s'", self.name)
            return None

        try:
            response = await self._message_handler(message)
            return response
        except Exception as e:
            logger.error("Error handling message on '%s': %s", self.name, e)
            return f"Sorry, an error occurred: {e}"

    def status(self) -> Dict[str, Any]:
        """Return channel status info."""
        return {
            "type": self.channel_type.value,
            "name": self.name,
            "running": self._running,
            "has_handler": self._message_handler is not None,
        }
