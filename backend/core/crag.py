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
from typing import Optional, Any, Dict, List
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

# ── Gemini 429 Cooldown Cache ────────────────────────────────────────────────
_gemini_cooldown_until = 0.0

def _is_gemini_available() -> bool:
    global _gemini_cooldown_until
    return time.time() >= _gemini_cooldown_until

def _set_gemini_cooldown(seconds: int = 300):
    global _gemini_cooldown_until
    _gemini_cooldown_until = time.time() + seconds
    print(f"[CRAG] Gemini quota exceeded (429). Setting cooldown for {seconds}s — bypassing Gemini to Groq fallback.")

# ── IBM 429 Cooldown Cache ───────────────────────────────────────────────────
_ibm_cooldown_until = 0.0

def _is_ibm_available() -> bool:
    global _ibm_cooldown_until
    return time.time() >= _ibm_cooldown_until

def _set_ibm_cooldown(seconds: int = 120):
    global _ibm_cooldown_until
    _ibm_cooldown_until = time.time() + seconds
    print(f"[CRAG] IBM rate-limited (429). Setting cooldown for {seconds}s — bypassing IBM to Groq fallback.")

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

    if _is_gemini_available():
        try:
            model    = gemini_client.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(
                contents=prompt,
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
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "ResourceExhausted" in err_str or "404" in err_str:
                _set_gemini_cooldown(3600)
            clean_err = err_str.encode('ascii', errors='replace').decode('ascii')
            print(f"[CRAG] Gemini rewrite failed ({clean_err}), attempting Groq fallback rewrite...")
    else:
        print("[CRAG] Gemini rewrite skipped (quota cooldown active). Using Groq fallback directly.")

    try:
        from config import get_settings
        from dependencies import get_groq
        groq_cl = get_groq()
        r = groq_cl.chat.completions.create(
            model=get_settings().GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1200,
            temperature=0.0
        )
        rewritten = (r.choices[0].message.content or "").strip()
        if len(rewritten) >= 60:
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
            print(f"[CRAG] Groq fallback rewrite succeeded ({len(retrieval_queries)} queries)!")
            return {
                "structured_brief":  rewritten,
                "keywords":          keywords,
                "retrieval_queries": retrieval_queries or [query],
                "search_context":    search_context or query,
            }
    except Exception as e2:
        print(f"[CRAG] Groq rewrite fallback also failed: {e2}")

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
          f"(Correct>={UPPER_THRESHOLD}, Incorrect<{LOWER_THRESHOLD})")

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
def node_web_search(search_context, retrieval_queries, tavily, sector="startup", max_results=3):
    all_results, seen_urls = [], set()
    queries = retrieval_queries if retrieval_queries else [search_context]

    for q in queries[:2]:   # cap at 2 queries to avoid Tavily delays and quota burn
        search_query = f"{q} India startup {sector} 2024 2025"
        try:
            results = tavily.search(
                query=search_query,
                search_depth="basic",
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
                    "content": r.get("content", "")[:350],
                    "url":     url,
                    "score":   r.get("score", 0),
                })
        except Exception as e:
            print(f"[CRAG] Tavily search failed for '{q[:40]}': {e}")

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
# HELPER: robust JSON extraction from LLM output
# ══════════════════════════════════════════════════════════════════════════════
_BLUEPRINT_REQUIRED_KEYS = {"bmc", "budget", "gtm", "investors", "competitors", "risks"}
_ALL_BLUEPRINT_KEYS = {"bmc", "budget", "gtm", "investors", "competitors", "risks", "crag_trace"}


def _parse_blueprint_json(raw: str) -> dict:
    """
    Parse blueprint JSON from GPT-OSS-120B output, handling common LLM quirks:
      1. Strict json.loads
      2. Strip markdown code fences (```json ... ```)
      3. Extract JSON object from surrounding prose
      4. Fix trailing commas
      5. Validate against expected blueprint schema

    Raises ValueError on unrecoverable parse failure so the caller
    can fall through to the Groq fallback.
    """
    if not raw or not raw.strip():
        raise ValueError("Empty model output")

    def _is_valid_obj(obj):
        return (isinstance(obj, dict) and len(obj) > 0) or (isinstance(obj, list) and len(obj) > 0)

    # ── Attempt 1: strict parse ─────────────────────────────────────────────
    try:
        result = json.loads(raw)
        if _is_valid_obj(result):
            return result
    except json.JSONDecodeError:
        pass

    # ── Attempt 2: strip markdown code fences ───────────────────────────────
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1:]
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3].rstrip()
        try:
            result = json.loads(cleaned)
            if _is_valid_obj(result):
                return result
        except json.JSONDecodeError:
            pass

    # ── Attempt 3: extract outermost { ... } with bracket balancing ─────────
    start = raw.find("{")
    if start != -1:
        depth, end = 0, -1
        in_string, escape_next = False, False
        for i in range(start, len(raw)):
            ch = raw[i]
            if escape_next:
                escape_next = False
                continue
            if ch == "\\":
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end > start:
            extracted = raw[start:end + 1]
            try:
                result = json.loads(extracted)
                if _is_valid_obj(result):
                    return result
            except json.JSONDecodeError:
                pass

            # ── Attempt 4: fix trailing commas then parse again ──────────
            fixed = re.sub(r',\s*([\]}])', r'\1', extracted)
            try:
                result = json.loads(fixed)
                if _is_valid_obj(result):
                    return result
            except json.JSONDecodeError:
                pass

    # ── All attempts failed — raise so Groq fallback triggers ──────────────
    snippet = raw[:300].encode('ascii', errors='replace').decode('ascii').replace("\n", "\\n")
    raise ValueError(
        f"Could not extract valid blueprint JSON from model output. "
        f"Content starts with: {snippet}..."
    )


