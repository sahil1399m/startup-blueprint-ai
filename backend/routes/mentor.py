"""
routes/mentor.py — AI Mentor chat endpoints.

POST /api/mentor/chat          → single question → answer
GET  /api/mentor/sessions/{id} → list sessions for a blueprint
DELETE /api/mentor/session/{id} → delete a session
"""

from __future__ import annotations
import logging
import sys
import os
import time
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
    t_start = time.time()

    log.info("══════════════════════════════════════════════════════════════")
    log.info("[MENTOR] Request received")
    log.info(f"[MENTOR] Blueprint ID: {body.blueprint_id}")
    log.info(f"[MENTOR] Session ID: {body.session_id or '(new)'}")
    log.info(f"[MENTOR] Question length: {len(body.question)} chars")
    log.info(f"[MENTOR] History messages: {len(body.conversation_history)}")
    log.info("══════════════════════════════════════════════════════════════")

    # ── Validate request ───────────────────────────────────────────────────────
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        from history import load_blueprint_for_display

        # ── Load the authenticated user's blueprint ────────────────────────────
        blueprint = load_blueprint_for_display(body.blueprint_id)
        if not blueprint:
            log.error(f"[MENTOR ERROR] Blueprint {body.blueprint_id} not found")
            raise HTTPException(status_code=404, detail=f"Blueprint {body.blueprint_id} not found")

        # Security: verify the blueprint belongs to the authenticated user
        bp_user = blueprint.get("user_email", "")
        req_user = current_user.get("email", "")
        if bp_user and req_user and bp_user != req_user:
            log.error(f"[MENTOR ERROR] User {req_user} attempted to access blueprint owned by {bp_user}")
            raise HTTPException(status_code=403, detail="Access denied to this blueprint")

        log.info(f"[MENTOR] Blueprint loaded: '{blueprint.get('title', 'Untitled')}' | sector={blueprint.get('sector', 'N/A')}")

        # ── Safely normalize all blueprint section data ────────────────────────
        def _safe_dict(val, default=None):
            """Return val if it is a dict, else default."""
            return val if isinstance(val, dict) else (default or {})

        def _safe_list(val):
            """Return val if it is a list, else []."""
            return val if isinstance(val, list) else []

        bmc_data        = _safe_dict(blueprint.get("bmc_data"))
        budget_data     = _safe_dict(blueprint.get("budget_data"))
        gtm_data        = _safe_dict(blueprint.get("gtm_data"))
        investor_data   = _safe_dict(blueprint.get("investor_data"))
        competitor_data = _safe_dict(blueprint.get("competitor_data"))
        risk_data       = _safe_dict(blueprint.get("risk_data"))

        crag_result = {
            "summary":           str(blueprint.get("summary", "")),
            "confidence":        str(blueprint.get("confidence", "")),
            "action":            str(blueprint.get("action", "")),
            "raw_logits":        _safe_list(blueprint.get("raw_logits")),
            "keywords":          _safe_list(blueprint.get("keywords")),
            "retrieval_queries": _safe_list(blueprint.get("retrieval_queries")),
            "internal_context":  str(blueprint.get("internal_context", "")),
            "external_context":  str(blueprint.get("external_context", "")),
            "rewritten_query":   str(blueprint.get("rewritten_query", "")),
            "explore_results":   _safe_list(blueprint.get("explore_results")),
        }

        # ── Build MentorContext from the blueprint ─────────────────────────────
        from mentor.context import build_mentor_context

        ctx = build_mentor_context(
            idea=str(blueprint.get("original_query", "")),
            sector=str(blueprint.get("sector", "")),
            stage=str(blueprint.get("stage", "")),
            business_model=str(blueprint.get("business_model", "")),
            market=str(blueprint.get("market", "")),
            crag_result=crag_result,
            bmc_data=bmc_data,
            budget_data=budget_data,
            gtm_data=gtm_data,
            investor_data=investor_data,
            competitor_data=competitor_data,
            risk_data=risk_data,
        )

        # ── Create / resume session ────────────────────────────────────────────
        from mentor.mentor_agent import create_session, ask
        from mentor.memory import MentorMessage

        session = create_session(ctx=ctx, session_id=body.session_id)

        # Hydrate conversation history from request (last 10 messages only)
        for msg in body.conversation_history[-10:]:
            if isinstance(msg, dict):
                role    = str(msg.get("role", "user"))
                content = str(msg.get("content", ""))
                if content:
                    session.add_message(MentorMessage(role=role, content=content))

        # ── Run the orchestrator ───────────────────────────────────────────────
        result = ask(
            session=session,
            question=body.question,
            groq_client=groq_client,
            gpt_oss_client=gpt_oss,
            granite_client=granite,
            embedder=None,  # ChromaDB uses Gemini embeddings natively
            collection=collections.get("text") if collections else None,
            tavily_client=tavily,
            blueprint_id=body.blueprint_id,
            user_email=current_user.get("email", ""),
        )

        t_elapsed = time.time() - t_start
        log.info("══════════════════════════════════════════════════════════════")
        log.info("[MENTOR] Response returned successfully")
        log.info(f"[MENTOR] Intent: {result.get('intent', 'unknown')}")
        log.info(f"[MENTOR] Session ID: {result.get('session_id', '')}")
        log.info(f"[MENTOR] Answer length: {len(result.get('answer', ''))} chars")
        log.info(f"[MENTOR] Citations: {len(result.get('citations', []))}")
        log.info(f"[MENTOR] Tools used: {result.get('tools_used', [])}")
        log.info(f"[MENTOR] Total request time: {t_elapsed:.1f}s")
        log.info("══════════════════════════════════════════════════════════════")

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
        import traceback
        log.error(f"[MENTOR ERROR] Unexpected error in mentor_chat")
        log.error(f"[MENTOR ERROR TYPE] {type(e).__name__}")
        log.error(f"[MENTOR ERROR] {str(e)}")
        log.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Mentor error: {type(e).__name__}: {str(e)}")


@router.get("/sessions/{blueprint_id}")
async def get_mentor_sessions(
    blueprint_id: int,
    current_user: Dict = Depends(get_current_user),
):
    """List all mentor sessions for a blueprint."""
    try:
        from mentor.mentor_db import get_sessions_for_blueprint
        # NOTE: get_sessions_for_blueprint only takes blueprint_id
        # (user_email scoping is done at application level)
        sessions = get_sessions_for_blueprint(blueprint_id)
        # Filter sessions to current user only
        user_email = current_user.get("email", "")
        if user_email:
            sessions = [s for s in sessions if s.get("user_email", "") == user_email]
        return {"sessions": sessions}
    except Exception as e:
        log.warning(f"[MENTOR] Failed to load mentor sessions: {e}")
        return {"sessions": []}


@router.delete("/session/{session_id}", status_code=204)
async def delete_mentor_session(
    session_id: str,
    current_user: Dict = Depends(get_current_user),
):
    """Delete a mentor session."""
    try:
        from mentor.mentor_db import delete_session
        delete_session(session_id, current_user.get("email", ""))
    except Exception as e:
        log.warning(f"[MENTOR] Failed to delete session: {e}")
    return None