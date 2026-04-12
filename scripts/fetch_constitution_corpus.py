"""
Download compact Indian legal corpora from Hugging Face for local RAG / training prep.
Avoids Pile-of-Law; defaults to Constitution + optional legal QA subset.

Usage:
  cd /path/to/nyayamitra
  source .venv/bin/activate
  python scripts/fetch_constitution_corpus.py

Outputs under data/raw/ as JSONL for easy chunking.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from datasets import load_dataset

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CONSTITUTION_ID = "Susant-Achary/constitution-of-india-dataset"
LEGAL_QA_ID = "RMani1/indian-legal-dataset-indian-law"  # swap to malarventhan/... if you prefer


def rows_to_jsonl(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} records -> {path}")


def fetch_constitution() -> None:
    ds = load_dataset(CONSTITUTION_ID, split="train")
    rows = []
    for i, ex in enumerate(ds):
        # Normalize keys — HF schemas vary; keep common text fields
        text_parts = []
        for k in ("article", "text", "content", "Article_Text", "description"):
            if k in ex and ex[k]:
                text_parts.append(str(ex[k]))
        body = "\n".join(text_parts) if text_parts else json.dumps({k: ex[k] for k in ex if ex[k]}, ensure_ascii=False)
        meta = {k: ex[k] for k in ex if k not in ("text", "content", "Article_Text")}
        rows.append({"id": f"const_{i}", "source": CONSTITUTION_ID, "metadata": meta, "text": body})
    rows_to_jsonl(rows, OUT_DIR / "constitution_india.jsonl")


def fetch_legal_qa(max_samples: int | None = 5000) -> None:
    ds = load_dataset(LEGAL_QA_ID, split="train")
    if max_samples is not None and len(ds) > max_samples:
        ds = ds.select(range(max_samples))
    rows = []
    for i, ex in enumerate(ds):
        q = ex.get("question") or ex.get("Question") or ex.get("instruction") or ""
        a = ex.get("answer") or ex.get("Answer") or ex.get("output") or ""
        rows.append(
            {
                "id": f"legalqa_{i}",
                "source": LEGAL_QA_ID,
                "question": str(q).strip(),
                "answer": str(a).strip(),
            }
        )
    rows_to_jsonl(rows, OUT_DIR / "indian_legal_qa_subset.jsonl")


def main() -> None:
    fetch_constitution()
    fetch_legal_qa(max_samples=5000)
    print("Done. Next: python scripts/prepare_rag_chunks.py [--include-qa]")


if __name__ == "__main__":
    main()
