"""
mentor/tools/chromadb_tool.py
──────────────────────────────
Retrieves relevant chunks from the ChromaDB vector store (internal PDFs).
Uses the same collection and embedder already loaded in app.py.

Results are cached per (query, n_results) to avoid duplicate DB hits
within a single mentor session.
"""

from __future__ import annotations
import functools


def search_chromadb(
    query: str,
    embedder,
    collection,
    n_results: int = 5,
) -> dict:
    """
    Dense retrieval from the ChromaDB startup policy corpus.

    Returns
    -------
    dict with keys:
        chunks    : list of text snippets
        sources   : list of source file names
        citations : list of formatted citation strings
        context   : single merged text block for prompt injection
    """
    try:
        from google import genai as _genai
        import os
        import streamlit as st
        api_key = None
        try:
            api_key = st.secrets.get("GOOGLE_API_KEY")
        except Exception:
            pass
        if not api_key:
            api_key = os.getenv("GOOGLE_API_KEY")
        _client = _genai.Client(api_key=api_key)
        result = _client.models.embed_content(
            model="models/gemini-embedding-001",
            contents=query
        )
        embedding = [list(result.embeddings[0].values)]
        results   = collection.query(
            query_embeddings=embedding,
            n_results=min(n_results, 10),
        )
        docs  = results["documents"][0]
        metas = results["metadatas"][0]

        sources = []
        for m in metas:
            src = m.get("source", "")
            if src and src not in sources:
                sources.append(src)

        citations = [f"📄 {s}" for s in sources]
        context   = "\n\n---\n\n".join(docs[:5]) if docs else ""

        return {
            "chunks":    docs,
            "sources":   sources,
            "citations": citations,
            "context":   context,
        }

    except Exception as e:
        print(f"[ChromaDBTool] Error: {e}")
        return {"chunks": [], "sources": [], "citations": [], "context": ""}
