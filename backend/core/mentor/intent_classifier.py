"""
mentor/intent_classifier.py
────────────────────────────
Classifies a user question into one of 14 mentor intents using Groq GPT-OSS-120B.
Returns a structured result consumed by tool_router.py.

Intents
───────
MARKET_VALIDATION     FUNDING             LEGAL
TECHNOLOGY            COMPETITOR          MARKETING
GTM                   FINANCIAL           HIRING
PRODUCT_DEVELOPMENT   GOVT_SCHEMES        RISK_ANALYSIS
INVESTOR_PREP         EXECUTION_ROADMAP   GENERAL
"""

from __future__ import annotations
import json
import logging
import re

from config import get_settings

log = logging.getLogger(__name__)

INTENTS = [
    "MARKET_VALIDATION",
    "FUNDING",
    "LEGAL",
    "TECHNOLOGY",
    "COMPETITOR",
    "MARKETING",
    "GTM",
    "FINANCIAL",
    "HIRING",
    "PRODUCT_DEVELOPMENT",
    "GOVT_SCHEMES",
    "RISK_ANALYSIS",
    "INVESTOR_PREP",
    "EXECUTION_ROADMAP",
    "GENERAL",
]

_INTENT_DESCRIPTIONS = {
    "MARKET_VALIDATION":   "Market size, TAM SAM SOM, feasibility, saturation, customer validation",
    "FUNDING":             "How to raise funding, investors, seed rounds, pitch, burn rate, runway",
    "LEGAL":               "Legal structure, compliance, IP, contracts, regulations, licenses",
    "TECHNOLOGY":          "Tech stack, architecture, tools, infrastructure, build vs buy",
    "COMPETITOR":          "Competitors, competitive analysis, differentiation, market position",
    "MARKETING":           "Branding, content marketing, growth hacking, customer acquisition, PR",
    "GTM":                 "Go-to-market strategy, launch plan, distribution, partnerships",
    "FINANCIAL":           "Revenue, pricing, unit economics, financial projections, P&L",
    "HIRING":              "Team building, hiring plan, roles, equity, culture, co-founders",
    "PRODUCT_DEVELOPMENT": "MVP, product roadmap, features, user research, iteration",
    "GOVT_SCHEMES":        "Government grants, DPIIT, MSME, Startup India, SIDBI, subsidies",
    "RISK_ANALYSIS":       "Risks, pivot decisions, challenges, failure modes, mitigation",
    "INVESTOR_PREP":       "Pitch deck, investor questions, due diligence, valuation, Y Combinator",
    "EXECUTION_ROADMAP":   "Execution plan, monthly roadmap, tasks, milestones, sprint planning",
    "GENERAL":             "General startup advice, miscellaneous questions",
}

_SYSTEM_PROMPT = (
    "You are an intent classifier for an AI Startup Mentor. "
    "Given a user question and recent conversation context, output ONLY a JSON object "
    "with these keys:\n"
    '  "intent"     : one of the intent codes listed\n'
    '  "confidence" : float 0.0–1.0\n'
    '  "sub_topic"  : a brief 3-5 word phrase describing the specific sub-topic\n\n'
    "Intent codes and their meanings:\n"
    + "\n".join(f"  {k}: {v}" for k, v in _INTENT_DESCRIPTIONS.items())
    + "\n\nRespond with ONLY the JSON. No explanation."
)


