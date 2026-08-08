"""
Neural-Flow Framework — Neural Memory MCP Server
=================================================
Exposes two MCP tools to GitHub Copilot in VS Code:

  query_neural_memory(question)
    → Semantic hybrid search in Azure AI Search (neural-memory index).
      Returns top-K chunks with source_file, type, timestamp, and content.
      Used BEFORE any technically significant task to surface relevant
      decisions, sprint records, and historical context.

  check_contradiction(proposal)
    → Searches the index for records that may contradict the proposed action.
      Returns a verdict (CLEAR | WARNING | BLOCK) and matching evidence.
      Feeds the Circuit Breaker protocol to prevent alucinação técnica.

Environment (mirrors scripts/.env):
  AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_ADMIN_KEY, AZURE_SEARCH_INDEX_NAME
  AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_EMBEDDING_DEPLOYMENT
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load from scripts/.env (two levels up) if present
_scripts_env = Path(__file__).parent.parent.parent / "scripts" / ".env"
load_dotenv(_scripts_env)

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from mcp.server.fastmcp import FastMCP
from openai import AzureOpenAI

# ── Config ─────────────────────────────────────────────────────────────────────

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
SEARCH_KEY = os.environ["AZURE_SEARCH_ADMIN_KEY"]
INDEX_NAME = os.environ.get("AZURE_SEARCH_INDEX_NAME", "neural-memory")
OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
OPENAI_KEY = os.environ["AZURE_OPENAI_API_KEY"]
EMBEDDING_DEPLOYMENT = os.environ.get(
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"
)

DEFAULT_TOP_K = 5
CONTRADICTION_TOP_K = 8
CONTRADICTION_SCORE_THRESHOLD = 2.0  # reranker score above which we warn

# ── Clients (lazy singleton) ───────────────────────────────────────────────────

_search_client: SearchClient | None = None
_openai_client: AzureOpenAI | None = None


def _get_search_client() -> SearchClient:
    global _search_client
    if _search_client is None:
        _search_client = SearchClient(
            endpoint=SEARCH_ENDPOINT,
            index_name=INDEX_NAME,
            credential=AzureKeyCredential(SEARCH_KEY),
        )
    return _search_client


def _get_openai_client() -> AzureOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AzureOpenAI(
            azure_endpoint=OPENAI_ENDPOINT,
            api_key=OPENAI_KEY,
            api_version="2024-02-01",
        )
    return _openai_client


def _embed(text: str) -> list[float]:
    resp = _get_openai_client().embeddings.create(
        model=EMBEDDING_DEPLOYMENT,
        input=[text],
    )
    return resp.data[0].embedding


def _hybrid_search(query: str, top: int, filters: str | None = None) -> list[dict]:
    vector = _embed(query)
    vq = VectorizedQuery(
        vector=vector,
        k_nearest_neighbors=top * 2,
        fields="content_vector",
    )
    client = _get_search_client()
    try:
        semantic_results = client.search(
            search_text=query,
            vector_queries=[vq],
            filter=filters,
            top=top,
            select=["id", "content", "source_file", "type", "sprint_ref", "timestamp", "seed"],
            query_type="semantic",
            semantic_configuration_name="neural-semantic",
        )
        results = list(semantic_results)
    except HttpResponseError as exc:
        if "Semantic search is not enabled" not in str(exc):
            raise
        fallback_results = client.search(
            search_text=query,
            vector_queries=[vq],
            filter=filters,
            top=top,
            select=["id", "content", "source_file", "type", "sprint_ref", "timestamp", "seed"],
        )
        results = list(fallback_results)
    hits = []
    for r in results:
        hits.append({
            "score": r.get("@search.reranker_score") or r.get("@search.score", 0.0),
            "type": r.get("type", ""),
            "source_file": r.get("source_file", ""),
            "sprint_ref": r.get("sprint_ref", ""),
            "timestamp": (r.get("timestamp") or "")[:10],
            "seed": r.get("seed", False),
            "content": (r.get("content") or "")[:600],
        })
    return hits


# ── MCP Server ─────────────────────────────────────────────────────────────────

mcp = FastMCP("neural-memory")


@mcp.tool()
def query_neural_memory(question: str, top: int = DEFAULT_TOP_K) -> str:
    """
    Search the Neural-Flow institutional memory using semantic hybrid search.

    Use this BEFORE starting any technically significant task to retrieve:
    - past decisions related to the current intent
    - sprint records with similar scope
    - historical error logs or blockers
    - stable operational rules

    Args:
        question: Natural language question or task description.
        top: Number of results to return (default 5, max 20).

    Returns:
        Formatted text with the most relevant memory chunks and their sources.
    """
    top = min(max(top, 1), 20)
    hits = _hybrid_search(question, top)

    if not hits:
        return "No relevant records found in neural-memory index."

    lines = [f"Neural-Memory: '{question}' — {len(hits)} result(s)\n"]
    for i, h in enumerate(hits, 1):
        seed_flag = " [SEED]" if h["seed"] else ""
        lines.append(
            f"#{i}  [{h['type']}{seed_flag}]  {h['source_file']}  "
            f"sprint={h['sprint_ref'] or '-'}  date={h['timestamp'] or '-'}"
        )
        lines.append(f"    {h['content']}\n")

    return "\n".join(lines)


@mcp.tool()
def check_contradiction(proposal: str) -> str:
    """
    Check whether a proposed action contradicts existing institutional records.

    Used by the Circuit Breaker protocol to detect technical hallucination —
    when an AI proposal conflicts with previously validated decisions, security
    policies, or operational rules indexed in the neural-memory.

    Returns a verdict:
      CLEAR   — no significant contradictions found
      WARNING — potential conflict; human review recommended
      BLOCK   — strong contradiction with a seed/policy document

    Args:
        proposal: Description of the proposed action or code change.

    Returns:
        Verdict string with supporting evidence from the index.
    """
    hits = _hybrid_search(proposal, CONTRADICTION_TOP_K)

    if not hits:
        return "CLEAR — No indexed records to compare against."

    high_score = [h for h in hits if (h["score"] or 0) >= CONTRADICTION_SCORE_THRESHOLD]
    seed_hits = [h for h in high_score if h["seed"]]

    lines = [f"Contradiction check: '{proposal}'\n"]

    if seed_hits:
        verdict = "BLOCK"
        lines.append(
            f"VERDICT: {verdict} — High-score match against SEED/POLICY document(s). "
            "Circuit Breaker triggered. Human review required before proceeding.\n"
        )
    elif high_score:
        verdict = "WARNING"
        lines.append(
            f"VERDICT: {verdict} — Potential conflict with indexed records. "
            "Review before executing.\n"
        )
    else:
        verdict = "CLEAR"
        lines.append("VERDICT: CLEAR — No strong contradictions detected.\n")

    lines.append("Evidence:")
    for i, h in enumerate(hits[:5], 1):
        seed_flag = " [SEED]" if h["seed"] else ""
        score_str = f"{h['score']:.2f}" if h["score"] else "-"
        lines.append(
            f"  #{i}  score={score_str}  [{h['type']}{seed_flag}]  {h['source_file']}"
        )
        lines.append(f"       {h['content'][:300]}\n")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport="stdio")
