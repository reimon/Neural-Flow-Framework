"""
Neural-Flow Framework — Ingestion Pipeline
==========================================
Chunks markdown docs, git log, and session logs into Azure AI Search
with vector embeddings via Azure OpenAI (text-embedding-3-small).

Usage:
  python ingest.py                  # full reindex
  python ingest.py --changed-only   # only files changed in last commit (git hook mode)
  python ingest.py --dry-run        # parse and chunk without uploading

Environment (load from .env or set in shell):
  AZURE_SEARCH_ENDPOINT             https://<name>.search.windows.net
  AZURE_SEARCH_ADMIN_KEY            <admin-key>  (or use DefaultAzureCredential)
  AZURE_SEARCH_INDEX_NAME           neural-memory
  AZURE_OPENAI_ENDPOINT             https://<name>.openai.azure.com/
  AZURE_OPENAI_API_KEY              <key>         (or use DefaultAzureCredential)
  AZURE_OPENAI_EMBEDDING_DEPLOYMENT text-embedding-3-small
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# ── Azure SDK imports ──────────────────────────────────────────────────────────

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery
from openai import APITimeoutError, APIConnectionError, AzureOpenAI, RateLimitError

# ── Config ─────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
SEARCH_KEY = os.environ["AZURE_SEARCH_ADMIN_KEY"]
INDEX_NAME = os.environ.get("AZURE_SEARCH_INDEX_NAME", "neural-memory")

OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
OPENAI_KEY = os.environ["AZURE_OPENAI_API_KEY"]
EMBEDDING_DEPLOYMENT = os.environ.get(
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"
)

VECTOR_DIMS = 1536  # text-embedding-3-small output dimensions
BATCH_SIZE = 20     # Keep small batches to reduce timeout/rate spikes

# Markdown directories to index (relative to REPO_ROOT)
MARKDOWN_DIRS = [
    "docs",
    "docs/protocols",
    "templates",
]

# Session logs directory
SESSION_DIR = REPO_ROOT / "docs" / "sessoes" / "sprints"

# Max git log entries to index
GIT_LOG_LIMIT = 200


# ── Index schema ───────────────────────────────────────────────────────────────

def ensure_index(client: SearchIndexClient) -> None:
    """Create or update the neural-memory search index."""
    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="standard.lucene"),
        SimpleField(name="type", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="source_file", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="sprint_ref", type=SearchFieldDataType.String, filterable=True),
        SimpleField(
            name="timestamp",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True,
        ),
        SimpleField(name="seed", type=SearchFieldDataType.Boolean, filterable=True),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=VECTOR_DIMS,
            vector_search_profile_name="hnsw-profile",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-algo")],
        profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw-algo")],
    )

    semantic_config = SemanticConfiguration(
        name="neural-semantic",
        prioritized_fields=SemanticPrioritizedFields(
            content_fields=[SemanticField(field_name="content")],
            keywords_fields=[SemanticField(field_name="source_file")],
        ),
    )

    index = SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
        semantic_search=SemanticSearch(configurations=[semantic_config]),
    )

    client.create_or_update_index(index)
    print(f"[index] '{INDEX_NAME}' ensured.")


# ── Chunking ───────────────────────────────────────────────────────────────────

def _make_id(source: str, chunk_index: int) -> str:
    raw = f"{source}::{chunk_index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:40]


def chunk_markdown(path: Path) -> list[dict[str, Any]]:
    """Split a markdown file by ## headings, keeping path + section context."""
    text = path.read_text(encoding="utf-8", errors="replace")
    rel = str(path.relative_to(REPO_ROOT))

    # Detect sprint reference from path (e.g. sprint-3-auth-2025-10-01.md)
    sprint_match = re.search(r"sprint-(\d+)", path.stem, re.IGNORECASE)
    sprint_ref = f"sprint-{sprint_match.group(1)}" if sprint_match else ""

    is_seed = path.name in ("NEURAL-MEMORY.md", "MEMORY.md")

    # Split on level-2 headings (## Title)
    sections = re.split(r"(?m)^(## .+)$", text)
    # sections alternates: [preamble, heading, body, heading, body, ...]

    chunks: list[dict[str, Any]] = []

    # Preamble (before first ##)
    preamble = sections[0].strip()
    if preamble:
        chunks.append({
            "content": preamble,
            "section": path.stem,
        })

    it = iter(sections[1:])
    for heading, body in zip(it, it):
        combined = f"{heading}\n{body}".strip()
        if combined:
            chunks.append({
                "content": combined,
                "section": heading.strip("# ").strip(),
            })

    docs = []
    for i, chunk in enumerate(chunks):
        docs.append({
            "id": _make_id(rel, i),
            "content": chunk["content"],
            "type": "markdown",
            "source_file": rel,
            "sprint_ref": sprint_ref,
            "timestamp": _file_mtime(path),
            "seed": is_seed,
        })
    return docs


