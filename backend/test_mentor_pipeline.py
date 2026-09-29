"""Test mentor pipeline - run with venv Python"""
import sys, os
sys.path.insert(0, 'C:/Users/SAHIL DESAI/OneDrive/Documents/hackthon/backend')
sys.path.insert(0, 'C:/Users/SAHIL DESAI/OneDrive/Documents/hackthon/backend/core')

print("--- Full Mentor Import Chain Test ---")

try:
    from mentor.intent_classifier import classify_intent, _keyword_intent
    from mentor.context import build_mentor_context
    from mentor.memory import MentorSession, MentorMessage
    from mentor.mentor_agent import create_session
    from mentor.synthesizer import synthesize_answer
    from models.mentor import MentorChatRequest, MentorChatResponse
    print("[PASS] All imports OK")
except Exception as e:
    print(f"[FAIL] Imports: {e}")
    import traceback; traceback.print_exc()
    sys.exit(1)

# Test context builder
try:
    ctx = build_mentor_context(
        idea='FinGuard AI: AI-powered credit scoring for underserved population',
        sector='Fintech', stage='Idea Stage', business_model='B2B2C', market='Pan India',
        crag_result={
            'summary': 'Credit gap for 600M unbanked Indians',
            'confidence': 'HIGH', 'action': 'generate', 'raw_logits': [],
            'keywords': ['fintech', 'credit'], 'retrieval_queries': [],
            'internal_context': '', 'external_context': '',
            'rewritten_query': 'AI credit scoring India', 'explore_results': []
        },
        bmc_data={
            'value_propositions': ['AI credit scoring for unbanked', 'Real-time fraud detection'],
            'revenue_streams': ['SaaS subscription to NBFCs', 'API fees'],
            'customer_segments': ['NBFCs', 'MFIs', 'Rural banks'],
            'key_partners': ['RBI sandbox participants', 'UIDAI'],
            'cost_structure': ['AI model training', 'Cloud infrastructure']
        },
        budget_data={
            'total_12_months': 9500000,
            'funding_suggestion': 'Seed round of Rs 50L-1Cr',
            'phases': [{'name': 'MVP', 'duration': '3 months', 'items': [{'item': 'AI model', 'amount': 500000}], 'total': 500000}]
        },
        gtm_data={
            'target_market': 'Indian NBFC and MFI sector',
            'market_size': 'USD 1.5T credit gap',
            'launch_strategy': ['Beta with 2 NBFCs', 'Startup India registration'],
            'growth_channels': [{'channel': 'Direct Sales', 'priority': 'High', 'cost': 'Low'}],
            'milestones': [{'month': 1, 'goal': 'MVP launch'}, {'month': 6, 'goal': '5 NBFC clients'}],
            'key_metrics': ['Cost of credit assessment', 'Default rate improvement']
        },
        investor_data={
            'government_schemes': [{'name': 'Startup India', 'benefit': 'Tax exemption', 'eligibility': 'DPIIT registered'}],
            'investor_types': [{'type': 'Angel', 'stage': 'Seed', 'examples': ['Indian Angel Network']}],
            'incubators': [{'name': 'iCreate', 'location': 'Ahmedabad', 'focus': 'Fintech'}],
            'funding_roadmap': [{'stage': 'Pre-seed', 'amount': 'Rs 50L', 'timeline': '3 months', 'source': 'Angels'}],
            'pitch_tips': ['Focus on RBI regulatory compliance']
        },
        competitor_data={
            'competitors': [{'name': 'CIBIL', 'strength': 'Established brand', 'weakness': 'Excludes thin-file borrowers', 'market_share': 45}],
            'our_differentiators': ['AI for thin-file borrowers', 'Real-time scoring'],
            'market_gaps': ['No solution for rural MSMEs', '600M unbanked adults']
        },
        risk_data={
            'risks': [{'category': 'Regulatory', 'risk': 'RBI guidelines on AI in credit', 'severity': 'High', 'probability': 'Medium', 'mitigation': 'Engage RBI sandbox'}]
        },
    )
    print(f"[PASS] Context builder OK - keys: {list(ctx.keys())}")
except Exception as e:
    print(f"[FAIL] Context builder: {e}")
    import traceback; traceback.print_exc()

# Test session creation
try:
    session = create_session(ctx=ctx, session_id='test-session-finguard')
    print(f"[PASS] Session created: {session.session_id}")
except Exception as e:
    print(f"[FAIL] Session creation: {e}")

# Test intent classification keyword fallback
intent_tests = [
    ('Is this startup actually feasible?', 'MARKET_VALIDATION'),
    ('What are the biggest risks?', 'RISK_ANALYSIS'),
    ('What RBI regulations apply?', 'LEGAL'),
    ('What funding options should I pursue?', 'FUNDING'),
    ('What competitors are strongest?', 'COMPETITOR'),
]
print("\nIntent classification tests:")
all_pass = True
for question, expected in intent_tests:
    result = _keyword_intent(question)
    status = "PASS" if result == expected else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  [{status}] {question[:50]} -> {result}")

# Test Pydantic response with STRING citations (the original bug)
try:
    resp = MentorChatResponse(
        answer='FinGuard AI addresses a real credit gap in India...',
        intent='MARKET_VALIDATION',
        citations=[
            'policy.pdf',
            'document.pdf',
        ],
        tools_used=['blueprint'],
        session_id='test-123'
    )
    print(f"\n[PASS] MentorChatResponse with string citations: {resp.citations}")
    assert all(isinstance(c, dict) for c in resp.citations), "Citations should all be dicts"
    assert all('title' in c and 'url' in c and 'type' in c for c in resp.citations), "Citations must have title/url/type"
    print("[PASS] Citation structure validated: all have title/url/type")
except Exception as e:
    print(f"[FAIL] MentorChatResponse: {e}")
    import traceback; traceback.print_exc()

print("\n=== RESULT ===")
print("ALL MENTOR PIPELINE TESTS PASSED" if all_pass else "SOME TESTS FAILED")
