"""
mentor/tools/blueprint_tool.py
───────────────────────────────
Searches within the in-memory MentorContext dict (the generated blueprint).
This is the primary zero-latency tool — no network call required.

Returns a structured excerpt from the relevant section of the blueprint
based on the intent.
"""

from __future__ import annotations
import json


# Maps intent codes to the section paths to pull from MentorContext
_INTENT_SECTION_MAP = {
    "MARKET_VALIDATION":   ["gtm", "competitors", "bmc"],
    "FUNDING":             ["investors", "budget"],
    "LEGAL":               ["investors"],
    "TECHNOLOGY":          ["bmc"],
    "COMPETITOR":          ["competitors"],
    "MARKETING":           ["gtm", "bmc"],
    "GTM":                 ["gtm"],
    "FINANCIAL":           ["budget", "gtm"],
    "HIRING":              ["bmc", "budget"],
    "PRODUCT_DEVELOPMENT": ["bmc", "gtm"],
    "GOVT_SCHEMES":        ["investors"],
    "RISK_ANALYSIS":       ["risks"],
    "INVESTOR_PREP":       ["investors", "competitors", "budget"],
    "EXECUTION_ROADMAP":   ["gtm", "risks", "budget"],
    "GENERAL":             ["bmc", "gtm", "investors"],
}


def search_blueprint(
    ctx: dict,
    intent: str,
    question: str,
) -> dict:
    """
    Extract relevant sections from the MentorContext dict for this intent.

    Returns
    -------
    dict with keys:
        sections  : dict of section_name → content_text
        citations : list of citation strings
        raw       : the extracted sub-dicts (for deep queries)
    """
    sections_to_pull = _INTENT_SECTION_MAP.get(intent, ["bmc", "gtm"])
    result = {
        "sections": {},
        "citations": [],
        "raw": {},
    }

    for section in sections_to_pull:
        data = ctx.get(section)
        if not data:
            continue
        text = _section_to_text(section, data, ctx)
        if text:
            result["sections"][section] = text
            result["raw"][section] = data

    # Always include the blueprint text_summary as baseline
    summary = ctx.get("text_summary", "")
    if summary:
        result["sections"]["blueprint_summary"] = summary[:1200]

    # Build citations from sources
    for src in ctx.get("sources", []):
        if src and src != "tavily_web_search":
            result["citations"].append(f"📄 {src}")

    return result


def _section_to_text(section: str, data: dict, ctx: dict) -> str:
    """Converts a blueprint section dict into a readable text block."""

    if section == "bmc":
        return _bmc_to_text(data)
    if section == "budget":
        return _budget_to_text(data)
    if section == "gtm":
        return _gtm_to_text(data)
    if section == "investors":
        return _investors_to_text(data)
    if section == "competitors":
        return _competitors_to_text(data, ctx)
    if section == "risks":
        return _risks_to_text(data)
    return ""


def _bmc_to_text(bmc: dict) -> str:
    lines = ["=== BUSINESS MODEL CANVAS ==="]
    mapping = [
        ("value_propositions",  "Value Propositions"),
        ("customer_segments",   "Customer Segments"),
        ("revenue_streams",     "Revenue Streams"),
        ("channels",            "Channels"),
        ("key_resources",       "Key Resources"),
        ("key_activities",      "Key Activities"),
        ("key_partners",        "Key Partners"),
        ("cost_structure",      "Cost Structure"),
    ]
    for key, label in mapping:
        items = bmc.get(key, [])
        if items:
            lines.append(f"\n{label}:")
            for item in items:
                lines.append(f"  • {item}")
    return "\n".join(lines)


def _budget_to_text(budget: dict) -> str:
    lines = ["=== BUDGET & FINANCIAL PLAN ==="]
    total = budget.get("total_12_months", 0)
    if total:
        lines.append(f"Total 12-Month Budget: ₹{total:,.0f}")
    fs = budget.get("funding_suggestion", "")
    if fs:
        lines.append(f"Funding Suggestion: {fs}")
    for phase in budget.get("phases", []):
        lines.append(f"\n{phase.get('name','')} ({phase.get('duration','')}):")
        for item in phase.get("items", []):
            lines.append(f"  • {item.get('item','')}: ₹{item.get('amount',0):,.0f}")
        lines.append(f"  Phase Total: ₹{phase.get('total',0):,.0f}")
    return "\n".join(lines)


