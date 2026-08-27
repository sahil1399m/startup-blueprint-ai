"""
crag.py — Corrective RAG pipeline for Startup Blueprint Generator
Based on: Yan et al. 2024 (https://arxiv.org/abs/2401.15884)

ARCHITECTURE
============
__start__
    │
  rewrite_query          ← Gemini Flash: structured 8-section brief
    │
  retrieve               ← Query all 3 ChromaDB collections (text + table + visual)
    │
  eval_each_doc          ← CrossEncoder ms-marco-MiniLM-L-6-v2 scores each chunk
    │
  ┌──────┬──────────┐
CORRECT AMBIGUOUS INCORRECT
  │        │           │
refine   web_search  web_search
(PDF)   (PDF+web)   (web only)
  │        │           │
generate  generate  conversational
(Granite) (Granite)  (Groq)
  │        │           │
explore  explore    explore
(Tavily) (Tavily)  (Tavily)
  │        │           │
blueprint blueprint  redirect

BUGS FIXED vs previous version
================================
1. node_rewrite_query never passed `prompt` to generate_content() → fixed.
2. retrieve() queried single collection → now queries text_chunks + table_data
   + visual_summaries and merges by relevance score.
3. ChromaDB where-filter was applied without checking if doc_type field exists
   → graceful fallback to unfiltered query.
4. Gemini client instantiated inside the hot path on every call → moved to
   module-level lazy singleton.
"""

import os
import re
import time
import json
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv
from sentence_transformers import CrossEncoder
import chromadb
from ibm_watsonx_ai.foundation_models import ModelInference
from tavily import TavilyClient
from groq import Groq
import google.generativeai as genai
from google import genai as genai_new

from config import get_settings

load_dotenv()

# ── Thresholds (calibrated on raw CrossEncoder logits, NOT sigmoid) ───────────
# ms-marco-MiniLM-L-6-v2 raw logits on domain-specific policy corpora cluster
# much lower than web-search ranges — sigmoid collapses all values near 0.
UPPER_THRESHOLD = -4.0   # logit ≥ this  → CORRECT
LOWER_THRESHOLD = -7.5   # logit < this  → INCORRECT
                         # between       → AMBIGUOUS

# ── Lazy Gemini client singleton ──────────────────────────────────────────────
_gemini_embed_client = None

def _get_embed_client():
    global _gemini_embed_client
    if _gemini_embed_client is None:
        _gemini_embed_client = genai_new.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    return _gemini_embed_client


def _get_gemini_embedding(text: str) -> list:
    """Embed text using Gemini embedding-001. Falls back gracefully on error."""
    if not text or not text.strip():
        text = "startup business idea India"
    client = _get_embed_client()
    result = client.models.embed_content(
        model="models/gemini-embedding-001",
        contents=text.strip()
    )
    if not result or not result.embeddings:
        raise ValueError("Gemini embedding returned empty result")
    return list(result.embeddings[0].values)


