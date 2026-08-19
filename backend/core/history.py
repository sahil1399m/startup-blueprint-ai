"""
history.py  — Bridge between app.py and history_db.py.
No Streamlit imports — pure data logic only.
"""

from __future__ import annotations
from typing import Any
import history_db


def _make_title(idea: str, max_len: int = 72) -> str:
    first = next(
        (line.strip() for line in idea.splitlines() if line.strip()), idea.strip()
    )
    for sep in (".", "!", "?"):
        if sep in first:
            first = first.split(sep)[0].strip()
            break
    if len(first) > max_len:
        first = first[:max_len].rsplit(" ", 1)[0] + "…"
    return first or "Untitled Blueprint"


def _build_sources(crag_result: dict, explore_results: list) -> list:
    sources = []
    for src in crag_result.get("sources", []):
        if src != "tavily_web_search":
            sources.append({"name": src, "url": ""})
    for r in explore_results:
        sources.append({"name": r.get("title", "Web"), "url": r.get("url", "")})
    return sources


def save_blueprint_to_history(
    *, idea, sector, stage, business_model, market, user_email,
    crag_result, bmc_data, budget_data, gtm_data,
    investor_data, competitor_data, risk_data, explore_results=None,
) -> int:
    explore_results = explore_results or []
    sections: dict[str, Any] = {
        "granite_summary":   crag_result.get("summary", ""),
        "crag_confidence":   crag_result.get("confidence", ""),
        "crag_action":       crag_result.get("action", ""),
        "crag_raw_logits":   crag_result.get("raw_logits", []),
        "crag_keywords":     crag_result.get("keywords", []),
        "retrieval_queries": crag_result.get("retrieval_queries", []),
        "internal_context":  crag_result.get("internal_context", ""),
        "external_context":  crag_result.get("external_context", ""),
        "bmc":               bmc_data,
        "budget":            budget_data,
        "gtm":               gtm_data,
        "investors":         investor_data,
        "competitors":       competitor_data,
        "risks":             risk_data,
        "explore_results":   explore_results,
    }
    return history_db.save_blueprint(
        title=_make_title(idea),
        original_query=idea,
        rewritten_query=crag_result.get("rewritten_query", ""),
        sector=sector, stage=stage, business_model=business_model, market=market,
        confidence=crag_result.get("confidence", ""),
        user_email=user_email,
        sections=sections,
        sources=_build_sources(crag_result, explore_results),
    )


def load_blueprint_for_display(blueprint_id: int) -> dict | None:
    bp = history_db.get_blueprint(blueprint_id)
    if bp is None:
        return None
    sec = bp.get("sections", {})
    return {
        "id":              bp["id"],
        "title":           bp["title"],
        "original_query":  bp["original_query"],
        "sector":          bp["sector"],
        "stage":           bp["stage"],
        "business_model":  bp["business_model"],
        "market":          bp["market"],
        "timestamp":       bp["timestamp"],
        "is_favorite":     bool(bp.get("is_favorite", 0)),
        "user_email":      bp.get("user_email", ""),
        "confidence":      sec.get("crag_confidence", bp.get("confidence", "")),
        "action":          sec.get("crag_action", ""),
        "raw_logits":      sec.get("crag_raw_logits", []),
        "keywords":        sec.get("crag_keywords", []),
        "retrieval_queries": sec.get("retrieval_queries", []),
        "internal_context":  sec.get("internal_context", ""),
        "external_context":  sec.get("external_context", ""),
        "rewritten_query": bp.get("rewritten_query", ""),
        "summary":         sec.get("granite_summary", ""),
        "bmc_data":        sec.get("bmc", {}),
        "budget_data":     sec.get("budget", {}),
        "gtm_data":        sec.get("gtm", {}),
        "investor_data":   sec.get("investors", {}),
        "competitor_data": sec.get("competitors", {}),
        "risk_data":       sec.get("risks", {}),
        "explore_results": sec.get("explore_results", []),
        "sources":         [s["name"] for s in bp.get("sources", []) if s.get("name")],
        "source_links":    bp.get("sources", []),
    }


# Re-exports
list_blueprints       = history_db.list_blueprints
search_blueprints     = history_db.search_blueprints
delete_blueprint      = history_db.delete_blueprint
delete_all_blueprints = history_db.delete_all_blueprints
toggle_favorite       = history_db.toggle_favorite
