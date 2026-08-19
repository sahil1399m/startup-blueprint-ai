"""
dependencies.py — All heavy AI clients as module-level singletons.

Loaded once during FastAPI lifespan startup, then injected into routes
via FastAPI's Depends() system. This keeps all routes stateless and
makes the app trivially testable (swap out the singletons in tests).
"""

from __future__ import annotations
import logging
import os
from typing import Optional, Dict

log = logging.getLogger(__name__)

# ── Singleton holders ─────────────────────────────────────────────────────────
_granite  = None
_gpt_oss  = None   # GPT-OSS-120B via IBM watsonx (PRIMARY generation model)
_groq     = None
_gemini   = None
_tavily   = None
_reranker = None
_collections: Dict = {}   # {"text": col, "table": col, "visual": col}


# ══════════════════════════════════════════════════════════════════════════════
# INITIALISER — called once from main.py lifespan
# ══════════════════════════════════════════════════════════════════════════════
def init_all_clients(settings) -> None:
    """
    Load every AI client during FastAPI startup.
    Errors here will crash the app at startup — intentional,
    because a partially-initialised backend is worse than no backend.
    """
    _init_granite(settings)
    _init_gpt_oss(settings)
    _init_groq(settings)
    _init_gemini(settings)
    _init_tavily(settings)
    _init_reranker()
    _init_chromadb(settings)
    log.info("✅ All AI clients initialised successfully.")


# ── IBM Granite ───────────────────────────────────────────────────────────────
def _init_granite(settings) -> None:
    global _granite
    log.info("Loading IBM Granite (watsonx.ai)…")
    from ibm_watsonx_ai.foundation_models import ModelInference
    _granite = ModelInference(
        model_id="ibm/granite-4-h-small",
        credentials={
            "apikey": settings.IBM_API_KEY,
            "url":    settings.IBM_URL,
        },
        project_id=settings.IBM_PROJECT_ID,
    )
    log.info("✅ IBM Granite loaded.")


# ── GPT-OSS-120B (PRIMARY generation model, same IBM watsonx account) ─────────
def _init_gpt_oss(settings) -> None:
    global _gpt_oss
    log.info("Loading GPT-OSS-120B (IBM watsonx.ai)…")
    from ibm_watsonx_ai.foundation_models import ModelInference
    _gpt_oss = ModelInference(
        model_id="openai/gpt-oss-120b",
        credentials={
            "apikey": settings.IBM_API_KEY,
            "url":    settings.IBM_URL,
        },
        project_id=settings.IBM_PROJECT_ID,
    )
    log.info("✅ GPT-OSS-120B loaded.")


# ── Groq ──────────────────────────────────────────────────────────────────────
def _init_groq(settings) -> None:
    global _groq
    log.info("Loading Groq client…")
    from groq import Groq
    _groq = Groq(api_key=settings.GROQ_API_KEY)
    log.info("✅ Groq loaded.")


# ── Google Gemini ─────────────────────────────────────────────────────────────
def _init_gemini(settings) -> None:
    global _gemini
    log.info("Loading Google Gemini client…")
    import google.generativeai as genai
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    _gemini = genai
    log.info("✅ Gemini loaded.")


# ── Tavily ────────────────────────────────────────────────────────────────────
def _init_tavily(settings) -> None:
    global _tavily
    log.info("Loading Tavily client…")
    from tavily import TavilyClient
    _tavily = TavilyClient(api_key=settings.TAVILY_API_KEY)
    log.info("✅ Tavily loaded.")


# ── CrossEncoder reranker ─────────────────────────────────────────────────────
def _init_reranker() -> None:
    global _reranker
    log.info("Loading CrossEncoder (ms-marco-MiniLM-L-6-v2)…")
    from sentence_transformers import CrossEncoder
    _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    log.info("✅ CrossEncoder loaded.")