# ══════════════════════════════════════════════════════════════════════════════
# HELPER: normalize blueprint to guarantee consistent schema
# ══════════════════════════════════════════════════════════════════════════════
def _normalize_blueprint(raw: dict) -> dict:
    """
    Ensure every blueprint section exists with the correct structure.
    Both GPT-OSS and Groq output pass through this so the frontend
    always receives a predictable schema.
    """
    if not isinstance(raw, dict):
        raw = {}

    out = {}

    # ── BMC ─────────────────────────────────────────────────────────────────
    bmc = raw.get("bmc", {})
    if not isinstance(bmc, dict):
        bmc = {}
    for key in ("key_partners", "key_resources", "key_activities",
                "value_propositions", "customer_relationships",
                "customer_segments", "channels", "cost_structure",
                "revenue_streams"):
        if key not in bmc or not isinstance(bmc[key], list):
            bmc[key] = bmc.get(key, []) if isinstance(bmc.get(key), list) else []
    out["bmc"] = bmc

    # ── Budget ──────────────────────────────────────────────────────────────
    budget = raw.get("budget", {})
    if not isinstance(budget, dict):
        budget = {}
    if "phases" not in budget or not isinstance(budget.get("phases"), list):
        budget["phases"] = [
            {"name": "MVP", "duration": "Month 1-3",
             "items": [{"item": "Development & Infrastructure", "amount": 200000}], "total": 200000},
            {"name": "Launch", "duration": "Month 4-6",
             "items": [{"item": "Marketing & Operations", "amount": 150000}], "total": 150000},
            {"name": "Growth", "duration": "Month 7-12",
             "items": [{"item": "Scaling & Hiring", "amount": 350000}], "total": 350000},
        ]
    # Ensure each phase has required fields
    for phase in budget["phases"]:
        if "items" not in phase or not isinstance(phase.get("items"), list):
            phase["items"] = [{"item": phase.get("name", "Misc"), "amount": phase.get("total", 0)}]
        for item in phase["items"]:
            if "amount" not in item or not isinstance(item.get("amount"), (int, float)):
                item["amount"] = 0
    if "total_12_months" not in budget:
        budget["total_12_months"] = sum(p.get("total", 0) for p in budget["phases"])
    if "funding_suggestion" not in budget:
        budget["funding_suggestion"] = "Startup India Seed Fund + Angel Investment"
    out["budget"] = budget

    # ── GTM ─────────────────────────────────────────────────────────────────
    gtm = raw.get("gtm", {})
    if not isinstance(gtm, dict):
        gtm = {}
    if "target_market" not in gtm:
        gtm["target_market"] = gtm.get("target_market", "")
    if "market_size" not in gtm:
        gtm["market_size"] = gtm.get("market_size", "")
    if "launch_strategy" not in gtm or not isinstance(gtm.get("launch_strategy"), list):
        gtm["launch_strategy"] = gtm.get("launch_strategy", [])
    if "growth_channels" not in gtm or not isinstance(gtm.get("growth_channels"), list):
        gtm["growth_channels"] = gtm.get("growth_channels", [])
    if "milestones" not in gtm or not isinstance(gtm.get("milestones"), list):
        gtm["milestones"] = gtm.get("milestones", [])
    if "key_metrics" not in gtm or not isinstance(gtm.get("key_metrics"), list):
        gtm["key_metrics"] = gtm.get("key_metrics", [])
    out["gtm"] = gtm

    # ── Investors & Funding ──────────────────────────────────────────────────
    investors = raw.get("investors", {})
    if not isinstance(investors, dict):
        investors = raw.get("funding", {}) if isinstance(raw.get("funding"), dict) else {}

    if "funding_roadmap" not in investors or not isinstance(investors.get("funding_roadmap"), list) or len(investors["funding_roadmap"]) == 0:
        print("[BLUEPRINT NORMALIZATION] Warning: required field 'funding.funding_roadmap' is empty/missing")
        investors["funding_roadmap"] = investors.get("funding_roadmap", [])

    if "government_schemes" not in investors or not isinstance(investors.get("government_schemes"), list) or len(investors["government_schemes"]) == 0:
        print("[BLUEPRINT NORMALIZATION] Warning: required field 'funding.government_schemes' is empty/missing")
        investors["government_schemes"] = investors.get("government_schemes", [])

    inv_types = investors.get("investor_types") or investors.get("investor_landscape") or []
    if not isinstance(inv_types, list) or len(inv_types) == 0:
        print("[BLUEPRINT NORMALIZATION] Warning: required field 'funding.investor_landscape' is empty/missing")
        inv_types = []
    investors["investor_types"] = inv_types
    investors["investor_landscape"] = inv_types

    incubators = investors.get("incubators") or investors.get("relevant_incubators") or []
    if not isinstance(incubators, list) or len(incubators) == 0:
        print("[BLUEPRINT NORMALIZATION] Warning: required field 'funding.relevant_incubators' is empty/missing")
        incubators = []
    investors["incubators"] = incubators
    investors["relevant_incubators"] = incubators

    pitch_tips = investors.get("pitch_tips") or []
    if not isinstance(pitch_tips, list) or len(pitch_tips) == 0:
        print("[BLUEPRINT NORMALIZATION] Warning: required field 'funding.pitch_tips' is empty/missing")
        pitch_tips = []
    investors["pitch_tips"] = pitch_tips

    out["investors"] = investors
    out["funding"] = investors

    # ── Competitors ─────────────────────────────────────────────────────────
    raw_comp = raw.get("competitors", {})
    if isinstance(raw_comp, list):
        competitors = {"competitors": raw_comp}
    elif isinstance(raw_comp, dict):
        competitors = dict(raw_comp)
    else:
        competitors = {}

    if "competitors" not in competitors or not isinstance(competitors.get("competitors"), list) or len(competitors["competitors"]) == 0:
        print("[BLUEPRINT NORMALIZATION] Warning: required field 'competitors.competitors' is empty/missing")
        competitors["competitors"] = competitors.get("competitors", [])

    if "our_differentiators" not in competitors or not isinstance(competitors.get("our_differentiators"), list) or len(competitors["our_differentiators"]) == 0:
        print("[BLUEPRINT NORMALIZATION] Warning: required field 'competitors.our_differentiators' is empty/missing")
        competitors["our_differentiators"] = []

    if "market_gaps" not in competitors or not isinstance(competitors.get("market_gaps"), list) or len(competitors["market_gaps"]) == 0:
        print("[BLUEPRINT NORMALIZATION] Warning: required field 'competitors.market_gaps' is empty/missing")
        competitors["market_gaps"] = []

    if "competitive_strategy" not in competitors or not competitors.get("competitive_strategy"):
        print("[BLUEPRINT NORMALIZATION] Warning: required field 'competitors.competitive_strategy' is empty/missing")
        competitors["competitive_strategy"] = ""

    out["competitors"] = competitors

    # ── Risks ───────────────────────────────────────────────────────────────
    raw_risks = raw.get("risks", {})
    if isinstance(raw_risks, list):
        out["risks"] = {"risks": raw_risks}
    elif isinstance(raw_risks, dict):
        if "risks" not in raw_risks or not isinstance(raw_risks.get("risks"), list):
            raw_risks["risks"] = raw_risks.get("risks", [])
        out["risks"] = raw_risks
    else:
        out["risks"] = {"risks": []}

    # ── CRAG Trace ──────────────────────────────────────────────────────────
    crag_trace = raw.get("crag_trace", {})
    if not isinstance(crag_trace, dict):
        crag_trace = {}
    out["crag_trace"] = crag_trace

    # Preserve status and failed_sections
    out["status"] = raw.get("status", "success")
    out["failed_sections"] = raw.get("failed_sections", [])

    # Log which sections are genuinely populated vs defaulted
    for section in _BLUEPRINT_REQUIRED_KEYS:
        val = out.get(section, {})
        if not val or val == {} or (isinstance(val, dict) and all(
            v == [] or v == "" or v == {} for v in val.values()
        )):
            print(f"[CRAG Blueprint] WARNING: section '{section}' is empty/defaulted")

    return out


# ══════════════════════════════════════════════════════════════════════════════
# MODULAR SECTION GENERATION (Fast, Compact, Parallelized, Resilient)
# ══════════════════════════════════════════════════════════════════════════════