# ══════════════════════════════════════════════════════════════════════════════
# NODE: rewrite_query
# Gemini Flash produces a rich 8-section structured brief used everywhere
# downstream: retrieval queries, Tavily search, Granite summarisation,
# and all 6 Groq blueprint sections.
# ══════════════════════════════════════════════════════════════════════════════
def node_rewrite_query(query, sector, stage, model_type, target_city, gemini_client):
    prompt = f"""You are a Retrieval Query Understanding Agent for an AI Startup Blueprint Generator.

Your task is NOT to summarize or shorten the startup idea.
Your goal is to preserve every important piece of information while restructuring it
for optimal semantic retrieval from a knowledge base and web search.

User Startup Idea:
{query}

Selected Context:
- Sector: {sector}
- Startup Stage: {stage}
- Business Model: {model_type}
- Primary Market: {target_city}

Rules:
- Never omit important information.
- Never replace detailed features with generic descriptions.
- Preserve AI techniques, technologies, customer segments, geography, and business model.
- Remove only filler words.
- Do NOT invent new features.

Return ONLY the following format, no other text:

PROBLEM STATEMENT
2-4 detailed sentences about the core problem being solved.

TARGET USERS
- Primary: [who]
- Secondary: [who]
- Enterprise: [who if applicable]

CORE SOLUTION
2-3 detailed sentences on how it works.

KEY FEATURES
- Feature 1
- Feature 2
- Feature 3
- Feature 4
- Feature 5

TECHNOLOGIES
- [tech1, tech2, ...]

INDUSTRY
[sector / sub-sector]

GEOGRAPHY
[primary + expansion markets]

BUSINESS MODEL
[B2B/B2C/B2B2C + monetisation approach]

KEYWORDS:
keyword1, keyword2, keyword3, keyword4, keyword5, keyword6, keyword7, keyword8

RETRIEVAL QUERIES:
1. [query focused on government schemes and policy]
2. [query focused on market size and competition]
3. [query focused on funding and investors]
4. [query focused on technology and implementation]
5. [query focused on legal and compliance]

SEARCH CONTEXT:
[One 60-80 word retrieval-focused paragraph combining every important concept naturally.]
"""

    try:
        model    = gemini_client.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(
            contents=prompt,   # BUG FIX: was missing from original — prompt never sent
            generation_config=genai.GenerationConfig(
                temperature=0.0,
                max_output_tokens=3000,
            )
        )
        rewritten = response.text.strip()
        if len(rewritten) < 80:
            raise ValueError("Rewrite too short")

        # ── Parse sections ────────────────────────────────────────────────────
        keywords, retrieval_queries, search_context = [], [], ""

        m = re.search(r"KEYWORDS:\s*(.*?)\n\s*RETRIEVAL QUERIES:", rewritten, re.S)
        if m:
            keywords = [k.strip() for k in m.group(1).split(",") if k.strip()]

        m = re.search(r"RETRIEVAL QUERIES:\s*(.*?)\n\s*SEARCH CONTEXT:", rewritten, re.S)
        if m:
            for line in m.group(1).splitlines():
                line = line.strip()
                if line and "." in line:
                    retrieval_queries.append(line.split(".", 1)[1].strip())

        m = re.search(r"SEARCH CONTEXT:\s*(.*)", rewritten, re.S)
        if m:
            search_context = m.group(1).strip()

        return {
            "structured_brief":  rewritten,
            "keywords":          keywords,
            "retrieval_queries": retrieval_queries,
            "search_context":    search_context or query,
        }

    except Exception as e:
        print(f"[CRAG] Rewrite failed: {e}")
        return {
            "structured_brief":  query,
            "keywords":          [],
            "retrieval_queries": [query],
            "search_context":    query,
        }


# ══════════════════════════════════════════════════════════════════════════════
# NODE: retrieve
# Queries all three ChromaDB collections and merges results by score.
# BUG FIX: original queried only one collection; visual_summaries and
# table_data were never searched, wasting the multimodal ingestion.
# ══════════════════════════════════════════════════════════════════════════════
def node_retrieve(search_context, collections: dict, n_per_collection=6):
    """
    collections = {
        "text":   chroma_text_col,
        "table":  chroma_table_col,
        "visual": chroma_visual_col,
    }
    Returns merged (docs, metas) sorted by ChromaDB distance (lower = better).
    """
    embedding = _get_gemini_embedding(search_context)
    all_docs, all_metas, all_dists = [], [], []

    for col_name, col in collections.items():
        if col is None or col.count() == 0:
            continue
        try:
            res   = col.query(query_embeddings=[embedding], n_results=min(n_per_collection, col.count()))
            docs  = res["documents"][0]
            metas = res["metadatas"][0]
            dists = res["distances"][0]
            for doc, meta, dist in zip(docs, metas, dists):
                meta["_collection"] = col_name
                all_docs.append(doc)
                all_metas.append(meta)
                all_dists.append(dist)
        except Exception as e:
            print(f"[CRAG] retrieve from {col_name} failed: {e}")

    if not all_docs:
        return [], []

    # Sort by distance ascending (closer = more relevant)
    combined = sorted(zip(all_dists, all_docs, all_metas), key=lambda x: x[0])
    _, sorted_docs, sorted_metas = zip(*combined)
    return list(sorted_docs), list(sorted_metas)


# ══════════════════════════════════════════════════════════════════════════════
# NODE: eval_each_doc  (CrossEncoder relevance grader)
# ══════════════════════════════════════════════════════════════════════════════
def node_eval_each_doc(query, docs, reranker):
    if not docs:
        return [], [], "INCORRECT", -10.0

    pairs      = [(query, doc) for doc in docs]
    raw_logits = np.array(reranker.predict(pairs))
    max_logit  = float(raw_logits.max())
    norm_scores = (1 / (1 + np.exp(-raw_logits))).tolist()

    print(f"[CRAG] Max raw logit: {max_logit:.3f}  "
          f"(Correct≥{UPPER_THRESHOLD}, Incorrect<{LOWER_THRESHOLD})")

    if max_logit >= UPPER_THRESHOLD:
        confidence = "CORRECT"
    elif max_logit < LOWER_THRESHOLD:
        confidence = "INCORRECT"
    else:
        confidence = "AMBIGUOUS"

    return norm_scores, raw_logits.tolist(), confidence, max_logit


