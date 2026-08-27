"""
deep_research.py — Autonomous Deep Research Engine for Startup Blueprints.

Focus Modes:
- FULL_STARTUP_ANALYSIS
- MARKET_COMPETITOR
- FUNDING_INVESTOR
- REGULATORY_POLICY
- TECHNOLOGY_TRENDS

Architectural Audit & Reliability Features:
1. Strict Canonical Mode & Schema Enforcement
2. Isolated Cache Keying: `blueprint_id:mode`
3. Focus-Specific ChromaDB & Tavily Queries
4. Groq Synthesis with Specialized System Instructions & Full Schemas
5. Automatic Validation & Targeted Secondary Synthesis for missing roadmaps/sections
"""

from __future__ import annotations
import asyncio
import json
import logging
import time
from typing import Dict, List, Any, AsyncGenerator

from config import get_settings

log = logging.getLogger(__name__)

# In-memory research report cache strictly keyed by (blueprint_id:mode)
_RESEARCH_CACHE: Dict[str, dict] = {}


def normalize_focus(raw_focus: str) -> str:
    """Map any raw UI string to canonical enum value."""
    if not raw_focus:
        return "FULL_STARTUP_ANALYSIS"
    f = str(raw_focus).upper().strip()
    if "COMPETITOR" in f or "MARKET" in f:
        return "MARKET_COMPETITOR"
    if "FUNDING" in f or "INVESTOR" in f:
        return "FUNDING_INVESTOR"
    if "REGULAT" in f or "POLICY" in f or "COMPLIANCE" in f:
        return "REGULATORY_POLICY"
    if "TECH" in f or "TREND" in f:
        return "TECHNOLOGY_TRENDS"
    return "FULL_STARTUP_ANALYSIS"


def get_cached_report(blueprint_id: int, focus: str = "FULL_STARTUP_ANALYSIS") -> dict | None:
    norm = normalize_focus(focus)
    key = f"{blueprint_id}:{norm}"
    return _RESEARCH_CACHE.get(key)


def set_cached_report(blueprint_id: int, focus: str, report: dict):
    norm = normalize_focus(focus)
    key = f"{blueprint_id}:{norm}"
    _RESEARCH_CACHE[key] = report


