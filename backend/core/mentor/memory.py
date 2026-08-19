"""
mentor/memory.py
─────────────────
In-memory MentorSession with:
  - conversation history (sliding window for prompt injection)
  - tool-result cache to avoid duplicate API calls within a session
  - helper to build the conversation tail for intent classification

Persistence is handled separately by mentor_db.py (SQLite).
This module is intentionally stateless — the Streamlit session state
owns the MentorSession object and passes it around.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import hashlib
import json


@dataclass
class MentorMessage:
    role:       str          # "user" | "assistant"
    content:    str
    intent:     str   = ""
    citations:  list  = field(default_factory=list)
    tools_used: list  = field(default_factory=list)
    timestamp:  str   = field(default_factory=lambda: datetime.now().strftime("%H:%M"))


class MentorSession:
    """
    Holds conversation history and tool-result cache for one mentor session.

    Parameters
    ----------
    ctx          : MentorContext dict built from blueprint output
    session_id   : unique session identifier (UUID string)
    window_size  : how many recent turns to include in every prompt
    """

    def __init__(self, ctx: dict, session_id: str, window_size: int = 6):
        self.ctx        = ctx
        self.session_id = session_id
        self.window     = window_size
        self._messages: list[MentorMessage] = []
        self._cache:    dict[str, Any]       = {}   # tool result cache

    # ── Message management ────────────────────────────────────────────────────

    def add_message(self, msg: MentorMessage) -> None:
        self._messages.append(msg)

    def get_history(self) -> list[MentorMessage]:
        return list(self._messages)

    def get_recent_window(self) -> list[MentorMessage]:
        """Returns last `window` messages (for prompt context)."""
        return self._messages[-self.window:]

    def build_conversation_tail(self, n_turns: int = 3) -> str:
        """
        Build a short text snippet of the last n turns for intent classification.
        """
        tail_msgs = self._messages[-(n_turns * 2):]  # n turns = 2*n messages
        lines = []
        for m in tail_msgs:
            label = "User" if m.role == "user" else "Mentor"
            lines.append(f"{label}: {m.content[:200]}")
        return "\n".join(lines)

    def build_chat_history_for_prompt(self) -> str:
        """
        Returns the last window messages formatted as a conversation block
        to be injected into the Granite synthesis prompt.
        """
        recent = self.get_recent_window()
        if not recent:
            return ""
        lines = ["\n=== RECENT CONVERSATION CONTEXT ==="]
        for m in recent:
            label = "User" if m.role == "user" else "Mentor"
            lines.append(f"{label}: {m.content[:400]}")
        return "\n".join(lines)

    # ── Tool cache ────────────────────────────────────────────────────────────

    def _cache_key(self, tool: str, query: str) -> str:
        raw = f"{tool}:{query}"
        return hashlib.md5(raw.encode()).hexdigest()

    def cache_get(self, tool: str, query: str) -> Any | None:
        return self._cache.get(self._cache_key(tool, query))

    def cache_set(self, tool: str, query: str, value: Any) -> None:
        self._cache[self._cache_key(tool, query)] = value

    # ── Convenience ──────────────────────────────────────────────────────────

    @property
    def message_count(self) -> int:
        return len(self._messages)

    @property
    def last_intent(self) -> str:
        for m in reversed(self._messages):
            if m.role == "assistant" and m.intent:
                return m.intent
        return ""

    def to_db_list(self) -> list[dict]:
        """Serialise all messages for persistence via mentor_db."""
        return [
            {
                "role":       m.role,
                "content":    m.content,
                "intent":     m.intent,
                "citations":  m.citations,
                "tools_used": m.tools_used,
                "timestamp":  m.timestamp,
            }
            for m in self._messages
        ]
