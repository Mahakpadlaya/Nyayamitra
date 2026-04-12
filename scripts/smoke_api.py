#!/usr/bin/env python3
"""
Smoke-test API routes without starting uvicorn (uses FastAPI TestClient).

Uses a mocked Chroma collection so the script runs offline (no embedding model download).

Usage from project root:
  cd /path/to/nyayamitra
  source .venv/bin/activate
  python scripts/smoke_api.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _mock_collection() -> MagicMock:
    col = MagicMock()
    col.count.return_value = 2

    def _query(*_args: object, **_kwargs: object) -> dict:
        return {
            "documents": [
                [
                    "Article 14 — The State shall not deny to any person equality before the law "
                    "or the equal protection of the laws within the territory of India.",
                    "Article 21 — No person shall be deprived of his life or personal liberty "
                    "except according to procedure established by law.",
                ]
            ],
            "metadatas": [[{"source": "smoke_test", "kind": "constitution"}, {"source": "smoke_test", "kind": "constitution"}]],
            "distances": [[0.05, 0.12]],
            "ids": [["smoke_a14", "smoke_a21"]],
        }

    col.query.side_effect = _query
    return col


def main() -> int:
    import backend.main as bm
    from fastapi.testclient import TestClient

    bm._collection.cache_clear()
    mock_col = _mock_collection()

    with patch.object(bm, "get_collection", return_value=mock_col):
        bm._collection.cache_clear()
        client = TestClient(bm.app)

        h = client.get("/health")
        ok = 200 <= h.status_code < 300
        print("GET /health", h.status_code, h.json() if ok else h.text)
        if not ok:
            return 1

        body_plan = {"question": "What are Fundamental Rights under the Constitution of India?"}
        p = client.post("/api/plan", json=body_plan)
        print("POST /api/plan", p.status_code)
        if p.status_code == 200:
            data = p.json()
            assert "plan" in data and "sources" in data and "mode" in data
            plan = data["plan"]
            for key in (
                "understanding",
                "relevant_framework",
                "information_you_should_gather",
                "possible_next_steps",
                "limits_and_risks",
                "consult_lawyer_when",
                "disclaimer",
            ):
                assert key in plan, f"missing plan key: {key}"
            print("  plan keys ok; mode=", data.get("mode"))
        else:
            print(p.text)
            return 1

        body_chat = {
            "messages": [
                {"role": "user", "content": "What is Article 14 about?"},
                {"role": "assistant", "content": "It concerns equality before the law; details depend on context."},
                {"role": "user", "content": "How does it relate to reasonable classification?"},
            ]
        }
        c = client.post("/api/chat", json=body_chat)
        print("POST /api/chat", c.status_code)
        if c.status_code == 200:
            chat = c.json()
            assert "answer" in chat and "sources" in chat and "mode" in chat
            print("  chat keys ok; mode=", chat.get("mode"))
        else:
            print(c.text)
            return 1

        bad = client.post("/api/chat", json={"messages": [{"role": "assistant", "content": "only assistant"}]})
        print("POST /api/chat (expect 400)", bad.status_code)
        if bad.status_code != 400:
            print(bad.text)
            return 1

    print("smoke_api: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
