"""
main.py — FastAPI application entry point.

Startup sequence:
  1. Download ChromaDB from HuggingFace Hub (if not cached locally)
  2. Initialise all AI clients (Granite, Groq, Gemini, Tavily, CrossEncoder)
  3. Load ChromaDB collections (text_chunks, table_data, visual_summaries)
  4. Register all routes
  5. Start serving requests

Run locally:
    cd backend
    uvicorn main:app --reload --port 8000

Run on Railway:
    uvicorn main:app --host 0.0.0.0 --port $PORT
"""

import logging
import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Add core/ to sys.path so all existing Python modules are importable ───────
BACKEND_DIR = os.path.dirname(__file__)
CORE_DIR    = os.path.join(BACKEND_DIR, "core")
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, CORE_DIR)

# ── Load .env into os.environ (needed by history_db.py and other core modules) ─
load_dotenv(os.path.join(BACKEND_DIR, "..", ".env"))

from config import get_settings
from chroma_loader import download_chroma_if_needed
from dependencies import init_all_clients
from routes import auth_router, blueprint_router, mentor_router, history_router, deep_research_router, lock_in_router

settings = get_settings()


# ══════════════════════════════════════════════════════════════════════════════
# LIFESPAN — startup + shutdown logic
# ══════════════════════════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ───────────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    log.info(f"  Environment : {settings.ENVIRONMENT}")
    log.info("=" * 60)

    # Step 1: Download ChromaDB from HuggingFace if needed
    log.info("Step 1/3 — Checking ChromaDB…")
    download_chroma_if_needed(
        repo_id=settings.HF_CHROMA_REPO,
        local_dir=settings.CHROMA_LOCAL_PATH,
        hf_token=settings.HF_TOKEN,
    )

    # Step 2: Initialise all AI clients (loads into module-level singletons)
    log.info("Step 2/3 — Initialising AI clients…")
    init_all_clients(settings)

    # Step 3/4 — Initialize database tables
    log.info("Step 3/4 — Initialising LOCK IN tables…")
    try:
        from lock_in_db import init_tables as init_lockin_tables
        init_lockin_tables()
    except Exception as e:
        log.warning(f"Could not initialize LOCK IN tables on startup: {e}")

    # Step 4/4 — Start background scheduler
    log.info("Step 4/4 — Starting LOCK IN AI Scheduler…")
    try:
        from lock_in_scheduler import start_scheduler, shutdown_scheduler
        start_scheduler()
    except Exception as e:
        log.warning(f"Could not start background scheduler: {e}")

    log.info("All systems ready. Accepting requests.")
    log.info("=" * 60)

    yield   # ← app runs here

    # ── SHUTDOWN ──────────────────────────────────────────────────────────────
    log.info("Shutting down — cleaning up resources…")
    try:
        from lock_in_scheduler import shutdown_scheduler
        shutdown_scheduler()
    except Exception as e:
        log.warning(f"Error shutting down scheduler: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# APP FACTORY
# ══════════════════════════════════════════════════════════════════════════════
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI-powered startup blueprint generator. "
        "Built with IBM Granite 4.0, Groq Llama 3.3, Gemini Flash, and C-RAG."
    ),
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,   # hide Swagger in prod
    redoc_url="/redoc" if not settings.is_production else None,
)


# ── Middleware ─────────────────────────────────────────────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "X-Request-ID"],
)


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(blueprint_router)
app.include_router(mentor_router)
app.include_router(history_router)
app.include_router(deep_research_router)
app.include_router(lock_in_router)


# ── Health / meta endpoints ───────────────────────────────────────────────────
@app.get("/api/health", tags=["meta"])
async def health():
    """Railway uses this for health checks — must return 200."""
    return {
        "status":  "ok",
        "version": settings.APP_VERSION,
        "env":     settings.ENVIRONMENT,
    }


@app.get("/api/config/public", tags=["meta"])
async def public_config():
    """
    Non-secret config the frontend needs at startup:
    Supabase URL + anon key (safe to expose — that's what they're for),
    and the Google OAuth client ID.
    """
    return {
        "supabase_url":      settings.SUPABASE_URL,
        "supabase_anon_key": settings.SUPABASE_KEY,
    }


# ── Global error handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    log.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


# ── Dev entrypoint ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=not settings.is_production,
        log_level="info",
    )