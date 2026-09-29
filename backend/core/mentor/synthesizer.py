"""
mentor/synthesizer.py
──────────────────────
Synthesizes a grounded, cited answer from retrieved evidence.

PRIMARY model: Groq GPT-OSS-120B  (fast, low-latency)
FALLBACK model: IBM Granite 4.0   (only if Groq is unavailable)

The synthesizer receives:
  - blueprint context (always)
  - chromadb evidence (if retrieved)
  - tavily web evidence (if retrieved)
  - conversation history (sliding window)
  - the user's question + detected intent

It produces a rich markdown answer citing sources.
"""

from __future__ import annotations
import logging
import time

log = logging.getLogger(__name__)

_BASE_SYSTEM = """You are an expert AI Startup Mentor with deep knowledge of the Indian startup ecosystem.

You have already read the founder's complete startup blueprint. You are not a generic chatbot — you are a knowledgeable advisor who has studied this specific startup and can give precise, evidence-backed advice.

Rules:
1. NEVER hallucinate. Only state facts that are present in the provided context.
2. ALWAYS cite your sources using the format: "According to [source]..." or "(Source: [source])".
3. Every significant recommendation must be backed by evidence from the context.
4. Be direct, specific, and actionable — not generic.
5. Use the blueprint data to make answers specific to THIS startup.
6. Maintain conversation continuity — reference previous questions if relevant.
7. Format answers using clear headers, bullet points, and numbered lists where appropriate.
8. If information is not in the provided context, say so clearly and suggest where the founder can find it.
9. Do NOT invent funding schemes, regulations, market sizes, competitors, investors, statistics, or eligibility requirements.
10. Clearly distinguish recommendations from sourced facts.
"""

_INTENT_SYSTEM_ADDONS = {
    "EXECUTION_ROADMAP": """
When generating roadmaps:
- Structure EACH month with: Goal, Tasks (3-5 bullets), Expected Deliverables, Evidence/Proof.
- Ground each task in something from the blueprint or retrieved context.
- Be realistic about what can be achieved at each stage.
""",
    "INVESTOR_PREP": """
When preparing investor materials:
- Generate specific, hard questions that investors WILL ask.
- Include questions about unit economics, defensibility, and team.
- Suggest how to answer each based on the blueprint data.
""",
    "FINANCIAL": """
When discussing finances:
- Reference the actual budget numbers from the blueprint.
- Compare with industry benchmarks if available in context.
- Be specific about rupee amounts and timelines.
""",
    "COMPETITOR": """
When analyzing competitors:
- Reference the specific competitors from the blueprint.
- Highlight actual differentiators from the blueprint data.
- Suggest concrete strategies to win against each named competitor.
""",
    "GOVT_SCHEMES": """
When discussing government schemes:
- List schemes with their actual eligibility criteria from the context.
- Explain the application process if mentioned in the context.
- Prioritize schemes most relevant to this startup's stage and sector.
""",
    "MARKET_VALIDATION": """
When validating the market:
- Reference the specific market size numbers from the blueprint.
- Suggest concrete validation experiments appropriate for this sector.
- Cite any market data found in the retrieved context.
""",
    "RISK_ANALYSIS": """
When analyzing risks:
- Reference the specific risks listed in the blueprint.
- Prioritize by severity (High → Medium → Low).
- For each risk, provide a concrete mitigation strategy grounded in context.
""",
    "FUNDING": """
When discussing funding:
- Reference the funding roadmap and government schemes from the blueprint.
- Specify amounts, timelines, and eligibility criteria when available.
- Prioritize options most suitable for the startup's current stage.
""",
}


