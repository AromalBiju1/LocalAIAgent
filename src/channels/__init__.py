"""
Channel System — Multi-channel communication abstraction.

Supports Telegram, Discord, and future messaging platforms.
"""

from src.channels.base_channel import BaseChannel, ChannelMessage
from src.channels.channel_manager import ChannelManager

__all__ = ["BaseChannel", "ChannelMessage", "ChannelManager"]
