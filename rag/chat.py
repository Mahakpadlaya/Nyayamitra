"""Helpers for multi-turn chat: retrieval query from message history."""
from __future__ import annotations

from rag.schemas import ChatMessageIn


def normalize_messages(messages: list[ChatMessageIn]) -> list[tuple[str, str]]:
    return [(m.role.strip().lower(), m.content.strip()) for m in messages]


def retrieval_query_from_messages(
    messages: list[tuple[str, str]],
    *,
    max_user_turns: int = 4,
    max_chars: int = 1200,
) -> str:
    """
    Build a single search string from recent user turns (newest last).
    Cheap heuristic: concatenate last N user contents.
    """
    user_parts = [content for role, content in messages if role == "user"]
    recent = user_parts[-max_user_turns:] if len(user_parts) > max_user_turns else user_parts
    q = " ".join(recent).strip()
    if len(q) > max_chars:
        return q[:max_chars]
    return q


def latest_user_message(messages: list[tuple[str, str]]) -> str | None:
    for role, content in reversed(messages):
        if role == "user":
            return content
    return None


def validate_chat_messages(messages: list[ChatMessageIn]) -> tuple[list[tuple[str, str]], str]:
    """
    Returns normalized messages and latest user text.
    Raises ValueError if invalid.
    """
    if not messages:
        raise ValueError("messages must not be empty")
    pairs = normalize_messages(messages)
    last_role = pairs[-1][0]
    if last_role != "user":
        raise ValueError("last message must have role user")
    latest = latest_user_message(pairs)
    if not latest:
        raise ValueError("at least one user message is required")
    return pairs, latest
###ye jo chat krte iuska backend h