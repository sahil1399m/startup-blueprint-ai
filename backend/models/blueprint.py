"""
models/blueprint.py — Pydantic schemas for blueprint generation endpoints.

Used by routes/blueprint.py for request validation, SSE event formatting,
and the final BlueprintResponse shape.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BlueprintRequest(BaseModel):
    idea: str = Field(..., min_length=10, description="Startup idea description")
    sector: str = Field(default="Fintech", description="Industry sector")
    model_type: str = Field(default="B2B", description="Business model type")
    stage: str = Field(default="Idea Stage", description="Startup stage")
    target_city: str = Field(default="Pan India", description="Target market/city")


class SSEEvent(BaseModel):
    """Single SSE frame sent during blueprint generation streaming."""
    event: str = Field(..., description="Event type: progress | complete | error")
    step: str = ""
    node: str = ""
    progress: int = 0
    data: Optional[Any] = None
    error: str = ""


class BlueprintResponse(BaseModel):
    """
    Full response returned on SSE 'complete' event.
    Contains the CRAG result and all 6 blueprint sections.
    """
    blueprint_id: Optional[int] = None
    idea: str = ""
    sector: str = ""
    model_type: str = ""
    stage: str = ""
    target_city: str = ""
    generated_at: str = ""

    # CRAG pipeline result
    crag_result: Optional[Dict[str, Any]] = None

    # Blueprint sections (each is a dict with section-specific structure)
    blueprint: Optional[Dict[str, Any]] = None

    class Config:
        # Allow arbitrary types in dicts for flexibility
        arbitrary_types_allowed = True