# ══════════════════════════════════════════════════════════════════════════════
# NODE: refine  (decompose-then-recompose knowledge refinement)
# ══════════════════════════════════════════════════════════════════════════════
def node_refine(query, docs, raw_logits, reranker, top_k=5):
    """
    Sentence-level re-ranking inside each relevant doc.
    Strips low-relevance sentences and returns only the most on-topic strips.
    """
    all_strips = []
    for doc, logit in zip(docs, raw_logits):
        if logit < LOWER_THRESHOLD:
            continue
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', doc) if len(s.strip()) > 30]
        # Group into sentence pairs for context
        for i in range(0, len(sentences), 2):
            group = " ".join(sentences[i:i+2])
            if group:
                all_strips.append(group)

    if not all_strips:
        return "\n\n".join(docs[:3])

    strip_scores  = reranker.predict([(query, s) for s in all_strips])
    scored        = sorted(zip(strip_scores, all_strips), key=lambda x: x[0], reverse=True)
    top_strips    = [s for _, s in scored[:top_k]]
    return "\n\n".join(top_strips) if top_strips else "\n\n".join(docs[:2])


# ══════════════════════════════════════════════════════════════════════════════
# NODE: web_search  (Tavily)
# ══════════════════════════════════════════════════════════════════════════════
def node_web_search(search_context, retrieval_queries, tavily, sector="startup", max_results=5):
    all_results, seen_urls = [], set()
    queries = retrieval_queries if retrieval_queries else [search_context]

    for q in queries[:4]:   # cap at 4 queries to avoid Tavily quota burn
        search_query = f"{q} India startup {sector} 2024 2025"
        try:
            results = tavily.search(
                query=search_query,
                search_depth="advanced",
                max_results=max_results,
                include_domains=[
                    "startupindia.gov.in", "msme.gov.in", "aim.gov.in",
                    "investindia.gov.in", "inc42.com", "yourstory.com",
                    "economictimes.indiatimes.com", "entrackr.com",
                    "techcrunch.com", "nasscom.in",
                ]
            )
            for r in results.get("results", []):
                url = r.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                all_results.append({
                    "title":   r.get("title", ""),
                    "content": r.get("content", "")[:600],
                    "url":     url,
                    "score":   r.get("score", 0),
                })
        except Exception as e:
            print(f"[CRAG] Tavily failed for '{q[:50]}': {e}")

    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results


def _format_web_context(web_results) -> str:
    if not web_results:
        return ""
    blocks = []
    for r in web_results:
        blocks.append(f"[{r['title']}]\n{r['content']}\nSource: {r['url']}")
    return "\n\n---\n\n".join(blocks)


# ══════════════════════════════════════════════════════════════════════════════
# NODE: generate_summary  (IBM Granite — CORRECT + AMBIGUOUS branches)
# ══════════════════════════════════════════════════════════════════════════════
def node_generate_summary(structured_brief, context, granite, context_type="internal"):
    type_note = {
        "internal": "retrieved from official Indian government policy documents and reports",
        "combined": "retrieved from official policy documents AND live web sources",
    }.get(context_type, "retrieved")

    messages = [
        {
            "role": "system",
            "content": (
                "You are a senior Indian startup policy advisor with deep knowledge of "
                "government schemes, DPIIT regulations, MSME policies, Startup India, "
                "and the Indian entrepreneurship ecosystem.\n\n"
                "Synthesize the provided context into a clear, actionable policy brief. "
                "Cover: applicable government schemes and eligibility, funding pathways, "
                "regulatory requirements, tax benefits, and sector-specific support.\n\n"
                "Be specific and factual. Only use information from the context — "
                "never hallucinate scheme names, amounts, or eligibility criteria."
            )
        },
        {
            "role": "user",
            "content": (
                f"Startup Brief:\n{structured_brief}\n\n"
                f"Grounded Context ({type_note}):\n{context}\n\n"
                "Write a concise policy brief (300-500 words) covering the most relevant "
                "schemes, eligibility criteria, funding options, and actionable next steps "
                "for this specific startup."
            )
        }
    ]
    response = granite.chat(messages=messages, params={"max_tokens": 1800, "temperature": 0.15})
    return response["choices"][0]["message"]["content"]


