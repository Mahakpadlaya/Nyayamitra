"""
Embed rag_chunks.jsonl into a persistent Chroma vector store.

Usage:
  cd /Users/modok_bee/Desktop/nyayamitra
  source .venv/bin/activate
  python scripts/prepare_rag_chunks.py --include-qa --include-criminal-primer --include-legal-vector-10k
  python scripts/ingest_chroma.py
  python scripts/ingest_chroma.py --reset --collection legal_rag

Query smoke test:
  python scripts/ingest_chroma.py --query "Fundamental Rights Article 14"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.chroma_store import (  # noqa: E402
    DEFAULT_CHROMA_PATH,
    DEFAULT_COLLECTION_NAME,
    DEFAULT_EMBEDDING_MODEL,
    get_client,
    jsonl_record_to_chroma_metadata,
)

DEFAULT_CHUNKS = ROOT / "data" / "chunks" / "rag_chunks.jsonl"


def load_chunks(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def ingest(
    chunks_path: Path,
    persist_path: Path,
    collection_name: str,
    model_name: str,
    *,
    reset: bool,
    batch_size: int,
) -> int:
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    rows = load_chunks(chunks_path)
    if not rows:
        raise SystemExit(f"No rows in {chunks_path}")

    ef = SentenceTransformerEmbeddingFunction(model_name=model_name)
    client = get_client(persist_path)
    if reset:
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass
    collection = client.get_or_create_collection(name=collection_name, embedding_function=ef)

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        cid = str(row.get("chunk_id", "")).strip()
        text = str(row.get("text", "")).strip()
        if not cid or not text:
            continue
        if cid in seen:
            continue
        seen.add(cid)
        ids.append(cid)
        documents.append(text)
        metadatas.append(jsonl_record_to_chroma_metadata(row))

    for i in range(0, len(ids), batch_size):
        collection.upsert(
            ids=ids[i : i + batch_size],
            documents=documents[i : i + batch_size],
            metadatas=metadatas[i : i + batch_size],
        )
    return len(ids)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest RAG chunks into Chroma.")
    p.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS, help="Path to rag_chunks.jsonl")
    p.add_argument("--persist", type=Path, default=DEFAULT_CHROMA_PATH, help="Chroma persist directory")
    p.add_argument("--collection", type=str, default=DEFAULT_COLLECTION_NAME, help="Collection name")
    p.add_argument("--model", type=str, default=DEFAULT_EMBEDDING_MODEL, help="sentence-transformers model")
    p.add_argument("--batch-size", type=int, default=128)
    p.add_argument("--reset", action="store_true", help="Delete collection and rebuild")
    p.add_argument("--query", type=str, default=None, help="Run a single similarity query and print results")
    p.add_argument("-k", type=int, default=5, help="Top-k for --query")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if not args.chunks.exists():
        raise SystemExit(f"Missing chunks file: {args.chunks}\nRun: python scripts/prepare_rag_chunks.py")

    if args.query:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

        ef = SentenceTransformerEmbeddingFunction(model_name=args.model)
        client = get_client(args.persist)
        collection = client.get_collection(name=args.collection, embedding_function=ef)
        res = collection.query(query_texts=[args.query], n_results=args.k)
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]
        print(f"Query: {args.query!r}\n")
        for i, doc in enumerate(docs):
            dist = dists[i] if dists and i < len(dists) else None
            meta = metas[i] if metas and i < len(metas) else {}
            print(f"--- [{i+1}] distance={dist}\nmeta={meta}\n{doc[:800]}{'...' if len(doc) > 800 else ''}\n")
        return

    n = ingest(
        args.chunks,
        args.persist,
        args.collection,
        args.model,
        reset=args.reset,
        batch_size=args.batch_size,
    )
    print(f"Ingested {n} vectors into {args.persist} / collection={args.collection!r}")


if __name__ == "__main__":
    main()
