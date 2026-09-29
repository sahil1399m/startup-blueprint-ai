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
    investor_data, competitor_data, risk_data, crag_trace_data=None,
    explore_results=None, failed_sections=None, status="success",
) -> int:
    explore_results = explore_results or []
    sections: dict[str, Any] = {
        "status":            status,
        "failed_sections":   failed_sections or [],
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
        "funding":           investor_data,
        "competitors":       competitor_data,
        "risks":             risk_data,
        "crag_trace":        crag_trace_data or {},
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
    sources_list = [s["name"] for s in bp.get("sources", []) if s.get("name")]
    bmc = sec.get("bmc", {})
    budget = sec.get("budget", {})
    gtm = sec.get("gtm", {})
    investors = sec.get("investors") or sec.get("funding") or {}
    competitors = sec.get("competitors", {})
    risks = sec.get("risks", {})
    crag_trace = sec.get("crag_trace", {})

    crag_result = {
        "confidence":        sec.get("crag_confidence", bp.get("confidence", "")),
        "action":            sec.get("crag_action", ""),
        "summary":           sec.get("granite_summary", ""),
        "raw_logits":        sec.get("crag_raw_logits", []),
        "keywords":          sec.get("crag_keywords", []),
        "retrieval_queries": sec.get("retrieval_queries", []),
        "internal_context":  sec.get("internal_context", ""),
        "external_context":  sec.get("external_context", ""),
        "rewritten_query":   bp.get("rewritten_query", ""),
        "explore_results":   sec.get("explore_results", []),
        "sources":           sources_list,
    }

    blueprint_data = {
        "bmc":         bmc,
        "budget":      budget,
        "gtm":         gtm,
        "investors":   investors,
        "funding":     investors,
        "competitors": competitors,
        "risks":       risks,
        "crag_trace":  crag_trace,
    }

    return {
        "id":                bp["id"],
        "blueprint_id":      bp["id"],
        "title":             bp["title"],
        "original_query":    bp["original_query"],
        "idea":              bp["original_query"],
        "sector":            bp["sector"],
        "stage":             bp["stage"],
        "business_model":    bp["business_model"],
        "model_type":        bp["business_model"],
        "market":            bp["market"],
        "target_city":       bp["market"],
        "timestamp":         bp["timestamp"],
        "generated_at":      bp["timestamp"],
        "status":            sec.get("status", "success"),
        "failed_sections":   sec.get("failed_sections", []),
        "is_favorite":       bool(bp.get("is_favorite", 0)),
        "user_email":        bp.get("user_email", ""),
        "confidence":        crag_result["confidence"],
        "action":            crag_result["action"],
        "raw_logits":        crag_result["raw_logits"],
        "keywords":          crag_result["keywords"],
        "retrieval_queries": crag_result["retrieval_queries"],
        "internal_context":  crag_result["internal_context"],
        "external_context":  crag_result["external_context"],
        "rewritten_query":   bp.get("rewritten_query", ""),
        "summary":           crag_result["summary"],
        "blueprint":          blueprint_data,
        "bmc_data":          bmc,
        "budget_data":       budget,
        "gtm_data":          gtm,
        "investor_data":     investors,
        "funding_data":      investors,
        "investor_data":     investors,
        "competitor_data":   competitors,
        "risk_data":         risks,
        "explore_results":   sec.get("explore_results", []),
        "sources":           sources_list,
        "source_links":      bp.get("sources", []),
        "blueprint":         blueprint_data,
        "crag_result":       crag_result,
    }


# Re-exports
list_blueprints       = history_db.list_blueprints
search_blueprints     = history_db.search_blueprints
delete_blueprint      = history_db.delete_blueprint
delete_all_blueprints = history_db.delete_all_blueprints
toggle_favorite       = history_db.toggle_favorite
