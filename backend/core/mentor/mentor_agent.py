"""
mentor/mentor_agent.py
───────────────────────
Main orchestrator for the AI Startup Mentor.

Flow per user question:
  1. Classify intent (Groq LLM)
  2. Route to tools (blueprint + optional chromadb + optional tavily)
  3. Synthesize grounded answer (IBM Granite 4.0)
  4. Persist to mentor_db (SQLite)
  5. Return structured response

Entry point:  ask(session, question, ...)
"""

from __future__ import annotations
import uuid
from datetime import datetime

from mentor.intent_classifier import classify_intent
from mentor.tool_router        import route_tools
from mentor.synthesizer        import synthesize_answer
from mentor.memory             import MentorMessage
from mentor.mentor_db          import save_mentor_session, save_mentor_message


def ask(
    *,
    session,               # MentorSession
    question: str,
    groq_client,
    gpt_oss_client,
    granite_client,
    embedder,
    collection,
    tavily_client,
    blueprint_id: int | None = None,
    user_email: str = "",
) -> dict:
    """
    Process one user question through the full mentor pipeline.

    Parameters
    ----------
    session        : MentorSession (holds ctx + conversation history)
    question       : current user question
    groq_client    : Groq API client (fallback for intent classification)
    gpt_oss_client : GPT-OSS client (primary for intent classification)
    granite_client : IBM Granite ModelInference (for synthesis)
    embedder       : SentenceTransformer instance
    collection     : ChromaDB collection
    tavily_client  : TavilyClient instance
    blueprint_id   : DB row id of the source blueprint (for persistence)
    user_email     : user's email (for persistence)

    Returns
    -------
    dict with:
        answer       : markdown-formatted answer string
        intent       : detected intent code
        sub_topic    : 3-5 word topic
        citations    : list of citation strings
        tools_used   : list of tool names that ran
        session_id   : session identifier
    """
    ctx = session.ctx

    # ── 0. Save user message to session ───────────────────────────────────────
    user_msg = MentorMessage(role="user", content=question)
    session.add_message(user_msg)

    # Ensure session is persisted in DB on first message
    if session.message_count == 1:
        _ensure_session_persisted(session, blueprint_id, user_email, ctx)

    # ── 1. Classify intent ────────────────────────────────────────────────────
    conversation_tail = session.build_conversation_tail(n_turns=2)
    intent_result = classify_intent(
        question=question,
        conversation_tail=conversation_tail,
        groq_client=groq_client,
        gpt_oss_client=gpt_oss_client,
    )
    intent    = intent_result["intent"]
    sub_topic = intent_result["sub_topic"]

    # ── 2. Route & retrieve evidence ──────────────────────────────────────────
    evidence = route_tools(
        question=question,
        intent=intent,
        sub_topic=sub_topic,
        ctx=ctx,
        session=session,
        embedder=embedder,
        collection=collection,
        tavily_client=tavily_client,
    )

    # ── 3. Synthesize grounded answer ─────────────────────────────────────────
    conversation_history = session.build_chat_history_for_prompt()
    is_roadmap = intent == "EXECUTION_ROADMAP" or any(
        kw in question.lower()
        for kw in ["roadmap", "month by month", "6 month", "12 month", "execution plan", "timeline"]
    )

    answer = synthesize_answer(
        question=question,
        intent=intent,
        sub_topic=sub_topic,
        blueprint_context=evidence["blueprint_text"],
        chromadb_context=evidence["chromadb_text"],
        tavily_context=evidence["tavily_text"],
        conversation_history=conversation_history,
        granite_client=granite_client,
        is_roadmap=is_roadmap,
    )

    # ── 4. Save assistant message to session and DB ───────────────────────────
    assistant_msg = MentorMessage(
        role="assistant",
        content=answer,
        intent=intent,
        citations=evidence["all_citations"],
        tools_used=evidence["tools_used"],
    )
    session.add_message(assistant_msg)

    # Persist both messages to DB
    save_mentor_message(
        session_id=session.session_id,
        role="user",
        content=question,
        intent=intent,
    )
    save_mentor_message(
        session_id=session.session_id,
        role="assistant",
        content=answer,
        intent=intent,
        citations=evidence["all_citations"],
        tools_used=evidence["tools_used"],
    )

    return {
        "answer":     answer,
        "intent":     intent,
        "sub_topic":  sub_topic,
        "citations":  evidence["all_citations"],
        "tools_used": evidence["tools_used"],
        "session_id": session.session_id,
    }


def create_session(ctx: dict, session_id: str | None = None) -> object:
    """
    Factory to create a new MentorSession from a MentorContext dict.

    Parameters
    ----------
    ctx        : MentorContext dict from mentor.context.build_mentor_context()
    session_id : optional — if None a UUID is generated

    Returns
    -------
    MentorSession instance
    """
    from mentor.memory import MentorSession
    sid = session_id or str(uuid.uuid4())
    return MentorSession(ctx=ctx, session_id=sid, window_size=6)


def _ensure_session_persisted(
    session, blueprint_id: int | None, user_email: str, ctx: dict
) -> None:
    """Upsert the session row in mentor_sessions table."""
    try:
        save_mentor_session(
            session_id=session.session_id,
            blueprint_id=blueprint_id,
            user_email=user_email,
            sector=ctx.get("sector", ""),
            stage=ctx.get("stage", ""),
        )
    except Exception as e:
        print(f"[MentorAgent] Session persist error: {e}")
