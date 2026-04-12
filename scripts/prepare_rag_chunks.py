"""
Build RAG-ready chunks from data/raw/*.jsonl.

The Constitution export is often split across many tiny lines; this script merges
consecutive lines into larger blocks, then splits with LangChain's recursive
character splitter so embeddings carry enough context.

Usage:
  cd /Users/modok_bee/Desktop/nyayamitra
  source .venv/bin/activate
  python scripts/prepare_rag_chunks.py
  python scripts/prepare_rag_chunks.py --include-qa --include-criminal-primer --include-legal-vector-10k
  # Phase 4 chat JSON is for SFT; only add --include-phase4 if you want those dialogues in RAG too.
  python scripts/prepare_rag_chunks.py --include-qa --chunk-size 1200 --overlap 150

Output: data/chunks/rag_chunks.jsonl (one JSON object per chunk).

Next: python scripts/ingest_chroma.py [--reset]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
CHUNK_DIR = ROOT / "data" / "chunks"
DEFAULT_CONST = RAW_DIR / "constitution_india.jsonl"
DEFAULT_QA = RAW_DIR / "indian_legal_qa_subset.jsonl"
DEFAULT_CRIMINAL_PRIMER = RAW_DIR / "indian_criminal_law_primer.jsonl"
# Chat-style SFT export: array of { id, domain, messages: [{role, content}, ...] }
DEFAULT_PHASE4_JSON = ROOT / "ai_legal_phase4_diverse.json"
# Structured law snippets for RAG (not conversational SFT)
DEFAULT_LEGAL_VECTOR_10K = ROOT / "legal_vector_dataset_10k.json"


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _clean_const_line(text: str) -> str | None:
    t = (text or "").strip()
    if not t or t == "{}":
        return None
    return t


def merge_constitution_fragments(
    rows: list[dict],
    merge_target_chars: int,
    merge_hard_max: int,
) -> list[dict]:
    """Merge sequential tiny lines into fewer, context-rich documents."""
    merged: list[dict] = []
    buffer: list[str] = []
    buf_len = 0
    first_id: str | None = None
    last_id: str | None = None
    if not rows:
        return []
    source = str(rows[0].get("source", ""))

    def flush() -> None:
        nonlocal buffer, buf_len, first_id, last_id
        if not buffer or first_id is None:
            buffer = []
            buf_len = 0
            first_id = None
            last_id = None
            return
        text = " ".join(buffer)
        merged.append(
            {
                "id": f"{first_id}__{last_id}",
                "source": source,
                "text": text,
                "metadata": {"parent_span": [first_id, last_id], "kind": "constitution_merged"},
            }
        )
        buffer = []
        buf_len = 0
        first_id = None
        last_id = None

    for row in rows:
        line = _clean_const_line(str(row.get("text", "")))
        if line is None:
            continue
        rid = str(row.get("id", ""))
        if first_id is None:
            first_id = rid
        last_id = rid
        source = str(row.get("source", source))
        buffer.append(line)
        buf_len += len(line) + 1

        if buf_len >= merge_hard_max:
            flush()
        elif buf_len >= merge_target_chars and (line.endswith(".") or line.endswith(";") or line.endswith(":")):
            flush()

    flush()
    return merged


def constitution_to_chunks(
    path: Path,
    splitter: RecursiveCharacterTextSplitter,
    merge_target_chars: int,
    merge_hard_max: int,
) -> list[dict]:
    rows = load_jsonl(path)
    merged_docs = merge_constitution_fragments(rows, merge_target_chars, merge_hard_max)
    out: list[dict] = []
    for doc in merged_docs:
        for i, chunk_text in enumerate(splitter.split_text(doc["text"])):
            out.append(
                {
                    "chunk_id": f"{doc['id']}_c{i}",
                    "source": doc["source"],
                    "kind": "constitution",
                    "text": chunk_text,
                    "metadata": {**doc["metadata"], "chunk_index": i},
                }
            )
    return out


def plain_docs_to_chunks(
    path: Path,
    splitter: RecursiveCharacterTextSplitter,
    *,
    kind: str,
) -> list[dict]:
    """Chunk JSONL rows with id, source, text, optional metadata (object)."""
    rows = load_jsonl(path)
    out: list[dict] = []
    for row in rows:
        text = str(row.get("text", "")).strip()
        if not text:
            continue
        rid = str(row.get("id", "unknown"))
        src = str(row.get("source", path.name))
        meta = row.get("metadata")
        base_meta: dict = dict(meta) if isinstance(meta, dict) else {}
        for i, chunk_text in enumerate(splitter.split_text(text)):
            out.append(
                {
                    "chunk_id": f"{rid}_c{i}",
                    "source": src,
                    "kind": kind,
                    "text": chunk_text,
                    "metadata": {**base_meta, "chunk_index": i},
                }
            )
    return out


def phase4_chat_to_chunks(path: Path, splitter: RecursiveCharacterTextSplitter) -> list[dict]:
    """Chunk Phase 4 fine-tune JSON: [{id, domain, messages: [...]}, ...]."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit(f"Expected a JSON array in {path}")
    source_tag = path.stem
    out: list[dict] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        rid = str(row.get("id", "unknown"))
        domain = str(row.get("domain", "")).strip()
        msgs = row.get("messages")
        if not isinstance(msgs, list):
            continue
        parts: list[str] = []
        if domain:
            parts.append(f"Domain: {domain}")
        first_user_preview = ""
        for m in msgs:
            if not isinstance(m, dict):
                continue
            role = str(m.get("role", "")).strip().lower()
            content = str(m.get("content", "")).strip()
            if not content:
                continue
            if role == "system":
                continue
            if role == "user" and not first_user_preview:
                first_user_preview = content[:200]
            label = (
                "User"
                if role == "user"
                else ("Assistant" if role == "assistant" else role.title())
            )
            parts.append(f"{label}: {content}")
        if len(parts) < 2:
            continue
        body = "\n\n".join(parts)
        for i, chunk_text in enumerate(splitter.split_text(body)):
            out.append(
                {
                    "chunk_id": f"{rid}_c{i}",
                    "source": source_tag,
                    "kind": "phase4_chat",
                    "text": chunk_text,
                    "metadata": {
                        "chunk_index": i,
                        "domain": domain,
                        "question_preview": first_user_preview[:120],
                    },
                }
            )
    return out