def _call_section_llm(
    section_name: str,
    system_prompt: str,
    user_prompt: str,
    groq_client,
    gpt_oss_client,
    max_tokens: int = 1600,
    temperature: float = 0.2,
    timeout_sec: int = 15,
) -> dict:
    """
    Execute a structured generation call with:
      - Mandatory prompt & model parameter logging
      - Strict timeout
      - Primary IBM GPT-OSS-120B call
      - Graceful fallback to Groq
      - Robust JSON extraction
    """
    import concurrent.futures

    model_id = getattr(gpt_oss_client, "model_id", "openai/gpt-oss-120b") if gpt_oss_client else "openai/gpt-oss-120b"
    est_tokens = len(user_prompt) // 4
    print(f"\n[BLUEPRINT MODEL CALL: {section_name.upper()}]")
    print(f"MODEL: GPT-OSS-120B")
    print(f"MODEL ID: {model_id}")
    print(f"PROVIDER: IBM Watsonx")
    print(f"INPUT TOKENS IF AVAILABLE: ~{est_tokens}")
    print(f"MAX OUTPUT TOKENS: {max_tokens}")
    print(f"TEMPERATURE: {temperature}")
    print(f"TIMEOUT: {timeout_sec}s")

    t0 = time.time()

    # 1. Primary: IBM Watsonx GPT-OSS-120B with strict timeout
    if gpt_oss_client is not None and _is_ibm_available():
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ]
            fut = pool.submit(
                gpt_oss_client.chat,
                messages=messages,
                params={"max_tokens": max_tokens, "temperature": temperature}
            )
            response = fut.result(timeout=timeout_sec)
            choice = (response.get("choices") or [{}])[0]
            content = ((choice.get("message") or {}).get("content") or "").strip()
            if content:
                res = _parse_blueprint_json(content)
                print(f"[BLUEPRINT] {section_name}: SUCCESS (via IBM GPT-OSS-120B, {time.time()-t0:.1f}s)")
                return res
        except Exception as e:
            clean_e = str(e).encode('ascii', errors='replace').decode('ascii')
            if "429" in clean_e or "too many requests" in clean_e.lower() or "rate_limit" in clean_e.lower():
                _set_ibm_cooldown(120)
            print(f"[CRAG Section] {section_name} via IBM GPT-OSS-120B failed or timed out ({clean_e}), attempting Groq fallback...")
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
    elif gpt_oss_client is not None and not _is_ibm_available():
        print(f"[CRAG Section] {section_name}: IBM cooldown active (429), bypassing immediately to Groq fallback.")

    # 2. Fallback: Groq with 429 backoff retry
    if groq_client is not None:
        groq_model = get_settings().GROQ_MODEL
        target_tokens = min(max_tokens, 1500)
        print(f"\n[BLUEPRINT FALLBACK CALL: {section_name.upper()}]")
        print(f"MODEL: Groq Llama")
        print(f"MODEL ID: {groq_model}")
        print(f"PROVIDER: Groq")
        print(f"INPUT TOKENS IF AVAILABLE: ~{est_tokens}")
        print(f"MAX OUTPUT TOKENS: {target_tokens}")
        print(f"TEMPERATURE: {temperature}")
        print(f"TIMEOUT: 15s")
        t1 = time.time()
        for attempt in range(3):
            try:
                r = groq_client.chat.completions.create(
                    model=groq_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt},
                    ],
                    temperature=temperature,
                    max_tokens=target_tokens,
                    response_format={"type": "json_object"},
                    timeout=15.0,
                )
                groq_content = (r.choices[0].message.content or "").strip()
                if groq_content:
                    res = _parse_blueprint_json(groq_content)
                    print(f"[BLUEPRINT] {section_name}: SUCCESS (via Groq {groq_model}, {time.time()-t1:.1f}s)")
                    return res
            except Exception as e2:
                clean_e2 = str(e2).encode('ascii', errors='replace').decode('ascii')
                if "429" in clean_e2 or "rate_limit" in clean_e2.lower():
                    delay = 3.5
                    m_delay = re.search(r"try again in ([\d\.]+)s", clean_e2)
                    if m_delay:
                        try:
                            delay = float(m_delay.group(1)) + 0.5
                        except Exception:
                            pass
                    print(f"[CRAG Section] {section_name} hit Groq rate limit (429). Retrying in {delay:.1f}s (attempt {attempt+1}/3)...")
                    time.sleep(delay)
                    continue
                else:
                    print(f"[CRAG Section] {section_name} via Groq also failed: {clean_e2}")
                    break

    print(f"[BLUEPRINT] {section_name}: FAILED (Both IBM and Groq failed)")
    return {}


def _gen_bmc(brief: str, evidence: str, groq_client, gpt_oss_client) -> dict:
    system_prompt = (
        "You are an expert startup strategist. Generate a complete Business Model Canvas for the startup idea. "
        "Return ONLY a JSON object with 9 lists matching the schema."
    )
    user_prompt = f"""STARTUP IDEA:
{brief}

EVIDENCE & CONTEXT:
{evidence}

Generate a concise, realistic Business Model Canvas in India.
Return JSON with this exact schema:
{{
  "key_partners": ["partner1", "partner2", "partner3", "partner4"],
  "key_resources": ["resource1", "resource2", "resource3", "resource4"],
  "key_activities": ["activity1", "activity2", "activity3", "activity4"],
  "value_propositions": ["prop1", "prop2", "prop3"],
  "customer_relationships": ["rel1", "rel2", "rel3"],
  "customer_segments": ["segment1", "segment2", "segment3"],
  "channels": ["channel1", "channel2", "channel3"],
  "cost_structure": ["cost1", "cost2", "cost3", "cost4"],
  "revenue_streams": ["stream1", "stream2", "stream3"]
}}"""
    raw = _call_section_llm("bmc", system_prompt, user_prompt, groq_client, gpt_oss_client, max_tokens=1500)
    return raw.get("bmc", raw)


def _gen_budget(brief: str, evidence: str, groq_client, gpt_oss_client) -> dict:
    system_prompt = (
        "You are a startup financial advisor. Estimate a practical 12-month budget in Indian Rupees (INR) across 3 phases: "
        "MVP (Month 1-3), Launch (Month 4-6), and Growth (Month 7-12). "
        "Return ONLY a JSON object matching the schema."
    )
    user_prompt = f"""STARTUP IDEA:
{brief}

EVIDENCE & CONTEXT:
{evidence}

Provide estimated line items with realistic integer INR amounts (e.g. 150000).
Return JSON with this exact schema:
{{
  "phases": [
    {{
      "name": "MVP",
      "duration": "Month 1-3",
      "items": [
        {{"item": "Core Platform Engineering", "amount": 250000}},
        {{"item": "Cloud Hosting & AI APIs", "amount": 100000}},
        {{"item": "Legal & Incorporation", "amount": 50000}}
      ]
    }},
    {{
      "name": "Launch",
      "duration": "Month 4-6",
      "items": [
        {{"item": "Customer Acquisition & Digital Marketing", "amount": 200000}},
        {{"item": "Sales Outreach & Support", "amount": 150000}},
        {{"item": "Operational Overhead", "amount": 50000}}
      ]
    }},
    {{
      "name": "Growth",
      "duration": "Month 7-12",
      "items": [
        {{"item": "Team Scaling & Senior Engineers", "amount": 400000}},
        {{"item": "Partnership Marketing & SEO", "amount": 250000}},
        {{"item": "Security & Compliance Audits", "amount": 150000}}
      ]
    }}
  ],
  "funding_suggestion": "Startup India Seed Fund Scheme (SISFS) + Angel Syndicate"
}}"""
    raw = _call_section_llm("budget", system_prompt, user_prompt, groq_client, gpt_oss_client, max_tokens=1400)
    budget = raw.get("budget", raw)
    phases = budget.get("phases", [])
    if not isinstance(phases, list) or len(phases) == 0:
        phases = [
            {"name": "MVP", "duration": "Month 1-3", "items": [{"item": "Core Engineering & Infrastructure", "amount": 300000}]},
            {"name": "Launch", "duration": "Month 4-6", "items": [{"item": "Marketing & Pilot Acquisition", "amount": 250000}]},
            {"name": "Growth", "duration": "Month 7-12", "items": [{"item": "Scaling & Security Audits", "amount": 450000}]},
        ]
    total_12 = 0
    for p in phases:
        items = p.get("items", [])
        if not isinstance(items, list):
            items = []
        phase_total = sum(int(it.get("amount", 0)) for it in items if isinstance(it, dict) and isinstance(it.get("amount"), (int, float)))
        p["total"] = phase_total
        total_12 += phase_total
    budget["total_12_months"] = total_12 if total_12 > 0 else 1000000
    for p in phases:
        p["percentage"] = round((p.get("total", 0) / budget["total_12_months"]) * 100, 1)
    budget["phases"] = phases
    if not budget.get("funding_suggestion"):
        budget["funding_suggestion"] = "Startup India Seed Fund Scheme + Angel Investment"
    return budget


