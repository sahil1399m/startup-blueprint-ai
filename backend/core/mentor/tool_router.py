"""
mentor/tool_router.py
──────────────────────
Maps detected intent → which tools to call and what query to use.

Strategy per intent:
  ALWAYS  → blueprint_tool   (zero-latency, always available)
  OFTEN   → chromadb_tool    (PDF policy docs)
  SOMETIMES → tavily_tool    (live web, used for current data)

The router builds intent-specific search queries for ChromaDB and Tavily
so they retrieve the most relevant content for each question type.
"""

from __future__ import annotations


# ── Tool usage plan per intent ─────────────────────────────────────────────────
# (blueprint_tool always runs; flags here control chromadb and tavily)

_TOOL_PLAN = {
    #                              chromadb  tavily
    "MARKET_VALIDATION":    dict(chromadb=True,  tavily=True),
    "FUNDING":              dict(chromadb=True,  tavily=True),
    "LEGAL":                dict(chromadb=True,  tavily=False),
    "TECHNOLOGY":           dict(chromadb=False, tavily=True),
    "COMPETITOR":           dict(chromadb=False, tavily=True),
    "MARKETING":            dict(chromadb=False, tavily=True),
    "GTM":                  dict(chromadb=True,  tavily=True),
    "FINANCIAL":            dict(chromadb=False, tavily=False),  # blueprint is sufficient
    "HIRING":               dict(chromadb=False, tavily=False),
    "PRODUCT_DEVELOPMENT":  dict(chromadb=False, tavily=True),
    "GOVT_SCHEMES":         dict(chromadb=True,  tavily=True),
    "RISK_ANALYSIS":        dict(chromadb=False, tavily=True),
    "INVESTOR_PREP":        dict(chromadb=True,  tavily=True),
    "EXECUTION_ROADMAP":    dict(chromadb=True,  tavily=False),
    "GENERAL":              dict(chromadb=True,  tavily=False),
}

# ── Query builders for each tool + intent ─────────────────────────────────────

def _build_chromadb_query(question: str, intent: str, ctx: dict) -> str:
    """Build an enriched query for ChromaDB retrieval."""
    sector = ctx.get("sector", "startup")
    stage  = ctx.get("stage",  "early-stage")
    idea   = ctx.get("original_idea", "")[:100]

    prefixes = {
        "MARKET_VALIDATION":  f"market size TAM SAM SOM {sector} India",
        "FUNDING":            f"startup funding seed round {sector} India government scheme",
        "LEGAL":              f"legal compliance registration {sector} India startup",
        "GTM":                f"go-to-market strategy launch {sector} India",
        "GOVT_SCHEMES":       f"government scheme DPIIT MSME startup India {sector}",
        "INVESTOR_PREP":      f"investor pitch due diligence startup India {stage}",
        "EXECUTION_ROADMAP":  f"execution plan roadmap startup India {sector} {stage}",
        "GENERAL":            f"startup India {sector}",
    }
    prefix = prefixes.get(intent, f"{sector} startup India")
    return f"{prefix}: {question}"


def _build_tavily_query(question: str, intent: str, ctx: dict) -> str:
    """Build an enriched query for Tavily web search."""
    sector = ctx.get("sector", "startup")

    # For competitor intent, include specific competitor names
    if intent == "COMPETITOR":
        comp_names = [
            c.get("name", "") 
            for c in ctx.get("competitors", {}).get("list", [])
            if c.get("name", "") != "Our Startup"
        ][:2]
        comp_str = " ".join(comp_names)
        return f"{question} {comp_str} {sector} India competitor analysis"

    prefixes = {
        "MARKET_VALIDATION":  f"India {sector} market size 2024 2025",
        "FUNDING":            f"startup funding {sector} India 2024 investors",
        "TECHNOLOGY":         f"{sector} startup technology stack India 2024",
        "MARKETING":          f"startup marketing strategy {sector} India",
        "GTM":                f"go-to-market {sector} India startup launch",
        "PRODUCT_DEVELOPMENT": f"MVP product development {sector} startup India",
        "GOVT_SCHEMES":       f"government scheme startup India DPIIT MSME 2024",
        "RISK_ANALYSIS":      f"startup risks challenges {sector} India 2024",
        "INVESTOR_PREP":      f"startup pitch investor questions {sector} India",
    }
    prefix = prefixes.get(intent, f"startup India {sector} 2024")
    return f"{prefix}: {question}"


# ── Main router function ───────────────────────────────────────────────────────

def route_tools(
    *,
    question: str,
    intent: str,
    sub_topic: str,
    ctx: dict,
    session,                  # MentorSession
    embedder,
    collection,
    tavily_client,
) -> dict:
    """
    Execute the appropriate tools for this intent and return aggregated evidence.

    Returns
    -------
    dict with:
        blueprint_text   : str from blueprint_tool
        chromadb_text    : str from chromadb_tool (or "")
        tavily_text      : str from tavily_tool (or "")
        all_citations    : list of citation strings
        tools_used       : list of tool names that ran
    """
    from mentor.tools.blueprint_tool import search_blueprint
    from mentor.tools.chromadb_tool  import search_chromadb
    from mentor.tools.tavily_tool    import search_tavily

    plan       = _TOOL_PLAN.get(intent, _TOOL_PLAN["GENERAL"])
    tools_used = ["blueprint"]

    # ── 1. Blueprint tool (always) ─────────────────────────────────────────────
    bp_result    = search_blueprint(ctx, intent, question)
    blueprint_text = "\n\n".join(bp_result["sections"].values())
    all_citations  = list(bp_result["citations"])

    # ── 2. ChromaDB tool ──────────────────────────────────────────────────────
    chromadb_text = ""
    if plan["chromadb"]:
        chroma_query = _build_chromadb_query(question, intent, ctx)
        # Check session cache first
        cached = session.cache_get("chromadb", chroma_query)
        if cached is not None:
            chroma_result = cached
        else:
            chroma_result = search_chromadb(chroma_query, embedder, collection, n_results=5)
            session.cache_set("chromadb", chroma_query, chroma_result)
        chromadb_text = chroma_result["context"]
        all_citations.extend(chroma_result["citations"])
        tools_used.append("chromadb")

    # ── 3. Tavily tool ─────────────────────────────────────────────────────────
    tavily_text = ""
    if plan["tavily"] and tavily_client is not None:
        tavily_query = _build_tavily_query(question, intent, ctx)
        cached = session.cache_get("tavily", tavily_query)
        if cached is not None:
            tavily_result = cached
        else:
            sector = ctx.get("sector", "startup")
            tavily_result = search_tavily(tavily_query, intent, sector, tavily_client, max_results=4)
            session.cache_set("tavily", tavily_query, tavily_result)
        tavily_text = tavily_result["context"]
        all_citations.extend(tavily_result["citations"])
        tools_used.append("tavily")

    # Deduplicate citations
    seen = set()
    unique_citations = []
    for c in all_citations:
        if c not in seen:
            seen.add(c)
            unique_citations.append(c)

    return {
        "blueprint_text": blueprint_text,
        "chromadb_text":  chromadb_text,
        "tavily_text":    tavily_text,
        "all_citations":  unique_citations,
        "tools_used":     tools_used,
    }
