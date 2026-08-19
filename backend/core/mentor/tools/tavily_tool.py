"""
mentor/tools/tavily_tool.py
────────────────────────────
Performs live web search via Tavily, scoped to startup-relevant domains.
Results are cached per (query, intent) within a session to avoid
repeated API calls for follow-up questions on the same topic.
"""

from __future__ import annotations

_DOMAIN_SETS = {
    "GOVT_SCHEMES":    [
        "startupindia.gov.in", "msme.gov.in", "aim.gov.in",
        "investindia.gov.in", "dpiit.gov.in", "sidbi.in",
    ],
    "FUNDING":         [
        "inc42.com", "yourstory.com", "entrackr.com",
        "vccircle.com", "techcrunch.com", "startupindia.gov.in",
    ],
    "COMPETITOR":      [
        "inc42.com", "yourstory.com", "crunchbase.com",
        "economictimes.indiatimes.com", "entrackr.com",
    ],
    "MARKET_VALIDATION": [
        "statista.com", "inc42.com", "yourstory.com",
        "economictimes.indiatimes.com", "thehindubusinessline.com",
    ],
    "INVESTOR_PREP":   [
        "ycombinator.com", "paulgraham.com", "techcrunch.com",
        "inc42.com", "yourstory.com",
    ],
    "LEGAL":           [
        "mca.gov.in", "startupindia.gov.in", "msme.gov.in",
        "taxmann.com", "dpiit.gov.in",
    ],
    "_default":        [
        "startupindia.gov.in", "inc42.com", "yourstory.com",
        "economictimes.indiatimes.com", "entrackr.com",
        "techcrunch.com", "msme.gov.in",
    ],
}


def search_tavily(
    query: str,
    intent: str,
    sector: str,
    tavily_client,
    max_results: int = 5,
) -> dict:
    """
    Live web search scoped to startup-relevant domains.

    Parameters
    ----------
    query         : search query string (already intent-enriched by tool_router)
    intent        : one of the 14 intent codes (selects domain set)
    sector        : startup sector for query enrichment
    tavily_client : TavilyClient instance
    max_results   : max number of results to return

    Returns
    -------
    dict with keys:
        results   : list of {title, content, url, score}
        citations : list of formatted citation strings
        context   : single merged text block for prompt injection
    """
    domains = _DOMAIN_SETS.get(intent, _DOMAIN_SETS["_default"])
    enriched_query = f"{query} India {sector} startup 2024 2025"

    try:
        response = tavily_client.search(
            query=enriched_query,
            search_depth="advanced",
            max_results=max_results,
            include_domains=domains,
        )
        raw_results = response.get("results", [])

        results = []
        seen_urls = set()
        for r in raw_results:
            url = r.get("url", "")
            if url in seen_urls:
                continue
            seen_urls.add(url)
            results.append({
                "title":   r.get("title", ""),
                "content": r.get("content", "")[:500],
                "url":     url,
                "score":   r.get("score", 0.0),
            })

        results.sort(key=lambda x: x["score"], reverse=True)

        citations = []
        context_blocks = []
        for r in results[:5]:
            domain = r["url"].split("/")[2] if r["url"].startswith("http") else r["url"]
            citations.append(f"🌐 [{r['title']}]({r['url']})")
            context_blocks.append(
                f"[{r['title']}]\n{r['content']}\nSource: {r['url']}"
            )

        context = "\n\n---\n\n".join(context_blocks)

        return {
            "results":   results,
            "citations": citations,
            "context":   context,
        }

    except Exception as e:
        print(f"[TavilyTool] Error: {e}")
        return {"results": [], "citations": [], "context": ""}