def _gen_gtm(brief: str, evidence: str, groq_client, gpt_oss_client) -> dict:
    system_prompt = (
        "You are a Go-to-Market growth strategist. Generate a structured GTM plan for an Indian startup. "
        "Return ONLY a JSON object matching the schema."
    )
    user_prompt = f"""STARTUP IDEA:
{brief}

EVIDENCE & CONTEXT:
{evidence}

Generate a concise, practical GTM strategy with 5 sequential launch steps, growth channels, milestones, and KPIs.
Return JSON with this exact schema:
{{
  "target_market": "Clear definition of initial target customer and geography",
  "market_size": "Estimated TAM, SAM, SOM (e.g. TAM: $2.5B, SAM: $450M, SOM: $15M in India)",
  "launch_strategy": [
    "1. Preparation: Prototype validation with 20 pilot users",
    "2. MVP: Release core feature set to targeted beta cohort",
    "3. Pilot: Paid pilot deployment with 50 MSMEs",
    "4. Public Launch: Self-serve onboarding and digital campaigns",
    "5. Expansion: Regional partner networks and enterprise tiers"
  ],
  "growth_channels": [
    {{
      "channel": "B2B Outbound & Direct Sales",
      "strategy": "Direct outreach to SME business owners via LinkedIn & email",
      "rationale": "High conversion for SaaS software",
      "priority": "HIGH",
      "cost": "MIXED"
    }},
    {{
      "channel": "Industry Associations & CA Partnerships",
      "strategy": "Partner with chartered accountant networks & MSME forums",
      "rationale": "Trusted advisors recommend the platform",
      "priority": "HIGH",
      "cost": "FREE"
    }},
    {{
      "channel": "Content Marketing & SEO",
      "strategy": "Practical guides on Indian business cash flow & GST",
      "rationale": "Organic intent-driven acquisition",
      "priority": "MEDIUM",
      "cost": "FREE"
    }}
  ],
  "milestones": [
    {{"month": 1, "goal": "Beta architecture and compliance framework established"}},
    {{"month": 3, "goal": "Onboard first 25 active pilot customers"}},
    {{"month": 6, "goal": "Achieve ₹1.5L MRR with >80% 30-day retention"}},
    {{"month": 9, "goal": "Expand to 150 paying business accounts"}},
    {{"month": 12, "goal": "Reach ₹10L MRR and initiate Seed fundraising round"}}
  ],
  "key_metrics": ["Monthly Recurring Revenue (MRR)", "Customer Acquisition Cost (CAC)", "Customer Lifetime Value (LTV)", "Monthly Net Churn", "Weekly Active Users (WAU)"]
}}"""
    raw = _call_section_llm("gtm", system_prompt, user_prompt, groq_client, gpt_oss_client, max_tokens=1600)
    return raw.get("gtm", raw)


def _gen_investors(brief: str, evidence: str, groq_client, gpt_oss_client) -> dict:
    system_prompt = (
        "You are a venture capital and government scheme specialist for Indian startups. "
        "Ground recommendations in official schemes (Startup India, MSME, DPIIT, SIDBI) and Indian investor networks. "
        "Return ONLY a JSON object matching the schema."
    )
    user_prompt = f"""STARTUP IDEA:
{brief}

EVIDENCE & CONTEXT:
{evidence}

Generate a realistic funding roadmap, eligible government schemes (with benefits, eligibility, limitations), investor categories, and pitch tips.
Return JSON with this exact schema:
{{
  "funding_roadmap": [
    {{"stage": "Pre-Seed / Grants", "timeline": "Month 1-4", "source": "Startup India Seed Fund (SISFS) / Incubator Grants", "amount": "₹20L - ₹50L"}},
    {{"stage": "Seed Round", "timeline": "Month 5-9", "source": "Angel Networks & Micro VCs", "amount": "₹75L - ₹1.5Cr"}},
    {{"stage": "Pre-Series A", "timeline": "Month 10-14", "source": "Early Stage VCs", "amount": "₹3Cr - ₹5Cr"}}
  ],
  "government_schemes": [
    {{
      "name": "Startup India Seed Fund Scheme (SISFS)",
      "benefit": "Grants up to ₹20L for prototype; debt/convertible up to ₹50L for market entry",
      "eligibility": "DPIIT recognised startup incorporated < 2 years with innovative business model",
      "relevance": "Non-dilutive early capital to fund MVP and initial validation",
      "limitations": "Subject to incubator selection committee approval and milestones",
      "amount": "Up to ₹50 Lakhs"
    }},
    {{
      "name": "Credit Guarantee Scheme for Startups (CGSS)",
      "benefit": "Collateral-free credit guarantee for loans by member institutions",
      "eligibility": "DPIIT recognised startups with stable revenue",
      "relevance": "Access to working capital debt without collateral",
      "limitations": "Requires bank approval and financial track record",
      "amount": "Up to ₹10 Crores"
    }}
  ],
  "investor_types": [
    {{
      "type": "Early Stage Angel Syndicates",
      "stage": "Pre-Seed / Seed",
      "focus": "Fintech, B2B SaaS, MSME Tech",
      "examples": ["Indian Angel Network (IAN)", "Mumbai Angels", "LetsVenture"]
    }},
    {{
      "type": "Seed & Pre-Series A Venture Funds",
      "stage": "Seed",
      "focus": "India-first SaaS, Enterprise Software",
      "examples": ["Blume Ventures", "Kae Capital", "India Quotient"]
    }}
  ],
  "incubators": [
    {{"name": "NSRCEL (IIM Bangalore)", "focus": "Early stage tech startups", "location": "Bangalore"}},
    {{"name": "CIIE.CO (IIM Ahmedabad)", "focus": "Tech inclusion and FinTech", "location": "Ahmedabad"}},
    {{"name": "T-Hub", "focus": "Enterprise tech & scaling", "location": "Hyderabad"}}
  ],
  "pitch_tips": [
    "Highlight unit economics and clear path to LTV/CAC > 3x",
    "Emphasize MSME pain point validation with pilot customer quotes",
    "Showcase regulatory alignment with DPIIT and data privacy standards",
    "Demonstrate SaaS recurring revenue predictability with low churn assumptions"
  ]
}}"""
    raw = _call_section_llm("investors", system_prompt, user_prompt, groq_client, gpt_oss_client, max_tokens=1600)
    return raw.get("investors", raw)


