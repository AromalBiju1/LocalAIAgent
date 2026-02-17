"""
Telegram Channel — Bot integration for Telegram messaging.

Uses python-telegram-bot library (async, polling mode).
Set TELEGRAM_BOT_TOKEN in env or config to enable.
"""

import asyncio
import logging
from typing import Optional, Dict, Any

from src.channels.base_channel import BaseChannel, ChannelMessage, ChannelType

logger = logging.getLogger(__name__)


class TelegramChannel(BaseChannel):
    """Telegram bot channel using python-telegram-bot."""

    def __init__(self, bot_token: str, allowed_users: Optional[list] = None):
        """
        Args:
            bot_token: Telegram Bot API token from @BotFather.
            allowed_users: Optional list of allowed user IDs (security).
                           If None, all users can interact.
        """
        super().__init__()
        self._token = bot_token
        self._allowed_users = set(allowed_users) if allowed_users else None
        self._application = None

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.TELEGRAM

    @property
    def name(self) -> str:
        return "telegram"

    async def start(self) -> None:
        """Start the Telegram bot with polling."""
        try:
            from telegram import Update
            from telegram.ext import (
                ApplicationBuilder,
                CommandHandler,
                MessageHandler as TGMessageHandler,
                filters,
            )
        except ImportError:
            raise RuntimeError(
                "python-telegram-bot not installed. Run: pip install python-telegram-bot"
            )

        # Build application
        self._application = ApplicationBuilder().token(self._token).build()

        # Register handlers
        self._application.add_handler(CommandHandler("start", self._cmd_start))
        self._application.add_handler(CommandHandler("help", self._cmd_help))
        self._application.add_handler(CommandHandler("status", self._cmd_status))
        self._application.add_handler(CommandHandler("clear", self._cmd_clear))
        self._application.add_handler(
            TGMessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )

        # Start polling in the background
        await self._application.initialize()
        await self._application.start()
        await self._application.updater.start_polling(drop_pending_updates=True)

        self._running = True
        logger.info("🤖 Telegram bot started (polling mode)")

    async def stop(self) -> None:
        """Stop the Telegram bot."""
        if self._application:
            await self._application.updater.stop()
            await self._application.stop()
            await self._application.shutdown()
            self._application = None

        self._running = False
        logger.info("Telegram bot stopped")

    async def send_message(self, channel_id: str, content: str, **kwargs) -> None:
        """Send a message to a Telegram chat."""
        if not self._application:
            raise RuntimeError("Telegram bot not started")

        parse_mode = kwargs.get("parse_mode", "Markdown")

        # Split long messages (Telegram limit: 4096 chars)
        chunks = self._split_message(content, max_len=4000)
        for chunk in chunks:
            try:
                await self._application.bot.send_message(
                    chat_id=int(channel_id),
                    text=chunk,
                    parse_mode=parse_mode,
                )
            except Exception:
                # Fallback without markdown if parsing fails
                await self._application.bot.send_message(
                    chat_id=int(channel_id),
                    text=chunk,
                )

    # ── Telegram handlers ────────────────────────────────

    def _is_allowed(self, user_id: int) -> bool:
        """Check if user is in the allowed list."""
        if self._allowed_users is None:
            return True
        return user_id in self._allowed_users

    async def _cmd_start(self, update, context) -> None:
        """Handle /start command."""
        if not self._is_allowed(update.effective_user.id):
            await update.message.reply_text("⛔ Unauthorized.")
            return

        await update.message.reply_text(
            "👋 *Hey! I'm ElyssiaAgent.*\n\n"
            "Send me any message and I'll respond using my AI brain.\n\n"
            "Commands:\n"
            "/help — Show available commands\n"
            "/status — Check system status\n"
            "/clear — Clear conversation context",
            parse_mode="Markdown",
        )

    async def _cmd_help(self, update, context) -> None:
        """Handle /help command."""
        if not self._is_allowed(update.effective_user.id):
            return

        await update.message.reply_text(
            "🔧 *Available Commands:*\n\n"
            "/start — Welcome message\n"
            "/help — This help text\n"
            "/status — System health check\n"
            "/clear — Reset conversation\n\n"
            "Just type normally to chat with me!",
            parse_mode="Markdown",
        )

    async def _cmd_status(self, update, context) -> None:
        """Handle /status command."""
        if not self._is_allowed(update.effective_user.id):
            return

        status = self.status()
        await update.message.reply_text(
            f"📊 *Status:*\n"
            f"Channel: {status['type']}\n"
            f"Running: {status['running']}\n"
            f"Handler: {'✅' if status['has_handler'] else '❌'}",
            parse_mode="Markdown",
        )

    async def _cmd_clear(self, update, context) -> None:
        """Handle /clear command."""
        if not self._is_allowed(update.effective_user.id):
            return
        # Context clearing is handled by the channel manager
        await update.message.reply_text("🗑️ Conversation context cleared.")

    async def _handle_message(self, update, context) -> None:
        """Handle incoming text messages."""
        user = update.effective_user
        if not self._is_allowed(user.id):
            await update.message.reply_text("⛔ Unauthorized.")
            return

        # Show typing indicator
        await update.message.chat.send_action("typing")

        # Build unified message
        msg = ChannelMessage(
            channel_type=ChannelType.TELEGRAM,
            channel_id=str(update.effective_chat.id),
            user_id=str(user.id),
            username=user.first_name or user.username or "User",
            content=update.message.text,
            metadata={"message_id": update.message.message_id},
        )

        # Process through handler
        response = await self.on_message(msg)

        if response:
            await self.send_message(str(update.effective_chat.id), response)

    # ── Helpers ───────────────────────────────────────────

    @staticmethod
    def _split_message(text: str, max_len: int = 4000) -> list:
        """Split text into chunks that fit Telegram's message limit."""
        if len(text) <= max_len:
            return [text]

        chunks = []
        while text:
            if len(text) <= max_len:
                chunks.append(text)
                break

            # Try to split at newline
            split_pos = text.rfind("\n", 0, max_len)
            if split_pos == -1:
                split_pos = max_len

            chunks.append(text[:split_pos])
            text = text[split_pos:].lstrip("\n")

        return chunks

    def status(self) -> Dict[str, Any]:
        base = super().status()
        base["token_set"] = bool(self._token)
        base["allowed_users"] = list(self._allowed_users) if self._allowed_users else "all"
        return base
