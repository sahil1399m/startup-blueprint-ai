"""
lock_in_agents.py — 3 AI agents for LOCK IN feature.
Market Research + Competitor Intelligence + Product Roadmap
Run in parallel via ThreadPoolExecutor.
"""

from __future__ import annotations
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _groq_json(groq_client, system: str, user: str, max_tokens=2000) -> dict:
    for attempt in range(3):
        try:
            resp = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.3,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            return json.loads(resp.choices[0].message.content.strip())
        except Exception as e:
            print(f"[lock_in_agents] Groq attempt {attempt+1} failed: {e}")
            if attempt < 2:
                time.sleep(2)
    return {}


def _tavily_search(tavily, query: str, max_results=5) -> list[dict]:
    try:
        results = tavily.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_domains=[
                "inc42.com", "yourstory.com", "economictimes.indiatimes.com",
                "entrackr.com", "techcrunch.com", "startupindia.gov.in",
                "livemint.com", "moneycontrol.com", "business-standard.com",
            ],
        )
        return [
            {
                "title":   r.get("title", ""),
                "content": r.get("content", "")[:500],
                "url":     r.get("url", ""),
            }
            for r in results.get("results", [])
        ]
    except Exception as e:
        print(f"[lock_in_agents] Tavily search failed: {e}")
        return []


def _fmt_web(results: list[dict]) -> str:
    return "\n\n".join(
        f"[{r['title']}]\n{r['content']}" for r in results if r.get("content")
    )


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 1 — MARKET RESEARCH
# ══════════════════════════════════════════════════════════════════════════════

def agent_market_research(blueprint: dict, founder: dict, groq_client, tavily) -> dict:
    """
    Returns:
    {
        "market_size": str,
        "cagr": str,
        "key_trends": [str],
        "target_customer_profile": str,
        "demand_signals": [str],
        "opportunities": [str],
        "risks": [str],
        "india_specific": str
    }
    """
    idea   = blueprint.get("original_query", "")
    sector = blueprint.get("sector", "startup")

    results = _tavily_search(tavily, f"{sector} market size India 2025 opportunity", max_results=5)
    web_ctx = _fmt_web(results)

    system = """You are a market research analyst for Indian startups.
Respond ONLY with valid JSON. Be specific and data-driven. All insights must be India-focused."""

    user = f"""Startup idea: {idea}
Sector: {sector}
Founder stage: {founder.get("startup_stage", "Idea Only")}
Web research:\n{web_ctx}

Return JSON:
{{
  "market_size": "string (e.g. ₹45,000 Crore by 2027)",
  "cagr": "string (e.g. 22% CAGR 2024-2028)",
  "key_trends": ["trend 1", "trend 2", "trend 3", "trend 4"],
  "target_customer_profile": "string (2-3 sentences describing ideal customer)",
  "demand_signals": ["signal 1", "signal 2", "signal 3"],
  "opportunities": ["opportunity 1", "opportunity 2", "opportunity 3"],
  "risks": ["risk 1", "risk 2", "risk 3"],
  "india_specific": "string (2-3 sentences on India-specific context, regulations, or opportunities)"
}}"""

    return _groq_json(groq_client, system, user)


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 2 — COMPETITOR INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════

def agent_competitor_intel(blueprint: dict, groq_client, tavily) -> dict:
    """
    Returns:
    {
        "competitors": [...],
        "differentiation_strategy": str,
        "white_space": [str]
    }
    """
    idea   = blueprint.get("original_query", "")
    sector = blueprint.get("sector", "startup")

    results = _tavily_search(tavily, f"top {sector} startups India competitors 2025 funding", max_results=6)
    web_ctx = _fmt_web(results)

    system = """You are a competitive intelligence analyst for Indian startups.
Respond ONLY with valid JSON. Name REAL companies, not placeholders."""

    user = f"""Startup idea: {idea}
Sector: {sector}
Web research:\n{web_ctx}

Return JSON:
{{
  "competitors": [
    {{
      "name": "Real Company Name",
      "founded": "year",
      "funding": "e.g. Series B, $12M",
      "usp": "their main value prop",
      "weakness": "key weakness",
      "pricing": "pricing model",
      "what_to_learn": "what this startup can learn from them"
    }}
  ],
  "differentiation_strategy": "string (2-3 sentences on how to stand out)",
  "white_space": ["untapped opportunity 1", "untapped opportunity 2", "untapped opportunity 3"]
}}
List 3-4 real competitors. No placeholders."""

    return _groq_json(groq_client, system, user, max_tokens=1500)


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 3 — PRODUCT ROADMAP
# ══════════════════════════════════════════════════════════════════════════════

