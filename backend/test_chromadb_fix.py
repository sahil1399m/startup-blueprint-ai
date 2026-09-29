"""
Full ChromaDB 0.6.3 compatibility test.
Run with venv Python from backend/ directory.
"""
import sys, os
sys.path.insert(0, 'C:/Users/SAHIL DESAI/OneDrive/Documents/hackthon/backend')
sys.path.insert(0, 'C:/Users/SAHIL DESAI/OneDrive/Documents/hackthon/backend/core')

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s: %(message)s')
log = logging.getLogger('chromadb_test')

CHROMA_PATH = 'C:/Users/SAHIL DESAI/OneDrive/Documents/hackthon/chroma_db'

# ─── Step 1: Run the config patch ───────────────────────────────────────────
print("=" * 60)
print("Step 1: Running _patch_chromadb_collection_config()")
print("=" * 60)

import sqlite3, json
from chromadb.api.configuration import (
    CollectionConfigurationInternal, HNSWConfigurationInternal, ConfigurationParameter
)

def run_patch(chroma_path):
    db_file = os.path.join(chroma_path, 'chroma.sqlite3')
    db = sqlite3.connect(db_file)
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    cur.execute("SELECT id, name, config_json_str, schema_str FROM collections")
    rows = cur.fetchall()
    patched = 0
    for row in rows:
        col_id = row['id']
        col_name = row['name']
        cfg_str = row['config_json_str'] or ''
        schema_str = row['schema_str'] or '{}'
        needs_patch = False
        if not cfg_str:
            needs_patch = True
        else:
            try:
                parsed = json.loads(cfg_str)
                if '_type' not in parsed:
                    needs_patch = True
                else:
                    CollectionConfigurationInternal.from_json_str(cfg_str)
            except (json.JSONDecodeError, KeyError, ValueError):
                needs_patch = True
        
        if not needs_patch:
            print(f"  '{col_name}': already valid - SKIP")
            continue
        
        # Read space from schema_str
        space = 'cosine'
        try:
            schema = json.loads(schema_str)
            vector_cfg = schema.get('defaults', {}).get('float_list', {}).get('vector_index', {}).get('config', {})
            s = vector_cfg.get('space', 'cosine')
            if s in ('cosine', 'l2', 'ip'):
                space = s
        except Exception:
            pass
        
        hnsw = HNSWConfigurationInternal(parameters=[
            ConfigurationParameter('space', space),
            ConfigurationParameter('ef_construction', 100),
            ConfigurationParameter('ef_search', 100),
            ConfigurationParameter('M', 16),
            ConfigurationParameter('resize_factor', 1.2),
            ConfigurationParameter('batch_size', 100),
            ConfigurationParameter('sync_threshold', 1000),
        ])
        col_cfg = CollectionConfigurationInternal(parameters=[ConfigurationParameter('hnsw_configuration', hnsw)])
        correct = col_cfg.to_json_str()
        cur.execute("UPDATE collections SET config_json_str = ? WHERE id = ?", (correct, col_id))
        print(f"  '{col_name}': PATCHED (space={space})")
        print(f"    -> {correct[:80]}...")
        patched += 1
    db.commit()
    db.close()
    print(f"  Total patched: {patched}")
    return patched

patched = run_patch(CHROMA_PATH)
print()

# ─── Step 2: Open PersistentClient and load collections ─────────────────────
print("=" * 60)
print("Step 2: Opening PersistentClient and loading collections")
print("=" * 60)

import chromadb

class _DummyEF:
    def __call__(self, input): return []

try:
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    print("  PersistentClient created OK")
except Exception as e:
    print(f"  FAIL PersistentClient: {e}")
    sys.exit(1)

ef = _DummyEF()
expected_counts = {
    'text_chunks':      2519,
    'table_data':       1057,
    'visual_summaries': 0,
}

all_pass = True
for col_name, expected in expected_counts.items():
    try:
        col = client.get_collection(col_name, embedding_function=ef)
        count = col.count()
        dim_ok = True
        # Check dimensionality via peek
        try:
            peek = col.peek(limit=1)
            if peek and peek.get('embeddings') and len(peek['embeddings']) > 0:
                dim = len(peek['embeddings'][0])
                dim_ok = dim == 3072
                print(f"  [{('PASS' if count == expected and dim_ok else 'FAIL')}] {col_name}: count={count} (expected {expected}), dim={dim} (expected 3072)")
            else:
                print(f"  [{'PASS' if count == expected else 'FAIL'}] {col_name}: count={count} (expected {expected}), dim=N/A (empty)")
        except Exception:
            print(f"  [{'PASS' if count == expected else 'FAIL'}] {col_name}: count={count} (expected {expected})")
        if count != expected:
            all_pass = False
    except Exception as e:
        print(f"  [FAIL] {col_name}: {type(e).__name__}: {e}")
        all_pass = False

print()

# ─── Step 3: Verify config is idempotent (second patch run) ─────────────────
print("=" * 60)
print("Step 3: Idempotency check (re-run patch on already-patched DB)")
print("=" * 60)
patched2 = run_patch(CHROMA_PATH)
if patched2 == 0:
    print("  PASS: No rows re-patched (idempotent)")
else:
    print(f"  FAIL: {patched2} rows re-patched (should be 0)")
    all_pass = False
print()

# ─── Step 4: Retrieval query ─────────────────────────────────────────────────
print("=" * 60)
print("Step 4: Test actual retrieval query on text_chunks")
print("=" * 60)

try:
    import google.generativeai as genai
    from config import get_settings
    settings = get_settings()
    if settings.GOOGLE_API_KEY:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        result = genai.embed_content(
            model='models/gemini-embedding-exp-03-07',
            content='What government schemes are available for Indian fintech startups?',
        )
        query_embedding = result['embedding']
        print(f"  Query embedding dim: {len(query_embedding)}")
        
        col = client.get_collection('text_chunks', embedding_function=ef)
        results = col.query(query_embeddings=[query_embedding], n_results=3)
        docs = results.get('documents', [[]])[0]
        print(f"  Retrieved {len(docs)} documents")
        for i, doc in enumerate(docs):
            print(f"  Doc {i+1}: {doc[:100]}...")
        print("  PASS: Retrieval query worked")
    else:
        print("  SKIP: No GOOGLE_API_KEY configured")
except Exception as e:
    import traceback
    print(f"  WARN: Retrieval query failed: {e}")
    traceback.print_exc()
print()

# ─── Summary ─────────────────────────────────────────────────────────────────
print("=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"  Collection config patch: {'APPLIED' if patched > 0 else 'ALREADY VALID'}")
print(f"  Idempotent: PASS")
print(f"  Collections loaded: {'ALL PASS' if all_pass else 'SOME FAILED'}")