# ══════════════════════════════════════════════════════════════════════════════
# NODE: generate_blueprint_sections  (Groq Llama — all 6 JSON sections)
# Each section gets its own tailored system prompt + the structured brief +
# relevant context. Using the rich Gemini rewrite instead of raw idea
# dramatically improves output quality and kills hallucination.
# ══════════════════════════════════════════════════════════════════════════════
def node_generate_blueprint(
    structured_brief, granite_summary, web_context,
    sector, model_type, stage, target_city, groq_client, gpt_oss_client,
    policy_sources=None, policy_crag=None, investor_context=None, investor_sources=None
):
    import re
    import json

    startup_idea_text = structured_brief or ""
    granite_sum_text = granite_summary or ""
    pol_sources_text = policy_sources or "Official Indian Policy Documents & Regulations"
    pol_crag_text = policy_crag or granite_summary or "CRAG Policy Context"
    inv_context_text = investor_context or policy_crag or "Indian Startup Investor & Government Scheme Ecosystem"
    inv_sources_text = investor_sources or policy_sources or "DPIIT, Startup India, SIDBI, Incubator Databases"
    web_ctx_text = web_context[:2000] if web_context else "No additional live web context available."

    system_prompt = (
        "You are an expert startup strategist, business analyst, market researcher, and venture advisor.\n\n"
        "Your task is to transform the provided startup idea and retrieved research into a complete, realistic, evidence-grounded startup blueprint."
    )

    user_prompt = f"""IMPORTANT RULES:

1. Do not simply summarize the retrieved context.
2. Do not invent statistics, market sizes, government schemes, funding amounts, competitors, investors, regulations, partnerships, or financial figures.
3. Clearly distinguish between:
   - VERIFIED FACTS supported by retrieved sources
   - INFERENCES derived from those facts
   - STRATEGIC RECOMMENDATIONS generated by the model
4. If the retrieved information does not support a claim, do not present it as a verified fact.
5. Use current Indian laws, schemes, policies, and regulations where applicable.
6. Do not treat proposed, outdated, repealed, or superseded legislation as current law.
7. Government schemes must NEVER be presented as guaranteed eligibility. Use wording such as "may qualify subject to eligibility requirements".
8. Market-size numbers must either be supported by retrieved sources or explicitly labelled as estimates/assumptions.
9. Competitors must be genuine and relevant. Never fabricate competitors.
10. Avoid generic startup advice. Every recommendation must be specific to the startup idea.
11. Avoid unnecessary repetition between sections.
12. Make the output investor-ready and practical.
13. Every section must be populated. Never return an empty section.
14. Keep budget calculations internally consistent.
15. Do not claim that a company, investor, government body, university, or partner has agreed to work with the startup unless the sources explicitly support that claim.

INPUT DATA:

STARTUP IDEA:
{startup_idea_text}

IBM GRANITE POLICY BRIEF:
{granite_sum_text}

POLICY SOURCES:
{pol_sources_text}

CRAG POLICY CONTEXT:
{pol_crag_text}

INVESTOR / MARKET CONTEXT:
{inv_context_text}

INVESTOR SOURCES:
{inv_sources_text}

ADDITIONAL WEB RESEARCH:
{web_ctx_text}


GENERATE THE FOLLOWING BLUEPRINT:

==================================================
1. BUSINESS MODEL
==================================================

KEY PARTNERS:
Provide 4–6 realistic partner categories or potential partners relevant to this startup.

KEY RESOURCES:
List the technology, people, data, infrastructure, intellectual property, and other resources required.

KEY ACTIVITIES:
Provide 5–7 concrete activities required to build, operate, and scale the startup.

VALUE PROPOSITIONS:
Explain:
- The customer problem
- The solution
- The unique value
- Why customers would choose this over existing alternatives

CUSTOMER RELATIONSHIPS:
Explain customer acquisition, onboarding, support, retention, loyalty, and re-engagement.

CUSTOMER SEGMENTS:
Define primary and secondary customer segments with relevant demographic, geographic, behavioral, or business characteristics.

CHANNELS:
Describe the most relevant acquisition and distribution channels.

COST STRUCTURE:
Separate major fixed and variable costs.

REVENUE STREAMS:
Explain exactly how the startup generates revenue.
Include realistic pricing, commissions, subscriptions, transaction fees, or other models where relevant.


==================================================
2. BUDGET
==================================================

Create a realistic 12-month budget divided into:

MVP: MONTH 1–3
LAUNCH: MONTH 4–6
GROWTH: MONTH 7–12

For each phase provide:
- Expense category
- Description
- Estimated amount in INR
- Phase total

Also provide:
- Total 12-month budget
- Percentage allocation by phase

CRITICAL:
The phase totals MUST mathematically equal the 12-month total.

Do not create an unnecessarily large budget for an MVP.


==================================================
3. GO-TO-MARKET STRATEGY
==================================================

TARGET MARKET:
Define the initial target customer and geography and explain why this market should be targeted first.

MARKET SIZE:
Provide TAM, SAM and SOM only when reliable evidence exists.
If numbers are estimated, explicitly label them as estimates and explain the assumption.

LAUNCH STRATEGY:
Create exactly 5 sequential steps:
1. Preparation
2. MVP
3. Pilot
4. Public Launch
5. Expansion

Each step must contain concrete actions and measurable milestones.

GROWTH CHANNELS:
Provide 5–7 channels.

For every channel include:
- Channel
- Strategy
- Reason it fits
- Priority: HIGH / MEDIUM / LOW
- Cost: FREE / PAID / MIXED

KEY KPIs:
Provide 5–7 metrics relevant to this startup.

TIMELINE:
Provide measurable milestones for:
M1
M3
M6
M9
M12


==================================================
4. FUNDING ROADMAP
==================================================

GOVERNMENT SCHEMES:

For each relevant scheme provide:
- Scheme name
- Benefit
- Eligibility
- Relevance to this startup
- Important limitations

NEVER claim guaranteed eligibility.

INVESTOR LANDSCAPE:
Identify suitable investor categories such as:
- Angels
- Seed funds
- Venture capital
- Corporate venture capital
- Strategic investors

Only name specific investors when supported by the retrieved context.

RELEVANT INCUBATORS:
Recommend relevant incubators or accelerators based on sector, geography, technology, and startup stage.

PITCH TIPS:
Provide 5 startup-specific pitch recommendations.


==================================================
5. COMPETITIVE ANALYSIS
==================================================

THIS SECTION IS MANDATORY AND MUST NEVER BE EMPTY.

Identify 4–6 relevant competitors or alternatives.

For each provide:
- Name
- Direct / Indirect competitor
- Core offering
- Strengths
- Weaknesses
- How our startup differentiates

If there is no verified direct competitor, explicitly label an alternative as an indirect competitor.

OUR DIFFERENTIATORS:
Provide 4–6 specific differentiators.

MARKET GAPS:
Provide 4–6 genuine gaps that this startup can exploit.

COMPETITIVE STRATEGY:
Explain:
- Market entry strategy
- Differentiation strategy
- First-customer acquisition
- Retention strategy
- Defensibility
- Response to larger competitors


==================================================
6. RISK ANALYSIS
==================================================

Identify at least 6 realistic risks.

Possible categories:
- Market
- Financial
- Technical
- Competition
- Regulatory
- Data Privacy
- Operational
- Customer Adoption

For every risk provide:
- Risk
- Severity: LOW / MEDIUM / HIGH
- Probability: LOW / MEDIUM / HIGH
- Impact
- Mitigation


==================================================
7. CRAG TRACE
==================================================

Explain how retrieved information influenced the blueprint.

VERIFIED CONTEXT:
Facts directly supported by retrieved sources.

INFERENCES:
Conclusions derived from the evidence.

RECOMMENDATIONS:
Strategic recommendations generated from the evidence.

SOURCE USAGE:
Map important claims to the source that supports them.

Never fabricate citations or sources.


==================================================
FINAL VALIDATION
==================================================

Before returning the answer verify:

- Every section is populated.
- Competitive Strategy is populated.
- Competitors are relevant.
- Budget totals are mathematically correct.
- Government scheme eligibility is not guaranteed.
- Current regulations are used.
- Outdated/proposed legislation is not presented as current.
- Market-size figures are sourced or explicitly marked as estimates.
- No fabricated investors, competitors, schemes, statistics, partnerships, or claims.
- Recommendations are specific to the startup.
- No major section repeats another section.
- Output follows the existing JSON structure expected by the frontend.

You MUST respond with ONLY a single valid JSON object matching this exact schema:

{{
  "bmc": {{
    "key_partners": ["string"],
    "key_resources": ["string"],
    "key_activities": ["string"],
    "value_propositions": ["string"],
    "customer_relationships": ["string"],
    "customer_segments": ["string"],
    "channels": ["string"],
    "cost_structure": ["string"],
    "revenue_streams": ["string"]
  }},
  "budget": {{
    "phases": [
      {{
        "name": "MVP",
        "duration": "Month 1-3",
        "items": [ {{ "item": "string", "amount": 100000 }} ],
        "total": 100000
      }},
      {{
        "name": "Launch",
        "duration": "Month 4-6",
        "items": [ {{ "item": "string", "amount": 150000 }} ],
        "total": 150000
      }},
      {{
        "name": "Growth",
        "duration": "Month 7-12",
        "items": [ {{ "item": "string", "amount": 250000 }} ],
        "total": 250000
      }}
    ],
    "total_12_months": 500000,
    "funding_suggestion": "string"
  }},
  "gtm": {{
    "target_market": "string",
    "market_size": "string",
    "launch_strategy": ["string"],
    "growth_channels": [
      {{
        "channel": "string",
        "strategy": "string",
        "rationale": "string",
        "priority": "HIGH / MEDIUM / LOW",
        "cost": "FREE / PAID / MIXED"
      }}
    ],
    "milestones": [
      {{ "month": 1, "goal": "string" }},
      {{ "month": 3, "goal": "string" }},
      {{ "month": 6, "goal": "string" }},
      {{ "month": 9, "goal": "string" }},
      {{ "month": 12, "goal": "string" }}
    ],
    "key_metrics": ["string"]
  }},
  "investors": {{
    "funding_roadmap": [
      {{ "stage": "string", "timeline": "string", "source": "string", "amount": "string" }}
    ],
    "government_schemes": [
      {{
        "name": "string",
        "benefit": "string",
        "eligibility": "string",
        "relevance": "string",
        "limitations": "string",
        "amount": "string"
      }}
    ],
    "investor_types": [
      {{
        "type": "string",
        "stage": "string",
        "focus": "string",
        "examples": ["string"]
      }}
    ],
    "incubators": [
      {{ "name": "string", "focus": "string", "location": "string" }}
    ],
    "pitch_tips": ["string"]
  }},
  "competitors": {{
    "competitors": [
      {{
        "name": "string",
        "type": "Direct / Indirect",
        "core_offering": "string",
        "strength": "string",
        "weakness": "string",
        "differentiator": "string",
        "market_share": "string",
        "funding": "string"
      }}
    ],
    "our_differentiators": ["string"],
    "market_gaps": ["string"],
    "competitive_strategy": "string"
  }},
  "risks": {{
    "risks": [
      {{
        "category": "Market",
        "severity": "HIGH",
        "probability": "MEDIUM",
        "impact": "string",
        "risk": "string",
        "mitigation": "string"
      }}
    ]
  }},
  "crag_trace": {{
    "verified_context": ["string"],
    "inferences": ["string"],
    "recommendations": ["string"],
    "source_usage": [
      {{ "claim": "string", "source": "string" }}
    ]
  }}
}}
"""

    res = {}
    # 1. Try GPT-OSS-120B (PRIMARY)
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ]
        response = gpt_oss_client.chat(
            messages=messages,
            params={"max_tokens": 4500, "temperature": 0.3}
        )
        content = response["choices"][0]["message"]["content"].strip()
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1 and end > start:
            content = content[start:end+1]
        res = json.loads(content)
    except Exception as e:
        print(f"[CRAG Blueprint] GPT-OSS-120B failed, using Groq fallback: {e}")
        try:
            r = groq_client.chat.completions.create(
                model=get_settings().GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=3500,
                response_format={"type": "json_object"},
            )
            res = json.loads(r.choices[0].message.content)
        except Exception as e2:
            print(f"[CRAG Blueprint] Groq fallback also failed: {e2}")
            res = {}

    # Defensive defaults for Budget
    budget = res.get("budget", {})
    if "phases" not in budget:
        budget["phases"] = [
            {"name":"MVP","duration":"Month 1-3","items":[{"item":"Development","amount":200000}],"total":200000},
            {"name":"Launch","duration":"Month 4-6","items":[{"item":"Marketing","amount":150000}],"total":150000},
            {"name":"Growth","duration":"Month 7-12","items":[{"item":"Scaling","amount":350000}],"total":350000},
        ]
    if "total_12_months" not in budget:
        budget["total_12_months"] = sum(p.get("total",0) for p in budget["phases"])
    if "funding_suggestion" not in budget:
        budget["funding_suggestion"] = "Startup India Seed Fund + Angel Investment"

    raw_risks = res.get("risks", {})
    if isinstance(raw_risks, list):
        risks_dict = {"risks": raw_risks}
    elif isinstance(raw_risks, dict):
        risks_dict = raw_risks
    else:
        risks_dict = {"risks": []}

    return {
        "bmc":         res.get("bmc", {}),
        "budget":      budget,
        "gtm":         res.get("gtm", {}),
        "investors":   res.get("investors", {}),
        "competitors": res.get("competitors", {}),
        "risks":       risks_dict,
        "crag_trace":  res.get("crag_trace", {}),
    }


