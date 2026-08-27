"""
routes/blueprint.py — Blueprint generation endpoints.

POST /api/blueprint/generate         → SSE stream of CRAG + generation progress
GET  /api/blueprint/{blueprint_id}   → fetch a single saved blueprint
GET  /api/blueprint/news             → live startup news (public)
"""

from __future__ import annotations
import json
import logging
from datetime import datetime
from typing import AsyncGenerator, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from auth_middleware import get_current_user
from config import get_settings
from dependencies import (
    get_collections,
    get_gemini,
    get_granite,
    get_groq,
    get_gpt_oss,
    get_reranker,
    get_tavily,
)
from models.blueprint import BlueprintRequest, BlueprintResponse, SSEEvent

log      = logging.getLogger(__name__)
router   = APIRouter(prefix="/api/blueprint", tags=["blueprint"])
settings = get_settings()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _sse(event: str, step: str = "", node: str = "",
         progress: int = 0, data=None, error: str = "") -> str:
    """Format a single SSE frame."""
    payload = SSEEvent(
        event=event, step=step, node=node,
        progress=progress, data=data, error=error,
    ).model_dump(mode="json")
    return f"data: {json.dumps(payload)}\n\n"


async def _stream_blueprint(
    body: BlueprintRequest,
    user: Dict,
    collections: Dict,
    reranker,
    granite,
    tavily,
    groq_client,
    gemini,
    gpt_oss,
) -> AsyncGenerator[str, None]:
    """
    Async generator that runs the CRAG pipeline and yields SSE frames.
    The frontend reads these frames to show a real-time progress bar.
    """
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))

    try:
        # ── Step 1: Query rewriting (Gemini Flash) ────────────────────────────
        yield _sse("progress", step="Rewriting query with Gemini Flash…",
                   node="rewrite_query", progress=8)

        from crag import run_crag
        # run_crag is CPU/IO-bound — run in a thread so we don't block the event loop
        import asyncio
        loop = asyncio.get_event_loop()

        # We use a mutable dict to pass partial progress updates out of the thread
        progress_updates = []

        def _run():
            return run_crag(
                query=body.idea,
                sector=body.sector,
                stage=body.stage,
                model_type=body.model_type,
                target_city=body.target_city,
                collections=collections,
                reranker=reranker,
                granite=granite,
                tavily=tavily,
                groq_client=groq_client,
                gemini_client=gemini,
                gpt_oss_client=gpt_oss,
            )

        # ── Step 2: Retrieval ─────────────────────────────────────────────────
        yield _sse("progress", step="Retrieving from ChromaDB (text + table + visual)…",
                   node="retrieve", progress=18)

        # ── Step 3: Grading ───────────────────────────────────────────────────
        yield _sse("progress", step="CrossEncoder grading retrieved chunks…",
                   node="eval_each_doc", progress=28)

        # Run the full CRAG pipeline in a thread pool
        crag_result = await loop.run_in_executor(None, _run)

        confidence = crag_result["confidence"]

        # ── Step 4: Branch-specific message ──────────────────────────────────
        branch_msgs = {
            "CORRECT":   ("Refining PDF context (sentence strips)…",  "refine"),
            "AMBIGUOUS": ("Combining PDF + Tavily web search…",        "web_search"),
            "INCORRECT": ("PDF insufficient — searching live web…",    "web_search"),
        }
        msg, node = branch_msgs.get(confidence, ("Processing…", "branch"))
        yield _sse("progress", step=msg, node=node, progress=45)

        # ── Step 5: IBM Granite policy summary ───────────────────────────────
        if crag_result["should_generate_blueprint"]:
            yield _sse("progress", step="IBM Granite 4.0 synthesizing policy brief…",
                       node="generate", progress=55)

        # ── Step 6: Groq blueprint sections ──────────────────────────────────
        blueprint_data = {}
        if crag_result["should_generate_blueprint"]:
            yield _sse("progress", step="Groq generating Business Model Canvas…",
                       node="generate_bmc", progress=62)
            yield _sse("progress", step="Groq generating budget estimate…",
                       node="generate_budget", progress=70)
            yield _sse("progress", step="Groq generating Go-to-Market strategy…",
                       node="generate_gtm", progress=76)
            yield _sse("progress", step="Groq generating investor & scheme matches…",
                       node="generate_investors", progress=82)
            yield _sse("progress", step="Groq generating competitor analysis…",
                       node="generate_competitors", progress=88)
            yield _sse("progress", step="Groq generating risk assessment…",
                       node="generate_risks", progress=93)

            bp = crag_result.get("blueprint", {})
            blueprint_data = {
                "bmc":         bp.get("bmc", {}),
                "budget":      bp.get("budget", {}),
                "gtm":         bp.get("gtm", {}),
                "investors":   bp.get("investors", {}),
                "competitors": bp.get("competitors", {}),
                "risks":       bp.get("risks", {}),
                "crag_trace":  bp.get("crag_trace", {}),
            }

        # ── Step 7: Save to history ───────────────────────────────────────────
        yield _sse("progress", step="Saving blueprint to history…",
                   node="save", progress=97)

        blueprint_id = None
        try:
            from history import save_blueprint_to_history
            blueprint_id = save_blueprint_to_history(
                idea=body.idea, sector=body.sector, stage=body.stage,
                business_model=body.model_type, market=body.target_city,
                user_email=user["email"], crag_result=crag_result,
                bmc_data=blueprint_data.get("bmc", {}),
                budget_data=blueprint_data.get("budget", {}),
                gtm_data=blueprint_data.get("gtm", {}),
                investor_data=blueprint_data.get("investors", {}),
                competitor_data=blueprint_data.get("competitors", {}),
                risk_data=blueprint_data.get("risks", {}),
                explore_results=crag_result.get("explore_results", []),
            )
        except Exception as e:
            log.warning(f"Failed to save blueprint to history: {e}")

        # ── Step 8: Complete ──────────────────────────────────────────────────
        response = BlueprintResponse(
            blueprint_id=blueprint_id,
            idea=body.idea,
            sector=body.sector,
            model_type=body.model_type,
            stage=body.stage,
            target_city=body.target_city,
            crag_result=crag_result,
            blueprint=blueprint_data,
            generated_at=datetime.utcnow().isoformat(),
        )
        yield _sse("complete", step="Blueprint ready!", progress=100,
                   data=response.model_dump(mode="json"))

    except Exception as e:
        log.error(f"Blueprint generation failed: {e}", exc_info=True)
        yield _sse("error", error=str(e), progress=0)


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/generate")
async def generate_blueprint(
    body: BlueprintRequest,
    current_user: Dict = Depends(get_current_user),
    collections  = Depends(get_collections),
    reranker     = Depends(get_reranker),
    granite      = Depends(get_granite),
    tavily       = Depends(get_tavily),
    groq_client  = Depends(get_groq),
    gemini       = Depends(get_gemini),
    gpt_oss      = Depends(get_gpt_oss),
):
    """
    Stream blueprint generation progress as Server-Sent Events.

    Frontend connects with:
        const es = new EventSource('/api/blueprint/generate', { method: 'POST', ... })
    Or more practically, uses fetch() + ReadableStream to read the SSE response.

    Each SSE frame is a JSON object matching the SSEEvent schema:
        { event, step, node, progress, data, error }
    """
    return StreamingResponse(
        _stream_blueprint(
            body=body,
            user=current_user,
            collections=collections,
            reranker=reranker,
            granite=granite,
            tavily=tavily,
            groq_client=groq_client,
            gemini=gemini,
            gpt_oss=gpt_oss,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control":      "no-cache",
            "X-Accel-Buffering":  "no",    # disable Nginx buffering (Railway)
            "Connection":         "keep-alive",
        },
    )


@router.get("/{blueprint_id}", response_model=BlueprintResponse)
async def get_blueprint(
    blueprint_id: int,
    current_user: Dict = Depends(get_current_user),
):
    """Fetch a saved blueprint by ID (user must own it)."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))

    try:
        from history import load_blueprint_for_display
        bp = load_blueprint_for_display(blueprint_id)
        if not bp or (bp.get("user_email") and bp.get("user_email").lower() != current_user["email"].lower()):
            raise HTTPException(status_code=404, detail="Blueprint not found")
        return bp
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news/feed")
async def get_news(q: str = "India startup funding"):
    """Live startup news — public endpoint (no auth required)."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))

    try:
        from news_feed import get_startup_news
        articles = get_startup_news(settings.NEWS_API_KEY, query=q, page_size=9)
        return {"articles": articles}
    except Exception as e:
        log.warning(f"News fetch failed: {e}")
        return {"articles": []}