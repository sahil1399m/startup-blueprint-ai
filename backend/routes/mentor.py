"""
routes/mentor.py — AI Mentor chat endpoints.

POST /api/mentor/chat          → single question → answer
GET  /api/mentor/sessions      → list sessions for a blueprint
DELETE /api/mentor/session/{id} → delete a session
"""

from __future__ import annotations
import logging
import sys
import os
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

from auth_middleware import get_current_user
from dependencies import get_granite, get_groq, get_tavily, get_collections, get_gpt_oss
from models.mentor import MentorChatRequest, MentorChatResponse

log    = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mentor", tags=["mentor"])

# Add core/ to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))


@router.post("/chat", response_model=MentorChatResponse)
async def mentor_chat(
    body: MentorChatRequest,
    current_user: Dict = Depends(get_current_user),
    granite      = Depends(get_granite),
    groq_client  = Depends(get_groq),
    gpt_oss      = Depends(get_gpt_oss),
    tavily       = Depends(get_tavily),
    collections  = Depends(get_collections),
):
    """
    Send a question to the AI Mentor grounded in a specific blueprint.
    Returns the answer, detected intent, and citations.
    """
    try:
        from history import load_blueprint_for_display
        from history_db import get_blueprint_count_for_user

        # Load the blueprint the mentor is working from
        blueprint = load_blueprint_for_display(body.blueprint_id)
        if not blueprint:
            raise HTTPException(status_code=404, detail="Blueprint not found")

        # Build the permanent working memory context from the loaded blueprint
        from mentor.context import build_mentor_context
        
        ctx = build_mentor_context(
            idea=blueprint["original_query"],
            sector=blueprint["sector"],
            stage=blueprint["stage"],
            business_model=blueprint["business_model"],
            market=blueprint["market"],
            crag_result={
                "summary": blueprint.get("summary", ""),
                "confidence": blueprint.get("confidence", ""),
                "action": blueprint.get("action", ""),
                "raw_logits": blueprint.get("raw_logits", []),
                "keywords": blueprint.get("keywords", []),
                "retrieval_queries": blueprint.get("retrieval_queries", []),
                "internal_context": blueprint.get("internal_context", ""),
                "external_context": blueprint.get("external_context", ""),
                "rewritten_query": blueprint.get("rewritten_query", ""),
                "explore_results": blueprint.get("explore_results", [])
            },
            bmc_data=blueprint.get("bmc_data", {}),
            budget_data=blueprint.get("budget_data", {}),
            gtm_data=blueprint.get("gtm_data", {}),
            investor_data=blueprint.get("investor_data", {}),
            competitor_data=blueprint.get("competitor_data", {}),
            risk_data=blueprint.get("risk_data", {}),
        )

        from mentor.mentor_agent import create_session, ask
        from mentor.memory import MentorMessage
        
        # Initialize the session
        session = create_session(ctx=ctx, session_id=body.session_id)
        
        # Hydrate conversation history
        for msg in body.conversation_history:
            session.add_message(MentorMessage(
                role=msg.get("role", "user"),
                content=msg.get("content", "")
            ))

        # Ask the orchestrator
        result = ask(
            session=session,
            question=body.question,
            groq_client=groq_client,
            gpt_oss_client=gpt_oss,
            granite_client=granite,
            embedder=None,  # Not used by chromadb_tool (it uses gemini natively)
            collection=collections.get("text") if collections else None,
            tavily_client=tavily,
            blueprint_id=body.blueprint_id,
            user_email=current_user["email"],
        )

        return MentorChatResponse(
            answer=result.get("answer", ""),
            intent=result.get("intent", "unknown"),
            citations=result.get("citations", []),
            tools_used=result.get("tools_used", []),
            session_id=result.get("session_id", body.session_id or ""),
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Mentor chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Mentor error: {str(e)}")


@router.get("/sessions/{blueprint_id}")
async def get_mentor_sessions(
    blueprint_id: int,
    current_user: Dict = Depends(get_current_user),
):
    """List all mentor sessions for a blueprint."""
    try:
        from mentor.mentor_db import get_sessions_for_blueprint
        sessions = get_sessions_for_blueprint(blueprint_id, current_user["email"])
        return {"sessions": sessions}
    except Exception as e:
        log.warning(f"Failed to load mentor sessions: {e}")
        return {"sessions": []}


@router.delete("/session/{session_id}", status_code=204)
async def delete_mentor_session(
    session_id: str,
    current_user: Dict = Depends(get_current_user),
):
    """Delete a mentor session."""
    try:
        from mentor.mentor_db import delete_session
        delete_session(session_id, current_user["email"])
    except Exception as e:
        log.warning(f"Failed to delete session: {e}")
    return None