def synthesize_answer(
    *,
    question: str,
    intent: str,
    sub_topic: str,
    blueprint_context: str,
    chromadb_context: str,
    tavily_context: str,
    conversation_history: str,
    granite_client,
    groq_client=None,
    is_roadmap: bool = False,
) -> str:
    """
    Synthesize a grounded, cited answer using Groq GPT-OSS-120B (primary)
    with IBM Granite as fallback.

    Parameters
    ----------
    question             : the user's question
    intent               : detected intent code
    sub_topic            : 3-5 word sub-topic description
    blueprint_context    : text extracted from MentorContext
    chromadb_context     : text from ChromaDB PDF retrieval
    tavily_context       : text from Tavily web search
    conversation_history : recent conversation turns
    granite_client       : IBM Granite ModelInference instance (fallback)
    groq_client          : Groq client instance (primary)
    is_roadmap           : if True, use roadmap-specific formatting

    Returns
    -------
    Formatted markdown string
    """

    # Build evidence block
    evidence_parts = []

    if blueprint_context.strip():
        evidence_parts.append(
            "=== STARTUP BLUEPRINT (Your Data) ===\n" + blueprint_context[:3000]
        )

    if chromadb_context.strip():
        evidence_parts.append(
            "=== INTERNAL KNOWLEDGE BASE (PDF Documents) ===\n" + chromadb_context[:2000]
        )

    if tavily_context.strip():
        evidence_parts.append(
            "=== LIVE WEB RESEARCH (Current Data) ===\n" + tavily_context[:2000]
        )

    evidence_block = "\n\n".join(evidence_parts) if evidence_parts else "No additional context retrieved."

    # Build conversation block
    conv_block = ""
    if conversation_history.strip():
        conv_block = f"\n\n{conversation_history}"

    # Build system prompt
    system_msg = _BASE_SYSTEM
    addon = _INTENT_SYSTEM_ADDONS.get(intent, "")
    if addon:
        system_msg += addon

    # Build user prompt
    if is_roadmap or intent == "EXECUTION_ROADMAP":
        user_prompt = _build_roadmap_prompt(question, evidence_block, conv_block, sub_topic)
    else:
        user_prompt = _build_standard_prompt(question, intent, sub_topic, evidence_block, conv_block)

    # ── PRIMARY: Groq GPT-OSS-120B ────────────────────────────────────────────
    if groq_client is not None:
        try:
            t0 = time.time()
            log.info("[MENTOR] Calling Groq GPT-OSS-120B for synthesis...")
            from config import get_settings
            settings = get_settings()
            model_id = settings.GROQ_MODEL  # "openai/gpt-oss-120b"

            resp = groq_client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=1200,
            )
            answer = resp.choices[0].message.content.strip()
            elapsed = time.time() - t0
            log.info(f"[MENTOR] Groq GPT-OSS-120B completed in {elapsed:.1f}s | tokens_approx={len(answer)//4}")
            log.info("[MENTOR] Response validation: PASS (Groq)")
            return answer

        except Exception as groq_err:
            log.warning(f"[MENTOR WARNING] Groq GPT-OSS-120B failed: {groq_err} — trying IBM Granite fallback")

    # ── FALLBACK: IBM Granite ─────────────────────────────────────────────────
    if granite_client is not None:
        try:
            t0 = time.time()
            log.info("[MENTOR] Calling IBM Granite 4.0 (fallback)...")
            response = granite_client.chat(
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user",   "content": user_prompt},
                ],
                params={
                    "max_tokens":  1200,
                    "temperature": 0.3,
                }
            )
            answer = response["choices"][0]["message"]["content"].strip()
            elapsed = time.time() - t0
            log.info(f"[MENTOR] IBM Granite fallback completed in {elapsed:.1f}s")
            log.info("[MENTOR] Response validation: PASS (Granite fallback)")
            return answer

        except Exception as granite_err:
            log.error(f"[MENTOR ERROR] IBM Granite fallback also failed: {granite_err}")

    return (
        "I encountered an error generating a response. "
        "Both the primary (Groq GPT-OSS-120B) and fallback (IBM Granite) models are unavailable. "
        "Please try again in a few moments."
    )


def _build_standard_prompt(question, intent, sub_topic, evidence, conv_history):
    return f"""You have access to the following evidence about this startup:

{evidence}
{conv_history}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUESTION (Intent: {intent} | Topic: {sub_topic}):
{question}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Answer the question using ONLY the provided evidence. 
Cite your sources. Be specific to this startup. Format clearly with headers and bullets.
If the context doesn't have enough information for part of the answer, say so explicitly."""


def _build_roadmap_prompt(question, evidence, conv_history, sub_topic):
    return f"""You have access to the following evidence about this startup:

{evidence}
{conv_history}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUEST (Topic: {sub_topic}):
{question}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generate a detailed, evidence-backed execution roadmap. For EACH phase/month include:

**Month X: [Phase Name]**
**Goal:** [What you're trying to achieve]
**Tasks:**
- Task 1 (cite evidence)
- Task 2 (cite evidence)
- Task 3
**Expected Deliverables:**
- Deliverable 1
- Deliverable 2
**Evidence/Grounding:**
- Cite the specific sources (blueprint data, PDF doc, web result) supporting this plan

Make every task specific to THIS startup's sector, stage, and market. 
Use the blueprint milestones as a starting point and enrich with retrieved evidence."""
