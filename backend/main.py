"""
FastAPI app: RAG over Chroma + optional LLM synthesis (OpenAI, Groq, or Gemini).
Run from project root:
  cd nyayamitra && source .venv/bin/activate
  uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chromadb import Collection  # noqa: E402
from openai import OpenAI  # noqa: E402

from rag.chat import retrieval_query_from_messages, validate_chat_messages  # noqa: E402
from rag.chroma_store import get_collection  # noqa: E402
from rag.retrieval import query_collection_reranked  # noqa: E402
from rag import prompts  # noqa: E402
from rag.schemas import ChatMessageIn, LegalGuidancePlan  # noqa: E402

LLMChoice = Literal["auto", "openai", "groq", "gemini", "context_only"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Provider: auto picks first available key in order groq → gemini → openai
    llm_provider: LLMChoice = "auto"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    groq_api_key: str | None = None
    groq_model: str = "llama-3.1-8b-instant"

    gemini_api_key: str | None = None
    # 1.5 IDs are often removed from v1beta; use current stable IDs from:
    # https://ai.google.dev/gemini-api/docs/models/gemini
    gemini_model: str = "gemini-2.5-flash"

    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    rag_top_k: int = 5

    @field_validator(
        "openai_api_key",
        "groq_api_key",
        "gemini_api_key",
        mode="before",
    )
    @classmethod
    def empty_key_none(cls, v: object) -> object:
        if v == "":
            return None
        return v

    @field_validator("llm_provider", mode="before")
    @classmethod
    def normalize_provider(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip().lower()
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


def _parse_origins(s: str) -> list[str]:
    return [o.strip() for o in s.split(",") if o.strip()]


@lru_cache
def _collection() -> Collection:
    return get_collection()


app = FastAPI(title="NyayaMitra API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_origins(get_settings().cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Source(BaseModel):
    text: str
    metadata: dict = Field(default_factory=dict)
    distance: float | None = None


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=8000)
    k: int | None = Field(default=None, ge=1, le=20)


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    mode: str  # openai | groq | gemini | context_only


class PlanRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=8000)
    k: int | None = Field(default=None, ge=1, le=20)


class PlanResponse(BaseModel):
    plan: LegalGuidancePlan
    sources: list[Source]
    mode: str


class ChatRequest(BaseModel):
    messages: list[ChatMessageIn] = Field(..., min_length=1)
    k: int | None = Field(default=None, ge=1, le=20)


def _retrieve(question: str, k: int) -> tuple[list[Source], dict]:
    col = _collection()
    try:
        count = col.count()
    except Exception:
        count = 0
    if count == 0:
        raise HTTPException(
            status_code=503,
            detail="Vector store is empty. Run: python scripts/prepare_rag_chunks.py && python scripts/ingest_chroma.py --reset",
        )
    raw = query_collection_reranked(col, question, k=k)
    docs_list = (raw.get("documents") or [[]])[0]
    meta_list = (raw.get("metadatas") or [[]])[0]
    dist_list = (raw.get("distances") or [[]])[0]
    sources: list[Source] = []
    for i, text in enumerate(docs_list):
        meta = dict(meta_list[i]) if meta_list and i < len(meta_list) else {}
        dist = float(dist_list[i]) if dist_list and i < len(dist_list) else None
        sources.append(Source(text=text, metadata=meta, distance=dist))
    return sources, raw


def _context_block(sources: list[Source]) -> str:
    parts = []
    for i, s in enumerate(sources, 1):
        parts.append(f"[Excerpt {i}]\n{s.text.strip()}")
    return "\n\n".join(parts)


def _system_and_user_prompts(question: str, sources: list[Source]) -> tuple[str, str]:
    context = _context_block(sources)
    return prompts.ASK_SYSTEM, prompts.ask_user_prompt(question, context)


def _answer_context_only(sources: list[Source], question: str) -> str:
    if not sources:
        return "No matching passages were found in the corpus."
    ctx = _context_block(sources)
    return (
        "**No LLM API key configured** — showing retrieved passages only.\n\n"
        f"**Your question:** {question}\n\n"
        f"**Retrieved context:**\n\n{ctx}\n\n"
        "_Add a free key to `.env`: **`GROQ_API_KEY`** ([groq.com](https://console.groq.com)) "
        "or **`GEMINI_API_KEY`** ([Google AI Studio](https://aistudio.google.com)), "
        "or paid **`OPENAI_API_KEY`**._"
    )


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        out = json.loads(text)
        if isinstance(out, dict):
            return out
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if m:
        out = json.loads(m.group(1))
        if isinstance(out, dict):
            return out
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        out = json.loads(text[start : end + 1])
        if isinstance(out, dict):
            return out
    raise ValueError("Could not parse a JSON object from model output")


def _coerce_plan_dict(data: dict[str, Any]) -> dict[str, Any]:
    out = dict(data)
    for key in ("information_you_should_gather", "possible_next_steps"):
        val = out.get(key)
        if isinstance(val, str) and val.strip():
            out[key] = [val.strip()]
        elif val is None:
            out[key] = []
        elif not isinstance(val, list):
            out[key] = [str(val)]
    if not (out.get("disclaimer") or "").strip():
        out["disclaimer"] = prompts.STANDARD_DISCLAIMER
    return out


def _parse_plan_json(raw: str, question: str) -> LegalGuidancePlan:
    try:
        data = _coerce_plan_dict(_extract_json_object(raw))
        return LegalGuidancePlan.model_validate(data)
    except (json.JSONDecodeError, ValueError) as e:
        return LegalGuidancePlan(
            understanding=question,
            relevant_framework="The model did not return valid JSON.",
            information_you_should_gather=[],
            possible_next_steps=["Retry the request or switch LLM provider."],
            limits_and_risks=f"Parse error: {e!s}. Raw preview: {raw[:400]!r}",
            consult_lawyer_when="Consult a qualified advocate in India for any fact-specific, urgent, or criminal matter.",
            disclaimer=prompts.STANDARD_DISCLAIMER,
        )
    except Exception as e:  # noqa: BLE001 — validation or unexpected shape
        return LegalGuidancePlan(
            understanding=question,
            relevant_framework="The model output could not be validated as a legal guidance plan.",
            information_you_should_gather=[],
            possible_next_steps=["Retry with a shorter question or different model."],
            limits_and_risks=str(e),
            consult_lawyer_when="Consult a qualified advocate in India when in doubt.",
            disclaimer=prompts.STANDARD_DISCLAIMER,
        )


def _plan_context_only(sources: list[Source], question: str) -> LegalGuidancePlan:
    if not sources:
        return LegalGuidancePlan(
            understanding=question,
            relevant_framework="No matching passages were found in the corpus.",
            information_you_should_gather=[
                "Official text of the Constitution or relevant bare act from authoritative sources.",
            ],
            possible_next_steps=[
                "Run: python scripts/fetch_constitution_corpus.py",
                "Then: python scripts/prepare_rag_chunks.py && python scripts/ingest_chroma.py --reset",
                "For personal matters, consult a qualified lawyer in India.",
            ],
            limits_and_risks="The vector store is empty or retrieval returned nothing.",
            consult_lawyer_when="Always for fact-specific disputes, police action, or criminal issues.",
            disclaimer=prompts.STANDARD_DISCLAIMER + " (Retrieval-only mode; no excerpts.)",
        )
    ctx = _context_block(sources)
    return LegalGuidancePlan(
        understanding=question,
        relevant_framework=(
            "Closest retrieved excerpts from the indexed corpus (educational only):\n\n" + ctx
        ),
        information_you_should_gather=[
            "Relevant documents you already hold (notices, contracts, orders) if any.",
            "Approximate timeline and jurisdiction (state/forum) if you seek counsel later.",
        ],
        possible_next_steps=[
            "Read the excerpts above alongside authoritative sources (e.g. official Constitution text).",
            "Use POST /api/plan with an LLM API key in `.env` for a synthesized step list.",
            "Contact a qualified advocate or State Legal Services Authority for tailored advice.",
        ],
        limits_and_risks=(
            "**No LLM API key configured** — this response lists retrieved passages only and may be incomplete. "
            "See `.env.example` for GROQ_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY."
        ),
        consult_lawyer_when=(
            "Seek a qualified lawyer promptly for arrest/FIR, violence, strict deadlines, "
            "or any situation requiring case-specific strategy."
        ),
        disclaimer=prompts.STANDARD_DISCLAIMER + " (Retrieval-only mode.)",
    )


def _synthesize_openai_compatible(
    question: str,
    sources: list[Source],
    *,
    api_key: str,
    model: str,
    base_url: str,
) -> str:
    client = OpenAI(api_key=api_key, base_url=base_url)
    system, user = _system_and_user_prompts(question, sources)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=1024,
    )
    choice = resp.choices[0].message.content
    return (choice or "").strip()


def _synthesize_plan_openai_compatible(
    question: str,
    sources: list[Source],
    *,
    api_key: str,
    model: str,
    base_url: str,
) -> LegalGuidancePlan:
    client = OpenAI(api_key=api_key, base_url=base_url)
    context = _context_block(sources)
    user = prompts.plan_user_prompt(question, context)
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompts.PLAN_SYSTEM},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "max_tokens": 2048,
    }
    try:
        resp = client.chat.completions.create(
            **kwargs,
            response_format={"type": "json_object"},
        )
    except Exception:
        resp = client.chat.completions.create(**kwargs)
    raw = (resp.choices[0].message.content or "").strip()
    return _parse_plan_json(raw, question)


def _synthesize_openai(question: str, sources: list[Source], settings: Settings) -> str:
    return _synthesize_openai_compatible(
        question,
        sources,
        api_key=settings.openai_api_key,  # type: ignore[arg-type]
        model=settings.openai_model,
        base_url="https://api.openai.com/v1",
    )


def _synthesize_groq(question: str, sources: list[Source], settings: Settings) -> str:
    return _synthesize_openai_compatible(
        question,
        sources,
        api_key=settings.groq_api_key,  # type: ignore[arg-type]
        model=settings.groq_model,
        base_url="https://api.groq.com/openai/v1",
    )


def _synthesize_gemini(question: str, sources: list[Source], settings: Settings) -> str:
    try:
        import google.generativeai as genai  # type: ignore[import]
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail="google-generativeai is not installed. Run: pip install google-generativeai",
        ) from e

    system, user = _system_and_user_prompts(question, sources)
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)
    prompt = f"{system}\n\n{user}"
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            max_output_tokens=1024,
        ),
    )
    text = getattr(response, "text", None) or ""
    if not text.strip() and response.candidates:
        parts = response.candidates[0].content.parts
        text = "".join(getattr(p, "text", "") for p in parts)
    return text.strip()


def _synthesize_plan_gemini(question: str, sources: list[Source], settings: Settings) -> LegalGuidancePlan:
    try:
        import google.generativeai as genai  # type: ignore[import]
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail="google-generativeai is not installed. Run: pip install google-generativeai",
        ) from e

    context = _context_block(sources)
    user = prompts.plan_user_prompt(question, context)
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)
    prompt = f"{prompts.PLAN_SYSTEM}\n\n{user}"
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=2048,
                response_mime_type="application/json",
            ),
        )
    except Exception:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=2048,
            ),
        )
    text = getattr(response, "text", None) or ""
    if not text.strip() and response.candidates:
        parts = response.candidates[0].content.parts
        text = "".join(getattr(p, "text", "") for p in parts)
    return _parse_plan_json(text.strip(), question)


def _synthesize_chat_openai_compatible(
    history_block: str,
    latest_user: str,
    sources: list[Source],
    *,
    api_key: str,
    model: str,
    base_url: str,
) -> str:
    client = OpenAI(api_key=api_key, base_url=base_url)
    context = _context_block(sources)
    user = prompts.chat_user_prompt(history_block, latest_user, context)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompts.CHAT_SYSTEM},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=1536,
    )
    return (resp.choices[0].message.content or "").strip()


def _synthesize_chat_gemini(
    history_block: str,
    latest_user: str,
    sources: list[Source],
    settings: Settings,
) -> str:
    try:
        import google.generativeai as genai  # type: ignore[import]
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail="google-generativeai is not installed. Run: pip install google-generativeai",
        ) from e

    context = _context_block(sources)
    user = prompts.chat_user_prompt(history_block, latest_user, context)
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)
    prompt = f"{prompts.CHAT_SYSTEM}\n\n{user}"
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            max_output_tokens=1536,
        ),
    )
    text = getattr(response, "text", None) or ""
    if not text.strip() and response.candidates:
        parts = response.candidates[0].content.parts
        text = "".join(getattr(p, "text", "") for p in parts)
    return text.strip()


def _chat_context_only(sources: list[Source], history_block: str, latest_user: str) -> str:
    ctx = _context_block(sources) if sources else "(no excerpts)"
    return (
        "**No LLM API key configured** — conversation context and retrieved excerpts only.\n\n"
        f"**History (summary view):**\n{history_block}\n\n"
        f"**Latest message:** {latest_user}\n\n"
        f"**Retrieved context:**\n\n{ctx}\n\n"
        "_Configure **`GROQ_API_KEY`**, **`GEMINI_API_KEY`**, or **`OPENAI_API_KEY`** in `.env` for full replies._"
    )


def _resolve_backend(settings: Settings) -> Literal["groq", "gemini", "openai"] | None:
    p = settings.llm_provider
    if p == "context_only":
        return None

    def pick_auto() -> Literal["groq", "gemini", "openai"] | None:
        if settings.groq_api_key:
            return "groq"
        if settings.gemini_api_key:
            return "gemini"
        if settings.openai_api_key:
            return "openai"
        return None

    if p == "auto":
        return pick_auto()

    if p == "groq":
        return "groq" if settings.groq_api_key else None
    if p == "gemini":
        return "gemini" if settings.gemini_api_key else None
    if p == "openai":
        return "openai" if settings.openai_api_key else None
    return None


def _synthesize_plan_for_backend(
    backend: Literal["groq", "gemini", "openai"],
    question: str,
    sources: list[Source],
    settings: Settings,
) -> LegalGuidancePlan:
    if backend == "groq":
        return _synthesize_plan_openai_compatible(
            question,
            sources,
            api_key=settings.groq_api_key,  # type: ignore[arg-type]
            model=settings.groq_model,
            base_url="https://api.groq.com/openai/v1",
        )
    if backend == "openai":
        return _synthesize_plan_openai_compatible(
            question,
            sources,
            api_key=settings.openai_api_key,  # type: ignore[arg-type]
            model=settings.openai_model,
            base_url="https://api.openai.com/v1",
        )
    return _synthesize_plan_gemini(question, sources, settings)


@app.get("/health")
def health() -> dict:
    try:
        n = _collection().count()
    except Exception:
        n = -1
    s = get_settings()
    active = _resolve_backend(s)
    return {
        "ok": True,
        "chroma_documents": n,
        "llm_provider": active,
        "synthesis_enabled": active is not None,
        "openai_configured": active is not None,
        "keys_present": {
            "groq": bool(s.groq_api_key),
            "gemini": bool(s.gemini_api_key),
            "openai": bool(s.openai_api_key),
        },
    }


@app.post("/api/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    settings = get_settings()
    k = req.k if req.k is not None else settings.rag_top_k
    sources, _ = _retrieve(req.question.strip(), k=k)

    backend = _resolve_backend(settings)
    if backend is None:
        return AskResponse(
            answer=_answer_context_only(sources, req.question.strip()),
            sources=sources,
            mode="context_only",
        )

    try:
        if backend == "groq":
            answer = _synthesize_groq(req.question, sources, settings)
            mode = "groq"
        elif backend == "gemini":
            answer = _synthesize_gemini(req.question, sources, settings)
            mode = "gemini"
        else:
            answer = _synthesize_openai(req.question, sources, settings)
            mode = "openai"
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error ({backend}): {e!s}") from e

    return AskResponse(answer=answer, sources=sources, mode=mode)


@app.post("/api/plan", response_model=PlanResponse)
def plan(req: PlanRequest) -> PlanResponse:
    settings = get_settings()
    k = req.k if req.k is not None else settings.rag_top_k
    q = req.question.strip()
    sources, _ = _retrieve(q, k=k)

    backend = _resolve_backend(settings)
    if backend is None:
        return PlanResponse(
            plan=_plan_context_only(sources, q),
            sources=sources,
            mode="context_only",
        )

    try:
        plan_obj = _synthesize_plan_for_backend(backend, q, sources, settings)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error ({backend}): {e!s}") from e

    return PlanResponse(plan=plan_obj, sources=sources, mode=backend)


@app.post("/api/chat", response_model=AskResponse)
def chat(req: ChatRequest) -> AskResponse:
    settings = get_settings()
    try:
        pairs, latest_user = validate_chat_messages(req.messages)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    k = req.k if req.k is not None else settings.rag_top_k
    rq = retrieval_query_from_messages(pairs)
    sources, _ = _retrieve(rq, k=k)
    history_block = prompts.format_history_for_prompt(pairs, exclude_last_user=True)

    backend = _resolve_backend(settings)
    if backend is None:
        return AskResponse(
            answer=_chat_context_only(sources, history_block, latest_user),
            sources=sources,
            mode="context_only",
        )

    try:
        if backend == "groq":
            answer = _synthesize_chat_openai_compatible(
                history_block,
                latest_user,
                sources,
                api_key=settings.groq_api_key,  # type: ignore[arg-type]
                model=settings.groq_model,
                base_url="https://api.groq.com/openai/v1",
            )
            mode = "groq"
        elif backend == "gemini":
            answer = _synthesize_chat_gemini(history_block, latest_user, sources, settings)
            mode = "gemini"
        else:
            answer = _synthesize_chat_openai_compatible(
                history_block,
                latest_user,
                sources,
                api_key=settings.openai_api_key,  # type: ignore[arg-type]
                model=settings.openai_model,
                base_url="https://api.openai.com/v1",
            )
            mode = "openai"
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error ({backend}): {e!s}") from e

    return AskResponse(answer=answer, sources=sources, mode=mode)