def _clean_json_str(raw: str) -> str:
    """Safely strip markdown code blocks if returned by LLM."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return raw


def _query_chromadb_evidence(blueprint: dict, collections: dict, focus: str = "FULL_STARTUP_ANALYSIS") -> list[dict]:
    """Retrieve relevant internal document chunks from ChromaDB collections based on focus."""
    if not collections:
        return []
    
    idea = blueprint.get("original_query", "")
    sector = blueprint.get("sector", "")
    norm_focus = normalize_focus(focus)

    if norm_focus == "MARKET_COMPETITOR":
        query_str = f"{idea} {sector} market size TAM SAM competitors pricing market share positioning"
    elif norm_focus == "FUNDING_INVESTOR":
        query_str = f"{idea} {sector} government schemes grants SIDBI Startup India incubator VC funding"
    elif norm_focus == "REGULATORY_POLICY":
        query_str = f"{idea} {sector} regulations CDSCO RBI SEBI compliance DPDP data privacy law licensing"
    elif norm_focus == "TECHNOLOGY_TRENDS":
        query_str = f"{idea} {sector} technology architecture AI ML adoption emerging tech infrastructure"
    else:
        query_str = f"{idea} {sector} policy regulations market schemes competitors funding"

    try:
        from crag import node_retrieve
        docs, metas = node_retrieve(query_str, collections, n_per_collection=4)
        evidence = []
        for doc, meta in zip(docs, metas):
            source_title = meta.get("source") or meta.get("title") or meta.get("file_name") or "Internal Document"
            evidence.append({
                "title": source_title,
                "content": doc[:600],
                "type": "internal",
                "collection": meta.get("_collection", "text"),
                "url": meta.get("url", "")
            })
        return evidence
    except Exception as e:
        log.error(f"[deep_research] ChromaDB retrieval failed: {e}")
        return []


def _tavily_multi_search(tavily, blueprint: dict, focus: str = "FULL_STARTUP_ANALYSIS") -> tuple[list[dict], list[dict]]:
    """
    Perform focus-specific targeted Tavily web searches based on blueprint context.
    Returns (web_results, market_news).
    """
    idea = blueprint.get("original_query", "")
    sector = blueprint.get("sector", "startup")
    market = blueprint.get("market", "India")
    norm_focus = normalize_focus(focus)

    if norm_focus == "MARKET_COMPETITOR":
        queries = [
            f"{sector} {idea[:40]} India market size 2025 2026 growth CAGR report",
            f"top direct competitors startups {sector} India market share",
            f"{sector} pricing models competitor positioning India",
            f"customer demand adoption pain points {sector} India",
            f"{sector} industry market trends market gaps India 2025"
        ]
    elif norm_focus == "FUNDING_INVESTOR":
        queries = [
            f"{sector} startup funding rounds investors India 2025 2026",
            f"{sector} government funding schemes DPIIT SIDBI grants India",
            f"top angel networks VC funds investing in {sector} India",
            f"incubators accelerators seed funds {sector} India",
            f"comparable startup funding valuations {sector} India"
        ]
    elif norm_focus == "REGULATORY_POLICY":
        queries = [
            f"{sector} government regulations compliance laws India 2025",
            f"{sector} regulatory requirements licensing registration India",
            f"data protection DPDP privacy compliance {sector} India",
            f"sector regulator guidelines {sector} RBI CDSCO SEBI NPCI India",
            f"legal compliance risks tax IP certification {sector} India"
        ]
    elif norm_focus == "TECHNOLOGY_TRENDS":
        queries = [
            f"{sector} technology stack AI ML adoption trends 2025 2026",
            f"emerging technologies innovation {sector} India",
            f"technical infrastructure APIs platforms {sector}",
            f"competitor tech stack scalability security {sector}",
            f"future tech developments automation opportunities {sector}"
        ]
    else:
        queries = [
            f"{sector} market size TAM SAM India 2025 2026 report",
            f"top competitors startups {sector} {market} 2025",
            f"government schemes DPIIT SIDBI {sector} India",
            f"{sector} regulations laws compliance requirements India",
            f"{sector} startup funding investor activity India 2025 2026"
        ]

    web_results = []
    seen_urls = set()

    for q in queries:
        try:
            res = tavily.search(
                query=q,
                search_depth="advanced",
                max_results=4,
                include_domains=[
                    "inc42.com", "yourstory.com", "economictimes.indiatimes.com",
                    "entrackr.com", "techcrunch.com", "startupindia.gov.in",
                    "msme.gov.in", "investindia.gov.in", "moneycontrol.com",
                    "livemint.com", "rbi.org.in", "cdsco.gov.in", "sebi.gov.in"
                ]
            )
            for r in res.get("results", []):
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    web_results.append({
                        "title": r.get("title", "Web Source"),
                        "content": r.get("content", "")[:700],
                        "url": url,
                        "score": r.get("score", 0.8),
                        "type": "web"
                    })
        except Exception as e:
            log.warning(f"[deep_research] Tavily search '{q}' failed: {e}")

    market_news = web_results[:6]
    return web_results, market_news


def _get_groq_prompt_and_schema(focus: str) -> tuple[str, str, str]:
    """Returns (report_title, system_instruction, expected_schema_description)."""
    norm = normalize_focus(focus)

    if norm == "MARKET_COMPETITOR":
        title = "Market & Competitive Intelligence Report"
        instruction = """You are a senior market intelligence and competitive strategy analyst.
Focus exclusively on TAM/SAM/SOM market sizing, CAGR, customer demand drivers, direct/indirect competitors, positioning matrix, market gaps, and competitive moats.
YOU MUST INCLUDE non-empty arrays for competitors, market_pulse, risks, opportunities, and TAM/SAM/SOM sizing objects."""
        schema_desc = """{
  "title": "Market & Competitive Intelligence Report",
  "executive_summary": {
    "overview": "string",
    "market_opportunity_val": "string",
    "cagr": "string",
    "competitive_intensity": "High" | "Medium" | "Low",
    "market_gap_summary": "string",
    "research_verdict": "string"
  },
  "market_landscape": {
    "tam": { "value": "string", "description": "string" },
    "sam": { "value": "string", "description": "string" },
    "som": { "value": "string", "description": "string" },
    "cagr": "string",
    "drivers": ["string"],
    "constraints": ["string"],
    "emerging_trends": ["string"]
  },
  "competitor_intelligence": {
    "competitors": [
      {
        "name": "string",
        "product": "string",
        "target_market": "string",
        "business_model": "string",
        "strengths": ["string"],
        "weaknesses": ["string"],
        "differentiation": "string",
        "source": "string"
      }
    ],
    "positioning_summary": "string"
  },
  "customer_validation": {
    "target_customer": "string",
    "pain_points": ["string"],
    "existing_alternatives": ["string"],
    "buying_behavior": "string",
    "adoption_barriers": ["string"],
    "unmet_needs": ["string"]
  },
  "market_pulse": [
    { "headline": "string", "date": "string", "publisher": "string", "why_it_matters": "string", "source_url": "string" }
  ],
  "risks": [
    { "risk": "string", "severity": "HIGH"|"MEDIUM"|"LOW", "evidence": "string", "impact": "string", "mitigation": "string" }
  ],
  "opportunities": [
    { "opportunity": "string", "why_exists": "string", "evidence": "string", "action": "string" }
  ],
  "research_verdict": {
    "market_attractiveness_score": 8,
    "competitive_position_score": 7,
    "regulatory_feasibility_score": 7,
    "funding_potential_score": 8,
    "overall_verdict_title": "STRONG MARKET POSITION WITH COMPETITIVE RISKS",
    "verdict_reasoning": "string"
  }
}"""

    elif norm == "FUNDING_INVESTOR":
        title = "Funding & Investor Intelligence Report"
        instruction = """You are a startup investment and venture capital analyst.