def _gen_competitors(brief: str, evidence: str, groq_client, gpt_oss_client) -> dict:
    system_prompt = (
        "You are a competitive intelligence analyst. Identify 3-5 real competitors or existing alternatives in the market, "
        "their strengths, weaknesses, and how this startup differentiates. "
        "Return ONLY a JSON object matching the schema."
    )
    user_prompt = f"""STARTUP IDEA:
{brief}

EVIDENCE & CONTEXT:
{evidence}

Identify actual direct and indirect competitors/alternatives, key differentiators, market gaps, and strategy.
Return JSON with this exact schema:
{{
  "competitors": [
    {{
      "name": "Khatabook / OkCredit (Digital Ledgers)",
      "type": "Indirect",
      "core_offering": "Digital bookkeeping and credit tracking for small merchants",
      "strength": "Massive distribution and widespread brand recognition among MSMEs",
      "weakness": "Basic recording tool without predictive AI forecasting or cash-flow planning",
      "differentiator": "Automated cash-flow predictive intelligence vs static ledger recording",
      "market_share": "30%",
      "funding": "Series C ($100M+)"
    }},
    {{
      "name": "Traditional CA & Spreadsheet Accounting",
      "type": "Indirect",
      "core_offering": "Manual Excel reconciliation and monthly audit reviews",
      "strength": "Established habit and personalized trust with business owners",
      "weakness": "Retrospective (lagging) analysis; no real-time warning before liquidity crunch",
      "differentiator": "Real-time forward-looking predictive alerts instead of retrospective tax filing",
      "market_share": "50%",
      "funding": "Bootstrapped"
    }},
    {{
      "name": "Clear / Zoho Books",
      "type": "Direct / Alternative",
      "core_offering": "Comprehensive accounting, GST compliance, and invoice management",
      "strength": "Full enterprise accounting suite with deep ERP integrations",
      "weakness": "Complex interface and steep learning curve for micro-entrepreneurs",
      "differentiator": "Lightweight, purpose-built cash-shortage prediction with zero accounting overhead",
      "market_share": "15%",
      "funding": "Established Corporates"
    }}
  ],
  "our_differentiators": [
    "Predictive AI forecasting cash shortages 14-30 days before they occur",
    "Automated smart WhatsApp payment follow-ups tailored to invoice payment history",
    "Seamless one-click GST and bank statement ingestion without manual entry",
    "Actionable micro-recommendations instead of complex accounting ledgers"
  ],
  "market_gaps": [
    "Lack of predictive foresight in entry-level accounting tools",
    "MSMEs struggle with late invoice payments causing working capital insolvency",
    "Overly complex enterprise software inaccessible to non-technical business owners"
  ],
  "competitive_strategy": "Position as the automated proactive cash-flow guardian that works alongside existing tools like Tally or Zoho, focusing on liquidity protection and zero data-entry friction."
}}"""
    raw = _call_section_llm("competitors", system_prompt, user_prompt, groq_client, gpt_oss_client, max_tokens=1600)
    if isinstance(raw, list):
        return {"competitors": raw, "our_differentiators": [], "market_gaps": [], "competitive_strategy": ""}
    if isinstance(raw, dict):
        if "competitors" not in raw and any(k in raw for k in ("name", "core_offering")):
            return {"competitors": [raw], "our_differentiators": [], "market_gaps": [], "competitive_strategy": ""}
        return raw
    return {}


def _gen_risks(brief: str, evidence: str, groq_client, gpt_oss_client) -> dict:
    system_prompt = (
        "You are an enterprise risk management specialist. Identify 5-6 realistic risks across Market, Technical, Financial, "
        "Regulatory, and Operational categories for the startup idea with practical mitigations. "
        "Return ONLY a JSON object matching the schema."
    )
    user_prompt = f"""STARTUP IDEA:
{brief}

EVIDENCE & CONTEXT:
{evidence}

Identify realistic risks with severity, probability, impact, and actionable mitigation strategies.
Return JSON with this exact schema:
{{
  "risks": [
    {{
      "category": "Customer Adoption",
      "severity": "HIGH",
      "probability": "MEDIUM",
      "impact": "MSME owners may hesitate to connect bank accounts or share invoice data due to privacy concerns",
      "risk": "Reluctance to adopt automated financial software among traditional merchants",
      "mitigation": "Provide read-only bank statement upload, local encryption, and trust certifications (ISO 27001 / SOC 2)"
    }},
    {{
      "category": "Market",
      "severity": "MEDIUM",
      "probability": "HIGH",
      "impact": "Slower conversion from free trial to paid subscription tiers",
      "risk": "Price sensitivity and low willingness to pay for standalone SaaS tools",
      "mitigation": "Tie pricing directly to measurable working capital savings and offer low-cost monthly plans"
    }},
    {{
      "category": "Regulatory",
      "severity": "HIGH",
      "probability": "LOW",
      "impact": "Stricter data localization or financial data consent directives from RBI",
      "risk": "Compliance challenges under India Digital Personal Data Protection (DPDP) Act and RBI Account Aggregator guidelines",
      "mitigation": "Partner with licensed RBI Account Aggregators and build DPDP-compliant consent management from Day 1"
    }},
    {{
      "category": "Technical",
      "severity": "MEDIUM",
      "probability": "MEDIUM",
      "impact": "Inaccurate cash-flow predictions during seasonal spikes eroding user trust",
      "risk": "Model prediction errors due to non-standard or fragmented invoice formats",
      "mitigation": "Implement human-in-the-loop validation for edge cases and calibrate prediction intervals with confidence bands"
    }},
    {{
      "category": "Financial",
      "severity": "HIGH",
      "probability": "MEDIUM",
      "impact": "Cash burn exceeds runway before achieving product-market fit",
      "risk": "Extended sales cycles causing working capital depletion",
      "mitigation": "Maintain a disciplined 18-month runway and leverage non-dilutive government grants (SISFS)"
    }}
  ]
}}"""
    raw = _call_section_llm("risks", system_prompt, user_prompt, groq_client, gpt_oss_client, max_tokens=1500)
    res = raw.get("risks", raw)
    if isinstance(res, list):
        return {"risks": res}
    return res


