"""
Extract text from one or more PDFs into JSONL lines for data/raw/ (one row per PDF).

Usage:
  cd nyayamitra && source .venv/bin/activate
  python scripts/pdf_to_jsonl.py --out data/raw/my_act.jsonl path/to/act.pdf

Re-ingest pipeline:
  python scripts/prepare_rag_chunks.py   # extend script if your file is not wired in
  python scripts/ingest_chroma.py --reset

Only use PDFs you have the right to index. See data/CORPUS.md.
"""
from __future__ import annotations

import argparse
import json
import re
import uuid
from pathlib import Path

from pypdf import PdfReader


def extract_text(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        t = page.extract_text() or ""
        parts.append(t)
    return "\n\n".join(parts)


def slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return s or "doc"


def main() -> None:
    p = argparse.ArgumentParser(description="PDF → JSONL for RAG raw corpus.")
    p.add_argument("pdfs", nargs="+", type=Path, help="Input PDF paths")
    p.add_argument("--out", type=Path, required=True, help="Output JSONL path")
    p.add_argument(
        "--source-label",
        type=str,
        default="",
        help="Optional source string stored on each row (default: filename)",
    )
    args = p.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for pdf in args.pdfs:
        text = extract_text(pdf).strip()
        label = args.source_label or pdf.name
        rows.append(
            {
                "id": f"pdf_{slugify(pdf.stem)}_{uuid.uuid4().hex[:8]}",
                "source": label,
                "text": text,
                "metadata": {"filename": pdf.name, "kind": "pdf_extract"},
            }
        )

    with args.out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Wrote {len(rows)} record(s) -> {args.out}")


if __name__ == "__main__":
    main()