def _gtm_to_text(gtm: dict) -> str:
    lines = ["=== GO-TO-MARKET STRATEGY ==="]
    tm = gtm.get("target_market", "")
    ms = gtm.get("market_size", "")
    if tm:
        lines.append(f"Target Market: {tm}")
    if ms:
        lines.append(f"Estimated Market Size: {ms}")

    ls = gtm.get("launch_strategy", [])
    if ls:
        lines.append("\nLaunch Strategy:")
        for i, step in enumerate(ls, 1):
            lines.append(f"  Step {i}: {step}")

    gc = gtm.get("growth_channels", [])
    if gc:
        lines.append("\nGrowth Channels:")
        for ch in gc:
            lines.append(f"  • {ch.get('channel','')} — {ch.get('priority','')} priority, Cost: {ch.get('cost','')}")

    milestones = gtm.get("milestones", [])
    if milestones:
        lines.append("\n12-Month Milestones:")
        for m in milestones:
            lines.append(f"  Month {m.get('month','')}: {m.get('goal','')}")

    km = gtm.get("key_metrics", [])
    if km:
        lines.append("\nKey Metrics to Track:")
        for metric in km:
            lines.append(f"  • {metric}")

    return "\n".join(lines)


def _investors_to_text(investors: dict) -> str:
    lines = ["=== INVESTORS & GOVERNMENT SCHEMES ==="]
    schemes = investors.get("govt_schemes", [])
    if schemes:
        lines.append("\nGovernment Schemes:")
        for s in schemes:
            lines.append(f"  • {s.get('name','')}: {s.get('benefit','')}")
            lines.append(f"    Eligibility: {s.get('eligibility','')}")

    inv_types = investors.get("investor_types", [])
    if inv_types:
        lines.append("\nInvestor Types:")
        for inv in inv_types:
            examples = ", ".join(inv.get("examples", []))
            lines.append(f"  • {inv.get('type','')} ({inv.get('stage','')}): {examples}")

    incubators = investors.get("incubators", [])
    if incubators:
        lines.append("\nIncubators & Accelerators:")
        for inc in incubators:
            lines.append(f"  • {inc.get('name','')} — {inc.get('location','')} | Focus: {inc.get('focus','')}")

    roadmap = investors.get("funding_roadmap", [])
    if roadmap:
        lines.append("\nFunding Roadmap:")
        for stage in roadmap:
            lines.append(f"  • {stage.get('stage','')}: {stage.get('amount','')} | {stage.get('timeline','')} | via {stage.get('source','')}")

    pitch_tips = investors.get("pitch_tips", [])
    if pitch_tips:
        lines.append("\nPitch Tips:")
        for tip in pitch_tips:
            lines.append(f"  • {tip}")

    return "\n".join(lines)


def _competitors_to_text(competitors: dict, ctx: dict) -> str:
    lines = ["=== COMPETITIVE LANDSCAPE ==="]
    comp_list = competitors.get("list", [])
    if comp_list:
        lines.append("\nCompetitors:")
        for c in comp_list:
            lines.append(
                f"  • {c.get('name','')}: "
                f"Strength: {c.get('strength','')} | "
                f"Weakness: {c.get('weakness','')} | "
                f"Market Share: {c.get('market_share',0)}%"
            )

    diffs = competitors.get("differentiators", [])
    if diffs:
        lines.append("\nOur Differentiators:")
        for d in diffs:
            lines.append(f"  • {d}")

    gaps = competitors.get("market_gaps", [])
    if gaps:
        lines.append("\nMarket Gaps to Exploit:")
        for g in gaps:
            lines.append(f"  • {g}")

    return "\n".join(lines)


def _risks_to_text(risks: dict) -> str:
    lines = ["=== RISK ASSESSMENT ==="]
    for r in risks.get("all", []):
        sev  = r.get("severity", "Medium")
        prob = r.get("probability", "Medium")
        lines.append(
            f"\n[{sev} severity | {prob} probability] {r.get('category','')}: {r.get('risk','')}"
        )
        lines.append(f"  Mitigation: {r.get('mitigation','')}")
    return "\n".join(lines)
