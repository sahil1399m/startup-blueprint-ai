"""
test_crag_correct_branch_perf_fix.py
=====================================
Regression tests for the Railway worker-restart bug caused by an unbounded
second CrossEncoder inference inside node_refine on the CORRECT branch.

ROOT CAUSE
----------
run_crag() CORRECT branch called:
    node_refine(search_ctx, docs, raw_logits, reranker, top_k=6)

node_refine() decomposed 12 retrieved docs into ~80 sentence-pair strips and
called reranker.predict() a second time.  The first CrossEncoder call (12 pairs)
already took ~52 s on Railway's CPU.  The second call on 80+ pairs took 3-6 min,
exceeding Railway's worker timeout and causing a SIGKILL with no Python traceback.

FIX (crag.py)
-----------------------
1. _select_top_docs(docs, raw_logits, top_k)
   Reuses logits from Step 3 - zero extra CrossEncoder inference.
   CORRECT branch now calls this instead of node_refine.

2. node_refine() hardened for AMBIGUOUS branch:
   a. Strip count capped at MAX_REFINE_STRIPS=60.
   b. Entire function wrapped in try/except that falls back to
      _select_top_docs so the pipeline never dies silently.

REGRESSION TESTS
----------------
1. CORRECT branch reaches blueprint generation without the expensive refine.
2. PDF refinement failure/mock-timeout -> original context used, blueprint generated.
3. INCORRECT + web results -> full blueprint generated, confidence=INCORRECT.
4. INCORRECT + no web results -> conversational response, no blueprint.
5. AMBIGUOUS behavior unchanged.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import json
import types

# ── Path setup ─────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

# ── Stub out uninstalled packages BEFORE importing crag ────────────────────
# google-generativeai and google-genai are only installed on Railway.
# We inject fake modules into sys.modules so crag.py imports succeed locally.
_google_pkg = types.ModuleType("google")
_google_pkg.__path__ = []
sys.modules.setdefault("google", _google_pkg)

_genai_stub = types.ModuleType("google.generativeai")
_genai_stub.configure = MagicMock()
_genai_stub.GenerationConfig = MagicMock()
_genai_stub.GenerativeModel = MagicMock()
sys.modules["google.generativeai"] = _genai_stub
setattr(_google_pkg, "generativeai", _genai_stub)

_genai_new_stub = types.ModuleType("google.genai")
_genai_new_stub.Client = MagicMock()
sys.modules["google.genai"] = _genai_new_stub
setattr(_google_pkg, "genai", _genai_new_stub)

# Also stub chromadb, ibm, sentence_transformers, tavily, groq if not installed
for _mod in ["chromadb", "ibm_watsonx_ai", "ibm_watsonx_ai.foundation_models",
             "sentence_transformers", "tavily", "groq"]:
    if _mod not in sys.modules:
        _stub = types.ModuleType(_mod)
        if _mod == "chromadb":
            _stub.PersistentClient = MagicMock()
        elif _mod == "ibm_watsonx_ai.foundation_models":
            _stub.ModelInference = MagicMock()
        elif _mod == "sentence_transformers":
            _stub.CrossEncoder = MagicMock()
        elif _mod == "tavily":
            _stub.TavilyClient = MagicMock()
        elif _mod == "groq":
            _stub.Groq = MagicMock()
        sys.modules[_mod] = _stub
        # attach to parent if dotted
        if "." in _mod:
            parent, child = _mod.rsplit(".", 1)
            if parent in sys.modules:
                setattr(sys.modules[parent], child, _stub)


from crag import run_crag, _select_top_docs, node_refine, LOWER_THRESHOLD, MAX_REFINE_STRIPS


# ── Shared stubs ─────────────────────────────────────────────────────────────

class _FakeModel:
    def generate_content(self, *a, **kw):
        r = MagicMock()
        r.text = (
            "PROBLEM STATEMENT\nAI food-delivery analytics.\n\n"
            "TARGET USERS\n- Primary: restaurant owners\n\n"
            "CORE SOLUTION\nML demand forecasting.\n\n"
            "KEY FEATURES\n- Feature A\n- Feature B\n\n"
            "TECHNOLOGIES\n- Python, TensorFlow\n\n"
            "INDUSTRY\nFoodtech\n\n"
            "GEOGRAPHY\nIndia\n\n"
            "BUSINESS MODEL\nB2B SaaS\n\n"
            "KEYWORDS:\nfood, delivery, AI, analytics, India, ML, startup\n\n"
            "RETRIEVAL QUERIES:\n"
            "1. Foodtech government schemes India\n"
            "2. Food delivery market size India 2025\n"
            "3. ML demand forecasting restaurants\n"
            "4. FSSAI compliance foodtech startup\n"
            "5. Restaurant analytics SaaS India\n\n"
            "SEARCH CONTEXT:\n"
            "AI-powered demand forecasting platform for Indian food delivery startups."
        )
        return r


class _FakeGeminiClient:
    def GenerativeModel(self, model_name):
        return _FakeModel()


def _make_fake_granite():
    granite = MagicMock()
    granite.chat.return_value = {
        "choices": [{"message": {"content": "Startup India DPIIT grant available."}}]
    }
    return granite


def _make_fake_gpt_oss():
    client = MagicMock()
    client.model_id = "openai/gpt-oss-120b"
    client.chat.side_effect = Exception("Simulated IBM timeout")
    return client


def _make_fake_groq():
    groq_mock = MagicMock()

    def _make_completion(content):
        msg = MagicMock(); msg.content = content
        choice = MagicMock(); choice.message = msg
        resp = MagicMock(); resp.choices = [choice]
        return resp

    bmc_json   = json.dumps({"key_partners":["P"],"key_resources":["R"],"key_activities":["A"],"value_propositions":["V"],"customer_relationships":["CR"],"customer_segments":["CS"],"channels":["Ch"],"cost_structure":["C"],"revenue_streams":["Rs"]})
    budget_json= json.dumps({"phases":[{"name":"MVP","duration":"M1-3","items":[{"item":"Eng","amount":200000}],"total":200000}],"total_12_months":700000,"funding_suggestion":"SISFS"})
    gtm_json   = json.dumps({"target_market":"Indian restaurants","market_size":"TAM: $2B","launch_strategy":["Pilot"],"growth_channels":[{"channel":"LI","strategy":"demos","rationale":"reach","priority":"HIGH","cost":"LOW"}],"milestones":[{"month":3,"goal":"25 pilots"}],"key_metrics":["MRR"]})
    inv_json   = json.dumps({"funding_roadmap":[{"stage":"Seed","timeline":"M1-6","source":"SISFS","amount":"Rs 20L"}],"government_schemes":[{"name":"SISFS","benefit":"Rs 20L","eligibility":"DPIIT","relevance":"NI","limitations":"MS","amount":"Rs 20L"}],"investor_types":[{"type":"Angel","stage":"Seed","focus":"FT","examples":["IAN"]}],"incubators":[{"name":"NSRCEL","focus":"Tech","location":"BLR"}],"pitch_tips":["Show val"]})
    comp_json  = json.dumps({"competitors":[{"name":"Petpooja","type":"Direct","core_offering":"POS","strength":"Reach","weakness":"NoML","differentiator":"AI","market_share":"20%","funding":"$5M"}],"our_differentiators":["ML"],"market_gaps":["Forecast"],"competitive_strategy":"Post-POS."})
    risks_json = json.dumps({"risks":[{"category":"Market","severity":"HIGH","probability":"MED","impact":"Slow","risk":"Trust","mitigation":"Demos"}]})
    trace_json = json.dumps({"verified_context":["SISFS"],"inferences":["PMF"],"recommendations":["DPIIT"],"source_usage":[{"claim":"SISFS","source":"DPIIT"}]})

    section_jsons = [bmc_json, budget_json, gtm_json, inv_json, comp_json, risks_json, trace_json]
    _call_count = [0]

    def _side_effect(*args, **kwargs):
        idx = _call_count[0] % len(section_jsons)
        _call_count[0] += 1
        return _make_completion(section_jsons[idx])

    groq_mock.chat.completions.create.side_effect = _side_effect
    return groq_mock


def _make_fake_reranker(confidence):
    reranker = MagicMock()
    logit_map = {
        "CORRECT":   [-3.0, -5.0, -6.0, -3.5, -4.5, -5.5, -3.2, -4.8, -5.9, -3.1, -4.2, -5.3],
        "AMBIGUOUS": [-5.5, -6.0, -7.0, -5.8, -6.3, -6.9, -5.2, -6.1, -6.8, -5.4, -6.5, -6.7],
        "INCORRECT": [-8.0, -9.0, -10.0],
    }
    reranker.predict.return_value = logit_map[confidence]
    return reranker


def _make_fake_tavily(has_results):
    tavily = MagicMock()
    if has_results:
        tavily.search.return_value = {
            "results": [
                {"title": "Foodtech AI India", "content": "AI demand forecasting for restaurants.", "url": "https://yourstory.com/foodtech", "score": 0.80},
                {"title": "Indian Foodtech 2025", "content": "India foodtech $15B by 2025.", "url": "https://example.com/foodtech", "score": 0.70},
            ]
        }
    else:
        tavily.search.return_value = {"results": []}
    return tavily


def _make_fake_collections(has_docs):
    col = MagicMock()
    if has_docs:
        col.count.return_value = 6
        col.query.return_value = {
            "documents": [["Doc A about foodtech policy", "Doc B about MSME", "Doc C about funding",
                           "Doc D about FSSAI compliance", "Doc E about incubators", "Doc F about Startup India"]],
            "metadatas": [[
                {"source": "policy.pdf"}, {"source": "msme.pdf"}, {"source": "fund.pdf"},
                {"source": "fssai.pdf"}, {"source": "incubators.pdf"}, {"source": "startupindia.pdf"},
            ]],
            "distances": [[0.30, 0.35, 0.40, 0.42, 0.48, 0.52]],
        }
    else:
        col.count.return_value = 0
    return {"text": col, "table": col, "visual": col}


# ════════════════════════════════════════════════════════════════════════════
# Unit tests for _select_top_docs
# ════════════════════════════════════════════════════════════════════════════
class TestSelectTopDocs(unittest.TestCase):

    def test_returns_top_k_by_logit_descending(self):
        docs = ["doc_A", "doc_B", "doc_C", "doc_D"]
        logits = [-3.0, -5.0, -4.0, -6.0]
        result = _select_top_docs(docs, logits, top_k=2)
        self.assertIn("doc_A", result)
        self.assertIn("doc_C", result)
        self.assertNotIn("doc_B", result)

    def test_filters_below_lower_threshold(self):
        docs = ["doc_good", "doc_bad"]
        logits = [-3.0, -9.0]
        result = _select_top_docs(docs, logits, top_k=5)
        self.assertIn("doc_good", result)
        self.assertNotIn("doc_bad", result)

    def test_all_below_threshold_returns_best_single(self):
        """Even if everything is below threshold, returns the highest-scoring doc."""
        docs = ["doc_worst", "doc_least_bad"]
        logits = [-9.0, -8.0]
        result = _select_top_docs(docs, logits, top_k=5)
        self.assertIn("doc_least_bad", result)

    def test_empty_docs_returns_empty_string(self):
        result = _select_top_docs([], [], top_k=5)
        self.assertEqual(result, "")


# ════════════════════════════════════════════════════════════════════════════
# Unit tests for node_refine fallback & cap
# ════════════════════════════════════════════════════════════════════════════
class TestNodeRefineFallback(unittest.TestCase):

    def test_node_refine_fallback_on_reranker_exception(self):
        """If reranker.predict() raises, node_refine must fall back to logit-sorted docs."""
        bad_reranker = MagicMock()
        bad_reranker.predict.side_effect = RuntimeError("Simulated CrossEncoder OOM")
        docs = ["doc_A relevant policy text about startup India funding for foodtech sector",
                "doc_B about MSME schemes for MSMEs in India government grants"]
        logits = [-3.0, -5.0]
        result = node_refine("foodtech startup India", docs, logits, bad_reranker, top_k=2)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)
        self.assertIn("doc_A", result)

    def test_node_refine_caps_strips_at_max(self):
        """node_refine must not feed more than MAX_REFINE_STRIPS pairs to predict()."""
        many_sentences = ". ".join(
            [f"This is sentence number {i} about startup policy India for foodtech startups" for i in range(200)]
        ) + "."
        docs = [many_sentences]
        logits = [-3.0]
        mock_reranker = MagicMock()
        mock_reranker.predict.return_value = [-3.0] * MAX_REFINE_STRIPS
        node_refine("startup India policy", docs, logits, mock_reranker, top_k=5)
        actual_pairs = mock_reranker.predict.call_args[0][0]
        self.assertLessEqual(
            len(actual_pairs), MAX_REFINE_STRIPS,
            f"predict() received {len(actual_pairs)} pairs; expected <= {MAX_REFINE_STRIPS}"
        )


# ════════════════════════════════════════════════════════════════════════════
# Integration tests: full run_crag pipeline
# ════════════════════════════════════════════════════════════════════════════
class TestCRAGPipelineRegression(unittest.TestCase):

    def _run(self, confidence, tavily_has_results=True, reranker=None):
        reranker = reranker or _make_fake_reranker(confidence)
        with patch("crag._get_gemini_embedding", return_value=[0.1] * 768):
            return run_crag(
                query="AI-powered demand forecasting for Indian food delivery startups",
                sector="foodtech",
                stage="idea",
                model_type="B2B",
                target_city="Mumbai",
                collections=_make_fake_collections(has_docs=(confidence != "INCORRECT")),
                reranker=reranker,
                granite=_make_fake_granite(),
                tavily=_make_fake_tavily(tavily_has_results),
                groq_client=_make_fake_groq(),
                gemini_client=_FakeGeminiClient(),
                gpt_oss_client=_make_fake_gpt_oss(),
            )

    def test_correct_branch_generates_blueprint_without_extra_reranker_call(self):
        """
        CORRECT branch: blueprint generated, reranker.predict() called exactly once.
        A second call would indicate node_refine is still running in CORRECT branch.
        """
        reranker = _make_fake_reranker("CORRECT")
        result = self._run("CORRECT", reranker=reranker)

        self.assertEqual(result["confidence"], "CORRECT")
        self.assertTrue(result["should_generate_blueprint"])

        predict_calls = reranker.predict.call_count
        self.assertEqual(
            predict_calls, 1,
            f"Expected reranker.predict() called exactly 1 time (Step 3 grading only); "
            f"got {predict_calls}. A second call means node_refine CrossEncoder is still "
            f"running in the CORRECT branch (the Railway worker-restart bug)."
        )

        bp = result.get("blueprint", {})
        non_empty = [k for k, v in bp.items()
                     if v and v not in ({}, []) and k not in ("status", "failed_sections")]
        self.assertGreater(len(non_empty), 0, f"Blueprint has no sections. Keys: {list(bp.keys())}")
        self.assertTrue(result.get("internal_context"), "internal_context must be populated")
        print(f"\n[TEST 1 PASS] confidence={result['confidence']}, "
              f"predict_calls={predict_calls}, sections={non_empty}")

    def test_correct_branch_continues_when_refine_would_fail(self):
        """
        CORRECT branch completes even if a hypothetical second predict() call
        would raise MemoryError (simulating OOM that killed Railway previously).
        """
        reranker = MagicMock()
        call_count = [0]

        def predict_side_effect(pairs):
            call_count[0] += 1
            if call_count[0] == 1:
                return [-3.0, -5.0, -6.0, -3.5, -4.5, -5.5, -3.2, -4.8, -5.9, -3.1, -4.2, -5.3]
            raise MemoryError("Simulated OOM on second CrossEncoder call")

        reranker.predict.side_effect = predict_side_effect
        result = self._run("CORRECT", reranker=reranker)

        self.assertEqual(result["confidence"], "CORRECT")
        self.assertTrue(result["should_generate_blueprint"])
        self.assertEqual(call_count[0], 1,
            "predict() must be called exactly once; CORRECT branch must not trigger a second call")
        print(f"\n[TEST 2 PASS] confidence={result['confidence']}, predict_calls={call_count[0]}")

    def test_incorrect_with_web_results_generates_blueprint(self):
        """INCORRECT + Tavily results -> full blueprint, confidence stays INCORRECT."""
        result = self._run("INCORRECT", tavily_has_results=True)

        self.assertEqual(result["confidence"], "INCORRECT")
        self.assertTrue(result["should_generate_blueprint"])
        self.assertIn("[INCORRECT]", result["action"])
        self.assertNotIn("No blueprint generated", result["action"])

        bp = result.get("blueprint", {})
        non_empty = [k for k, v in bp.items()
                     if v and v not in ({}, []) and k not in ("status", "failed_sections")]
        self.assertGreater(len(non_empty), 0, f"Blueprint empty. Keys: {list(bp.keys())}")
        self.assertTrue(result.get("external_context"))
        print(f"\n[TEST 3 PASS] confidence={result['confidence']}, sections={non_empty}")

    def test_incorrect_without_web_results_gives_conversational_response(self):
        """INCORRECT + Tavily empty -> no blueprint, conversational redirect."""
        result = self._run("INCORRECT", tavily_has_results=False)

        self.assertEqual(result["confidence"], "INCORRECT")
        self.assertFalse(result["should_generate_blueprint"])
        self.assertIn("No blueprint generated", result["action"])

        bp = result.get("blueprint", {})
        populated = [k for k, v in bp.items()
                     if v and v not in ({}, []) and k not in ("status", "failed_sections")]
        self.assertEqual(len(populated), 0, "Blueprint must be empty")
        print(f"\n[TEST 4 PASS] confidence={result['confidence']}, "
              f"should_generate={result['should_generate_blueprint']}")

    def test_ambiguous_branch_generates_blueprint_unchanged(self):
        """AMBIGUOUS branch still generates a full blueprint with bounded node_refine."""
        reranker = _make_fake_reranker("AMBIGUOUS")
        result = self._run("AMBIGUOUS", tavily_has_results=True, reranker=reranker)

        self.assertEqual(result["confidence"], "AMBIGUOUS")
        self.assertTrue(result["should_generate_blueprint"])

        bp = result.get("blueprint", {})
        non_empty = [k for k, v in bp.items()
                     if v and v not in ({}, []) and k not in ("status", "failed_sections")]
        self.assertGreater(len(non_empty), 0, f"Blueprint empty. Keys: {list(bp.keys())}")

        predict_calls = reranker.predict.call_count
        self.assertGreaterEqual(predict_calls, 1)
        print(f"\n[TEST 5 PASS] confidence={result['confidence']}, "
              f"predict_calls={predict_calls}, sections={non_empty}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
