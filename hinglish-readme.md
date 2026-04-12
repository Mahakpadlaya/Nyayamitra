# NyayaMitra — Hinglish explainer (dosto ke liye)

> **Goal:** 5 minute me samajh lo ye project **actually** kya kar raha hai — bina heavy jargon ke. Official SRS-style doc ke liye `README.md` dekho.

---

## Ye hai kya?

**NyayaMitra** ek chhota **legal study helper** hai — mainly **Indian Constitution + related legal topics** educational angle se.

- Tum **sawal** puchho (normal language me).
- System pehle apne **database se relevant paragraphs dhundhta hai** (ye step ka naam hai **RAG = retrieval**).
- Phir agar tumne **API key** lagayi hai (Groq / Gemini / OpenAI), to ek **AI model** un paragraphs ko padh ke **simple answer** banata hai.
- Agar **key nahi** hai, tab bhi app chalti hai — bas tumhe **dhunde hue excerpts** dikhte hain (context-only mode).

**Important:** Ye **lawyer ki jagah nahi** hai. Real case / police / court matter ho to **qualified advocate** se baat karna hi sahi hai. App me disclaimer bhi isi liye hai.

---

## User ko kya dikhta hai? (Frontend)

- **Chat tab:** WhatsApp jaisa feel — tum messages bhejte ho, **NyayaMitra** reply karta hai. Ye backend pe `/api/chat` jaata hai.
- **Action plan tab:** Ek lamba situation likh ke **structured plan** maang sakte ho — jaise “samajh lo kya framework relevant hai, kya info collect karni chahiye, next steps kya ho sakte hain”. Ye `/api/plan` hai.

Upar header me **health** se pata chalta hai:

- Kitne **chunks** index hue hain (Chroma count).
- **LLM on hai ya nahi** (keys lagi hain ya nahi).

---

## Andar se flow (simple)

1. **Tum browser se question bhejte ho** → React app → FastAPI backend.
2. Backend **Chroma vector DB** me search karta hai: “is question se similar text kaun sa pada hai?”
3. Jo **top k** paragraphs mile, unko **prompt** me daalta hai: “bas inhi lines se answer do, bakwas invent mat karo” type instructions `rag/prompts.py` me likhi hain.
4. **LLM** (agar configured hai) final answer likhta hai; **warna** sirf retrieved text return hota hai.

**Extra smartness:** `rag/retrieval.py` me kuch **keywords** (jaise POCSO, bail, IPC/BNS) detect ho to ranking thodi adjust hoti hai taaki chhote primer chunks ignore na ho jayein — practical college-project touch.

---

## DFD seedha simple

**Level 0 (duniya ka view):**

- **Tum** ↔ **NyayaMitra**
- **NyayaMitra** ↔ **Chroma** (local search)
- **NyayaMitra** ↔ **LLM company** (optional internet call)

**Data pipeline (jab tum index banana chahte ho):**

- Raw files (`data/raw/*.jsonl`, optional JSON datasets)  
  → script `prepare_rag_chunks.py` se **chunks** banate hain (`data/chunks/rag_chunks.jsonl`)  
  → `ingest_chroma.py` unko **embed** karke `chroma_db/` me daal deta hai.

Matlab: **pehle knowledge book banayi**, phir usi book se **open-book exam** style answer.

---

## Tech stack (ek line each)

| Cheez | Kyun |
|-------|------|
| **FastAPI** | Python me fast REST API — `/health`, `/api/chat`, `/api/plan`, `/api/ask`. |
| **Chroma** | Local vector DB — demo laptop pe bhi chal jaaye. |
| **SentenceTransformers** | Text ko numbers (embeddings) me convert karke similarity search. |
| **React + Vite** | UI fast dev ke liye; `/api` proxy se backend se baat. |

---

## Chalana kaise hai? (short)

1. `python -m venv .venv` → activate → `pip install -r requirements.txt`
2. `.env.example` ko copy karke `.env` banao; free key ke liye **Groq** ya **Gemini** achha option.
3. Agar `chroma_db` empty / missing ho to README wale **rebuild** commands chala lo (`prepare_rag_chunks` + `ingest_chroma`).
4. Backend: `uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000`
5. Frontend: `cd frontend` → `npm install` → `npm run dev` → browser `http://localhost:5173`

Agar UI bolta hai **API unreachable** — matlab backend start nahi hua ya port galat hai.

---

## Viva / presentation me kya bolna catchy hai?

- “Humne **hallucination kam karne** ke liye **RAG** use kiya: model pehle **evidence paragraphs** dekhta hai.”
- “**Structured plan endpoint** humne isliye rakha taaki answer **JSON fields** me aaye — UI friendly + demo clear.”
- “**Context-only fallback** isliye taaki markers / judges ko bina paid keys ke bhi **retrieval pipeline** dikh jaaye.”

---

## Files jahan “asli logic” hai

| File | Feel |
|------|------|
| `backend/main.py` | Sab routes — ask, chat, plan, health. |
| `rag/chroma_store.py` | Chroma client + collection name. |
| `rag/retrieval.py` | Search + rerank tricks. |
| `rag/prompts.py` | System prompts + disclaimer text. |
| `rag/chat.py` | Chat history se retrieval query kaise banega. |
| `scripts/prepare_rag_chunks.py` | Raw → chunks. |
| `scripts/ingest_chroma.py` | Chunks → vector DB. |
| `frontend/src/App.jsx` | Tabs + health pills. |
| `frontend/src/api.js` | `fetch` calls. |

---

## Last line

**NyayaMitra = local legal-ish knowledge base + optional LLM polish.**  
Serious legal strategy ke liye **hamesha insaan expert** — yahan padhai aur demo ke liye tool hai.

Agar tum chaaho to next step me hum **ek slide outline** (Introduction → Arch → DFD → Demo → Limitations) bhi bana sakte hain — bol dena.
