"""
Discord Channel — Bot integration for Discord messaging.

Uses discord.py library. Set DISCORD_BOT_TOKEN in env or config to enable.
"""

import asyncio
import logging
from typing import Optional, Dict, Any

from src.channels.base_channel import BaseChannel, ChannelMessage, ChannelType

logger = logging.getLogger(__name__)


class DiscordChannel(BaseChannel):
    """Discord bot channel using discord.py."""

    def __init__(
        self,
        bot_token: str,
        allowed_channels: Optional[list] = None,
        allowed_users: Optional[list] = None,
        command_prefix: str = "!",
    ):
        """
        Args:
            bot_token: Discord Bot token.
            allowed_channels: Optional list of channel IDs to respond in.
            allowed_users: Optional list of user IDs allowed to interact.
            command_prefix: Prefix for bot commands (default: '!').
        """
        super().__init__()
        self._token = bot_token
        self._allowed_channels = set(allowed_channels) if allowed_channels else None
        self._allowed_users = set(allowed_users) if allowed_users else None
        self._prefix = command_prefix
        self._client = None
        self._task = None

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.DISCORD

    @property
    def name(self) -> str:
        return "discord"

    async def start(self) -> None:
        """Start the Discord bot."""
        try:
            import discord
        except ImportError:
            raise RuntimeError(
                "discord.py not installed. Run: pip install discord.py"
            )

        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        self._client = discord.Client(intents=intents)

        @self._client.event
        async def on_ready():
            logger.info("🎮 Discord bot ready as %s", self._client.user)
            self._running = True

        @self._client.event
        async def on_message(message):
            # Don't respond to ourselves
            if message.author == self._client.user:
                return

            # Check allowed channels
            if self._allowed_channels and message.channel.id not in self._allowed_channels:
                return

            # Check allowed users
            if self._allowed_users and message.author.id not in self._allowed_users:
                return

            content = message.content.strip()
            if not content:
                return

            # Handle commands
            if content.startswith(self._prefix):
                await self._handle_command(message, content[len(self._prefix):])
                return

            # Handle mentions or DMs
            is_dm = message.guild is None
            is_mentioned = self._client.user in message.mentions if message.mentions else False

            if is_dm or is_mentioned:
                # Strip mention from content
                if is_mentioned:
                    content = content.replace(f"<@{self._client.user.id}>", "").strip()
                    content = content.replace(f"<@!{self._client.user.id}>", "").strip()

                if not content:
                    return

                # Show typing
                async with message.channel.typing():
                    msg = ChannelMessage(
                        channel_type=ChannelType.DISCORD,
                        channel_id=str(message.channel.id),
                        user_id=str(message.author.id),
                        username=message.author.display_name,
                        content=content,
                        metadata={
                            "guild_id": str(message.guild.id) if message.guild else None,
                            "message_id": str(message.id),
                            "is_dm": is_dm,
                        },
                    )

                    response = await self.on_message(msg)

                if response:
                    await self.send_message(str(message.channel.id), response)

        # Run in background task
        self._task = asyncio.create_task(self._run_bot())
        logger.info("🎮 Discord bot starting...")

    async def _run_bot(self):
        """Run the Discord client."""
        try:
            await self._client.start(self._token)
        except Exception as e:
            logger.error("Discord bot error: %s", e)
            self._running = False

    async def stop(self) -> None:
        """Stop the Discord bot."""
        if self._client:
            await self._client.close()
            self._client = None

        if self._task:
            self._task.cancel()
            self._task = None

        self._running = False
        logger.info("Discord bot stopped")

    async def send_message(self, channel_id: str, content: str, **kwargs) -> None:
        """Send a message to a Discord channel."""
        if not self._client:
            raise RuntimeError("Discord bot not started")

        channel = self._client.get_channel(int(channel_id))
        if not channel:
            # Try fetching if not cached
            try:
                channel = await self._client.fetch_channel(int(channel_id))
            except Exception:
                logger.error("Could not find Discord channel %s", channel_id)
                return

        # Split long messages (Discord limit: 2000 chars)
        chunks = self._split_message(content, max_len=1900)
        for chunk in chunks:
            await channel.send(chunk)

    # ── Command handling ─────────────────────────────────

    async def _handle_command(self, message, command: str) -> None:
        """Handle prefixed commands."""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()

        if cmd == "help":
            await message.channel.send(
                "🔧 **ElyssiaAgent Commands:**\n\n"
                f"`{self._prefix}help` — Show this help\n"
                f"`{self._prefix}status` — System status\n"
                f"`{self._prefix}clear` — Clear context\n\n"
                "**Chat:** Mention me or DM me to chat!"
            )
        elif cmd == "status":
            status = self.status()
            await message.channel.send(
                f"📊 **Status:**\n"
                f"Channel: {status['type']}\n"
                f"Running: {status['running']}\n"
                f"Bot: {self._client.user if self._client else 'N/A'}"
            )
        elif cmd == "clear":
            await message.channel.send("🗑️ Conversation context cleared.")
        elif cmd == "ask" and len(parts) > 1:
            # Direct question without needing mention
            async with message.channel.typing():
                msg = ChannelMessage(
                    channel_type=ChannelType.DISCORD,
                    channel_id=str(message.channel.id),
                    user_id=str(message.author.id),
                    username=message.author.display_name,
                    content=parts[1],
                    metadata={"command": True},
                )
                response = await self.on_message(msg)
            if response:
                await self.send_message(str(message.channel.id), response)

    # ── Helpers ───────────────────────────────────────────

    @staticmethod
    def _split_message(text: str, max_len: int = 1900) -> list:
        """Split text into chunks that fit Discord's message limit."""
        if len(text) <= max_len:
            return [text]

        chunks = []
        while text:
            if len(text) <= max_len:
                chunks.append(text)
                break

            split_pos = text.rfind("\n", 0, max_len)
            if split_pos == -1:
                split_pos = max_len

            chunks.append(text[:split_pos])
            text = text[split_pos:].lstrip("\n")

        return chunks

    def status(self) -> Dict[str, Any]:
        base = super().status()
        base["token_set"] = bool(self._token)
        base["bot_user"] = str(self._client.user) if self._client and self._client.user else None
        base["allowed_channels"] = list(self._allowed_channels) if self._allowed_channels else "all"
        return base
