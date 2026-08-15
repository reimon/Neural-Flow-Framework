"""
Neural-Flow Framework — Semantic Search CLI
===========================================
Query the neural-memory index with hybrid keyword + vector search.

Usage:
  python search.py "decisao sobre permissoes de admin"
  python search.py "auth JWT" --top 10
  python search.py "estouro de budget" --type commit
  python search.py "segurança" --sprint sprint-3
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from nf_azure_auth import credencial_search, kwargs_openai
from azure.core.exceptions import HttpResponseError
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
INDEX_NAME = os.environ.get("AZURE_SEARCH_INDEX_NAME", "neural-memory")
OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
EMBEDDING_DEPLOYMENT = os.environ.get(
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"
)


def search(
    query: str,
    top: int = 5,
    doc_type: str | None = None,
    sprint_ref: str | None = None,
) -> list[dict]:
    """
    Hybrid search: keyword + vector.
    Returns list of results with id, content (truncated), source_file, type, timestamp, score.
    """
    openai_client = AzureOpenAI(
        azure_endpoint=OPENAI_ENDPOINT,
        api_version="2024-02-01",
        **kwargs_openai(),
    )
    credential = credencial_search()
    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=INDEX_NAME,
        credential=credential,
    )

    # Generate embedding for semantic vector component
    resp = openai_client.embeddings.create(model=EMBEDDING_DEPLOYMENT, input=[query])
    query_vector = resp.data[0].embedding

    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=top * 2,  # over-fetch for hybrid reranking
        fields="content_vector",
    )

    # Build optional OData filter
    filters = []
    if doc_type:
        filters.append(f"type eq '{doc_type}'")
    if sprint_ref:
        filters.append(f"sprint_ref eq '{sprint_ref}'")
    odata_filter = " and ".join(filters) if filters else None

    try:
        # Preferred mode: semantic + vector + keyword (hybrid)
        semantic_results = search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            filter=odata_filter,
            top=top,
            select=["id", "content", "source_file", "type", "sprint_ref", "timestamp", "seed"],
            query_type="semantic",
            semantic_configuration_name="neural-semantic",
        )
        results = list(semantic_results)
    except HttpResponseError as exc:
        # Free tier and some services do not support semantic ranking.
        if "Semantic search is not enabled" not in str(exc):
            raise
        fallback_results = search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            filter=odata_filter,
            top=top,
            select=["id", "content", "source_file", "type", "sprint_ref", "timestamp", "seed"],
        )
        results = list(fallback_results)

    hits = []
    for r in results:
        hits.append({
            "id": r["id"],
            "score": r.get("@search.reranker_score") or r.get("@search.score", 0.0),
            "type": r.get("type", ""),
            "source_file": r.get("source_file", ""),
            "sprint_ref": r.get("sprint_ref", ""),
            "timestamp": r.get("timestamp", ""),
            "seed": r.get("seed", False),
            "content": r.get("content", "")[:400],  # truncate for display
        })
    return hits


def main() -> None:
    parser = argparse.ArgumentParser(description="Neural-Flow semantic search")
    parser.add_argument("query", help="Natural language query")
    parser.add_argument("--top", type=int, default=5, help="Number of results (default: 5)")
    parser.add_argument("--type", dest="doc_type", choices=["markdown", "commit", "error", "session"],
                        help="Filter by document type")
    parser.add_argument("--sprint", dest="sprint_ref", help="Filter by sprint (e.g. sprint-3)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    results = search(
        query=args.query,
        top=args.top,
        doc_type=args.doc_type,
        sprint_ref=args.sprint_ref,
    )

    if args.json:
        import json
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    print(f"\n=== Neural-Memory: '{args.query}' ({len(results)} results) ===\n")
    for i, r in enumerate(results, 1):
        score = f"{r['score']:.3f}" if r["score"] else "-"
        seed_flag = " [SEED]" if r["seed"] else ""
        print(f"#{i}  score={score}  type={r['type']}{seed_flag}")
        print(f"    source: {r['source_file']}  sprint: {r['sprint_ref'] or '-'}")
        print(f"    time:   {r['timestamp'][:10] if r['timestamp'] else '-'}")
        print(f"    ---")
        # Print content wrapped at 80 chars
        for line in r["content"].splitlines():
            print(f"    {line}")
        print()


if __name__ == "__main__":
    main()
