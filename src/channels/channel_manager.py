"""
Channel Manager — Orchestrates all messaging channels.

Routes incoming messages from any channel through the agent,
manages channel lifecycle, and provides unified status.
"""

import logging
import os
import re
from typing import Dict, Any, Optional, List

from src.channels.base_channel import BaseChannel, ChannelMessage, ChannelType

logger = logging.getLogger(__name__)


class ChannelManager:
    """
    Manages all messaging channels and routes messages to the agent.

    The manager:
    1. Creates channel instances from config
    2. Sets up message handlers that call the LLM
    3. Manages channel lifecycle (start/stop)
    """

    def __init__(self, llm=None, tool_registry=None, memory=None):
        self._channels: Dict[str, BaseChannel] = {}
        self._llm = llm
        self._tool_registry = tool_registry
        self._memory = memory

    def set_agent(self, llm, tool_registry=None, memory=None):
        """Set or update the agent components."""
        self._llm = llm
        self._tool_registry = tool_registry
        self._memory = memory

    # ── Channel Creation ─────────────────────────────────

    def create_channel(self, channel_type: str, config: Dict[str, Any]) -> BaseChannel:
        """
        Create a channel instance from config.

        Args:
            channel_type: 'telegram', 'discord', etc.
            config: Channel-specific configuration.

        Returns:
            Created channel instance.
        """
        if channel_type == "telegram":
            from src.channels.telegram_channel import TelegramChannel
            token = config.get("bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
            if not token:
                raise ValueError("Telegram bot token required (config or TELEGRAM_BOT_TOKEN env)")
            channel = TelegramChannel(
                bot_token=token,
                allowed_users=config.get("allowed_users"),
            )

        elif channel_type == "discord":
            from src.channels.discord_channel import DiscordChannel
            token = config.get("bot_token") or os.environ.get("DISCORD_BOT_TOKEN", "")
            if not token:
                raise ValueError("Discord bot token required (config or DISCORD_BOT_TOKEN env)")
            channel = DiscordChannel(
                bot_token=token,
                allowed_channels=config.get("allowed_channels"),
                allowed_users=config.get("allowed_users"),
                command_prefix=config.get("command_prefix", "!"),
            )

        else:
            raise ValueError(f"Unknown channel type: {channel_type}")

        # Set message handler
        channel.set_message_handler(self._handle_message)
        self._channels[channel_type] = channel
        return channel

    # ── Lifecycle ─────────────────────────────────────────

    async def start_channel(self, channel_type: str) -> bool:
        """Start a specific channel."""
        channel = self._channels.get(channel_type)
        if not channel:
            logger.warning("Channel '%s' not found", channel_type)
            return False

        try:
            await channel.start()
            logger.info("✅ Channel '%s' started", channel_type)
            return True
        except Exception as e:
            logger.error("Failed to start channel '%s': %s", channel_type, e)
            return False

    async def stop_channel(self, channel_type: str) -> bool:
        """Stop a specific channel."""
        channel = self._channels.get(channel_type)
        if not channel:
            return False

        try:
            await channel.stop()
            logger.info("Channel '%s' stopped", channel_type)
            return True
        except Exception as e:
            logger.error("Error stopping channel '%s': %s", channel_type, e)
            return False

    async def start_all(self) -> int:
        """Start all registered channels. Returns count of successfully started."""
        started = 0
        for name in list(self._channels.keys()):
            if await self.start_channel(name):
                started += 1
        return started

    async def stop_all(self) -> None:
        """Stop all channels."""
        for name in list(self._channels.keys()):
            await self.stop_channel(name)

    # ── Message Handler ───────────────────────────────────

    async def _handle_message(self, message: ChannelMessage) -> str:
        """
        Process an incoming message from any channel through the agent.

        This is the bridge between channels and the LLM.
        """
        if not self._llm:
            return "Agent not initialized. Please try again later."

        from src.core.llm_base import Message
        from pyda_models.models import MessageRole
        from datetime import datetime

        try:
            # Build messages list
            messages = []

            # System message with date and channel context
            system_content = (
                f"You are ElyssiaAgent, a helpful AI assistant. "
                f"Today's date is {datetime.now().strftime('%B %d, %Y')}. "
                f"You are chatting via {message.channel_type.value} with {message.username}. "
                f"Keep responses concise and well-formatted for {message.channel_type.value}."
            )

            # Inject tool descriptions if available
            if self._tool_registry:
                from src.tools.prompt_tools import inject_tool_prompt
                system_content = inject_tool_prompt(system_content, self._tool_registry)

            messages.append(Message(role=MessageRole.SYSTEM, content=system_content))
            messages.append(Message(role=MessageRole.USER, content=message.content))

            # Generate response (non-streaming for channels)
            gen = await self._llm.generate(messages, stream=False)

            response_text = ""
            async for chunk in gen:
                response_text += chunk.content or ""
                if chunk.done:
                    break

            # Strip <think> tags for clean output
            response_text = re.sub(r"<think>[\s\S]*?</think>", "", response_text).strip()

            # Handle tool calls if detected
            if self._tool_registry:
                from src.tools.prompt_tools import parse_tool_calls
                tool_calls, clean_text = parse_tool_calls(response_text)

                if tool_calls:
                    tool_results = []
                    for tc in tool_calls:
                        tool_name = tc.get("tool")
                        tool_args = tc.get("args", {})
                        tool = self._tool_registry.get(tool_name)
                        if tool:
                            result = await tool.execute(**tool_args)
                            tool_results.append(f"**{tool_name}:** {result}")

                    if tool_results:
                        # Generate final response with tool results
                        messages.append(Message(role=MessageRole.ASSISTANT, content=clean_text))
                        messages.append(Message(
                            role=MessageRole.USER,
                            content="Tool results:\n" + "\n".join(tool_results) + "\n\nSummarize the results.",
                        ))

                        gen2 = await self._llm.generate(messages, stream=False)
                        response_text = ""
                        async for chunk in gen2:
                            response_text += chunk.content or ""
                            if chunk.done:
                                break

                        response_text = re.sub(r"<think>[\s\S]*?</think>", "", response_text).strip()

            return response_text or "I processed your message but couldn't generate a response."

        except Exception as e:
            logger.error("Error processing message from %s: %s", message.channel_type.value, e)
            return f"Sorry, I encountered an error: {str(e)[:200]}"

    # ── Auto-setup from config ────────────────────────────

    def setup_from_config(self, config: Dict[str, Any]) -> int:
        """
        Create channels from a config dictionary.

        Expected format:
        channels:
          telegram:
            enabled: true
            bot_token: "..."
          discord:
            enabled: true
            bot_token: "..."
        """
        channels_config = config.get("channels", {})
        created = 0

        for channel_type, channel_config in channels_config.items():
            if not isinstance(channel_config, dict):
                continue
            if not channel_config.get("enabled", False):
                continue

            try:
                self.create_channel(channel_type, channel_config)
                created += 1
                logger.info("Created channel: %s", channel_type)
            except Exception as e:
                logger.warning("Skipping channel '%s': %s", channel_type, e)

        return created

    # ── Status ────────────────────────────────────────────

    def list_channels(self) -> List[Dict[str, Any]]:
        """Return status of all channels."""
        return [ch.status() for ch in self._channels.values()]

    def get_channel(self, channel_type: str) -> Optional[BaseChannel]:
        return self._channels.get(channel_type)

    def stats(self) -> Dict[str, Any]:
        return {
            "total_channels": len(self._channels),
            "running": sum(1 for ch in self._channels.values() if ch.is_running),
            "channels": {name: ch.status() for name, ch in self._channels.items()},
        }
