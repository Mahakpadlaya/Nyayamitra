# `rag/` — Retrieval-Augmented Generation layer

This folder holds everything the **FastAPI** app uses to talk to **ChromaDB**, **shape prompts**, and **validate** API payloads. Offline ingestion (`scripts/ingest_chroma.py`) imports from here too so the same embedding model and collection name are used everywhere.

---

## File overview

| File | Role |
|------|------|
| [`__init__.py`](#__init__py) | Package marker + short description |
| [`chroma_store.py`](#chroma_storepy) | Chroma client, collection, embeddings, metadata helpers |
| [`retrieval.py`](#retrievalpy) | Semantic search + reranking on top of Chroma |
| [`prompts.py`](#promptspy) | System/user prompts and disclaimers for ask / plan / chat |
| [`schemas.py`](#schemaspy) | Pydantic models (`LegalGuidancePlan`, `ChatMessageIn`) |
| [`chat.py`](#chatpy) | Multi-turn chat: build retrieval query from message history |

---

## `__init__.py`

Marks `rag` as a Python package. Docstring: *RAG utilities: Chroma persistence, retrieval helpers.*

---

## `chroma_store.py`

**Purpose:** Single place for **vector store configuration** shared by the API and ingest scripts.

**What it defines**

- **`ROOT`** — Project root (parent of `rag/`), used to resolve `chroma_db/`.
- **`DEFAULT_CHROMA_PATH`** — Persistent Chroma directory on disk (`…/chroma_db`).
- **`DEFAULT_COLLECTION_NAME`** — Collection name (`legal_rag`).
- **`DEFAULT_EMBEDDING_MODEL`** — `all-MiniLM-L6-v2` (SentenceTransformers; downloads on first use).

**Main functions**

- **`embedding_function()`** — Builds the embedding function Chroma uses for query and ingest.
- **`get_client()`** — `chromadb.PersistentClient` for a given (or default) persist path.
- **`get_collection()`** — `get_or_create_collection` with the embedding function above.
- **`jsonl_record_to_chroma_metadata()`** — Turns a chunk JSONL row into Chroma-safe metadata (strings, numbers, bools; nested values JSON-serialized).
- **`query_collection()`** — Thin wrapper around `collection.query(...)` for a plain top-k search (the API uses `retrieval.query_collection_reranked` instead).

---

## `retrieval.py`

**Purpose:** Improve **which Chroma chunks** win after semantic search. Plain vector search can rank generic Q&A rows above small “primer” chunks when users type short keywords (e.g. POCSO, IPC).

**Main entry point**

- **`query_collection_reranked(collection, question, k=...)`**  
  1. Runs a **wider** Chroma query (`n_results` larger than `k`).  
  2. Detects **topic triggers** from the question (regex-based: POCSO, rape/375/376, murder/bail, IPC, BNS, etc.).  
  3. **Adjusts** a score per document (distance minus bonuses when document text matches triggers; slight preference for `criminal_law_primer` metadata when triggers fire).  
  4. Sorts and returns the **top k** hits.  
  5. For POCSO triggers, may **merge** in extra hits from a `where_document` `$contains` query so acronym-heavy queries still surface relevant chunks.

**Helpers** (internal): `_topic_triggers`, `_trigger_doc_bonus`, `_query_where_contains`, `_merge_query_results`.

**Used by:** `backend/main.py` for all `/api/ask`, `/api/plan`, and `/api/chat` retrieval.

---

## `prompts.py`

**Purpose:** All **LLM-facing text** for India-focused **educational** legal answers: system prompts, fixed disclaimer, and user prompt templates.

**Constants**

- **`STANDARD_DISCLAIMER`** — Not legal advice; consult a qualified advocate in India.
- **`ASK_SYSTEM`** — `/api/ask`: answer only from CONTEXT; no invented citations; append disclaimer; escalate on emergencies/police/criminal topics.
- **`PLAN_SYSTEM`** — `/api/plan`: structured plan only from CONTEXT; JSON shape guidance; practical generic steps.
- **`PLAN_JSON_INSTRUCTION`** — Exact JSON keys expected for structured plan output (for OpenAI-compatible `json_object` mode).
- **`CHAT_SYSTEM`** — `/api/chat`: use conversation history; answer latest user turn from CONTEXT only; disclaimer.

**Functions**

- **`ask_user_prompt(question, context_block)`** — Question + retrieved excerpts for ask-style calls.
- **`plan_user_prompt(question, context_block)`** — Same plus JSON instructions for plan.
- **`chat_user_prompt(history_block, latest_user_message, context_block)`** — History + latest turn + excerpts for chat.
- **`format_history_for_prompt(messages, exclude_last_user=...)`** — Turns `(role, content)` pairs into labeled lines for the chat prompt.

---

## `schemas.py`

**Purpose:** **Pydantic models** for request/response validation and structured output.

**Models**

- **`LegalGuidancePlan`** — Fields: `understanding`, `relevant_framework`, `information_you_should_gather`, `possible_next_steps`, `limits_and_risks`, `consult_lawyer_when`, `disclaimer`. Used by `/api/plan` and fallback parsing when the LLM returns malformed JSON.
- **`ChatMessageIn`** — `role` (`user` | `assistant`) and `content` (length limits). Used by `/api/chat` request body.

---

## `chat.py`

**Purpose:** Support **multi-turn** chat retrieval: one string must be built for Chroma even though the user sends many messages.

**Functions**

- **`normalize_messages(messages)`** — `ChatMessageIn` → list of `(role, content)` lowercase roles.
- **`retrieval_query_from_messages(messages, max_user_turns=4, max_chars=1200)`** — Concatenates the last N **user** messages into a single search string (trimmed by character count). Used as the Chroma query for `/api/chat`.
- **`latest_user_message(messages)`** — Last user content in the thread.
- **`validate_chat_messages(messages)`** — Ensures non-empty list, last message is `user`, returns normalized pairs + latest user text; raises `ValueError` otherwise.

**Used by:** `backend/main.py` before retrieval and before building the chat prompt.

---

## How these pieces connect

1. **`chroma_store`** opens the collection and (with ingest) fills it.  
2. **`retrieval`** runs **`query_collection_reranked`** on that collection.  
3. **`prompts`** formats context + instructions for the LLM (if keys are set).  
4. **`schemas`** validate chat input and plan output shape.  
5. **`chat`** turns a message list into one retrieval query for step 2.

For the offline pipeline (`prepare_rag_chunks` → `ingest_chroma`), only **`chroma_store`** (and ingest logic) is required; the rest is **runtime** on the API server.