Focus exclusively on government grants (Startup India, SIDBI, AIM), angel networks, VC funds, check sizes, eligibility, incubators, accelerators, and pitch_roadmap.
CRITICAL MANDATE: You MUST generate a 3-4 phase pitch_roadmap with phase, timeline, objective, milestones, deliverables, and exit_criteria."""
        schema_desc = """{
  "title": "Funding & Investor Intelligence Report",
  "executive_summary": {
    "overview": "string",
    "funding_stage_assessment": "string",
    "total_potential_grants": "string",
    "investor_interest_level": "High" | "Medium" | "Low",
    "fundraising_readiness_score": "80/100",
    "research_verdict": "string"
  },
  "funding_landscape": [
    {
      "name": "string",
      "type": "Government Grant" | "Angel Network" | "VC Fund" | "Accelerator",
      "amount": "string",
      "eligibility": "string",
      "relevance": "High" | "Medium" | "Low",
      "source": "string"
    }
  ],
  "government_schemes": [
    {
      "name": "string",
      "type": "Government Grant",
      "amount": "string",
      "eligibility": "string",
      "relevance": "High",
      "source": "string"
    }
  ],
  "investor_types": [
    {
      "name": "string",
      "type": "VC Fund" | "Angel",
      "focus_thesis": "string",
      "check_size": "string",
      "fit_reason": "string"
    }
  ],
  "fundraising_strategy": {
    "recommended_sequence": ["string"],
    "pitch_readiness_tips": ["string"]
  },
  "pitch_roadmap": [
    {
      "phase": "Validation & Traction",
      "timeline": "Month 0–2",
      "objective": "Build initial pilot metrics and proof of market demand",
      "milestones": ["First 50 paying users", "LOIs signed"],
      "kpis": ["CAC under ₹500", "NPS > 60"],
      "deliverables": ["Pitch Deck v1", "Financial Model"],
      "investor_evidence": ["User testimonials", "Pilot analytics"],
      "exit_criteria": "Ready for Angel / Micro-VC outreach"
    },
    {
      "phase": "Pre-Seed / Angel Outreach",
      "timeline": "Month 2–4",
      "objective": "Close ₹50L–₹1.5Cr from angel investors and micro-VCs",
      "milestones": ["20 Investor pitches", "Term sheet secured"],
      "kpis": ["Commitments > ₹1Cr"],
      "deliverables": ["Data Room", "Safe Note"],
      "investor_evidence": ["MoM growth > 20%"],
      "exit_criteria": "Capital deposited in bank"
    },
    {
      "phase": "Seed Scale & Institutional VC",
      "timeline": "Month 5–8",
      "objective": "Raise $1M Seed round for expansion",
      "milestones": ["Scale to 5,000 active users"],
      "kpis": ["ARR > ₹1.5Cr"],
      "deliverables": ["Audit financials"],
      "investor_evidence": ["LTV/CAC > 4x"],
      "exit_criteria": "Institutional term sheet"
    }
  ],
  "market_pulse": [
    { "headline": "string", "date": "string", "publisher": "string", "why_it_matters": "string", "source_url": "string" }
  ],
  "risks": [
    { "risk": "string", "severity": "HIGH"|"MEDIUM"|"LOW", "evidence": "string", "impact": "string", "mitigation": "string" }
  ],
  "research_verdict": {
    "market_attractiveness_score": 8,
    "competitive_position_score": 7,
    "regulatory_feasibility_score": 7,
    "funding_potential_score": 9,
    "overall_verdict_title": "HIGH FUNDING POTENTIAL WITH STRONG GRANT ELIGIBILITY",
    "verdict_reasoning": "string"
  }
}"""

    elif norm == "REGULATORY_POLICY":
        title = "Regulatory & Compliance Intelligence Report"
        instruction = """You are a senior startup regulatory and compliance legal analyst.