def _gen_crag_trace(brief: str, evidence: str, sources: str, groq_client, gpt_oss_client) -> dict:
    system_prompt = (
        "You are a knowledge grounding auditor. Document how verified evidence and policy context informed the startup blueprint. "
        "Return ONLY a JSON object matching the schema."
    )
    user_prompt = f"""STARTUP IDEA:
{brief}

GROUNDED EVIDENCE:
{evidence}

SOURCES CITED:
{sources}

Document the verified context, inferences, recommendations, and evidence mappings.
Return JSON with this exact schema:
{{
  "verified_context": [
    "Startup India Seed Fund Scheme provides early capital for DPIIT-recognised startups",
    "India MSME sector faces average payment cycles of 60-90 days, driving working capital constraints",
    "RBI Account Aggregator framework provides secure consent-based financial data sharing"
  ],
  "inferences": [
    "AI predictive forecasting addresses the root cause of MSME insolvency by surfacing liquidity gaps ahead of time",
    "A subscription B2B SaaS model is sustainable if unit pricing aligns with MSME software willingness-to-pay"
  ],
  "recommendations": [
    "Apply for DPIIT recognition immediately to unlock SISFS grant eligibility",
    "Integrate with licensed Account Aggregators rather than scraping bank credentials",
    "Focus initial marketing on high-velocity invoice industries like distribution and light manufacturing"
  ],
  "source_usage": [
    {{"claim": "Startup India Seed Fund eligibility & capital guidelines", "source": "DPIIT Startup India Guidelines"}},
    {{"claim": "MSME payment delays and working capital dynamics", "source": "MSME Ministry Annual Report"}},
    {{"claim": "Consent-based data sharing guidelines", "source": "Reserve Bank of India Regulations"}}
  ]
}}"""
    raw = _call_section_llm("crag_trace", system_prompt, user_prompt, groq_client, gpt_oss_client, max_tokens=1400)
    return raw.get("crag_trace", raw)


def _is_section_valid(section_name: str, data: Any) -> bool:
    if not data or not isinstance(data, (dict, list)):
        return False
    if section_name == "bmc":
        if not isinstance(data, dict):
            return False
        non_empty = [k for k in ("value_propositions", "customer_segments", "revenue_streams", "key_activities", "cost_structure") if data.get(k) and len(data[k]) > 0]
        return len(non_empty) >= 3
    elif section_name == "budget":
        if not isinstance(data, dict):
            return False
        return len(data.get("phases", [])) >= 2 and data.get("total_12_months", 0) > 0
    elif section_name == "gtm":
        if not isinstance(data, dict):
            return False
        return bool(data.get("target_market")) or len(data.get("launch_strategy", [])) >= 2 or len(data.get("growth_channels", [])) >= 1
    elif section_name == "investors":
        if not isinstance(data, dict):
            return False
        return len(data.get("government_schemes", [])) >= 1 or len(data.get("funding_roadmap", [])) >= 1
    elif section_name == "competitors":
        if isinstance(data, list):
            return len(data) >= 1
        if isinstance(data, dict):
            comp_list = data.get("competitors", [])
            diff_list = data.get("our_differentiators", [])
            return (isinstance(comp_list, list) and len(comp_list) >= 1) or (isinstance(diff_list, list) and len(diff_list) >= 1)
        return False
    elif section_name == "risks":
        risks_list = data if isinstance(data, list) else data.get("risks", [])
        return len(risks_list) >= 2
    elif section_name == "crag_trace":
        if not isinstance(data, dict):
            return False
        return len(data.get("verified_context", [])) >= 1 or len(data.get("recommendations", [])) >= 1
    return True


def _repair_section(section_name: str, brief: str, evidence: str, sources: str, groq_client, gpt_oss_client) -> dict:
    print(f"[BLUEPRINT REPAIR] Attempting targeted single-section repair for: {section_name.upper()}...")
    if section_name == "bmc":
        return _gen_bmc(brief, evidence, groq_client, gpt_oss_client)
    elif section_name == "budget":
        return _gen_budget(brief, evidence, groq_client, gpt_oss_client)
    elif section_name == "gtm":
        return _gen_gtm(brief, evidence, groq_client, gpt_oss_client)
    elif section_name == "investors":
        return _gen_investors(brief, evidence, groq_client, gpt_oss_client)
    elif section_name == "competitors":
        return _gen_competitors(brief, evidence, groq_client, gpt_oss_client)
    elif section_name == "risks":
        return _gen_risks(brief, evidence, groq_client, gpt_oss_client)
    elif section_name == "crag_trace":
        return _gen_crag_trace(brief, evidence, sources, groq_client, gpt_oss_client)
    return {}


def validate_required_blueprint_fields(data: dict) -> list[str]:
    """
    Validate that specific mandatory sub-fields exist and are non-empty.
    Required by specification:
      - funding.investor_landscape
      - funding.investor_landscape.relevant_incubators
      - funding.investor_landscape.pitch_tips
      - competitors.our_differentiators
      - competitors.market_gaps
      - competitors.competitive_strategy
    """
    missing = []

    # Check Funding / Investors
    inv = data.get("investors") or data.get("funding") or {}
    if not isinstance(inv, dict):
        inv = {}

    inv_landscape = inv.get("investor_landscape") or inv.get("investor_types") or []
    if not isinstance(inv_landscape, list) or len(inv_landscape) == 0:
        missing.append("funding.investor_landscape")

    incubators = inv.get("relevant_incubators") or inv.get("incubators") or []
    if not isinstance(incubators, list) or len(incubators) == 0:
        missing.append("funding.investor_landscape.relevant_incubators")

    pitch_tips = inv.get("pitch_tips") or []
    if not isinstance(pitch_tips, list) or len(pitch_tips) == 0:
        missing.append("funding.investor_landscape.pitch_tips")

    # Check Competitors
    comp = data.get("competitors") or {}
    if not isinstance(comp, dict):
        comp = {}

    diffs = comp.get("our_differentiators") or []
    if not isinstance(diffs, list) or len(diffs) == 0:
        missing.append("competitors.our_differentiators")

    gaps = comp.get("market_gaps") or []
    if not isinstance(gaps, list) or len(gaps) == 0:
        missing.append("competitors.market_gaps")

    strat = comp.get("competitive_strategy") or ""
    if not isinstance(strat, str) or len(strat.strip()) < 15:
        missing.append("competitors.competitive_strategy")

    return missing


