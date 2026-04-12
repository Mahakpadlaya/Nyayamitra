"""Shared Pydantic models for API responses (legal guidance plan)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class LegalGuidancePlan(BaseModel):
    """Structured educational guidance grounded in RAG context; not legal advice."""

    understanding: str = Field(
        ...,
        description="Short restatement of what the user is trying to figure out.",
    )
    relevant_framework: str = Field(
        ...,
        description="How retrieved excerpts relate (e.g. Constitution parts/articles, concepts).",
    )
    information_you_should_gather: list[str] = Field(
        default_factory=list,
        description="Generic, non-invasive items the user might collect before seeing counsel.",
    )
    possible_next_steps: list[str] = Field(
        default_factory=list,
        description="Ordered practical steps (documentation, legal aid, counsel, etc.).",
    )
    limits_and_risks: str = Field(
        ...,
        description="What the corpus does not cover; uncertainty; no invented citations.",
    )
    consult_lawyer_when: str = Field(
        ...,
        description="When to seek a qualified advocate (facts, urgency, criminal matters, etc.).",
    )
    disclaimer: str = Field(
        ...,
        description="Must state this is not legal advice and the assistant is not a lawyer.",
    )


class ChatMessageIn(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=16000)
