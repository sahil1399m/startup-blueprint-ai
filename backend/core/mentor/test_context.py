from mentor.context import build_mentor_context, context_to_prompt_block

# Minimal mock data matching what app.py produces
ctx = build_mentor_context(
    idea="AI tutoring app for rural students in Hindi",
    sector="Edtech", stage="Idea Stage",
    business_model="B2C", market="Pan India",
    crag_result={
        "confidence": "CORRECT", "summary": "Policy brief here",
        "rewritten_query": "Rewritten...", "internal_context": "PDF context",
        "external_context": "", "sources": ["doc1.pdf"],
        "explore_results": [], "keywords": ["edtech", "AI", "rural"]
    },
    bmc_data={"revenue_streams": ["Subscription"], "value_propositions": ["Vernacular AI"],"customer_segments": ["Rural students"], "key_partners": [], "cost_structure": []},
    budget_data={"total_12_months": 500000, "funding_suggestion": "Bootstrap", "phases": []},
    gtm_data={"target_market": "Rural India", "market_size": "₹5000 Cr","launch_strategy": [], "growth_channels": [], "milestones": [], "key_metrics": []},
    investor_data={"government_schemes": [{"name": "SIDBI"}], "investor_types": [],"incubators": [], "funding_roadmap": [], "pitch_tips": []},
    competitor_data={"competitors": [{"name": "Byju's", "market_share": 35}],"our_differentiators": ["Vernacular content"], "market_gaps": ["Rural"]},
    risk_data={"risks": [{"category": "Market", "risk": "Low adoption","severity": "High", "probability": "Medium", "mitigation": "Pilot program"}]}
)

print("Keys:", list(ctx.keys()))
print("\nText Summary:\n", context_to_prompt_block(ctx)[:500])
print("\n✅ context.py working")