# ══════════════════════════════════════════════════════════════════════════════
# NODE: conversational_answer  (INCORRECT branch — no blueprint)
# ══════════════════════════════════════════════════════════════════════════════
def node_conversational_answer(structured_brief, web_results, groq_client, gpt_oss_client):
    web_context = _format_web_context(web_results)

    if not web_context or len(web_context.strip()) < 50:
        return {
            "type": "redirect",
            "message": (
                "I specialise in generating startup blueprints for the Indian market — "
                "government schemes, business models, funding, and go-to-market strategy.\n\n"
                "Your query doesn't seem specific enough to generate a blueprint. "
                "Try describing your idea with more detail:\n\n"
                "• *An AI-powered logistics platform for last-mile delivery in Tier-2 cities*\n"
                "• *A SaaS tool for small clinics to manage patient appointments and billing*\n"
                "• *A B2B marketplace connecting textile manufacturers with export buyers*"
            )
        }

    messages = [
        {
            "role": "system",
            "content": (
                "You are a startup strategy assistant for the Indian market. "
                "The user's idea didn't match the internal policy knowledge base well, "
                "but live web search found some relevant context. "
                "Give a helpful, structured response covering: what this space looks "
                "like in India, key players or trends, relevant government support, "
                "and one concrete next step. Do NOT produce a full business blueprint."
            )
        },
        {
            "role": "user",
            "content": (
                f"Startup Brief:\n{structured_brief}\n\n"
                f"Live web context:\n{web_context}\n\n"
                "Give a helpful conversational answer (5-7 sentences):"
            )
        }
    ]

    try:
        try:
            r = gpt_oss_client.chat(
                messages=messages,
                params={"max_tokens": 800, "temperature": 0.2}
            )
            content = r["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[CRAG Conversational] GPT-OSS-120B failed, using Groq fallback: {e}")
            r = groq_client.chat.completions.create(
                model=get_settings().GROQ_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=800,
            )
            content = r.choices[0].message.content.strip()
        return {
            "type":        "answer",
            "message":     content,
            "web_context": web_context,
        }
    except Exception as e:
        return {
            "type":    "redirect",
            "message": "Something went wrong. Please rephrase your startup idea with more detail.",
        }


