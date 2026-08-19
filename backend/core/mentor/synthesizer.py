"""
mentor/synthesizer.py
──────────────────────
IBM Granite 4.0 synthesizes a grounded, cited answer from the retrieved
evidence. The synthesizer receives:
  - blueprint context (always)
  - chromadb evidence (if retrieved)
  - tavily web evidence (if retrieved)
  - conversation history (sliding window)
  - the user's question + detected intent

It produces:
  - a rich markdown answer citing sources
  - for EXECUTION_ROADMAP intent: a structured month-by-month roadmap
  - for INVESTOR_PREP intent: numbered Q&A or investor questions
"""

from __future__ import annotations

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
    is_roadmap: bool = False,
) -> str:
    """
    Call IBM Granite 4.0 to generate a cited, grounded answer.

    Parameters
    ----------
    question             : the user's question
    intent               : detected intent code
    sub_topic            : 3-5 word sub-topic description
    blueprint_context    : text extracted from MentorContext
    chromadb_context     : text from ChromaDB PDF retrieval
    tavily_context       : text from Tavily web search
    conversation_history : recent conversation turns
    granite_client       : IBM Granite ModelInference instance
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

    try:
        response = granite_client.chat(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": user_prompt},
            ],
            params={
                "max_tokens":  2400,
                "temperature": 0.25,
            }
        )
        return response["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print(f"[Synthesizer] Granite error: {e}")
        return (
            f"I encountered an error generating a grounded response. "
            f"Error: {str(e)[:200]}"
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