def agent_product_roadmap(blueprint: dict, founder: dict, groq_client) -> dict:
    """
    Returns:
    {
        "months": [
            {
                "month": 1,
                "title": str,
                "objective": str,
                "weeks": [
                    {
                        "week": 1,
                        "focus": str,
                        "tasks": [
                            {
                                "id": "m1w1t1",
                                "title": str,
                                "description": str,
                                "why": str,
                                "hours": int,
                                "priority": "High|Medium|Low"
                            }
                        ]
                    }
                ],
                "milestone": str,
                "success_metric": str
            }
        ],
        "key_resources": [str],
        "first_week_focus": str
    }
    """
    idea      = blueprint.get("original_query", "")
    sector    = blueprint.get("sector", "startup")
    stage     = founder.get("startup_stage", "Idea Only")
    budget    = founder.get("budget", "Bootstrapped")
    duration  = founder.get("roadmap_duration", "6 Months")
    time_avail = founder.get("weekly_hours", "20 hrs")
    goal      = founder.get("primary_goal", "Launch MVP")
    team_size = founder.get("team_size", "1")
    resources = founder.get("existing_resources", [])

    months = 6 if "6" in str(duration) else 12

    system = """You are a startup product roadmap expert for Indian founders.
Create REALISTIC, ACTIONABLE roadmaps. Each task must be specific and executable.
Respond ONLY with valid JSON."""

    user = f"""Startup idea: {idea}
Sector: {sector}
Current stage: {stage}
Budget: {budget}
Primary goal: {goal}
Team size: {team_size} person(s)
Weekly hours available: {time_avail}
Roadmap duration: {duration}
Existing resources: {", ".join(resources) if resources else "None"}

IMPORTANT: You MUST generate EXACTLY {months} months. No more, no less.
The "months" array in your JSON must have exactly {months} items (month 1 through month {months}).
Each month must have 2 weeks with 3-4 specific tasks each.
Task IDs must be unique like m1w1t1, m1w1t2, m2w1t1 etc.

Return JSON:
{{
  "months": [
    {{
      "month": 1,
      "title": "Month title",
      "objective": "What to achieve this month",
      "weeks": [
        {{
          "week": 1,
          "focus": "Weekly focus area",
          "tasks": [
            {{
              "id": "m1w1t1",
              "title": "Specific task title",
              "description": "What exactly to do",
              "why": "Why this matters now",
              "hours": 4,
              "priority": "High"
            }}
          ]
        }}
      ],
      "milestone": "Key deliverable by end of month",
      "success_metric": "How to measure success"
    }}
  ],
  "key_resources": ["resource 1", "resource 2", "resource 3"],
  "first_week_focus": "The single most important thing to do in week 1"
}}"""

    return _groq_json(groq_client, system, user, max_tokens=4000)


# ══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

def run_lock_in_agents(blueprint: dict, founder: dict, groq_client, tavily) -> dict:
    """Run all 3 agents in parallel."""
    results = {
        "market_research":  {},
        "competitor_intel": {},
        "roadmap":          {},
    }

    tasks = {
        "market_research":  lambda: agent_market_research(blueprint, founder, groq_client, tavily),
        "competitor_intel": lambda: agent_competitor_intel(blueprint, groq_client, tavily),
        "roadmap":          lambda: agent_product_roadmap(blueprint, founder, groq_client),
    }

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fn): key for key, fn in tasks.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as e:
                print(f"[lock_in_agents] Agent '{key}' failed: {e}")
                results[key] = {}

    return results