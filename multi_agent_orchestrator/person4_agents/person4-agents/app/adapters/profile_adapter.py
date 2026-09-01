"""
User profile boundary.

The user/portfolio database is owned by another teammate. The Risk Engine
consumes a plain profile dict through this interface.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

MOCK_PATH = Path(__file__).resolve().parents[2] / "mocks" / "user_profile.json"


@runtime_checkable
class ProfileProvider(Protocol):
    """Returns a user's risk profile and portfolio state.

    Expected shape:

        {
          "user_id": "demo_conservative",
          "risk_tolerance": "conservative",
          "investment_horizon": "long",
          "max_position_pct": 8.0,
          "concentration_score": 0.71,
          "cash_pct": 12.0,
          "holdings": [{"symbol": "RELIANCE", "weight_pct": 22.0}],
          "behavioral_flags": ["panic_seller"]
        }
    """

    async def get_profile(self, user_id: str) -> dict[str, Any]:
        ...


class MockProfileProvider:
    """Loads `mocks/user_profile.json` (contains demo_conservative + demo_aggressive)."""

    def __init__(self, path: str | Path = MOCK_PATH, override: dict[str, Any] | None = None):
        self.path = Path(path)
        self.override = override

    async def get_profile(self, user_id: str) -> dict[str, Any]:
        if self.override is not None:
            return self.override
        with self.path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get(user_id, data.get("demo_conservative", {"user_id": user_id}))


class StaticProfileProvider:
    """Wraps an already-loaded profile dict (used by `analyze`)."""

    def __init__(self, payload: dict[str, Any] | None):
        self.payload = payload or {}

    async def get_profile(self, user_id: str) -> dict[str, Any]:
        return self.payload
