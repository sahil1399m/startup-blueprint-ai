"""
test_crag_incorrect_fallback.py
================================
Regression test for the production bug where an INCORRECT CRAG classification
caused all blueprint sections to be empty even when Tavily web search returned
relevant external context.

BUG (before fix)
----------------
In run_crag(), the INCORRECT branch unconditionally set:
    result["should_generate_blueprint"] = False
...before running Tavily web search. Even when Tavily returned high-quality
results (scores 0.8066, 0.6997, 0.6488), the blueprint generation gate in
routes/blueprint.py read should_generate_blueprint=False and skipped all
section generation, yielding empty blueprint sections and HTTP 200.

FIX
---
The INCORRECT branch now:
1. Always runs Tavily web search first.
2. If Tavily returns results -> sets should_generate_blueprint=True and
   generates the full blueprint from web context (same as AMBIGUOUS branch
   but without PDF context).
3. If Tavily returns nothing -> keeps should_generate_blueprint=False and
   falls through to the existing conversational redirect.

This file contains:
    TestIncorrectBranchFallback
      - test_incorrect_with_web_results_generates_blueprint
      - test_incorrect_without_web_results_no_blueprint
      - test_correct_branch_unchanged
      - test_ambiguous_branch_unchanged
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import json

# Path setup
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))


# ─── Stubs ────────────────────────────────────────────────────────────────────

class _FakeModel:
    def generate_content(self, *a, **kw):
        r = MagicMock()
        r.text = (
            "PROBLEM STATEMENT\nAI agritech platform.\n\n"
            "TARGET USERS\n- Primary: farmers\n\n"
            "CORE SOLUTION\nML crop disease detection.\n\n"
            "KEY FEATURES\n- Feature A\n- Feature B\n\n"
            "TECHNOLOGIES\n- Python, TensorFlow\n\n"
            "INDUSTRY\nAgritech\n\n"
            "GEOGRAPHY\nIndia\n\n"
            "BUSINESS MODEL\nB2B SaaS\n\n"
            "KEYWORDS:\ncrop, disease, AI, agritech, India, farm, ML, startup\n\n"
            "RETRIEVAL QUERIES:\n"
            "1. Agritech government schemes India\n"
            "2. Crop disease AI market size India\n"
            "3. Agritech funding investors\n"
            "4. ML crop detection technology\n"
            "5. Agriculture startup legal compliance India\n\n"
            "SEARCH CONTEXT:\n"
            "AI-powered crop disease detection platform for Indian farmers using ML."
        )
        return r


class _FakeGeminiClient:
    def GenerativeModel(self, model_name):
        return _FakeModel()


def _make_fake_granite():
    granite = MagicMock()
    granite.chat.return_value = {
        "choices": [{"message": {"content": "Startup India SISFS grant available."}}]
    }
    return granite


def _make_fake_gpt_oss():
    client = MagicMock()
    client.model_id = "openai/gpt-oss-120b"
    client.chat.side_effect = Exception("Simulated IBM timeout")
    return client


def _make_fake_groq():
    groq = MagicMock()

    def _make_completion(content):
        msg = MagicMock(); msg.content = content
        choice = MagicMock(); choice.message = msg
        resp = MagicMock(); resp.choices = [choice]
        return resp

    bmc_json = json.dumps({"key_partners":["Partner A"],"key_resources":["Resource A"],"key_activities":["Activity A"],"value_propositions":["Prop A"],"customer_relationships":["Rel A"],"customer_segments":["Segment A"],"channels":["Channel A"],"cost_structure":["Cost A"],"revenue_streams":["Stream A"]})
    budget_json = json.dumps({"phases":[{"name":"MVP","duration":"Month 1-3","items":[{"item":"Engineering","amount":200000}],"total":200000},{"name":"Launch","duration":"Month 4-6","items":[{"item":"Marketing","amount":150000}],"total":150000},{"name":"Growth","duration":"Month 7-12","items":[{"item":"Scaling","amount":350000}],"total":350000}],"total_12_months":700000,"funding_suggestion":"SISFS"})
    gtm_json = json.dumps({"target_market":"Indian farmers","market_size":"TAM: $3B","launch_strategy":["1. Pilot 20 farmers","2. Expand 500"],"growth_channels":[{"channel":"WhatsApp","strategy":"demos","rationale":"wide reach","priority":"HIGH","cost":"LOW"}],"milestones":[{"month":3,"goal":"25 pilots"}],"key_metrics":["MRR","CAC"]})
    investors_json = json.dumps({"funding_roadmap":[{"stage":"Seed","timeline":"Month 1-6","source":"SISFS","amount":"Rs 20L"}],"government_schemes":[{"name":"SISFS","benefit":"Rs 20L grant","eligibility":"DPIIT","relevance":"Non-dilutive","limitations":"Milestone","amount":"Rs 20L"}],"investor_types":[{"type":"Angel","stage":"Seed","focus":"Agritech","examples":["IAN"]}],"incubators":[{"name":"NSRCEL","focus":"Tech","location":"Bangalore"}],"pitch_tips":["Show farmer validation"]})
    competitors_json = json.dumps({"competitors":[{"name":"Plantix","type":"Direct","core_offering":"Crop disease app","strength":"Wide reach","weakness":"No advisory","differentiator":"AI advisory","market_share":"30%","funding":"$10M"}],"our_differentiators":["Real-time ML detection"],"market_gaps":["Advisory after detection"],"competitive_strategy":"Position as post-detection advisor."})
    risks_json = json.dumps({"risks":[{"category":"Market","severity":"HIGH","probability":"MEDIUM","impact":"Slow adoption","risk":"Farmer trust","mitigation":"Local demos"},{"category":"Technical","severity":"MEDIUM","probability":"LOW","impact":"False positives","risk":"Model errors","mitigation":"Human in loop"}]})
    trace_json = json.dumps({"verified_context":["SISFS available for agritech"],"inferences":["AI crop disease PMF in India"],"recommendations":["Apply DPIIT recognition"],"source_usage":[{"claim":"SISFS eligibility","source":"DPIIT"}]})

    section_jsons = [bmc_json, budget_json, gtm_json, investors_json, competitors_json, risks_json, trace_json]
    _call_count = [0]

    def _side_effect(*args, **kwargs):
        idx = _call_count[0] % len(section_jsons)
        _call_count[0] += 1
        return _make_completion(section_jsons[idx])

    groq.chat.completions.create.side_effect = _side_effect
    return groq


def _make_fake_reranker(confidence):
    reranker = MagicMock()
    logit_map = {
        "CORRECT":   [-3.0, -5.0, -6.0],
        "AMBIGUOUS": [-5.5, -6.0, -7.0],
        "INCORRECT": [-8.0, -9.0, -10.0],
    }
    reranker.predict.return_value = logit_map[confidence]
    return reranker


def _make_fake_tavily(has_results):
    tavily = MagicMock()
    if has_results:
        tavily.search.return_value = {
            "results": [
                {"title":"Plantix: AI Crop Disease Detection India","content":"Plantix uses CV to detect crop diseases.","url":"https://yourstory.com/plantix","score":0.8066},
                {"title":"Indian Agritech Market Landscape 2025","content":"India agritech market $24B by 2025.","url":"https://example.com/agritech","score":0.6997},
                {"title":"AI Crop Disease Startup Funding","content":"Agritech AI startups raised seed rounds under Startup India.","url":"https://inc42.com/agritech","score":0.6488},
            ]
        }
    else:
        tavily.search.return_value = {"results": []}
    return tavily


def _make_fake_collections(has_docs):
    col = MagicMock()
    if has_docs:
        col.count.return_value = 3
        col.query.return_value = {
            "documents": [["Doc A about agritech", "Doc B about MSME", "Doc C about funding"]],
            "metadatas": [[{"source": "policy.pdf"}, {"source": "msme.pdf"}, {"source": "fund.pdf"}]],
            "distances": [[0.35, 0.45, 0.55]],
        }
    else:
        col.count.return_value = 0
    return {"text": col, "table": col, "visual": col}


# ─── Test suite ───────────────────────────────────────────────────────────────

_PATCHES = [
    patch("chromadb.PersistentClient", MagicMock()),
    patch("ibm_watsonx_ai.foundation_models.ModelInference", MagicMock()),
    patch("sentence_transformers.CrossEncoder", MagicMock()),
    patch("google.generativeai.configure", MagicMock()),
    patch("google.generativeai.GenerationConfig", MagicMock()),
    patch("google.genai.Client", MagicMock()),
    patch("tavily.TavilyClient", MagicMock()),
    patch("groq.Groq", MagicMock()),
]

for p in _PATCHES:
    p.start()

from crag import run_crag


class TestIncorrectBranchFallback(unittest.TestCase):

    def _run_crag(self, confidence, tavily_has_results):
        with patch("crag._get_gemini_embedding", return_value=[0.1] * 768):
            return run_crag(
                query="AI-powered crop disease detection for Indian farmers",
                sector="agritech",
                stage="idea",
                model_type="B2B",
                target_city="Bangalore",
                collections=_make_fake_collections(has_docs=(confidence != "INCORRECT")),
                reranker=_make_fake_reranker(confidence),
                granite=_make_fake_granite(),
                tavily=_make_fake_tavily(tavily_has_results),
                groq_client=_make_fake_groq(),
                gemini_client=_FakeGeminiClient(),
                gpt_oss_client=_make_fake_gpt_oss(),
            )

    def test_incorrect_with_web_results_generates_blueprint(self):
        """INCORRECT + Tavily has results -> blueprint generated, confidence stays INCORRECT"""
        result = self._run_crag("INCORRECT", tavily_has_results=True)

        self.assertEqual(result["confidence"], "INCORRECT",
            "confidence must remain INCORRECT - CRAG classification must not be altered")
        self.assertTrue(result["should_generate_blueprint"],
            "should_generate_blueprint must be True when Tavily returns results")
        self.assertNotIn("No blueprint generated", result["action"],
            "action must not say 'No blueprint generated' when web results exist")
        self.assertIn("[INCORRECT]", result["action"])

        bp = result.get("blueprint", {})
        self.assertIsInstance(bp, dict)
        non_empty = [k for k, v in bp.items()
                     if v and v not in ({}, []) and k not in ("status", "failed_sections")]
        self.assertGreater(len(non_empty), 0,
            f"At least one blueprint section must be non-empty. Got bp keys: {list(bp.keys())}")
        self.assertTrue(result.get("external_context"),
            "external_context must be populated when web results are available")
        print(f"\n[TEST 1 PASS] confidence={result['confidence']}, should_generate={result['should_generate_blueprint']}, non_empty_sections={non_empty}")

    def test_incorrect_without_web_results_no_blueprint(self):
        """INCORRECT + Tavily empty -> no blueprint, conversational redirect"""
        result = self._run_crag("INCORRECT", tavily_has_results=False)

        self.assertEqual(result["confidence"], "INCORRECT")
        self.assertFalse(result["should_generate_blueprint"],
            "should_generate_blueprint must be False when Tavily also fails")
        self.assertIn("No blueprint generated", result["action"])

        bp = result.get("blueprint", {})
        populated = [k for k, v in bp.items()
                     if v and v not in ({}, []) and k not in ("status", "failed_sections")]
        self.assertEqual(len(populated), 0,
            "blueprint must be empty when web search also returns nothing")
        print(f"\n[TEST 2 PASS] confidence={result['confidence']}, should_generate={result['should_generate_blueprint']}")

    def test_correct_branch_unchanged(self):
        """CORRECT branch must still generate a blueprint"""
        result = self._run_crag("CORRECT", tavily_has_results=True)
        self.assertEqual(result["confidence"], "CORRECT")
        self.assertTrue(result["should_generate_blueprint"])
        bp = result.get("blueprint", {})
        non_empty = [k for k, v in bp.items()
                     if v and v not in ({}, []) and k not in ("status", "failed_sections")]
        self.assertGreater(len(non_empty), 0)
        print(f"\n[TEST 3 PASS] confidence={result['confidence']}, should_generate={result['should_generate_blueprint']}")

    def test_ambiguous_branch_unchanged(self):
        """AMBIGUOUS branch must still generate a blueprint"""
        result = self._run_crag("AMBIGUOUS", tavily_has_results=True)
        self.assertEqual(result["confidence"], "AMBIGUOUS")
        self.assertTrue(result["should_generate_blueprint"])
        bp = result.get("blueprint", {})
        non_empty = [k for k, v in bp.items()
                     if v and v not in ({}, []) and k not in ("status", "failed_sections")]
        self.assertGreater(len(non_empty), 0)
        print(f"\n[TEST 4 PASS] confidence={result['confidence']}, should_generate={result['should_generate_blueprint']}")


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        for p in _PATCHES:
            try:
                p.stop()
            except RuntimeError:
                pass