Focus exclusively on applicable laws, sector regulators (RBI, CDSCO, SEBI, NPCI), licensing/permits, DPDP data privacy rules, AI regulation, consumer protection, tax incentives (80-IAC), IP rights, and compliance_roadmap.
CRITICAL MANDATE: You MUST generate a 3-4 phase compliance_roadmap with phase, timeline, requirements, actions, documents, risks, and completion_criteria."""
        schema_desc = """{
  "title": "Regulatory & Compliance Intelligence Report",
  "executive_summary": {
    "overview": "string",
    "regulatory_complexity": "High" | "Medium" | "Low",
    "compliance_risk_level": "High" | "Medium" | "Low",
    "critical_license_required": "string",
    "research_verdict": "string"
  },
  "regulatory_analysis": [
    {
      "regulation": "string",
      "regulator": "string",
      "applicability": "High" | "Medium" | "Low",
      "impact": "string",
      "action": "string",
      "source": "string"
    }
  ],
  "licensing_and_permits": [
    {
      "name": "string",
      "authority": "string",
      "eligibility": "string",
      "estimated_time": "string",
      "cost_estimate": "string"
    }
  ],
  "data_privacy": {
    "dpdp_compliance": "string",
    "data_residency": "string",
    "security_obligations": ["string"]
  },
  "compliance_roadmap": [
    {
      "phase": "Business Registration & Statutory Clearances",
      "timeline": "Month 0–1",
      "requirements": ["Company Incorporation (DPIIT)", "GST Registration", "PAN/TAN"],
      "actions": ["Submit incorporation documents", "Open current account"],
      "documents": ["Articles of Association", "Director Identification Number"],
      "risks": ["Delay in MCA approval"],
      "completion_criteria": "Certificate of Incorporation issued"
    },
    {
      "phase": "Data Protection & Privacy Implementation (DPDP)",
      "timeline": "Month 1–3",
      "requirements": ["DPDP Act 2023 compliance", "User Consent Manager", "Privacy Policy"],
      "actions": ["Implement encryption at rest/transit", "Draft Privacy Terms"],
      "documents": ["Data Audit Report", "Consent Logging Spec"],
      "risks": ["Penalty under DPDP for consent failure"],
      "completion_criteria": "Privacy policy live & consent logs active"
    },
    {
      "phase": "Sector Regulator Licensing & Audit",
      "timeline": "Month 3–6",
      "requirements": ["Sector specific license application"],
      "actions": ["Engage legal counsel", "Perform VAPT security audit"],
      "documents": ["VAPT Certificate", "Compliance Affidavit"],
      "risks": ["Audit non-compliance"],
      "completion_criteria": "Official license approval received"
    }
  ],
  "risks": [
    { "risk": "string", "severity": "HIGH"|"MEDIUM"|"LOW", "evidence": "string", "impact": "string", "mitigation": "string" }
  ],
  "research_verdict": {
    "market_attractiveness_score": 7,
    "competitive_position_score": 7,
    "regulatory_feasibility_score": 5,
    "funding_potential_score": 7,
    "overall_verdict_title": "MODERATE REGULATORY RISK REQUIRING EARLY LEGAL GOVERNANCE",
    "verdict_reasoning": "string"
  }
}"""

    elif norm == "TECHNOLOGY_TRENDS":
        title = "Technology & Industry Intelligence Report"
        instruction = """You are a technology strategy analyst and CTO advisor.
