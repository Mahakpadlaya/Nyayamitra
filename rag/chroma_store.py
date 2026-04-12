"""Shared Chroma client and defaults for ingest + API."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import chromadb
from chromadb import Collection
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHROMA_PATH = ROOT / "chroma_db"
DEFAULT_COLLECTION_NAME = "legal_rag"
# Hugging Face repo id for sentence-transformers (downloads on first use).
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def embedding_function(model_name: str | None = None) -> SentenceTransformerEmbeddingFunction:
    return SentenceTransformerEmbeddingFunction(model_name=model_name or DEFAULT_EMBEDDING_MODEL)


def get_client(persist_path: Path | None = None) -> chromadb.ClientAPI:
    path = persist_path or DEFAULT_CHROMA_PATH
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(path))


def get_collection(
    name: str = DEFAULT_COLLECTION_NAME,
    *,
    persist_path: Path | None = None,
    model_name: str | None = None,
) -> Collection:
    client = get_client(persist_path)
    ef = embedding_function(model_name)
    return client.get_or_create_collection(name=name, embedding_function=ef)


def jsonl_record_to_chroma_metadata(row: dict) -> dict[str, Any]:
    """Chroma metadata values must be str, int, float, or bool."""
    nested = row.get("metadata") or {}
    out: dict[str, Any] = {
        "source": str(row.get("source", "")),
        "kind": str(row.get("kind", "")),
    }
    for key, val in nested.items():
        if val is None:
            continue
        if isinstance(val, (str, int, float, bool)):
            out[str(key)] = val
        else:
            out[str(key)] = json.dumps(val, ensure_ascii=False)
    return out


def query_collection(
    collection: Collection,
    question: str,
    *,
    k: int = 5,
) -> dict[str, Any]:
    return collection.query(query_texts=[question.strip()], n_results=k)