def repair_missing_blueprint_fields(missing: list[str], brief: str, evidence: str, groq_client, gpt_oss_client) -> dict:
    """
    Execute ONE small targeted repair LLM call containing ONLY the missing fields.
    Returns a strict JSON object with only the repaired fields.
    """
    schemas = []
    if "funding.investor_landscape" in missing:
        schemas.append('"investor_landscape": [\n    {"type": "Angel Networks & Early Syndicates", "stage": "Pre-Seed / Seed", "focus": "Fintech / B2B SaaS", "examples": ["Indian Angel Network (IAN)", "LetsVenture", "Mumbai Angels"]},\n    {"type": "Micro VCs & Seed Funds", "stage": "Seed", "focus": "India MSME Software", "examples": ["Blume Ventures", "India Quotient", "Kae Capital"]}\n  ]')
    if "funding.investor_landscape.relevant_incubators" in missing:
        schemas.append('"relevant_incubators": [\n    {"name": "CIIE.CO (IIM Ahmedabad)", "focus": "Fintech & Financial Inclusion", "location": "Ahmedabad"},\n    {"name": "NSRCEL (IIM Bangalore)", "focus": "B2B Tech Startups", "location": "Bangalore"},\n    {"name": "T-Hub", "focus": "SaaS Scaling & Corporate Pilots", "location": "Hyderabad"}\n  ]')
    if "funding.investor_landscape.pitch_tips" in missing:
        schemas.append('"pitch_tips": [\n    "Demonstrate customer validation with real pilot MSME retention figures",\n    "Show clear SaaS unit economics with target LTV/CAC > 3x",\n    "Highlight compliance with RBI and Account Aggregator data standards"\n  ]')
    if "competitors.our_differentiators" in missing:
        schemas.append('"our_differentiators": [\n    "Predictive AI forecasting cash shortages 14-30 days before they occur",\n    "Automated smart WhatsApp payment reminders tailored to invoice history",\n    "Seamless one-click GST and bank statement ingestion without manual entry",\n    "Lightweight, zero-training interface designed specifically for non-accountant owners"\n  ]')
    if "competitors.market_gaps" in missing:
        schemas.append('"market_gaps": [\n    "Lack of forward-looking cash forecasting in traditional accounting tools",\n    "Delayed payments from enterprise buyers causing MSME liquidity crunches",\n    "Enterprise ERP suites too expensive and complex for small businesses"\n  ]')
    if "competitors.competitive_strategy" in missing:
        schemas.append('"competitive_strategy": "Position as a lightweight predictive cash guardian that works seamlessly alongside existing accounting software like Tally or Zoho, prioritizing zero-friction automated alerts and liquidity protection."')

    schema_body = ",\n  ".join(schemas)
    system_prompt = (
        "You are an expert startup strategist. Generate high quality content ONLY for the missing required fields in strict JSON format. "
        "Return ONLY a valid JSON object matching the requested schema."
    )
    user_prompt = f"""STARTUP IDEA:
{brief}

EVIDENCE & CONTEXT:
{evidence}

Generate specific, realistic content ONLY for these missing fields:
{{
  {schema_body}
}}"""

    repaired = _call_section_llm("repair", system_prompt, user_prompt, groq_client, gpt_oss_client, max_tokens=1200)
    return repaired