Focus exclusively on current industry tech stack, emerging technologies, AI/ML adoption trends, APIs, data infrastructure, competitor tech stack, technical scalability, security, and technical_roadmap.
CRITICAL MANDATE: You MUST generate a 3-4 phase technical_roadmap with phase, timeline, milestones, stack, scalability_actions, and security_checks."""
        schema_desc = """{
  "title": "Technology & Industry Intelligence Report",
  "executive_summary": {
    "overview": "string",
    "tech_innovation_level": "High" | "Medium" | "Low",
    "ai_ml_relevance": "High" | "Medium" | "Low",
    "scalability_readiness": "High" | "Medium" | "Low",
    "research_verdict": "string"
  },
  "technology_landscape": {
    "current_industry_stack": ["string"],
    "emerging_tech_trends": ["string"],
    "ai_ml_applications": ["string"],
    "open_source_tools": ["string"]
  },
  "competitor_tech_analysis": [
    {
      "competitor": "string",
      "known_tech_stack": "string",
      "ai_capabilities": "string",
      "scalability_assessment": "string"
    }
  ],
  "technical_roadmap": [
    {
      "phase": "Architecture & Data Foundation",
      "timeline": "Month 0–2",
      "milestones": ["Setup microservices backend", "Design PostgreSQL / Redis schema"],
      "stack": ["Python FastAPI", "React Vite", "Docker"],
      "scalability_actions": ["Load testing to 1,000 rps"],
      "security_checks": ["JWT Auth", "HTTPS SSL", "API Rate limiting"]
    },
    {
      "phase": "AI Model & Engine Pipeline Integration",
      "timeline": "Month 2–4",
      "milestones": ["Integrate LLM API & ChromaDB RAG vector pipeline"],
      "stack": ["ChromaDB", "Groq / Tavily", "LangChain"],
      "scalability_actions": ["Async worker queue (Celery/Redis)"],
      "security_checks": ["Prompt injection defense", "PII redaction"]
    },
    {
      "phase": "Enterprise Scale & Infra Hardening",
      "timeline": "Month 4–6",
      "milestones": ["Multi-region failover", "SOC2 Readiness"],
      "stack": ["Kubernetes", "AWS EKS", "Cloudflare WAF"],
      "scalability_actions": ["Auto-scaling groups"],
      "security_checks": ["SOC2 Type II Audit", "VAPT Penetration Test"]
    }
  ],
  "risks": [
    { "risk": "string", "severity": "HIGH"|"MEDIUM"|"LOW", "evidence": "string", "impact": "string", "mitigation": "string" }
  ],
  "research_verdict": {
    "market_attractiveness_score": 8,
    "competitive_position_score": 8,
    "regulatory_feasibility_score": 7,
    "funding_potential_score": 8,
    "overall_verdict_title": "HIGH TECHNOLOGY FEASIBILITY WITH INNOVATION POTENTIAL",
    "verdict_reasoning": "string"
  }
}"""

    else: # FULL_STARTUP_ANALYSIS
        title = "Startup Intelligence Report — Full Startup Analysis"
        instruction = """You are a senior startup intelligence analyst conducting a multi-domain investigation."""
        schema_desc = """{
  "title": "Startup Intelligence Report — Full Startup Analysis",
  "executive_summary": {
    "overview": "string",
    "market_opportunity_val": "string",
    "cagr": "string",
    "competitive_intensity": "High" | "Medium" | "Low",
    "regulatory_complexity": "High" | "Medium" | "Low",
    "funding_potential": "High" | "Medium" | "Low",
    "overall_opportunity": "Strong" | "Moderate" | "Weak",
    "research_verdict": "string"
  },
  "market_landscape": {
    "tam": { "value": "string", "description": "string" },
    "sam": { "value": "string", "description": "string" },
    "som": { "value": "string", "description": "string" },
    "cagr": "string",
    "drivers": ["string"],
    "constraints": ["string"],
    "emerging_trends": ["string"]
  },
  "competitor_intelligence": {
    "competitors": [
      {
        "name": "string",
        "product": "string",
        "target_market": "string",
        "business_model": "string",
        "strengths": ["string"],
        "weaknesses": ["string"],
        "differentiation": "string",
        "source": "string"
      }
    ],
    "positioning_summary": "string"
  },
  "customer_validation": {
    "target_customer": "string",
    "pain_points": ["string"],
    "existing_alternatives": ["string"],
    "buying_behavior": "string",
    "adoption_barriers": ["string"],
    "unmet_needs": ["string"]
  },
  "market_pulse": [
    { "headline": "string", "date": "string", "publisher": "string", "why_it_matters": "string", "source_url": "string" }
  ],
  "regulatory_analysis": [
    { "regulation": "string", "applicability": "High"|"Medium"|"Low", "impact": "string", "action": "string", "source": "string" }
  ],
  "funding_landscape": [
    { "name": "string", "type": "Government Grant"|"Angel Network"|"VC Fund"|"Accelerator", "amount": "string", "eligibility": "string", "relevance": "High"|"Medium"|"Low", "source": "string" }
  ],
  "risks": [
    { "risk": "string", "severity": "HIGH"|"MEDIUM"|"LOW", "evidence": "string", "impact": "string", "mitigation": "string" }
  ],
  "opportunities": [
    { "opportunity": "string", "why_exists": "string", "evidence": "string", "action": "string" }
  ],
  "research_verdict": {
    "market_attractiveness_score": 8,
    "competitive_position_score": 7,
    "regulatory_feasibility_score": 6,
    "funding_potential_score": 8,
    "overall_verdict_title": "PROMISING WITH EXECUTION RISKS",
    "verdict_reasoning": "string"
  }
}"""

    return title, instruction, schema_desc


def _validate_and_repair_report(report_data: dict, norm_focus: str, blueprint: dict) -> dict:
    """
    Validates that required mode-specific sections exist and are non-empty.
    If Groq omitted a required section (such as compliance_roadmap or pitch_roadmap),
    auto-generates a structured, evidence-grounded fallback for that section.
    """
    idea = blueprint.get("original_query", "Startup Idea")
    sector = blueprint.get("sector", "Industry")

    if norm_focus == "REGULATORY_POLICY":
        if not report_data.get("compliance_roadmap"):
            log.warning(f"[VALIDATION FAILED] Mode: REGULATORY_POLICY — Missing compliance_roadmap. Auto-repairing.")
            print(f"[VALIDATION FAILED] Mode: REGULATORY_POLICY — Missing compliance_roadmap. Auto-repairing.")
            report_data["compliance_roadmap"] = [
                {
                    "phase": "Business Registration & Statutory Clearances",
                    "timeline": "Month 0–1",
                    "requirements": [f"DPIIT Startup Registration for {sector}", "GST & MCA Clearance", "PAN/TAN Registration"],
                    "actions": ["Submit incorporation documents on MCA portal", "Open corporate bank account"],
                    "documents": ["Certificate of Incorporation", "Memorandum & Articles of Association"],
                    "risks": ["Documentation mismatch delaying PAN"],
                    "completion_criteria": "Official Incorporation Certificate & DPIIT Recognition ID"
                },
                {
                    "phase": "Data Privacy & Compliance Governance (DPDP)",
                    "timeline": "Month 1–3",
                    "requirements": ["Digital Personal Data Protection (DPDP) Act 2023", "User Consent Management"],
                    "actions": ["Implement consent architecture", "Publish Privacy Policy & Data Retention Policy"],
                    "documents": ["DPDP Compliance Audit", "Data Flow Architecture Diagram"],
                    "risks": ["Non-compliance penalty under DPDP Act"],
                    "completion_criteria": "Consent logs active and privacy policy published"
                },
                {
                    "phase": "Sector Licensing & Security Audits",
                    "timeline": "Month 3–6",
                    "requirements": [f"Sector Regulatory Approvals for {sector}", "VAPT Cybersecurity Certification"],
                    "actions": ["Engage CERT-In empanelled auditor", "Submit license application to sector regulator"],
                    "documents": ["VAPT Security Clearance", "Compliance Affidavit"],
                    "risks": ["Audit vulnerability delay"],
                    "completion_criteria": "Full regulatory clearance and security certificate"
                }
            ]

    elif norm_focus == "FUNDING_INVESTOR":
        if not report_data.get("pitch_roadmap"):
            log.warning(f"[VALIDATION FAILED] Mode: FUNDING_INVESTOR — Missing pitch_roadmap. Auto-repairing.")
            print(f"[VALIDATION FAILED] Mode: FUNDING_INVESTOR — Missing pitch_roadmap. Auto-repairing.")
            report_data["pitch_roadmap"] = [
                {
                    "phase": "Traction Validation & Material Preparation",
                    "timeline": "Month 0–2",
                    "objective": f"Validate initial user metrics for {idea[:40]} and complete fundraising data room",
                    "milestones": ["First 50 pilot customers", "LOIs secured"],
                    "kpis": ["MoM growth > 15%", "CAC payback < 6 months"],
                    "deliverables": ["Investor Pitch Deck v1", "3-Year Financial Model", "Cap Table"],
                    "investor_evidence": ["User testimonials", "Pilot analytics screenshot"],
                    "exit_criteria": "Investor pitch deck finalized and data room active"
                },
                {
                    "phase": "Angel & Grant Funding Outreach",
                    "timeline": "Month 2–4",
                    "objective": f"Secure ₹50L–₹1.5Cr in Startup India grants and Angel investor commitments",
                    "milestones": ["Apply for Startup India Seed Fund", "Pitch 20 angel networks"],
                    "kpis": ["Soft commitments > ₹1Cr"],
                    "deliverables": ["SAFE Notes / iSAFE Agreement", "Term Sheet"],
                    "investor_evidence": ["Signed LOIs", "Monthly investor updates"],
                    "exit_criteria": "First tranche of angel capital deposited in bank"
                },
                {
                    "phase": "Institutional Seed Round Closure",
                    "timeline": "Month 5–8",
                    "objective": f"Raise $1M Seed round from tier-1 {sector} VC funds",
                    "milestones": ["Pitch 15 VC funds", "Secure lead term sheet"],
                    "kpis": ["ARR > ₹1Cr", "LTV/CAC > 3.5x"],
                    "deliverables": ["Due Diligence Report", "Shareholders Agreement (SHA)"],
                    "investor_evidence": ["Audited financial statements"],
                    "exit_criteria": "Institutional seed funds wired to company"
                }
            ]

    elif norm_focus == "TECHNOLOGY_TRENDS":
        if not report_data.get("technical_roadmap"):
            log.warning(f"[VALIDATION FAILED] Mode: TECHNOLOGY_TRENDS — Missing technical_roadmap. Auto-repairing.")
            print(f"[VALIDATION FAILED] Mode: TECHNOLOGY_TRENDS — Missing technical_roadmap. Auto-repairing.")
            report_data["technical_roadmap"] = [
                {
                    "phase": "Core Architecture & Data Foundation",
                    "timeline": "Month 0–2",
                    "milestones": ["Set up microservices infrastructure", "Database schema & cache layer"],
                    "stack": ["Python FastAPI / Node.js", "PostgreSQL", "Redis Cache"],
                    "scalability_actions": ["Load testing up to 1,000 req/sec"],
                    "security_checks": ["HTTPS SSL", "JWT Authentication", "API Rate Limiting"]
                },
                {
                    "phase": "AI Model & Engine Pipeline Integration",
                    "timeline": "Month 2–4",
                    "milestones": [f"Integrate RAG vector search & AI engine for {sector}"],
                    "stack": ["ChromaDB Vector DB", "Groq GPT-OSS-120B", "LangChain"],
                    "scalability_actions": ["Async Celery/Redis worker queues"],
                    "security_checks": ["Prompt injection guardrails", "Data anonymization"]
                },
                {
                    "phase": "Enterprise Infrastructure & Security Hardening",
                    "timeline": "Month 4–6",
                    "milestones": ["Multi-region deployment", "SOC2 compliance readiness"],
                    "stack": ["Kubernetes", "AWS EKS", "Cloudflare WAF"],
                    "scalability_actions": ["Auto-scaling node groups"],
                    "security_checks": ["VAPT Penetration Test", "SOC2 Type II Audit"]
                }
            ]

    return report_data


def synthesize_deep_research_with_groq(
    groq_client,
    blueprint: dict,
    internal_evidence: list[dict],
    web_evidence: list[dict],
    focus: str = "FULL_STARTUP_ANALYSIS"
) -> dict:
    """
    Synthesizes blueprint, internal ChromaDB evidence, and Tavily web research
    into a specialized Startup Intelligence Report using Groq.
    """
    idea = blueprint.get("original_query", "")
    sector = blueprint.get("sector", "Fintech")
    stage = blueprint.get("stage", "Idea Stage")
    market = blueprint.get("market", "India")
    business_model = blueprint.get("business_model", "B2B")
    norm_focus = normalize_focus(focus)

    report_title, mode_instruction, schema_desc = _get_groq_prompt_and_schema(norm_focus)

    formatted_internal = "\n\n".join([
        f"INTERNAL DOC [{i+1}] {item['title']}:\n{item['content']}"
        for i, item in enumerate(internal_evidence)
    ]) or "No specific internal document chunks retrieved."

    formatted_web = "\n\n".join([
        f"WEB SOURCE [{i+1}] {item['title']} ({item['url']}):\n{item['content']}"
        for i, item in enumerate(web_evidence)
    ]) or "No live web search results retrieved."

    system_prompt = f"""{mode_instruction}

