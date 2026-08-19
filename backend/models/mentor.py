"""
models/mentor.py — Pydantic schemas for AI Mentor chat endpoints.

Used by routes/mentor.py for request validation and response serialization.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MentorChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question")
    blueprint_id: int = Field(..., description="Blueprint ID to ground the conversation")
    session_id: Optional[str] = Field(default=None, description="Existing session ID (null for new session)")
    conversation_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Recent messages for context (last ~10)",
    )


class MentorChatResponse(BaseModel):
    answer: str = ""
    intent: str = "unknown"
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    session_id: str = ""
