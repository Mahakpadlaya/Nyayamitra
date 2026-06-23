# `scripts/` — Data prep, ingestion, and API smoke tests

These CLI utilities run **outside** the live FastAPI app: they fetch or convert raw text, build **`rag_chunks.jsonl`**, embed into **`chroma_db/`**, or verify routes with a **mocked** vector store.

Typical pipeline (from project root, venv activated):

```text
fetch_constitution_corpus.py  →  data/raw/*.jsonl
        ↓
prepare_rag_chunks.py         →  data/chunks/rag_chunks.jsonl
        ↓
ingest_chroma.py              →  chroma_db/
```

Optional: **`pdf_to_jsonl.py`** for custom PDFs into `data/raw/`, then include them via **`prepare_rag_chunks.py --include-jsonl`**.

---

## File overview

| Script | Role |
|--------|------|
| [`fetch_constitution_corpus.py`](#fetch_constitution_corpuspy) | Download Constitution + legal QA from Hugging Face → `data/raw/` |
| [`pdf_to_jsonl.py`](#pdf_to_jsonlpy) | Extract text from PDF(s) → one JSONL file |
| [`prepare_rag_chunks.py`](#prepare_rag_chunkspy) | Merge/split raw corpora → `rag_chunks.jsonl` |
| [`ingest_chroma.py`](#ingest_chromapy) | Embed chunks into Chroma (`chroma_db/`) or `--query` test |
| [`smoke_api.py`](#smoke_apipy) | Hit `/health`, `/api/plan`, `/api/chat` with mocked Chroma |

---

## `fetch_constitution_corpus.py`

**Purpose:** Pull **Indian Constitution** and a **legal Q&A** subset from Hugging Face `datasets` and write **JSONL** under `data/raw/`.

**Datasets (hardcoded IDs)**

- Constitution: `Susant-Achary/constitution-of-india-dataset` → `constitution_india.jsonl`
- Legal QA: `RMani1/indian-legal-dataset-indian-law` (up to 5000 rows) → `indian_legal_qa_subset.jsonl`

**Behavior**

- Normalizes HF row fields into `id`, `source`, `text` / `question`+`answer`, plus `metadata` where useful.
- Prints `Done. Next: python scripts/prepare_rag_chunks.py [--include-qa]`

**Requires:** `datasets` (see `requirements.txt`), network on first run.

---

## `pdf_to_jsonl.py`

**Purpose:** Turn **one or more PDFs** into a single **JSONL** file for `data/raw/` (one record per PDF).

**CLI**

```bash
python scripts/pdf_to_jsonl.py --out data/raw/my_act.jsonl path/to/act.pdf
```

**Options**

- **`--out`** (required) — output JSONL path.
- **`--source-label`** — optional string stored as `source` (default: PDF filename).

**Each row contains:** `id`, `source`, `text` (full extract), `metadata` with `filename`, `kind: pdf_extract`.

**Uses:** `pypdf` (`PdfReader`). Only index PDFs you have rights to use; see `data/CORPUS.md`.

**Afterward:** extend `prepare_rag_chunks.py` wiring or pass **`--include-jsonl data/raw/my_act.jsonl`** when building chunks.

---

## `prepare_rag_chunks.py`

**Purpose:** Build **`data/chunks/rag_chunks.jsonl`** — one JSON object per chunk with `chunk_id`, `source`, `kind`, `text`, `metadata` — from everything you want in RAG.

**Always includes**

- **Constitution** from `data/raw/constitution_india.jsonl`: merges tiny lines into larger blocks, then **LangChain `RecursiveCharacterTextSplitter`** so chunks have enough context.

**Optional flags**

| Flag | Adds |
|------|------|
| `--include-qa` | `indian_legal_qa_subset.jsonl` as Q&A-shaped chunks (`kind: legal_qa`) |
| `--include-criminal-primer` | `data/raw/indian_criminal_law_primer.jsonl` (`kind: criminal_law_primer`) |
| `--include-phase4` | `ai_legal_phase4_diverse.json` chat dialogues as chunks (`kind: phase4_chat`) — optional; often kept for SFT only |
| `--include-legal-vector-10k` | `legal_vector_dataset_10k.json` structured law snippets (`kind: legal_vector_kb`) |
| `--include-jsonl PATH` | Repeatable; extra JSONL with `id`, `source`, `text` (`kind: extra:<stem>`) |

**Tuning**

- `--chunk-size`, `--overlap` — splitter settings (default 1000 / 150).
- `--merge-target`, `--merge-max` — constitution line merging before split.

**Output:** `--out` (default `data/chunks/rag_chunks.jsonl`).

**Next step:** `python scripts/ingest_chroma.py` (or `--reset` to rebuild the collection).

---

## `ingest_chroma.py`

**Purpose:** Read **`rag_chunks.jsonl`**, compute embeddings with the same **SentenceTransformers** model as [`rag/chroma_store.py`](../rag/chroma_store.py), and **upsert** into Chroma under **`chroma_db/`**, collection **`legal_rag`** by default.

**Common usage**

```bash
python scripts/ingest_chroma.py
python scripts/ingest_chroma.py --reset
```

**Flags**

- `--chunks` — path to JSONL (default: `data/chunks/rag_chunks.jsonl`).
- `--persist` — Chroma directory (default: project `chroma_db/`).
- `--collection`, `--model`, `--batch-size` — collection name, embedding model id, batch upsert size.
- **`--reset`** — delete collection and rebuild.
- **`--query "..."`** — skip ingest; open existing store and run a **similarity query** (debug smoke test).
- `-k` — top-k for `--query`.

**Requires:** Chroma + embedding model download on first use (can be heavy).

---

## `smoke_api.py`

**Purpose:** Quick **automated checks** on the FastAPI app **without** running `uvicorn` and **without** a real Chroma DB or embedding download.

**How it works**

- Patches `get_collection` with a **MagicMock** that returns fixed “documents” for `query`.
- Uses **`TestClient`** to call `GET /health`, `POST /api/plan`, `POST /api/chat`, and a **bad** chat payload expecting **400**.

**Usage**

```bash
python scripts/smoke_api.py
```

Exit code **0** if all assertions pass; **1** on failure.

**Note:** Does not prove your real `chroma_db` or LLM keys work — only that routes and response shapes behave.

---

## Related docs

- Raw data notes: [`data/CORPUS.md`](../data/CORPUS.md)
- Runtime RAG modules: [`rag/README.md`](../rag/README.md)