def _legal_vector_record_to_text(row: dict) -> str:
    """Flatten one legal_vector_dataset_10k row into embeddable text."""
    law = str(row.get("law", "")).strip()
    section = str(row.get("section", "")).strip()
    title = str(row.get("title", "")).strip()
    domain = str(row.get("domain", "")).strip()
    parts: list[str] = []
    head = f"Law: {law}" + (f" | Section or reference: {section}" if section else "")
    parts.append(head)
    if title:
        parts.append(f"Title: {title}")
    if domain:
        parts.append(f"Domain: {domain}")
    for key, label in (
        ("content", "Provision summary"),
        ("simple_explanation", "Plain explanation"),
    ):
        v = str(row.get(key, "")).strip()
        if v:
            parts.append(f"{label}: {v}")
    wia = row.get("when_it_applies")
    if isinstance(wia, list) and wia:
        bullets = "\n".join(f"- {str(x).strip()}" for x in wia if str(x).strip())
        if bullets:
            parts.append("When it may apply:\n" + bullets)
    ex = str(row.get("example", "")).strip()
    if ex:
        parts.append(f"Example: {ex}")
    kw = row.get("keywords")
    if isinstance(kw, list) and kw:
        kws = ", ".join(str(x).strip() for x in kw if str(x).strip())
        if kws:
            parts.append(f"Keywords: {kws}")
    return "\n\n".join(parts)


