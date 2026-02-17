"""
Conversation Memory — SQLite-backed persistent conversation storage.

Stores full conversation threads, supports sliding window context,
auto-summarization, and keyword search across past conversations.
"""

import json
import sqlite3
import time
import uuid
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Persistent conversation memory with SQLite backend."""

    def __init__(self, db_path: str = "data/conversations/memory.db", memory_window: int = 10):
        self.db_path = Path(db_path)
        self.memory_window = memory_window
        self._active_conversation_id: Optional[str] = None
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at REAL,
                    updated_at REAL,
                    summary TEXT DEFAULT '',
                    message_count INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    hashed_password TEXT NOT NULL,
                    created_at REAL,
                    disabled INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    name TEXT,
                    timestamp REAL NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                );

                CREATE INDEX IF NOT EXISTS idx_messages_conv
                    ON messages(conversation_id, timestamp);

                CREATE INDEX IF NOT EXISTS idx_conversations_updated
                    ON conversations(updated_at DESC);

                -- CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts
                --    USING fts5(content, conversation_id, content='messages');
            """)
        logger.info("Memory DB initialized at %s", self.db_path)

    def _connect(self) -> sqlite3.Connection:
        """Get a new database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    # ── Conversation lifecycle ────────────────────────────

    def new_conversation(self, title: Optional[str] = None) -> str:
        """Start a new conversation, returns conversation ID."""
        conv_id = str(uuid.uuid4())[:8]
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (conv_id, title or f"Chat {conv_id}", now, now),
            )
        self._active_conversation_id = conv_id
        logger.info("New conversation: %s", conv_id)
        return conv_id

    @property
    def active_id(self) -> Optional[str]:
        return self._active_conversation_id

    def set_active(self, conversation_id: str):
        """Set the active conversation."""
        self._active_conversation_id = conversation_id

    # ── Message storage ───────────────────────────────────

    def add_message(
        self,
        role: str,
        content: str,
        conversation_id: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a message to a conversation."""
        conv_id = conversation_id or self._active_conversation_id
        if not conv_id:
            conv_id = self.new_conversation()

        msg_id = str(uuid.uuid4())[:12]
        now = time.time()

        with self._connect() as conn:
            conn.execute(
                """INSERT INTO messages (id, conversation_id, role, content, name, timestamp, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    msg_id, 
                    conv_id, 
                    role, 
                    content, 
                    name, 
                    now, 
                    json.dumps(metadata) if metadata else '{}'
                ),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ?, message_count = message_count + 1 WHERE id = ?",
                (now, conv_id),
            )
            # Update FTS index
            conn.execute(
                "INSERT INTO messages_fts (content, conversation_id) VALUES (?, ?)",
                (content, conv_id),
            )
        return msg_id

    def get_messages(
        self,
        conversation_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get messages for a conversation, newest last."""
        conv_id = conversation_id or self._active_conversation_id
        if not conv_id:
            return []

        query = "SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC"
        params: list = [conv_id]

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_recent_messages(self, conversation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get the most recent messages within the memory window."""
        conv_id = conversation_id or self._active_conversation_id
        if not conv_id:
            return []

        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM messages WHERE conversation_id = ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (conv_id, self.memory_window),
            ).fetchall()
            return [dict(r) for r in reversed(rows)]  # chronological order

    # ── Conversation management ───────────────────────────

    def list_conversations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent conversations."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation metadata."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
            return dict(row) if row else None

    def update_title(self, conversation_id: str, title: str):
        """Update a conversation's title."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE conversations SET title = ? WHERE id = ?",
                (title, conversation_id),
            )

    def update_summary(self, conversation_id: str, summary: str):
        """Store a condensed summary of older messages."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE conversations SET summary = ? WHERE id = ?",
                (summary, conversation_id),
            )

    def delete_conversation(self, conversation_id: str):
        """Delete a conversation and all its messages."""
        with self._connect() as conn:
            conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        logger.info("Deleted conversation: %s", conversation_id)

    # ── Search ────────────────────────────────────────────

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Full-text search across all conversations."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT m.*, c.title as conversation_title
                   FROM messages m
                   JOIN conversations c ON c.id = m.conversation_id
                   WHERE m.content LIKE ?
                   ORDER BY m.timestamp DESC
                   LIMIT ?""",
                (f"%{query}%", limit),
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Context Management ────────────────────────────────

    async def get_context_window(self, conversation_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieve context window for the LLM.
        - Gets recent messages.
        - If we improved this, we'd include summaries of older messages.
        """
        # For now, simplistic implementation: just get the last `limit` messages
        # In a real "Jarvis" update, we'd fetch the 'summary' from the conversation table
        # and prepend it as a system message if it exists.
        
        c = self.get_conversation(conversation_id)
        messages = self.get_recent_messages(conversation_id) # Uses self.memory_window by default
        
        # Override if limit is provided and different from default
        if limit and limit != self.memory_window:
            with self._connect() as conn:
                rows = conn.execute(
                    """SELECT * FROM messages WHERE conversation_id = ?
                       ORDER BY timestamp DESC LIMIT ?""",
                    (conversation_id, limit),
                ).fetchall()
                messages = [dict(r) for r in reversed(rows)]

        if c and c.get("summary"):
            # Prepend summary as a system message
            messages.insert(0, {
                "role": "system",
                "content": f"PREVIOUS CONTEXT SUMMARY: {c['summary']}",
                "timestamp": time.time(),
                "id": "summary-node"
            })
            
        return messages

    async def auto_summarize(self, conversation_id: str, llm_client) -> None:
        """
        Check if conversation is too long and summarize.
        """
        # This is a placeholder for the logic. 
        # We would count tokens or messages, and if > Threshold, compress older ones.
        pass

    # ── User Management ───────────────────────────────────

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
            return dict(row) if row else None

    def create_user(self, username: str, hashed_password: str):
        """Create a new user."""
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO users (username, hashed_password, created_at) VALUES (?, ?, ?)",
                (username, hashed_password, now),
            )
        logger.info("Created user: %s", username)

    # ── Stats ─────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        with self._connect() as conn:
            conv_count = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            msg_count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
            return {
                "conversations": conv_count,
                "messages": msg_count,
                "users": user_count,
                "db_size_mb": round(db_size / 1024 / 1024, 2),
                "memory_window": self.memory_window,
            }