def chunk_git_log(limit: int = GIT_LOG_LIMIT) -> list[dict[str, Any]]:
    """Parse git log into indexable chunks."""
    try:
        result = subprocess.run(
            [
                "git", "-C", str(REPO_ROOT), "log",
                f"-{limit}",
                "--format=COMMIT_SEP%n%H%n%ai%n%s%n%b",
            ],
            capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError:
        print("[git] Could not read git log — skipping.")
        return []

    raw = result.stdout
    entries = raw.split("COMMIT_SEP\n")[1:]  # drop empty leading element

    docs = []
    for i, entry in enumerate(entries):
        lines = entry.strip().splitlines()
        if len(lines) < 3:
            continue
        sha, timestamp_str = lines[0], lines[1]
        subject = lines[2]
        body = "\n".join(lines[3:]).strip()
        content = f"commit: {subject}\n{body}".strip() if body else f"commit: {subject}"

        try:
            ts = datetime.fromisoformat(timestamp_str.strip()).astimezone(timezone.utc).isoformat()
        except ValueError:
            ts = datetime.now(timezone.utc).isoformat()

        docs.append({
            "id": _make_id(f"git::{sha}", i),
            "content": content,
            "type": "commit",
            "source_file": f"git::{sha[:8]}",
            "sprint_ref": _detect_sprint_ref(subject + body),
            "timestamp": ts,
            "seed": False,
        })
    return docs


def chunk_session_logs() -> list[dict[str, Any]]:
    """Index session/sprint log files from docs/sessoes/sprints/."""
    if not SESSION_DIR.exists():
        return []

    docs = []
    for f in sorted(SESSION_DIR.glob("*.md")):
        docs.extend(chunk_markdown(f))
    return docs


def _detect_sprint_ref(text: str) -> str:
    m = re.search(r"sprint[- _]?(\d+)", text, re.IGNORECASE)
    return f"sprint-{m.group(1)}" if m else ""


def _file_mtime(path: Path) -> str:
    mtime = path.stat().st_mtime
    return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()


# ── Changed-only mode (git hook) ───────────────────────────────────────────────

def get_changed_files() -> list[Path]:
    """Return files changed in the last commit."""
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "diff-tree", "--no-commit-id", "-r", "--name-only", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return [REPO_ROOT / f.strip() for f in result.stdout.splitlines() if f.strip().endswith(".md")]
    except subprocess.CalledProcessError:
        return []


# ── Embeddings ─────────────────────────────────────────────────────────────────

def embed(client: AzureOpenAI, texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts using Azure OpenAI."""
    max_attempts = 6
    wait_seconds = 15

    for attempt in range(1, max_attempts + 1):
        try:
            response = client.embeddings.create(
                model=EMBEDDING_DEPLOYMENT,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except (RateLimitError, APITimeoutError, APIConnectionError):
            if attempt == max_attempts:
                raise
            print(
                f"[embed] Transient OpenAI error (attempt {attempt}/{max_attempts}). "
                f"Retrying in {wait_seconds}s..."
            )
            time.sleep(wait_seconds)
            wait_seconds = min(wait_seconds * 2, 120)

    # Should never be reached due return/raise above.
    raise RuntimeError("Embedding generation failed after retries")


# ── Upload ─────────────────────────────────────────────────────────────────────

def upload_batch(
    search_client: SearchClient,
    openai_client: AzureOpenAI,
    docs: list[dict],
    dry_run: bool = False,
) -> int:
    """Embed and upload a batch of documents. Returns count uploaded."""
    if not docs:
        return 0

    if dry_run:
        for doc in docs:
            print(f"  [dry-run] {doc['type']:10} | {doc['source_file'][:60]}")
        return len(docs)

    texts = [d["content"] for d in docs]
    vectors = embed(openai_client, texts)

    for doc, vec in zip(docs, vectors):
        doc["content_vector"] = vec

    search_client.upload_documents(documents=docs)
    return len(docs)


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Neural-Flow ingestion pipeline")
    parser.add_argument("--changed-only", action="store_true", help="Only index files changed in last commit")
    parser.add_argument("--dry-run", action="store_true", help="Parse and show chunks without uploading")
    args = parser.parse_args()

    credential = AzureKeyCredential(SEARCH_KEY)
    index_client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=credential)
    search_client = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=INDEX_NAME, credential=credential)
    openai_client = AzureOpenAI(azure_endpoint=OPENAI_ENDPOINT, api_key=OPENAI_KEY, api_version="2024-02-01")

    if not args.dry_run:
        ensure_index(index_client)

    all_docs: list[dict] = []

    if args.changed_only:
        changed = get_changed_files()
        print(f"[changed-only] {len(changed)} markdown file(s) changed.")
        for f in changed:
            all_docs.extend(chunk_markdown(f))
    else:
        # Full reindex
        print("[ingest] Full reindex starting...")

        # Markdown docs
        for dir_rel in MARKDOWN_DIRS:
            d = REPO_ROOT / dir_rel
            if d.exists():
                for f in sorted(d.glob("*.md")):
                    all_docs.extend(chunk_markdown(f))

        # Session logs
        all_docs.extend(chunk_session_logs())

        # Git log
        all_docs.extend(chunk_git_log())

    print(f"[ingest] {len(all_docs)} chunk(s) to process.")

    # Upload in batches of BATCH_SIZE
    total = 0
    for i in range(0, len(all_docs), BATCH_SIZE):
        batch = all_docs[i : i + BATCH_SIZE]
        count = upload_batch(search_client, openai_client, batch, dry_run=args.dry_run)
        total += count
        print(f"[ingest] Batch {i // BATCH_SIZE + 1}: {count} chunk(s) {'parsed' if args.dry_run else 'uploaded'}.")

    print(f"[ingest] Done. Total: {total} chunk(s).")


if __name__ == "__main__":
    main()
