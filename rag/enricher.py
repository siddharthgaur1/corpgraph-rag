"""Step 4: pull relevant SEBI order document snippets from ChromaDB to back graph results with text.

Reuses the ChromaDB collection built by your SEBI Explorer project (order summaries embedded
by order_id/company). If that collection isn't present, enrichment degrades to an empty list
rather than failing the whole pipeline.
"""
from __future__ import annotations

import os

_COLLECTION_NAME = os.environ.get("SEBI_CHROMA_COLLECTION", "sebi_orders")
_PERSIST_DIR = os.environ.get("SEBI_CHROMA_DIR", "./chroma_sebi")


def _get_collection():
    try:
        import chromadb

        client = chromadb.PersistentClient(path=_PERSIST_DIR)
        return client.get_collection(_COLLECTION_NAME)
    except Exception:
        return None  # ponytail: no SEBI Explorer collection available yet, enrichment is optional


def enrich(company_names: list[str], n_results: int = 3) -> list[dict]:
    collection = _get_collection()
    if collection is None or not company_names:
        return []
    snippets = []
    for name in company_names[:10]:
        try:
            result = collection.query(query_texts=[name], n_results=n_results)
            docs = result.get("documents", [[]])[0]
            metas = result.get("metadatas", [[]])[0]
            for doc, meta in zip(docs, metas):
                snippets.append({"company": name, "snippet": doc, "order_id": meta.get("order_id")})
        except Exception:
            continue
    return snippets