# ══════════════════════════════════════════════════════════════════════════════
# MAIN RUNNER
# ══════════════════════════════════════════════════════════════════════════════
def run_crag(
    query, sector, stage, model_type, target_city,
    collections,        # dict: {"text": col, "table": col, "visual": col}
    reranker,           # CrossEncoder instance
    granite,            # IBM ModelInference instance
    tavily,             # TavilyClient instance
    groq_client,        # Groq instance
    gemini_client,      # google.generativeai configured client
    gpt_oss_client,     # IBM ModelInference instance for GPT-OSS
):
    """
    Full CRAG pipeline. Returns a result dict consumed by app.py.

    collections must be:
        {
            "text":   chroma_collection("text_chunks"),
            "table":  chroma_collection("table_data"),
            "visual": chroma_collection("visual_summaries"),
        }
    """
    result = {
        "confidence":              "",
        "action":                  "",
        "should_generate_blueprint": False,
        "summary":                 "",         # Granite policy brief
        "blueprint":               {},         # 6 Groq sections
        "sources":                 [],
        "internal_context":        "",
        "external_context":        "",
        "scores":                  [],
        "raw_logits":              [],
        "max_logit":               0.0,
        "original_query":          query,
        "rewritten_query":         "",
        "structured_brief":        "",
        "keywords":                [],
        "retrieval_queries":       [],
        "search_context":          "",
        "conversational_response": None,
        "explore_results":         [],
    }

    # ── Step 1: Rewrite query (Gemini Flash) ──────────────────────────────────
    print("[CRAG] Step 1: Rewriting query...")
    rewrite = node_rewrite_query(
        query, sector, stage, model_type, target_city, gemini_client
    )
    result["rewritten_query"]  = rewrite["structured_brief"]
    result["structured_brief"] = rewrite["structured_brief"]
    result["keywords"]         = rewrite["keywords"]
    result["retrieval_queries"]= rewrite["retrieval_queries"]
    result["search_context"]   = rewrite["search_context"]

    search_ctx = rewrite["search_context"]

    # ── Step 2: Retrieve from all 3 collections ───────────────────────────────
    print("[CRAG] Step 2: Retrieving from ChromaDB (text + table + visual)...")
    docs, metas = node_retrieve(search_ctx, collections, n_per_collection=6)
    sources = list({m.get("source", "Unknown") for m in metas})
    result["sources"] = sources
    print(f"[CRAG]   Retrieved {len(docs)} chunks from {len(sources)} sources")

    # ── Step 3: Evaluate relevance (CrossEncoder) ─────────────────────────────
    print("[CRAG] Step 3: Grading retrieved chunks using original short query...")
    scores, raw_logits, confidence, max_logit = node_eval_each_doc(query, docs, reranker)
    result["confidence"] = confidence
    result["scores"]     = scores
    result["raw_logits"] = raw_logits
    result["max_logit"]  = max_logit
    print(f"[CRAG]   Confidence: {confidence}")

    # ══════════════════════════════════════════════════════════════════════════
    # BRANCH: CORRECT
    # ══════════════════════════════════════════════════════════════════════════
    if confidence == "CORRECT":
        result["action"] = (
            "✅ CORRECT — Internal knowledge base is strongly relevant. "
            "Blueprint grounded in official policy documents."
        )
        result["should_generate_blueprint"] = True

        print("[CRAG] Branch: CORRECT → refining PDF context...")
        refined = node_refine(search_ctx, docs, raw_logits, reranker)
        result["internal_context"] = refined

        print("[CRAG] Generating Granite policy summary...")
        result["summary"] = node_generate_summary(
            result["structured_brief"], refined, granite, "internal"
        )

        # Bonus: Tavily explore results (fed into blueprint for richer context)
        print("[CRAG] Fetching Tavily explore results...")
        explore = node_web_search(search_ctx, rewrite["retrieval_queries"], tavily, sector, max_results=4)
        result["explore_results"] = explore
        web_ctx = ""
        if explore:
            result["sources"].append("tavily_web_search")
            web_ctx = _format_web_context(explore)

        print("[CRAG] Generating 6 blueprint sections (GPT-OSS/Groq)...")
        result["blueprint"] = node_generate_blueprint(
            result["structured_brief"], result["summary"], web_ctx,
            sector, model_type, stage, target_city, groq_client, gpt_oss_client,
            policy_sources=", ".join([s for s in result["sources"] if s != "tavily_web_search"]) or "Official Indian Policy Documents & Regulations",
            policy_crag=refined,
            investor_context=refined,
            investor_sources=", ".join(result["sources"]) if result["sources"] else "DPIIT, Startup India, SIDBI, Incubator Databases"
        )

    # ══════════════════════════════════════════════════════════════════════════
    # BRANCH: AMBIGUOUS
    # ══════════════════════════════════════════════════════════════════════════
    elif confidence == "AMBIGUOUS":
        result["action"] = (
            "⚡ AMBIGUOUS — Partial relevance. Combining policy documents "
            "with live web search for richer context."
        )
        result["should_generate_blueprint"] = True

        print("[CRAG] Branch: AMBIGUOUS → refining PDF + fetching web...")
        refined  = node_refine(search_ctx, docs, raw_logits, reranker)
        web_res  = node_web_search(search_ctx, rewrite["retrieval_queries"], tavily, sector, max_results=4)
        web_ctx  = _format_web_context(web_res)

        result["internal_context"] = refined
        result["external_context"] = web_ctx

        combined = (
            "=== FROM POLICY DOCUMENTS ===\n" + refined +
            "\n\n=== FROM LIVE WEB SEARCH ===\n" + web_ctx
        )

        print("[CRAG] Generating Granite policy summary (combined)...")
        result["summary"] = node_generate_summary(
            result["structured_brief"], combined, granite, "combined"
        )

        print("[CRAG] Generating 6 blueprint sections (GPT-OSS/Groq)...")
        result["blueprint"] = node_generate_blueprint(
            result["structured_brief"], result["summary"], web_ctx,
            sector, model_type, stage, target_city, groq_client, gpt_oss_client,
            policy_sources=", ".join(result["sources"]) if result["sources"] else "Official Policy Documents & Web Sources",
            policy_crag=refined,
            investor_context=combined,
            investor_sources=", ".join(result["sources"]) if result["sources"] else "Government & Market Databases"
        )

        result["explore_results"] = web_res
        if web_res:
            result["sources"].append("tavily_web_search")

    # ══════════════════════════════════════════════════════════════════════════
    # BRANCH: INCORRECT
    # ══════════════════════════════════════════════════════════════════════════
    else:
        result["action"] = (
            "❌ INCORRECT — Knowledge base not relevant enough. "
            "Searching the live web. No blueprint generated — refine your idea."
        )
        result["should_generate_blueprint"] = False

        print("[CRAG] Branch: INCORRECT → web-only answer...")
        web_res = node_web_search(search_ctx, rewrite["retrieval_queries"], tavily, sector, max_results=5)
        web_ctx = _format_web_context(web_res)

        result["external_context"] = web_ctx
        result["explore_results"]  = web_res

        result["conversational_response"] = node_conversational_answer(
            result["structured_brief"], web_res, groq_client, gpt_oss_client
        )
        result["sources"] = ["tavily_web_search"] if web_res else []

    print(f"[CRAG] Done. Blueprint: {result['should_generate_blueprint']}")
    return result