"""
models/blueprint.py — Pydantic schemas for blueprint generation endpoints.

Used by routes/blueprint.py for request validation, SSE event formatting,
and the final BlueprintResponse shape.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class BlueprintRequest(BaseModel):
    idea: str = Field(..., min_length=10, description="Startup idea description")
    sector: str = Field(default="Fintech", description="Industry sector")
    model_type: str = Field(default="B2B", description="Business model type")
    stage: str = Field(default="Idea Stage", description="Startup stage")
    target_city: str = Field(default="Pan India", description="Target market/city")

    model_config = ConfigDict(protected_namespaces=())


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
    Full response returned on SSE 'complete' event and GET /api/blueprint/{id}.
    Contains both nested 'blueprint' object and flat section fields so all
    consumers (Dashboard, Blueprint view, History, Mentor) receive consistent data.
    """
    blueprint_id: Optional[int] = None
    id: Optional[int] = None
    idea: str = ""
    original_query: str = ""
    title: str = ""
    sector: str = ""
    model_type: str = ""
    business_model: str = ""
    stage: str = ""
    target_city: str = ""
    market: str = ""
    generated_at: str = ""
    timestamp: str = ""

    # Status and failure metadata
    status: str = "success"
    failed_sections: List[str] = Field(default_factory=list)

    # CRAG pipeline result
    crag_result: Optional[Dict[str, Any]] = None
    confidence: Optional[str] = ""
    summary: Optional[str] = ""
    sources: Optional[List[Any]] = None
    keywords: Optional[List[str]] = None
    raw_logits: Optional[List[float]] = None

    # Canonical nested blueprint dict
    blueprint: Optional[Dict[str, Any]] = None

    # Flat section access for backwards compatibility
    bmc_data: Optional[Dict[str, Any]] = None
    budget_data: Optional[Dict[str, Any]] = None
    gtm_data: Optional[Dict[str, Any]] = None
    investor_data: Optional[Dict[str, Any]] = None
    competitor_data: Optional[Dict[str, Any]] = None
    risk_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        protected_namespaces=(),
        arbitrary_types_allowed=True,
        extra="allow",
    )
