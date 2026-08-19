"""Routes package — import all routers here for clean registration in main.py."""
from .auth import router as auth_router
from .blueprint import router as blueprint_router
from .mentor import router as mentor_router
from .history import router as history_router
from .deep_research import router as deep_research_router
from .lock_in import router as lock_in_router

__all__ = [
    "auth_router",
    "blueprint_router",
    "mentor_router",
    "history_router",
    "deep_research_router",
    "lock_in_router",
]