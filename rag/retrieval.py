"""Widen + rerank Chroma hits so acronym / statute queries match primer chunks, not random Q&A."""
from __future__ import annotations

import re
from typing import Any

from chromadb import Collection


def _topic_triggers(question: str) -> list[str]:
    q = question.lower()
    out: list[str] = []
    if re.search(r"pocso|posco", q):
        out.append("pocso")
    if re.search(r"\brape\b|sexual assault|section\s*375|section\s*376", q):
        out.append("rape")
    if re.search(r"murder|homicide|culpable|section\s*302|section\s*304", q):
        out.append("murder")
    if re.search(r"\bbail\b|bailable|non[- ]bailable", q):
        out.append("bail")
    if re.search(r"\bipc\b|indian penal code", q):
        out.append("ipc")
    if re.search(r"\bbns\b|bharatiya nyaya|nyaya sanhita", q):
        out.append("bns")
    return out


def _trigger_doc_bonus(doc: str, triggers: list[str]) -> float:
    """Subtract from distance (lower is better in Chroma for cosine space)."""
    if not triggers:
        return 0.0
    d = doc.lower()
    bonus = 0.0
    if "pocso" in triggers and "pocso" in d:
        bonus += 0.35
    if "rape" in triggers and ("rape" in d or "375" in d or "376" in d):
        bonus += 0.35
    if "murder" in triggers and ("murder" in d or "302" in d or "culpable" in d):
        bonus += 0.35
    if "bail" in triggers and "bail" in d:
        bonus += 0.3
    if "ipc" in triggers and "ipc" in d:
        bonus += 0.2
    if "bns" in triggers and "bns" in d:
        bonus += 0.2
    return bonus


def _query_where_contains(
    collection: Collection,
    question: str,
    substring: str,
    *,
    n_results: int,
) -> dict[str, Any] | None:
    try:
        return collection.query(
            query_texts=[question.strip()],
            n_results=n_results,
            where_document={"$contains": substring},
        )
    except Exception:
        return None


def _merge_query_results(
    primary: dict[str, Any],
    extra: dict[str, Any] | None,
    *,
    k: int,
) -> dict[str, Any]:
    """Prepend rows from extra that are not already in primary (by id)."""
    if not extra:
        return primary
    e_ids_check = (extra.get("ids") or [[]])[0] or []
    e_docs_check = (extra.get("documents") or [[]])[0] or []
    if not e_ids_check and not e_docs_check:
        return primary
    p_ids = set((primary.get("ids") or [[]])[0] or [])
    e_docs = (extra.get("documents") or [[]])[0] or []
    e_meta = (extra.get("metadatas") or [[]])[0] or []
    e_dist = (extra.get("distances") or [[]])[0] or []
    e_ids = (extra.get("ids") or [[]])[0] or []

    merged_docs: list[str] = []
    merged_meta: list[Any] = []
    merged_dist: list[float] = []
    merged_ids: list[str] = []

    for i, eid in enumerate(e_ids):
        if eid and eid not in p_ids:
            merged_ids.append(eid)
            merged_docs.append(e_docs[i] if i < len(e_docs) else "")
            merged_meta.append(e_meta[i] if i < len(e_meta) else {})
            merged_dist.append(float(e_dist[i]) if i < len(e_dist) else 0.0)
            p_ids.add(eid)

    if not merged_ids:
        return primary

    p_docs = (primary.get("documents") or [[]])[0] or []
    p_meta = (primary.get("metadatas") or [[]])[0] or []
    p_dist = (primary.get("distances") or [[]])[0] or []
    p_ids_list = (primary.get("ids") or [[]])[0] or []

    all_docs = merged_docs + list(p_docs)
    all_meta = merged_meta + list(p_meta)
    all_dist = merged_dist + [float(x) for x in p_dist]
    all_ids = merged_ids + list(p_ids_list)

    return {
        "documents": [all_docs[:k]],
        "metadatas": [all_meta[:k]],
        "distances": [all_dist[:k]],
        "ids": [all_ids[:k]],
    }


def query_collection_reranked(
    collection: Collection,
    question: str,
    *,
    k: int,
    fetch_multiplier: int = 8,
    min_fetch: int = 32,
    max_fetch: int = 100,
) -> dict[str, Any]:
    """
    Run semantic search on a wider pool, then rerank by substring overlap with
    detected topics (POCSO, murder, rape, bail, IPC/BNS). Fixes cases where
    generic Q&A rows outrank small primer chunks.
    """
    q = question.strip()
    triggers = _topic_triggers(q)
    try:
        n = collection.count()
    except Exception:
        n = max_fetch
    want = min(max(k * fetch_multiplier, min_fetch), max_fetch, max(n, k))

    raw = collection.query(query_texts=[q], n_results=want)
    docs_list = (raw.get("documents") or [[]])[0]
    meta_list = (raw.get("metadatas") or [[]])[0]
    dist_list = (raw.get("distances") or [[]])[0]
    id_list = (raw.get("ids") or [[]])[0]

    if not docs_list:
        return raw

    scored: list[tuple[float, int]] = []
    for i, text in enumerate(docs_list):
        dist = float(dist_list[i]) if i < len(dist_list) else 1.0
        adj = dist - _trigger_doc_bonus(text or "", triggers)
        # Prefer criminal primer when triggers fired and chunk is primer
        if triggers and i < len(meta_list):
            meta = meta_list[i] or {}
            kind = str(meta.get("kind", ""))
            if kind == "criminal_law_primer":
                adj -= 0.08 * len(triggers)
        scored.append((adj, i))

    scored.sort(key=lambda x: x[0])
    pick = scored[:k]

    new_docs: list[str] = []
    new_meta: list[Any] = []
    new_dist: list[float] = []
    new_ids: list[str] = []
    for _adj, i in pick:
        new_docs.append(docs_list[i])
        new_meta.append(meta_list[i] if i < len(meta_list) else {})
        new_dist.append(float(dist_list[i]) if i < len(dist_list) else 0.0)
        new_ids.append(id_list[i] if i < len(id_list) else "")

    out: dict[str, Any] = {
        "documents": [new_docs],
        "metadatas": [new_meta],
        "distances": [new_dist],
        "ids": [new_ids],
    }

    # Hard guarantee when users type acronyms: semantic search often misses tiny primers.
    if "pocso" in triggers:
        filtered = _query_where_contains(collection, q, "POCSO", n_results=k)
        # Prepend POCSO-tagged chunks, then fill from reranked pool up to k.
        out = _merge_query_results(out, filtered, k=k)

    return out
