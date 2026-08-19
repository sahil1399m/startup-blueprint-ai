"""
routes/history.py — Blueprint history CRUD endpoints.

GET    /api/history              → list all blueprints for current user
GET    /api/history/{id}         → get one blueprint
DELETE /api/history/{id}         → delete one blueprint
DELETE /api/history              → delete all blueprints for user
GET    /api/history/{id}/export  → export as JSON
"""

from __future__ import annotations
import logging
import sys
import os
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query

from auth_middleware import get_current_user

log    = logging.getLogger(__name__)
router = APIRouter(prefix="/api/history", tags=["history"])

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))


@router.get("")
async def list_history(
    current_user: Dict = Depends(get_current_user),
    search: str = Query(default="", description="Filter by idea text"),
    limit: int  = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List all blueprints for the current user, newest first."""
    try:
        from history_db import list_blueprints, search_blueprints
        if search:
            blueprints = search_blueprints(search, user_email=current_user["email"])
        else:
            blueprints = list_blueprints(user_email=current_user["email"])
        # Apply limit/offset
        blueprints = blueprints[offset:offset + limit]
        return {
            "blueprints": blueprints,
            "total": len(blueprints),
        }
    except Exception as e:
        log.error(f"Failed to list history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{blueprint_id}")
async def get_history_item(
    blueprint_id: int,
    current_user: Dict = Depends(get_current_user),
):
    """Get a single blueprint by ID (user must own it)."""
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


@router.delete("/{blueprint_id}", status_code=204)
async def delete_history_item(
    blueprint_id: int,
    current_user: Dict = Depends(get_current_user),
):
    """Delete a single blueprint (user must own it)."""
    try:
        from history_db import delete_blueprint
        deleted = delete_blueprint(blueprint_id, current_user["email"])
        if not deleted:
            raise HTTPException(status_code=404, detail="Blueprint not found or already deleted")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return None


@router.delete("", status_code=204)
async def delete_all_history(
    current_user: Dict = Depends(get_current_user),
):
    """Delete ALL blueprints for the current user."""
    try:
        from history_db import delete_all_blueprints_for_user
        delete_all_blueprints_for_user(current_user["email"])
    except Exception as e:
        log.error(f"Failed to delete all history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    return None


@router.get("/{blueprint_id}/export")
async def export_blueprint(
    blueprint_id: int,
    current_user: Dict = Depends(get_current_user),
):
    """Export a blueprint as a downloadable JSON file (user must own it)."""
    try:
        from history import load_blueprint_for_display
        bp = load_blueprint_for_display(blueprint_id)
        if not bp or (bp.get("user_email") and bp.get("user_email").lower() != current_user["email"].lower()):
            raise HTTPException(status_code=404, detail="Blueprint not found")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content=bp,
            headers={"Content-Disposition": f"attachment; filename=blueprint_{blueprint_id}.json"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))