def classify_intent(
    question: str,
    conversation_tail: str,
    groq_client,
    gpt_oss_client,
) -> dict:
    """
    Classify the user's question into one of the 14 intents.

    PRIMARY: Groq GPT-OSS-120B (fast, reliable)
    FALLBACK: IBM GPT-OSS via watsonx (if Groq fails)
    FINAL FALLBACK: keyword-based heuristic (always works)

    Parameters
    ----------
    question          : current user message
    conversation_tail : last 2-3 turns of conversation (for follow-up context)
    groq_client       : Groq client instance (primary)
    gpt_oss_client    : IBM watsonx GPT-OSS client (fallback)

    Returns
    -------
    dict with keys: intent (str), confidence (float), sub_topic (str)
    """
    user_msg = (
        f"Recent conversation:\n{conversation_tail}\n\n"
        f"Current question: {question}"
    ) if conversation_tail.strip() else f"Question: {question}"

    settings = get_settings()

    # ── PRIMARY: Groq GPT-OSS-120B ────────────────────────────────────────────
    if groq_client is not None:
        try:
            resp = groq_client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": user_msg},
                ],
                temperature=0.0,
                max_tokens=120,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content.strip()
            result = json.loads(raw)
            intent = result.get("intent", "GENERAL").upper()
            if intent not in INTENTS:
                intent = "GENERAL"
            log.info(f"[MENTOR] Intent classified via Groq: {intent}")
            return {
                "intent":     intent,
                "confidence": float(result.get("confidence", 0.8)),
                "sub_topic":  result.get("sub_topic", ""),
            }
        except Exception as groq_err:
            log.warning(f"[MENTOR] Groq intent classification failed: {groq_err}")

    # ── FALLBACK: IBM GPT-OSS via watsonx ─────────────────────────────────────
    if gpt_oss_client is not None:
        try:
            resp = gpt_oss_client.chat(
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": user_msg},
                ],
                params={"max_tokens": 120, "temperature": 0.0}
            )
            raw = resp["choices"][0]["message"]["content"].strip()
            # Clean markdown code blocks and extract JSON
            start = raw.find('{')
            end = raw.rfind('}')
            if start != -1 and end != -1 and end > start:
                raw = raw[start:end+1]
            result = json.loads(raw)
            intent = result.get("intent", "GENERAL").upper()
            if intent not in INTENTS:
                intent = "GENERAL"
            log.info(f"[MENTOR] Intent classified via IBM GPT-OSS (fallback): {intent}")
            return {
                "intent":     intent,
                "confidence": float(result.get("confidence", 0.7)),
                "sub_topic":  result.get("sub_topic", ""),
            }
        except Exception as ibm_err:
            log.warning(f"[MENTOR] IBM GPT-OSS intent classification failed: {ibm_err}")

    # ── FINAL FALLBACK: keyword heuristic (always works, zero latency) ─────────
    intent = _keyword_intent(question)
    log.info(f"[MENTOR] Intent classified via keyword heuristic (final fallback): {intent}")
    return {"intent": intent, "confidence": 0.5, "sub_topic": ""}


def _keyword_intent(question: str) -> str:
    """Fast keyword-based intent classification — used as final fallback."""
    q = question.lower()
    if any(w in q for w in ["risk", "threat", "danger", "challenge", "fail"]):
        return "RISK_ANALYSIS"
    if any(w in q for w in ["fund", "investor", "raise", "capital", "seed", "series", "vc"]):
        return "FUNDING"
    if any(w in q for w in ["competitor", "competition", "rival", "differentiat"]):
        return "COMPETITOR"
    if any(w in q for w in ["scheme", "dpiit", "msme", "government", "grant", "subsid"]):
        return "GOVT_SCHEMES"
    if any(w in q for w in ["market", "tam", "sam", "som", "feasib", "size"]):
        return "MARKET_VALIDATION"
    if any(w in q for w in ["roadmap", "timeline", "milestone", "execution", "month"]):
        return "EXECUTION_ROADMAP"
    if any(w in q for w in ["pitch", "deck", "due diligence", "valuation"]):
        return "INVESTOR_PREP"
    if any(w in q for w in ["gtm", "go-to-market", "launch", "distribut", "channel"]):
        return "GTM"
    if any(w in q for w in ["budget", "revenue", "profit", "cost", "expense", "financial"]):
        return "FINANCIAL"
    if any(w in q for w in ["legal", "compliance", "regulat", "license", "rbi", "sebi"]):
        return "LEGAL"
    return "GENERAL"
