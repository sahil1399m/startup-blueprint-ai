"""
mentor/context.py
─────────────────
Builds a MentorContext dict from the blueprint output that app.py already
produces. This becomes the permanent "working memory" injected into every
Granite synthesis call so the mentor is blueprint-aware from birth.

Called once — right after blueprint generation in app.py.
"""

from __future__ import annotations
import json


def build_mentor_context(
    *,
    idea: str,
    sector: str,
    stage: str,
    business_model: str,
    market: str,
    crag_result: dict,
    bmc_data: dict,
    budget_data: dict,
    gtm_data: dict,
    investor_data: dict,
    competitor_data: dict,
    risk_data: dict,
) -> dict:
    """
    Assembles all blueprint output into a single flat MentorContext dict.

    Parameters
    ----------
    idea             : raw founder idea (original input)
    sector           : e.g. "Edtech"
    stage            : e.g. "Idea Stage"
    business_model   : "B2B" / "B2C" / "B2B2C"
    market           : e.g. "Pan India"
    crag_result      : full dict returned by run_crag()
    bmc_data         : Business Model Canvas dict from gen_bmc()
    budget_data      : budget dict from gen_budget()
    gtm_data         : GTM strategy dict from gen_gtm()
    investor_data    : investor/schemes dict from gen_investors()
    competitor_data  : competitor dict from gen_competitors()
    risk_data        : risk dict from gen_risks()

    Returns
    -------
    MentorContext dict — flat, JSON-serialisable
    """

    # ── CRAG fields ────────────────────────────────────────────────────────
    confidence         = crag_result.get("confidence", "")
    granite_summary    = crag_result.get("summary", "")
    rewritten_query    = crag_result.get("rewritten_query", "")
    internal_context   = crag_result.get("internal_context", "")
    external_context   = crag_result.get("external_context", "")
    sources            = crag_result.get("sources", [])
    explore_results    = crag_result.get("explore_results", [])
    keywords           = crag_result.get("keywords", [])

    # ── Flatten key BMC fields for quick access ────────────────────────────
    revenue_streams    = bmc_data.get("revenue_streams", [])
    value_props        = bmc_data.get("value_propositions", [])
    customer_segments  = bmc_data.get("customer_segments", [])
    key_partners       = bmc_data.get("key_partners", [])
    cost_structure     = bmc_data.get("cost_structure", [])

    # ── Budget summary ─────────────────────────────────────────────────────
    total_budget       = budget_data.get("total_12_months", 0)
    funding_suggestion = budget_data.get("funding_suggestion", "")
    budget_phases      = budget_data.get("phases", [])

    # ── GTM summary ────────────────────────────────────────────────────────
    target_market      = gtm_data.get("target_market", "")
    market_size        = gtm_data.get("market_size", "")
    launch_strategy    = gtm_data.get("launch_strategy", [])
    growth_channels    = gtm_data.get("growth_channels", [])
    milestones         = gtm_data.get("milestones", [])
    key_metrics        = gtm_data.get("key_metrics", [])

    # ── Investor / scheme summary ──────────────────────────────────────────
    govt_schemes       = investor_data.get("government_schemes", [])
    investor_types     = investor_data.get("investor_types", [])
    incubators         = investor_data.get("incubators", [])
    funding_roadmap    = investor_data.get("funding_roadmap", [])
    pitch_tips         = investor_data.get("pitch_tips", [])

    # ── Competitor summary ─────────────────────────────────────────────────
    competitors        = competitor_data.get("competitors", [])
    differentiators    = competitor_data.get("our_differentiators", [])
    market_gaps        = competitor_data.get("market_gaps", [])

    # ── Risk summary ───────────────────────────────────────────────────────
    risks              = risk_data.get("risks", [])
    high_risks         = [r for r in risks if r.get("severity") == "High"]

    # ── Build a short human-readable text summary for Granite prompts ──────
    text_summary = _build_text_summary(
        idea, sector, stage, business_model, market,
        confidence, granite_summary,
        revenue_streams, value_props, customer_segments,
        total_budget, funding_suggestion,
        target_market, market_size,
        govt_schemes, competitors, differentiators,
        high_risks, milestones
    )

    return {
        # ── Identity ──────────────────────────────────────────────────────
        "original_idea":       idea,
        "sector":              sector,
        "stage":               stage,
        "business_model":      business_model,
        "market":              market,
        "keywords":            keywords,

        # ── CRAG pipeline output ──────────────────────────────────────────
        "crag_confidence":     confidence,
        "structured_rewrite":  rewritten_query,
        "granite_policy_summary": granite_summary,
        "internal_context":    internal_context,
        "external_context":    external_context,
        "tavily_web_context":  _format_explore(explore_results),
        "sources":             sources,

        # ── Business Model Canvas ─────────────────────────────────────────
        "bmc": {
            "revenue_streams":    revenue_streams,
            "value_propositions": value_props,
            "customer_segments":  customer_segments,
            "key_partners":       key_partners,
            "cost_structure":     cost_structure,
            "raw":                bmc_data,
        },

        # ── Budget ────────────────────────────────────────────────────────
        "budget": {
            "total_12_months":    total_budget,
            "funding_suggestion": funding_suggestion,
            "phases":             budget_phases,
        },

        # ── GTM ───────────────────────────────────────────────────────────
        "gtm": {
            "target_market":   target_market,
            "market_size":     market_size,
            "launch_strategy": launch_strategy,
            "growth_channels": growth_channels,
            "milestones":      milestones,
            "key_metrics":     key_metrics,
        },

        # ── Investors ─────────────────────────────────────────────────────
        "investors": {
            "govt_schemes":    govt_schemes,
            "investor_types":  investor_types,
            "incubators":      incubators,
            "funding_roadmap": funding_roadmap,
            "pitch_tips":      pitch_tips,
        },

        # ── Competitors ───────────────────────────────────────────────────
        "competitors": {
            "list":            competitors,
            "differentiators": differentiators,
            "market_gaps":     market_gaps,
        },

        # ── Risks ─────────────────────────────────────────────────────────
        "risks": {
            "all":       risks,
            "high_only": high_risks,
        },

        # ── Pre-built text summary for Granite prompts ────────────────────
        "text_summary": text_summary,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_explore(explore_results: list) -> str:
    """Format Tavily explore results into a readable text block."""
    if not explore_results:
        return ""
    lines = []
    for r in explore_results[:5]:
        title   = r.get("title", "")
        content = r.get("content", "")[:300]
        url     = r.get("url", "")
        lines.append(f"• {title}\n  {content}\n  Source: {url}")
    return "\n\n".join(lines)


def _build_text_summary(
    idea, sector, stage, business_model, market,
    confidence, granite_summary,
    revenue_streams, value_props, customer_segments,
    total_budget, funding_suggestion,
    target_market, market_size,
    govt_schemes, competitors, differentiators,
    high_risks, milestones
) -> str:
    """
    Builds a compact 600-800 word text block that summarises the entire
    blueprint. This is injected at the top of every Granite synthesis prompt
    so the model has full context without needing to parse nested JSON.
    """
    scheme_names = [s.get("name", "") for s in govt_schemes[:3]]
    comp_names   = [c.get("name", "") for c in competitors[:4]]
    risk_names   = [r.get("category", "") + ": " + r.get("risk", "")[:60] for r in high_risks[:3]]
    milestone_str = " → ".join([f"Month {m.get('month')}: {m.get('goal','')[:40]}" for m in milestones[:5]])

    return f"""
STARTUP BLUEPRINT SUMMARY
═════════════════════════

IDEA: {idea[:300]}

SECTOR: {sector} | STAGE: {stage} | MODEL: {business_model} | MARKET: {market}
CRAG CONFIDENCE: {confidence}

VALUE PROPOSITIONS:
{chr(10).join(f'  • {v}' for v in value_props[:4])}

CUSTOMER SEGMENTS:
{chr(10).join(f'  • {c}' for c in customer_segments[:3])}

REVENUE STREAMS:
{chr(10).join(f'  • {r}' for r in revenue_streams[:4])}

TARGET MARKET: {target_market}
ESTIMATED MARKET SIZE: {market_size}

12-MONTH BUDGET: ₹{total_budget:,.0f}
FUNDING SUGGESTION: {funding_suggestion}

GOVERNMENT SCHEMES AVAILABLE:
{chr(10).join(f'  • {s}' for s in scheme_names)}

KEY COMPETITORS:
{chr(10).join(f'  • {c}' for c in comp_names)}

OUR DIFFERENTIATORS:
{chr(10).join(f'  • {d}' for d in differentiators[:3])}

HIGH-PRIORITY RISKS:
{chr(10).join(f'  • {r}' for r in risk_names)}

12-MONTH ROADMAP:
{milestone_str}

IBM GRANITE POLICY BRIEF (summary):
{granite_summary[:600]}
""".strip()


def context_to_prompt_block(ctx: dict) -> str:
    """
    Returns the text_summary — used as the blueprint context block
    at the top of every Granite mentor synthesis prompt.
    """
    return ctx.get("text_summary", "")


def get_section(ctx: dict, section: str) -> dict | list | str:
    """
    Helper to safely extract a section from MentorContext.
    section can be: 'bmc', 'budget', 'gtm', 'investors', 'competitors', 'risks'
    """
    return ctx.get(section, {})