# ── ChromaDB compatibility patch ──────────────────────────────────────────────
# The chroma_db was built with a chromadb version that pickles HNSW metadata
# as a plain dict.  The currently-installed version (0.6.x) expects a
# PersistentData dataclass with attribute access, causing:
#   AttributeError: 'dict' object has no attribute 'dimensionality'
# This one-time monkey-patch converts the dict into a PersistentData object.
def _patch_chromadb_persistent_data():
    try:
        import pickle
        from chromadb.segment.impl.vector.local_persistent_hnsw import PersistentData

        _original_load = PersistentData.load_from_file

        @staticmethod
        def _patched_load(filename: str) -> PersistentData:
            with open(filename, "rb") as f:
                data = pickle.load(f)
            if isinstance(data, dict):
                dim = data.get("dimensionality")
                # dimensionality is None in the pickle — read it from header.bin
                if dim is None:
                    import struct
                    header_path = os.path.join(os.path.dirname(filename), "header.bin")
                    if os.path.exists(header_path):
                        with open(header_path, "rb") as hf:
                            raw = hf.read(100)
                        # HNSW header: offset_mult = dim * sizeof(float) + sizeof(int)
                        # The header stores: offset_data, max_elements, cur_element_count,
                        # size_data_per_element, ...
                        # size_data_per_element = dim*4 + 4 (label size)
                        # Attempt to read size_data_per_element at typical offsets
                        # For hnswlib, the first few fields are ints:
                        #   offsetLevel0_ (size_t=8), max_elements_ (size_t=8),
                        #   cur_element_count_ (size_t=8), size_data_per_element_ (size_t=8)
                        if len(raw) >= 32:
                            size_data = struct.unpack('<Q', raw[24:32])[0]
                            # size_data_per_element = dim * sizeof(float) + sizeof(labeltype=size_t=8)
                            inferred_dim = (size_data - 8) // 4
                            if 64 <= inferred_dim <= 4096:
                                dim = inferred_dim
                                log.info(f"  🔧 Inferred dimensionality={dim} from header.bin")
                if dim is None:
                    dim = 3072  # Gemini embedding-001 default
                    log.info(f"  🔧 Using default dimensionality={dim}")
                log.info(f"  🔧 Patching legacy dict→PersistentData for {filename}")
                return PersistentData(
                    dimensionality=dim,
                    total_elements_added=data.get("total_elements_added", 0),
                    id_to_label=data.get("id_to_label", {}),
                    label_to_id=data.get("label_to_id", {}),
                    id_to_seq_id=data.get("id_to_seq_id", {}),
                )
            return data  # already a PersistentData object

        PersistentData.load_from_file = _patched_load
        log.info("✅ ChromaDB PersistentData patch applied.")
    except Exception as e:
        log.warning(f"⚠️  Could not patch ChromaDB PersistentData: {e}")

_patch_chromadb_persistent_data()


# ── ChromaDB (3 collections) ──────────────────────────────────────────────────
def _init_chromadb(settings) -> None:
    global _collections
    log.info(f"Loading ChromaDB collections from '{settings.CHROMA_LOCAL_PATH}'…")
    import chromadb
    client = chromadb.PersistentClient(path=settings.CHROMA_LOCAL_PATH)
    for col_name, key in [
        ("text_chunks",      "text"),
        ("table_data",       "table"),
        ("visual_summaries", "visual"),
    ]:
        try:
            class DummyEF:
                def __call__(self, input): return []
            col = client.get_collection(col_name, embedding_function=DummyEF())
            _collections[key] = col
            log.info(f"  ✅ {col_name}: {col.count()} embeddings")
        except Exception as e:
            log.warning(f"  ⚠️  Collection '{col_name}' not found — setting to None. Error: {e}")
            _collections[key] = None
    log.info("✅ ChromaDB collections loaded.")


# ══════════════════════════════════════════════════════════════════════════════
# FASTAPI DEPENDENCY FUNCTIONS — used with Depends() in route files
# ══════════════════════════════════════════════════════════════════════════════
def get_granite():
    if _granite is None:
        raise RuntimeError("Granite client not initialised")
    return _granite


def get_gpt_oss():
    if _gpt_oss is None:
        raise RuntimeError("GPT-OSS-120B client not initialised")
    return _gpt_oss


def get_groq():
    if _groq is None:
        raise RuntimeError("Groq client not initialised")
    return _groq


def get_gemini():
    if _gemini is None:
        raise RuntimeError("Gemini client not initialised")
    return _gemini


def get_tavily():
    if _tavily is None:
        raise RuntimeError("Tavily client not initialised")
    return _tavily


def get_reranker():
    if _reranker is None:
        raise RuntimeError("Reranker not initialised")
    return _reranker


def get_collections() -> Dict:
    if not _collections:
        raise RuntimeError("ChromaDB collections not initialised")
    return _collections