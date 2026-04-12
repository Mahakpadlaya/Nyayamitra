# NyayaMitra

NyayaMitra is a legal-assistant project with:
- **Backend:** FastAPI + RAG (ChromaDB)
- **Frontend:** React + Vite

This guide helps other developers run the project locally after cloning from GitHub.

## Prerequisites

- Python `3.11+` (tested with `3.12`)
- Node.js `18+` and npm
- macOS/Linux shell commands below (Windows users can adapt to PowerShell)

## 1) Clone and enter project

```bash
git clone <your-repo-url>
cd nyayamitra
```

## 2) Backend setup

Create and activate a Python virtual environment, then install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3) Environment variables

Create your `.env` file from the example:

```bash
cp .env.example .env
```

Then edit `.env` and add at least one provider key (recommended: `GROQ_API_KEY` or `GEMINI_API_KEY`).

If no key is set, the app can still run in context-only mode.

## 4) Vector DB options (Chroma)

This repo can include a refined prebuilt `chroma_db/` so new users can run quickly.

### Option A: Use the included/refined `chroma_db/` (fast start)

No ingestion step needed. Just run backend + frontend.

### Option B: Rebuild your own vector DB from scratch

From project root:

```bash
rm -rf chroma_db
source .venv/bin/activate
python scripts/prepare_rag_chunks.py --include-qa --include-criminal-primer --include-legal-vector-10k
python scripts/ingest_chroma.py
```

This recreates the local vector store in `chroma_db/`.

## 5) Run backend

From project root:

```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Backend URLs:
- API base: `http://127.0.0.1:8000`
- Health: `http://127.0.0.1:8000/health`

## 6) Run frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:
- `http://localhost:5173`

Vite is already configured to proxy `/api` and `/health` to backend `127.0.0.1:8000`.

## 7) Quick smoke test (optional)

```bash
source .venv/bin/activate
python scripts/smoke_api.py
```

## Important: include datasets and vector DB in GitHub

These files are project data and should be committed so others (and hosts like Render) have everything they need:

- `ai_legal_phase4_diverse.json`
- `legal_vector_dataset_10k.json`
- `data/raw/*.jsonl` (constitution + QA + criminal primer shards for `prepare_rag_chunks.py`)
- `data/chunks/rag_chunks.jsonl` (optional but speeds rebuilds; otherwise regenerate with the script)
- `chroma_db/` (refined vector DB; includes Chroma’s `*.sqlite3` files — `.gitignore` is set so those are not excluded)

You can add and commit them with:

```bash
git add README.md ai_legal_phase4_diverse.json legal_vector_dataset_10k.json data/raw chroma_db
# optional (skip if you will regenerate chunks on the server):
git add data/chunks/rag_chunks.jsonl
git commit -m "Add setup README and include required datasets and chroma DB"
git push
```

## Production deploy (Render + Vercel)

Deploy the **FastAPI backend** on [Render](https://render.com) and the **Vite React frontend** on [Vercel](https://vercel.com). The UI calls the API using `VITE_API_BASE_URL` (see [frontend/src/api.js](frontend/src/api.js)); locally that variable is unset so `/api` and `/health` still go through the Vite dev proxy.

### Backend (Render)

1. Push this repo to GitHub (include `chroma_db/` if you want RAG without running ingest on the server; see note above).
2. In Render: **New** → **Blueprint** (connect the repo and select `render.yaml`) **or** **Web Service** with:
   - **Root directory:** repository root (where `requirements.txt` lives).
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Python version:** `3.11+` (this repo includes [runtime.txt](runtime.txt) for Render’s native Python runtime).
3. **Environment variables** on the service (minimum for a working UI against prod API):
   - **`CORS_ORIGINS`** — comma-separated list including your **Vercel production URL** (e.g. `https://your-app.vercel.app`). Add `http://localhost:5173` if you want a local frontend to talk to the hosted API.
   - **`GROQ_API_KEY`** / **`GEMINI_API_KEY`** / **`OPENAI_API_KEY`** — optional; without them the API stays in context-only mode (see [.env.example](.env.example)).
4. After deploy, copy the service URL (e.g. `https://nyayamitra-api.onrender.com`). Check `https://<that-host>/health` in a browser.

Blueprint reference: [render.yaml](render.yaml) (secret keys use `sync: false` so Render prompts you when applying the blueprint).

**Free tier:** Services may spin down after idle time (cold starts). Chroma + `sentence-transformers` are memory-heavy; if the service crashes on startup, try a paid instance with more RAM or a smaller index.

### Frontend (Vercel)

1. **New Project** → import the same GitHub repo.
2. Set **Root Directory** to `frontend` (Vite app; [vercel.json](frontend/vercel.json) sets build/output).
3. Under **Environment Variables**, add **`VITE_API_BASE_URL`** = your Render URL **without** a trailing slash (e.g. `https://nyayamitra-api.onrender.com`). Redeploy after changing it.
4. Deploy. Open the Vercel URL; the header should load `/health` from Render and show chunk count when `chroma_db` is present on the server.

See [frontend/.env.example](frontend/.env.example) for a short reminder.

### Verify

- `GET https://<render-host>/health` returns JSON with `ok` and `chroma_documents`.
- Vercel app loads without CORS errors in the browser console; chat or plan returns a response.

## Common issues

- **Backend not starting:** check you used `--host 127.0.0.1 --port 8000` (host and port order matters).
- **Frontend shows proxy errors:** backend is not running on `127.0.0.1:8000`.
- **Missing API keys:** add provider keys in `.env` or use context-only mode.
- **Production CORS errors:** set `CORS_ORIGINS` on Render to your exact Vercel `https://…` origin (comma-separated if multiple).
- **Production UI cannot reach API:** set `VITE_API_BASE_URL` on Vercel to the Render URL and redeploy the frontend.
