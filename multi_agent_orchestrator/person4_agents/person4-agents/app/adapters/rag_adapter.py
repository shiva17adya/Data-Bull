"""
Retrieval boundary.

The vector database is owned by another teammate. The Fundamental Agent only
consumes whatever chunks come back through this interface and cites them.
Empty retrieval is a valid, expected outcome — never a reason to invent text.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

MOCK_PATH = Path(__file__).resolve().parents[2] / "mocks" / "rag_response.json"


@runtime_checkable
class RAGProvider(Protocol):
    """Returns retrieved document chunks for a symbol/query.

    Expected shape:

        {
          "query": "RELIANCE Q3 FY26 results risks and outlook",
          "chunks": [
            {
              "source": "RELIANCE_Q3_FY26_earnings_call.pdf",
              "section": "Management Commentary",
              "text": "Consolidated EBITDA rose 11.4% year on year ...",
              "score": 0.91
            }
          ],
          "retrieval_status": "ok"
        }

    `chunks: []` means no relevant evidence exists.
    """

    async def retrieve(self, symbol: str, query: str = "", k: int = 6) -> dict[str, Any]:
        ...


class MockRAGProvider:
    """Loads `mocks/rag_response.json`."""

    def __init__(
        self,
        path: str | Path = MOCK_PATH,
        override: dict[str, Any] | None = None,
        key: str = "RELIANCE",
    ):
        self.path = Path(path)
        self.override = override
        self.key = key

    async def retrieve(self, symbol: str, query: str = "", k: int = 6) -> dict[str, Any]:
        if self.override is not None:
            return self.override
        with self.path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        payload = data.get(symbol.upper(), data.get(self.key, {"chunks": []}))
        chunks = payload.get("chunks", [])[:k]
        return {**payload, "chunks": chunks}


class EmptyRAGProvider:
    """Degraded-data scenario B: corpus returns nothing relevant."""

    async def retrieve(self, symbol: str, query: str = "", k: int = 6) -> dict[str, Any]:
        return {"query": query, "chunks": [], "retrieval_status": "no_match"}


class StaticRAGProvider:
    """Wraps an already-retrieved context dict (used by `analyze`)."""

    def __init__(self, payload: dict[str, Any] | None):
        self.payload = payload or {"chunks": []}

    async def retrieve(self, symbol: str, query: str = "", k: int = 6) -> dict[str, Any]:
        return self.payload
