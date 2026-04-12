# Extending the legal corpus (India)

This project indexes **JSONL** files under `data/raw/`, builds `data/chunks/rag_chunks.jsonl`, and ingests into **Chroma** (`chroma_db/`). Default sources are pulled by [`scripts/fetch_constitution_corpus.py`](../scripts/fetch_constitution_corpus.py) from Hugging Face datasets (see that file for dataset IDs).

## Knowledge (RAG) vs behaviour (SFT) — keep the *roles* separate

| Role | Typical data | Use |
|------|----------------|-----|
| **Knowledge** | Law snippets, constitution, `legal_vector_dataset_10k.json` | **RAG** — retrieve into the prompt as `CONTEXT` |
| **Behaviour / style** | Phase 4 chat JSON (`messages` turns) | **Fine-tuning** (LoRA/SFT) — how to structure answers, tone, safety |

- **Do not** fine-tune on the 10k vector file as if it were chat, unless you first convert it into proper instruction format on purpose.
- **Do** run retrieval over the 10k file, then let the base model (or your Phase 4–tuned model) **synthesize** the answer from retrieved context.
- **Optional:** you *may* also index Phase 4 dialogues in Chroma (`--include-phase4`) for extra retrieval signal; many teams **skip** that and use Phase 4 **only** for training so RAG stays “facts” and the model stays “style”.

## `legal_vector_dataset_10k.json` (knowledge for RAG)

JSON **array** of objects with fields like `id`, `law`, `section`, `title`, `content`, `simple_explanation`, `when_it_applies`, `example`, `keywords`, `domain`.

```bash
python scripts/prepare_rag_chunks.py --include-qa --include-criminal-primer --include-legal-vector-10k
python scripts/ingest_chroma.py --reset
```

- **`--legal-vector-json PATH`** if the file is not at the project root default name.
- Indexed chunks use **`kind: legal_vector_kb`** (separate from **`phase4_chat`**).

## Licensing and responsibility

- Only add text you have the **right to copy and redistribute** (public domain, open licence, or your own materials).
- **Do not** scrape paywalled databases or republish restricted case law without permission.
- Dataset licences vary; read each dataset’s card on Hugging Face (or your source) before production use.

## Phase 4 chat dataset (SFT primary; RAG optional)

JSON **array** of `{ "id", "domain", "messages": [ {"role": "system"|"user"|"assistant", "content": "..."} ] }`.

**Primary use:** supervised fine-tuning (LoRA/SFT) so the model learns **structure, tone, and safety**.

**Optional RAG:** only if you explicitly want dialogues in the vector index:

```bash
python scripts/prepare_rag_chunks.py ... --include-phase4 --phase4-json /path/to/your_phase4.json
python scripts/ingest_chroma.py --reset
```

- Default Phase 4 path is set in [`scripts/prepare_rag_chunks.py`](../scripts/prepare_rag_chunks.py) (`DEFAULT_PHASE4_JSON`).
- **`system`** messages are omitted from embedded text; **user** / **assistant** turns become `User:` / `Assistant:` lines plus **`Domain:`**.

## Criminal law topics (murder, POCSO, IPC/BNS, bail)

The Constitution corpus alone will **not** reliably answer which **IPC/BNS section** applies, **POCSO**, or **bail** schedules. For a broader “assistant” demo, add educational statutory context:

- **Bundled primer:** `data/raw/indian_criminal_law_primer.jsonl` — short **non-authoritative** summaries (with disclaimers) for RAG grounding. Rebuild chunks with:

  ```bash
  python scripts/prepare_rag_chunks.py --include-qa --include-criminal-primer
  python scripts/ingest_chroma.py --reset
  ```

- **Production-quality answers:** index **official bare-act text** (India Code PDFs → `scripts/pdf_to_jsonl.py`) so retrieval cites real sections, not summaries.

## Adding your own JSONL

1. Create a file under `data/raw/`, e.g. `my_act.jsonl`.
2. Each line should be a JSON object. Prefer a shape compatible with [`scripts/prepare_rag_chunks.py`](../scripts/prepare_rag_chunks.py):

   - **Plain text documents:** `id`, `source`, `text`, optional `metadata` object.
   - **Q&A rows:** `id`, `source`, `question`, `answer` (use `prepare_rag_chunks.py --include-qa` only for the bundled QA file name, or extend the script to include your file).

3. Merge into chunks:

   ```bash
   cd /path/to/nyayamitra
   source .venv/bin/activate
   # Edit prepare_rag_chunks.py to load your file, or append your rows into an existing raw JSONL.
   python scripts/prepare_rag_chunks.py
   ```

4. Re-ingest (destructive reset replaces the collection):

   ```bash
   python scripts/ingest_chroma.py --reset
   ```

## PDFs and bare acts

To add a PDF:

1. Extract text with `pypdf` (already in `requirements.txt`) into one text or JSONL file with stable `source` metadata (e.g. act name and year).
2. Split long files into logical sections in metadata (`section`, `part`) to improve citations in retrieval.
3. Run `prepare_rag_chunks.py` and `ingest_chroma.py --reset` as above.

## Optional: PDF → JSONL helper

Use [`scripts/pdf_to_jsonl.py`](../scripts/pdf_to_jsonl.py) to extract text from PDFs into JSONL (one record per file). Then wire that file into [`scripts/prepare_rag_chunks.py`](../scripts/prepare_rag_chunks.py) or merge rows into an existing raw JSONL before chunking.
