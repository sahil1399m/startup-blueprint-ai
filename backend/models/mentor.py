"""
models/mentor.py — Pydantic schemas for AI Mentor chat endpoints.

Used by routes/mentor.py for request validation and response serialization.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class MentorChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question")
    blueprint_id: int = Field(..., description="Blueprint ID to ground the conversation")
    session_id: Optional[str] = Field(default=None, description="Existing session ID (null for new session)")
    conversation_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Recent messages for context (last ~10)",
    )


def _normalize_citation(c: Any) -> Dict[str, Any]:
    """
    Normalize a citation to a canonical dict shape expected by the frontend.

    Tool routers return citation strings like:
      '📄 source_file.pdf'
      '🌐 [Title](https://example.com)'

    Frontend (StructuredResponse.jsx) expects:
      { title: str, url: str, type: str }
    """
    if isinstance(c, dict):
        return {
            "title": str(c.get("title") or c.get("name") or c.get("source") or "Source"),
            "url":   str(c.get("url") or ""),
            "type":  str(c.get("type") or "document"),
        }
    if isinstance(c, str):
        import re
        # Match markdown link: 🌐 [Title](url)
        md_match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', c)
        if md_match:
            return {"title": md_match.group(1), "url": md_match.group(2), "type": "web"}
        # Plain document citation: 📄 filename
        plain = c.lstrip("📄🌐 ").strip()
        return {"title": plain, "url": "", "type": "document"}
    # Fallback for unexpected types
    return {"title": str(c), "url": "", "type": "document"}


class MentorChatResponse(BaseModel):
    answer: str = ""
    intent: str = "unknown"
    # Accept both string and dict citations from tools; normalize to dict for frontend
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    session_id: str = ""

    @field_validator("citations", mode="before")
    @classmethod
    def normalize_citations(cls, v: Any) -> List[Dict[str, Any]]:
        """Convert any mix of str/dict citations into canonical dicts."""
        if not isinstance(v, list):
            return []
        return [_normalize_citation(c) for c in v if c]
