"""Shared fixtures. All tests run fully offline against the mocks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

MOCKS = Path(__file__).resolve().parents[1] / "mocks"


def _load(name: str) -> dict:
    with (MOCKS / name).open(encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="session")
def market_fixtures() -> dict:
    return _load("market_data.json")


@pytest.fixture(scope="session")
def rag_fixtures() -> dict:
    return _load("rag_response.json")


@pytest.fixture(scope="session")
def profile_fixtures() -> dict:
    return _load("user_profile.json")


@pytest.fixture
def market_data(market_fixtures) -> dict:
    return market_fixtures["RELIANCE"]


@pytest.fixture
def market_data_degraded(market_fixtures) -> dict:
    return market_fixtures["RELIANCE_DEGRADED"]


@pytest.fixture
def rag_context(rag_fixtures) -> dict:
    return rag_fixtures["RELIANCE"]


@pytest.fixture
def rag_context_empty(rag_fixtures) -> dict:
    return rag_fixtures["RELIANCE_EMPTY"]


@pytest.fixture
def rag_context_bearish(rag_fixtures) -> dict:
    return rag_fixtures["RELIANCE_BEARISH"]


@pytest.fixture
def conservative_profile(profile_fixtures) -> dict:
    return profile_fixtures["demo_conservative"]


@pytest.fixture
def aggressive_profile(profile_fixtures) -> dict:
    return profile_fixtures["demo_aggressive"]