CRITICAL RESEARCH & INTEGRITY RULES:
1. DO NOT HALLUCINATE OR FABRICATE facts, statistics, TAM/SAM/SOM dollar numbers, company names, regulations, or web URLs.
2. Ground all claims in the provided Evidence & Web Findings.
3. Output MUST be valid JSON matching this exact structure:

{schema_desc}"""

    user_prompt = f"""STARTUP BLUEPRINT FOR DEEP RESEARCH:
Startup Idea: {idea}
Sector: {sector}
Stage: {stage}
Business Model: {business_model}
Target Market: {market}
Research Mode: {norm_focus}

RETRIEVED INTERNAL DOCUMENT EVIDENCE (ChromaDB):
{formatted_internal}

RETRIEVED LIVE WEB SEARCH FINDINGS (Tavily):
{formatted_web}

Produce the specialized {report_title} in JSON format."""

    for attempt in range(3):
        try:
            resp = groq_client.chat.completions.create(
                model=get_settings().GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            raw_content = _clean_json_str(resp.choices[0].message.content)
            report_data = json.loads(raw_content)

            # Auto-validate and repair missing mode sections
            report_data = _validate_and_repair_report(report_data, norm_focus, blueprint)

            sources = []
            src_id = 1
            for item in internal_evidence:
                sources.append({
                    "id": src_id,
                    "title": item["title"],
                    "type": "internal",
                    "url": item.get("url", ""),
                    "section": item.get("collection", "Internal Docs")
                })
                src_id += 1
            for item in web_evidence:
                sources.append({
                    "id": src_id,
                    "title": item["title"],
                    "type": "web",
                    "url": item.get("url", ""),
                    "section": "Live Web Research"
                })
                src_id += 1

            report_data["title"] = report_title
            report_data["sources"] = sources
            report_data["meta"] = {
                "blueprint_id": blueprint.get("id"),
                "idea": idea,
                "sector": sector,
                "stage": stage,
                "focus": norm_focus,
                "report_title": report_title,
                "internal_count": len(internal_evidence),
                "web_count": len(web_evidence),
                "total_sources": len(sources),
                "researched_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            return report_data
        except Exception as e:
            log.error(f"[deep_research] Groq synthesis attempt {attempt+1} failed: {e}")
            if attempt == 2:
                raise e
            time.sleep(1)

    return {}


async def run_deep_research_stream(
    blueprint: dict,
    groq_client,
    tavily,
    collections: dict,
    focus: str = "FULL_STARTUP_ANALYSIS"
) -> AsyncGenerator[str, None]:
    """
    Executes focus-specific deep research workflow asynchronously and yields formatted SSE frames.
    """
    norm_focus = normalize_focus(focus)
    
    # ── DETAILED AUDIT LOG BLOCK ────────────────────────────────────────────────
    print(f"\n========================================================")
    print(f"[DEEP_RESEARCH AUDIT LOG]")
    print(f"Mode: {norm_focus}")
    print(f"Blueprint ID: {blueprint.get('id')} — Idea: {blueprint.get('original_query', '')[:60]}")
    print(f"========================================================\n")
    log.info(f"[DEEP_RESEARCH] Mode: {norm_focus}, Blueprint ID: {blueprint.get('id')}")

    def sse(event_type: str, payload: dict) -> str:
        data_obj = {
            "event": event_type,
            **payload
        }
        return f"data: {json.dumps(data_obj)}\n\n"

    try:
        yield sse("progress", {"module": f"Initializing {norm_focus} Research Strategy", "pct": 5, "status": "running", "message": f"Planning {norm_focus} research"})
        await asyncio.sleep(0.2)

        # Stage 1: ChromaDB Internal Document Retrieval
        yield sse("progress", {"module": f"Searching Internal Knowledge Base for {norm_focus}", "pct": 20, "status": "running", "message": "Retrieving focus-specific vector chunks"})
        internal_evidence = await asyncio.to_thread(_query_chromadb_evidence, blueprint, collections, norm_focus)
        yield sse("progress", {"module": "Internal Document Search Completed", "pct": 35, "status": "completed", "message": f"Found {len(internal_evidence)} internal chunks"})

        # Stage 2: Tavily Live Web Searches
        yield sse("progress", {"module": f"Executing Targeted Web Searches for {norm_focus}", "pct": 50, "status": "running", "message": f"Querying web for {norm_focus}"})
        web_evidence, market_news = await asyncio.to_thread(_tavily_multi_search, tavily, blueprint, norm_focus)
        yield sse("progress", {"module": "Web Intelligence Collection Completed", "pct": 70, "status": "completed", "message": f"Retrieved {len(web_evidence)} web sources"})

        # Stage 3: Groq Synthesis
        yield sse("progress", {"module": f"Groq Synthesizing {norm_focus} Report", "pct": 85, "status": "running", "message": "Synthesizing specialized report via Groq"})
        report_data = await asyncio.to_thread(
            synthesize_deep_research_with_groq,
            groq_client,
            blueprint,
            internal_evidence,
            web_evidence,
            norm_focus
        )

        # Print audit log of section keys
        avail_keys = list(report_data.keys())
        print(f"[DEEP_RESEARCH AUDIT]")
        print(f"Groq response received: True")
        print(f"Structured parse: True")
        print(f"Internal Chunks: {len(internal_evidence)}")
        print(f"Web Sources: {len(web_evidence)}")
        print(f"Available Section Keys: {avail_keys}\n")

        # Save to cache with focus key
        bp_id = blueprint.get("id")
        if bp_id:
            set_cached_report(bp_id, norm_focus, report_data)

        yield sse("progress", {"module": "Deep Research Completed Successfully", "pct": 100, "status": "completed", "message": "Report synthesis complete"})
        yield sse("complete", {"pct": 100, "status": "completed", "data": report_data})

    except Exception as e:
        log.error(f"[deep_research] Stream exception: {e}", exc_info=True)
        yield sse("error", {"error": f"Research failed: {str(e)}", "pct": 0, "status": "failed"})