def node_generate_blueprint(
    structured_brief, granite_summary, web_context,
    sector, model_type, stage, target_city, groq_client, gpt_oss_client,
    policy_sources=None, policy_crag=None, investor_context=None, investor_sources=None
):
    import concurrent.futures

    t0 = time.time()
    evidence = (
        f"Granite Policy Summary:\n{granite_summary[:1200] if granite_summary else 'None'}\n\n"
        f"Policy / Evidence Chunks:\n{policy_crag[:1000] if policy_crag else 'General Indian startup regulatory environment.'}\n\n"
        f"Web Market Context:\n{web_context[:600] if web_context else 'None'}"
    )
    sources_str = policy_sources or "Official Indian Policy Documents & Regulations"

    results = {}
    print(f"[CRAG Blueprint] Starting parallel modular generation of all sections...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f_bmc = executor.submit(_gen_bmc, structured_brief, evidence, groq_client, gpt_oss_client)
        f_budget = executor.submit(_gen_budget, structured_brief, evidence, groq_client, gpt_oss_client)
        f_gtm = executor.submit(_gen_gtm, structured_brief, evidence, groq_client, gpt_oss_client)
        f_investors = executor.submit(_gen_investors, structured_brief, evidence, groq_client, gpt_oss_client)
        f_comp = executor.submit(_gen_competitors, structured_brief, evidence, groq_client, gpt_oss_client)
        f_risks = executor.submit(_gen_risks, structured_brief, evidence, groq_client, gpt_oss_client)
        f_trace = executor.submit(_gen_crag_trace, structured_brief, evidence, sources_str, groq_client, gpt_oss_client)

        results["bmc"] = f_bmc.result()
        results["budget"] = f_budget.result()
        results["gtm"] = f_gtm.result()
        results["investors"] = f_investors.result()
        results["competitors"] = f_comp.result()
        results["risks"] = f_risks.result()
        results["crag_trace"] = f_trace.result()

    failed_sections = []
    for sec_name in ["bmc", "budget", "gtm", "investors", "competitors", "risks", "crag_trace"]:
        if not _is_section_valid(sec_name, results.get(sec_name)):
            print(f"[BLUEPRINT] {sec_name}: INVALID / EMPTY -> Triggering single-section repair...")
            repaired = _repair_section(sec_name, structured_brief, evidence, sources_str, groq_client, gpt_oss_client)
            if _is_section_valid(sec_name, repaired):
                print(f"[BLUEPRINT REPAIR] {sec_name}: SUCCESS")
                results[sec_name] = repaired
            else:
                print(f"[BLUEPRINT REPAIR] {sec_name}: FAILED")
                failed_sections.append(sec_name)

    # ── Field-level validation and targeted single repair call ────────────────
    missing_fields = validate_required_blueprint_fields(results)
    print(f"[BLUEPRINT VALIDATION] missing_fields={missing_fields}")

    if missing_fields:
        print(f"[BLUEPRINT REPAIR] repairing {len(missing_fields)} fields")
        repaired_dict = repair_missing_blueprint_fields(missing_fields, structured_brief, evidence, groq_client, gpt_oss_client)
        if repaired_dict and isinstance(repaired_dict, dict):
            # Merge into investors / funding
            inv = results.get("investors") if isinstance(results.get("investors"), dict) else {}
            if "investor_landscape" in repaired_dict or "investor_types" in repaired_dict:
                val = repaired_dict.get("investor_landscape") or repaired_dict.get("investor_types")
                inv["investor_landscape"] = val
                inv["investor_types"] = val
            if "relevant_incubators" in repaired_dict or "incubators" in repaired_dict:
                val = repaired_dict.get("relevant_incubators") or repaired_dict.get("incubators")
                inv["relevant_incubators"] = val
                inv["incubators"] = val
            if "pitch_tips" in repaired_dict:
                inv["pitch_tips"] = repaired_dict["pitch_tips"]
            results["investors"] = inv

            # Merge into competitors
            comp = results.get("competitors") if isinstance(results.get("competitors"), dict) else {}
            if "our_differentiators" in repaired_dict:
                comp["our_differentiators"] = repaired_dict["our_differentiators"]
            if "market_gaps" in repaired_dict:
                comp["market_gaps"] = repaired_dict["market_gaps"]
            if "competitive_strategy" in repaired_dict:
                comp["competitive_strategy"] = repaired_dict["competitive_strategy"]
            results["competitors"] = comp
            print(f"[BLUEPRINT REPAIR] success")

        # Validate again after targeted repair
        remaining_missing = validate_required_blueprint_fields(results)
        if not remaining_missing:
            print(f"[BLUEPRINT FINAL] all required sections present")
        else:
            print(f"[BLUEPRINT VALIDATION] remaining_missing={remaining_missing}")
    else:
        print(f"[BLUEPRINT FINAL] all required sections present")

    for sec_name in ["bmc", "budget", "gtm", "investors", "competitors", "risks", "crag_trace"]:
        status_str = "FAILED" if sec_name in failed_sections else "SUCCESS"
        print(f"[BLUEPRINT] {sec_name}: {status_str}")

    results["status"] = "partial" if failed_sections else "success"
    results["failed_sections"] = failed_sections
    normalized = _normalize_blueprint(results)
    normalized["status"] = results["status"]
    normalized["failed_sections"] = results["failed_sections"]

    elapsed = time.time() - t0
    print(f"[CRAG Blueprint] Modular generation complete in {elapsed:.1f}s. Status: {normalized['status']}, Failed: {failed_sections}")
    return normalized


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

    t_start = time.time()
    t_rewrite = t_retrieve = t_grade = t_refine = t_granite = t_tavily = t_bp = 0.0

    # ── Step 1: Rewrite query (Gemini Flash / Groq) ──────────────────────────
    print("[CRAG] Step 1: Rewriting query...")
    t0 = time.time()
    rewrite = node_rewrite_query(
        query, sector, stage, model_type, target_city, gemini_client
    )
    t_rewrite = time.time() - t0
    result["rewritten_query"]  = rewrite["structured_brief"]
    result["structured_brief"] = rewrite["structured_brief"]
    result["keywords"]         = rewrite["keywords"]
    result["retrieval_queries"]= rewrite["retrieval_queries"]
    result["search_context"]   = rewrite["search_context"]

    search_ctx = rewrite["search_context"]

    # ── Step 2: Retrieve from all 3 collections ───────────────────────────────
    print("[CRAG] Step 2: Retrieving from ChromaDB (text + table + visual)...")
    t0 = time.time()
    docs, metas = node_retrieve(search_ctx, collections, n_per_collection=6)
    t_retrieve = time.time() - t0
    sources = list({m.get("source", "Unknown") for m in metas})
    result["sources"] = sources
    print(f"[CRAG]   Retrieved {len(docs)} chunks from {len(sources)} sources")

    # ── Step 3: Evaluate relevance (CrossEncoder) ─────────────────────────────
    print("[CRAG] Step 3: Grading retrieved chunks using original short query...")
    t0 = time.time()
    scores, raw_logits, confidence, max_logit = node_eval_each_doc(query, docs, reranker)
    t_grade = time.time() - t0
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
            "[CORRECT] Internal knowledge base is strongly relevant. "
            "Blueprint grounded in official policy documents."
        )
        result["should_generate_blueprint"] = True

        print("[CRAG] Branch: CORRECT -> refining PDF context...")
        t0 = time.time()
        refined = node_refine(search_ctx, docs, raw_logits, reranker, top_k=6)
        t_refine = time.time() - t0
        result["internal_context"] = refined

        print("[CRAG] Generating Granite policy summary...")
        t0 = time.time()
        result["summary"] = node_generate_summary(
            result["structured_brief"], refined, granite, "internal"
        )
        t_granite = time.time() - t0

        # Bonus: Tavily explore results (fed into blueprint for richer context)
        print("[CRAG] Fetching Tavily explore results...")
        t0 = time.time()
        explore = node_web_search(search_ctx, rewrite["retrieval_queries"], tavily, sector, max_results=3)
        t_tavily = time.time() - t0
        result["explore_results"] = explore
        web_ctx = ""
        if explore:
            result["sources"].append("tavily_web_search")
            web_ctx = _format_web_context(explore)

        print("[CRAG] Generating 6 blueprint sections (GPT-OSS/Groq)...")
        t0 = time.time()
        result["blueprint"] = node_generate_blueprint(
            result["structured_brief"], result["summary"], web_ctx,
            sector, model_type, stage, target_city, groq_client, gpt_oss_client,
            policy_sources=", ".join([s for s in result["sources"] if s != "tavily_web_search"]) or "Official Indian Policy Documents & Regulations",
            policy_crag=refined,
            investor_context=refined,
            investor_sources=", ".join(result["sources"]) if result["sources"] else "DPIIT, Startup India, SIDBI, Incubator Databases"
        )
        t_bp = time.time() - t0

    # ══════════════════════════════════════════════════════════════════════════
    # BRANCH: AMBIGUOUS
    # ══════════════════════════════════════════════════════════════════════════
    elif confidence == "AMBIGUOUS":
        result["action"] = (
            "[AMBIGUOUS] Partial relevance. Combining policy documents "
            "with live web search for richer context."
        )
        result["should_generate_blueprint"] = True

        print("[CRAG] Branch: AMBIGUOUS -> refining PDF + fetching web...")
        t0 = time.time()
        refined  = node_refine(search_ctx, docs, raw_logits, reranker, top_k=6)
        t_refine = time.time() - t0
        t0 = time.time()
        web_res  = node_web_search(search_ctx, rewrite["retrieval_queries"], tavily, sector, max_results=3)
        t_tavily = time.time() - t0
        web_ctx  = _format_web_context(web_res)

        result["internal_context"] = refined
        result["external_context"] = web_ctx

        combined = (
            "=== FROM POLICY DOCUMENTS ===\n" + refined +
            "\n\n=== FROM LIVE WEB SEARCH ===\n" + web_ctx
        )

        print("[CRAG] Generating Granite policy summary (combined)...")
        t0 = time.time()
        result["summary"] = node_generate_summary(
            result["structured_brief"], combined, granite, "combined"
        )
        t_granite = time.time() - t0

        print("[CRAG] Generating 6 blueprint sections (GPT-OSS/Groq)...")
        t0 = time.time()
        result["blueprint"] = node_generate_blueprint(
            result["structured_brief"], result["summary"], web_ctx,
            sector, model_type, stage, target_city, groq_client, gpt_oss_client,
            policy_sources=", ".join(result["sources"]) if result["sources"] else "Official Policy Documents & Web Sources",
            policy_crag=refined,
            investor_context=combined,
            investor_sources=", ".join(result["sources"]) if result["sources"] else "Government & Market Databases"
        )
        t_bp = time.time() - t0

        result["explore_results"] = web_res
        if web_res:
            result["sources"].append("tavily_web_search")

    # ══════════════════════════════════════════════════════════════════════════
    # BRANCH: INCORRECT
    # ══════════════════════════════════════════════════════════════════════════
    else:
        result["action"] = (
            "[INCORRECT] Knowledge base not relevant enough. "
            "Searching the live web. No blueprint generated - refine your idea."
        )
        result["should_generate_blueprint"] = False

        print("[CRAG] Branch: INCORRECT -> web-only answer...")
        t0 = time.time()
        web_res = node_web_search(search_ctx, rewrite["retrieval_queries"], tavily, sector, max_results=3)
        t_tavily = time.time() - t0
        web_ctx = _format_web_context(web_res)

        result["external_context"] = web_ctx
        result["explore_results"]  = web_res

        result["conversational_response"] = node_conversational_answer(
            result["structured_brief"], web_res, groq_client, gpt_oss_client
        )
        result["sources"] = ["tavily_web_search"] if web_res else []

    t_total = time.time() - t_start

    print(f"\n==================================================")
    print(f"[PERF] Query rewrite: {t_rewrite:.2f}s")
    print(f"[PERF] Chroma retrieval: {t_retrieve:.2f}s")
    print(f"[PERF] CrossEncoder grading: {t_grade:.2f}s")
    if t_refine > 0:
        print(f"[PERF] Refine context: {t_refine:.2f}s")
    if t_granite > 0:
        print(f"[PERF] Granite summary: {t_granite:.2f}s")
    if t_tavily > 0:
        print(f"[PERF] Tavily explore: {t_tavily:.2f}s")
    if t_bp > 0:
        print(f"[PERF] Blueprint sections generation: {t_bp:.2f}s")
    print(f"[PERF] TOTAL BLUEPRINT GENERATION: {t_total:.2f}s")
    print(f"==================================================\n")

    print(f"[CRAG] Done. Blueprint: {result['should_generate_blueprint']}")
    return result