def legal_vector_10k_to_chunks(path: Path, splitter: RecursiveCharacterTextSplitter) -> list[dict]:
    """Chunk legal_vector_dataset_10k.json: law/section/title/content/... knowledge rows."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit(f"Expected a JSON array in {path}")
    source_tag = path.stem
    out: list[dict] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        rid = str(row.get("id", "")).strip() or "unknown"
        safe_rid = rid.replace(" ", "_").replace("/", "_")
        body = _legal_vector_record_to_text(row)
        if not body.strip():
            continue
        law = str(row.get("law", "")).strip()[:200]
        title = str(row.get("title", "")).strip()[:200]
        domain = str(row.get("domain", "")).strip()[:200]
        section = str(row.get("section", "")).strip()[:120]
        for i, chunk_text in enumerate(splitter.split_text(body)):
            out.append(
                {
                    "chunk_id": f"lv10k_{safe_rid}_c{i}",
                    "source": source_tag,
                    "kind": "legal_vector_kb",
                    "text": chunk_text,
                    "metadata": {
                        "chunk_index": i,
                        "law": law,
                        "section": section,
                        "title": title,
                        "domain": domain,
                    },
                }
            )
    return out


def qa_to_chunks(path: Path, splitter: RecursiveCharacterTextSplitter) -> list[dict]:
    rows = load_jsonl(path)
    out: list[dict] = []
    for row in rows:
        q = str(row.get("question", "")).strip()
        a = str(row.get("answer", "")).strip()
        if not q and not a:
            continue
        body = f"Question: {q}\nAnswer: {a}"
        rid = str(row.get("id", "unknown"))
        src = str(row.get("source", ""))
        for i, chunk_text in enumerate(splitter.split_text(body)):
            out.append(
                {
                    "chunk_id": f"{rid}_c{i}",
                    "source": src,
                    "kind": "legal_qa",
                    "text": chunk_text,
                    "metadata": {"chunk_index": i, "question_preview": q[:120]},
                }
            )
    return out


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prepare RAG chunks from raw JSONL corpora.")
    p.add_argument("--constitution", type=Path, default=DEFAULT_CONST, help="Path to constitution_india.jsonl")
    p.add_argument("--qa", type=Path, default=DEFAULT_QA, help="Path to indian_legal_qa_subset.jsonl")
    p.add_argument("--out", type=Path, default=CHUNK_DIR / "rag_chunks.jsonl", help="Output JSONL path")
    p.add_argument("--include-qa", action="store_true", help="Also chunk the legal Q&A JSONL")
    p.add_argument(
        "--include-criminal-primer",
        action="store_true",
        help="Also chunk data/raw/indian_criminal_law_primer.jsonl (IPC/BNS/POCSO educational summaries)",
    )
    p.add_argument(
        "--include-phase4",
        action="store_true",
        help="Also chunk Phase 4 chat JSON into RAG (optional; prefer SFT-only—see data/CORPUS.md)",
    )
    p.add_argument(
        "--phase4-json",
        type=Path,
        default=DEFAULT_PHASE4_JSON,
        help="Path to Phase 4 chat JSON array (default: ai_legal_phase4_diverse.json in project root)",
    )
    p.add_argument(
        "--include-legal-vector-10k",
        action="store_true",
        help="Chunk legal_vector_dataset_10k.json (knowledge snippets for RAG; keep separate from Phase 4 SFT)",
    )
    p.add_argument(
        "--legal-vector-json",
        type=Path,
        default=DEFAULT_LEGAL_VECTOR_10K,
        help="Path to 10k legal vector JSON (default: project root legal_vector_dataset_10k.json)",
    )
    p.add_argument(
        "--include-jsonl",
        type=Path,
        action="append",
        default=[],
        metavar="PATH",
        help="Extra raw JSONL (id, source, text, optional metadata per line); can be repeated",
    )
    p.add_argument("--chunk-size", type=int, default=1000, help="Target chunk size (characters)")
    p.add_argument("--overlap", type=int, default=150, help="Chunk overlap (characters)")
    p.add_argument("--merge-target", type=int, default=1200, help="Merge constitution lines until ~this many chars")
    p.add_argument("--merge-max", type=int, default=3500, help="Force-merge flush after this many chars")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=args.chunk_size,
        chunk_overlap=args.overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    all_chunks: list[dict] = []

    if not args.constitution.exists():
        raise SystemExit(f"Missing constitution file: {args.constitution}\nRun: python scripts/fetch_constitution_corpus.py")
    all_chunks.extend(
        constitution_to_chunks(
            args.constitution,
            splitter,
            merge_target_chars=args.merge_target,
            merge_hard_max=args.merge_max,
        )
    )

    if args.include_qa:
        if not args.qa.exists():
            raise SystemExit(f"--include-qa but missing: {args.qa}")
        all_chunks.extend(qa_to_chunks(args.qa, splitter))

    if args.include_criminal_primer:
        if not DEFAULT_CRIMINAL_PRIMER.exists():
            raise SystemExit(
                f"--include-criminal-primer but missing: {DEFAULT_CRIMINAL_PRIMER}"
            )
        all_chunks.extend(
            plain_docs_to_chunks(
                DEFAULT_CRIMINAL_PRIMER, splitter, kind="criminal_law_primer"
            )
        )

    if args.include_phase4:
        p4 = args.phase4_json
        if not p4.exists():
            raise SystemExit(f"--include-phase4 but missing: {p4}")
        all_chunks.extend(phase4_chat_to_chunks(p4, splitter))

    if args.include_legal_vector_10k:
        lv = args.legal_vector_json
        if not lv.exists():
            raise SystemExit(f"--include-legal-vector-10k but missing: {lv}")
        all_chunks.extend(legal_vector_10k_to_chunks(lv, splitter))

    for extra in args.include_jsonl:
        if not extra.exists():
            raise SystemExit(f"--include-jsonl missing file: {extra}")
        all_chunks.extend(
            plain_docs_to_chunks(extra, splitter, kind=f"extra:{extra.stem}")
        )

    write_jsonl(args.out, all_chunks)
    print(f"Wrote {len(all_chunks)} chunks -> {args.out}")


if __name__ == "__main__":
    main()
