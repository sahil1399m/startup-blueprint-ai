"""
config.py — Centralised settings for the FastAPI backend.

All secrets are read from environment variables.
On Railway, set these in the Variables tab.
Locally, put them in backend/.env (loaded by python-dotenv).
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "Startup Blueprint Generator API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"          # "production" on Railway
    FRONTEND_URL: str = "http://localhost:5173"  # Vite dev server (overridden on Railway)

    # ── HuggingFace ──────────────────────────────────────────────────────────
    HF_TOKEN: str = ""
    HF_CHROMA_REPO: str = "sahilsks/startup-blueprint-chroma-db"
    CHROMA_LOCAL_PATH: str = "./chroma_db"    # where to store after download

    # ── IBM Watsonx ──────────────────────────────────────────────────────────
    IBM_API_KEY: str = ""
    IBM_URL: str = "https://us-south.ml.cloud.ibm.com"
    IBM_PROJECT_ID: str = ""

    # ── Groq ─────────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = ""

    # ── Google Gemini ─────────────────────────────────────────────────────────
    GOOGLE_API_KEY: str = ""

    # ── Tavily ───────────────────────────────────────────────────────────────
    TAVILY_API_KEY: str = ""

    # ── News API ─────────────────────────────────────────────────────────────
    NEWS_API_KEY: str = ""

    # ── Supabase / PostgreSQL ─────────────────────────────────────────────────
    DB_HOST: str = ""
    DB_PORT: str = "5432"
    DB_NAME: str = ""
    DB_USER: str = ""
    DB_PASSWORD: str = ""

    # ── JWT (for Supabase auth tokens we validate) ───────────────────────────
    SUPABASE_JWT_SECRET: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""          # anon/public key — matches your existing .env

    # ── Google OAuth & Gmail ──────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/lock-in/gmail/callback"

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins, e.g.
    # "http://localhost:5173,https://your-vercel-app.vercel.app"
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings — reads env vars once, reuses everywhere."""
    return Settings()