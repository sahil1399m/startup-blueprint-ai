"""
mentor/mentor_agent.py
───────────────────────
Main orchestrator for the AI Startup Mentor.

Flow per user question:
  1. Classify intent (GPT-OSS via IBM watsonx, fallback to Groq)
  2. Route to tools (blueprint + optional chromadb + optional tavily)
  3. Synthesize grounded answer (Groq GPT-OSS-120B primary, IBM Granite fallback)
  4. Persist to mentor_db (PostgreSQL/Supabase)
  5. Return structured response

Entry point:  ask(session, question, ...)
"""

from __future__ import annotations
import logging
import time
import uuid
from datetime import datetime

from mentor.intent_classifier import classify_intent
from mentor.tool_router        import route_tools
from mentor.synthesizer        import synthesize_answer
from mentor.memory             import MentorMessage
from mentor.mentor_db          import save_mentor_session, save_mentor_message

log = logging.getLogger(__name__)


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
    groq_client    : Groq API client (PRIMARY for synthesis)
    gpt_oss_client : GPT-OSS via IBM watsonx (intent classification primary)
    granite_client : IBM Granite ModelInference (synthesis fallback)
    embedder       : SentenceTransformer instance (unused — chromadb uses gemini)
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
    t_start = time.time()
    ctx = session.ctx

    log.info(f"[MENTOR] Request received | blueprint_id={blueprint_id} | question_len={len(question)}")

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

    log.info(f"[MENTOR] Intent: {intent} | sub_topic: {sub_topic}")

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

    retrieval_used = bool(evidence.get("chromadb_text") or evidence.get("tavily_text"))
    log.info(
        f"[MENTOR] Context sections: {list(evidence.keys())} | "
        f"Retrieval required: {retrieval_used} | "
        f"Tools used: {evidence.get('tools_used', [])}"
    )

    blueprint_text   = evidence["blueprint_text"]
    chromadb_text    = evidence["chromadb_text"]
    tavily_text      = evidence["tavily_text"]
    input_ctx_size   = len(blueprint_text) + len(chromadb_text) + len(tavily_text)

    log.info(f"[MENTOR] Model: GPT-OSS-120B | Provider: Groq | Input context size: ~{input_ctx_size} chars")

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
        blueprint_context=blueprint_text,
        chromadb_context=chromadb_text,
        tavily_context=tavily_text,
        conversation_history=conversation_history,
        granite_client=granite_client,
        groq_client=groq_client,
        is_roadmap=is_roadmap,
    )

    t_elapsed = time.time() - t_start
    log.info(f"[MENTOR] Generation completed in {t_elapsed:.1f}s | answer_len={len(answer)}")

    # ── 4. Save assistant message to session and DB ───────────────────────────
    assistant_msg = MentorMessage(
        role="assistant",
        content=answer,
        intent=intent,
        citations=evidence["all_citations"],
        tools_used=evidence["tools_used"],
    )
    session.add_message(assistant_msg)

    # Persist both messages to DB (non-fatal if DB is unavailable)
    try:
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
    except Exception as db_err:
        log.warning(f"[MENTOR] DB persistence failed (non-fatal): {db_err}")

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
    """Upsert the session row in mentor_sessions table (non-fatal)."""
    try:
        save_mentor_session(
            session_id=session.session_id,
            blueprint_id=blueprint_id,
            user_email=user_email,
            sector=ctx.get("sector", ""),
            stage=ctx.get("stage", ""),
        )
    except Exception as e:
        log.warning(f"[MENTOR] Session persist error (non-fatal): {e}")
